"""OpenTelemetry 初始化模块

为什么做：全链路追踪（HTTP 请求 → LangGraph 节点 → LLM 调用），每个环节自动生成 span，
      所有 span 串成一条 trace 送 Jaeger 可视化，debug 时不用再猜数据在哪丢的。

实现方法：init_otel() 配置 OTLP HTTP exporter → localhost:4318（Jaeger all-in-one），
         BatchSpanProcessor 异步批量发送，collector 不可用时静默丢弃不影响主流程。

环境变量：
  OTEL_EXPORTER_OTLP_ENDPOINT: OTLP collector 地址（默认 http://localhost:4318/v1/traces）
  FLYPIG_OTEL_ENABLED: 设为 "0" 禁用（默认启用）

层&依赖：bootstrap 层，被 app_factory.py 在 create_app() 中调用
"""

from __future__ import annotations

import os

from loguru import logger as _log
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_tracer: trace.Tracer | None = None
_initialized: bool = False


def _is_enabled() -> bool:
    return os.getenv("FLYPIG_OTEL_ENABLED", "1") != "0"


def init_otel(service_name: str = "flypig") -> trace.Tracer:
    """初始化 OpenTelemetry SDK

    配置 OTLP exporter 连接到 Jaeger/Collector。
    collector 不可用时 BatchSpanProcessor 静默丢弃 span 不会抛异常。
    FLYPIG_OTEL_ENABLED=0 可完全禁用。

    Args:
        service_name: 服务名，显示在 Jaeger UI 中

    Returns:
        trace.Tracer 实例
    """
    global _tracer, _initialized

    if _initialized:
        return _tracer  # type: ignore[return-value]

    _initialized = True

    if not _is_enabled():
        _log.info("OTel 追踪已禁用 (FLYPIG_OTEL_ENABLED=0)")
        _tracer = trace.get_tracer(__name__)
        return _tracer

    otlp_endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_ENDPOINT",
        "http://localhost:4318/v1/traces",
    )

    resource = Resource.create({SERVICE_NAME: service_name})
    provider = TracerProvider(resource=resource)

    exporter = OTLPSpanExporter(endpoint=otlp_endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)

    _tracer = trace.get_tracer(__name__)
    _log.info("OTel 追踪已启用 -> {}", otlp_endpoint)

    return _tracer


def get_tracer() -> trace.Tracer:
    """获取 OTel tracer（未初始化时自动初始化）"""
    global _tracer
    if _tracer is None:
        _tracer = init_otel()
    return _tracer
