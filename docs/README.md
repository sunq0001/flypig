# FlyPig - AI Coding Agent

轻量级 AI 编程助手，支持多模型、自动价格感知。

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行（首次使用会提示录入 API Key）
python -m flypig
```

## 使用流程

```
启动 → 选择模型 → 自动获取价格 → 开始对话
                         ↓
             在线抓取成功 → 显示官方价
             在线失败     → 显示内置参考价
             都失败       → 提示无价格信息
```

## 配置

编辑 `config.yaml`：

```yaml
# 默认模型（从 model_registry.py 中选）
llm:
  default_model: deepseek-v4-flash

# API Key（按提供商，未设置则首次提示录入）
api_keys:
  DeepSeek:  "${DEEPSEEK_API_KEY}"
  OpenAI:    "${OPENAI_API_KEY}"
  Anthropic: "${ANTHROPIC_API_KEY}"
```

**配置即代码**：模型元数据（provider、base_url、env_key）定义在 `model_registry.py` 中，
只需在那里加一行，新模型即可在菜单中出现。

## 架构

```
flypig/
  ├── __init__.py          # 包标识
  ├── __main__.py          # 入口 (python -m flypig)
  ├── cli.py               # CLI 交互 + 模型选择 + 价格获取
  ├── config.py            # 配置加载（yaml + env var 解析）
  ├── config.yaml          # 用户配置（模型选择、API Key）
  ├── model_registry.py    # 模型注册表（名称 → 元数据映射）
  ├── pricing_fetcher.py   # 价格抓取（在线 > 内置参考表）
  ├── model.py             # LLM 模型适配器
  ├── agent.py             # Agent 核心循环
  ├── tools.py             # 工具集（文件/终端/搜索）
  └── cost.py              # Token 成本追踪
```

## 添加新模型

只需两步：

1. **`model_registry.py`** 的 `REGISTRY` 加一行：
```python
"my-model": {"provider": "DeepSeek", "base_url": "https://api.deepseek.com", "env_key": "DEEPSEEK_API_KEY"},
```

2. **`config.yaml`** 改 `default_model` 为新的名字

重启即可在菜单中看到。

## ModelAdapter 说明

当前 ModelAdapter 基于 OpenAI 兼容协议，支持：
- DeepSeek ✅
- OpenAI ✅
- 其他兼容 OpenAI 协议的 API（如 Groq、Together AI 等）

Anthropic 等非兼容协议需扩展 `model.py`。

## 命令

| 命令 | 说明 |
|------|------|
| `/help` | 帮助 |
| `/reset` | 重置对话 |
| `/cost` | 查看会话成本 |
| `/model` | 切换模型 |
| `/exit` | 退出 |
