"""批量修复 docstring — 只前置 docstring，不破坏已有内容"""
from pathlib import Path

base = Path(__file__).resolve().parent.parent / "flypig"
count = 0
skip = 0

# ── __init__.py：在文件头部前置 docstring ──
init_sections: dict[str, str] = {
    "application/__init__.py": "应用层 — 编排领域逻辑",
    "application/dto/__init__.py": "DTO 包 — 应用服务与接口层之间的数据契约",
    "domain/event/__init__.py": "领域事件包 — DomainEvent 和 EventHandler 的统一出口",
    "domain/interfaces/__init__.py": "领域接口包 — 所有 ABC 抽象接口的统一出口",
    "domain/specification/__init__.py": "规格模式包 — 可组合的业务规则",
    "infrastructure/event/__init__.py": "事件总线包",
    "infrastructure/usage/__init__.py": "用量与定价包",
    "orchestration/__init__.py": "编排层 — LangGraph Agent 状态图",
}

for rel_path, desc in init_sections.items():
    f = base / rel_path
    if not f.exists():
        continue
    content = f.read_text(encoding="utf-8")
    # 如果已有 docstring 就跳过
    if content.strip().startswith('"""') or content.strip().startswith("'''"):
        print(f"  skip (has doc): {rel_path}")
        skip += 1
        continue
    layer = rel_path.split("/")[0]
    new = f'"""{desc}\n\n层&依赖：{layer} 层\n"""\n\n{content}'
    f.write_text(new, encoding="utf-8")
    count += 1
    print(f"  fixed: {rel_path}")

# ── 兼容导入桩：如果完全空，加 docstring ──
stub_files = [
    "domain/message_id.py",
    "domain/session_id.py",
    "domain/session_status.py",
    "domain/tool_def.py",
    "domain/tool_result.py",
]

for rel_path in stub_files:
    f = base / rel_path
    if not f.exists():
        continue
    content = f.read_text(encoding="utf-8").strip()
    if not content:
        cls = rel_path.replace(".py", "").split("/")[-1]
        src_mod = rel_path.replace("_id.py", ".py").replace("_status.py", ".py").replace("_def.py", ".py").replace("_result.py", ".py").split("/")[-1].replace(".py", "")
        mod_path = "/".join(rel_path.split("/")[:-1])
        f.write_text(
            f'"""兼容导入 — {cls} 定义在 {src_mod} 中\n\n'
            f"层&依赖：domain 层\n"
            f'"""\n'
            f"from flypig.domain.{src_mod} import {cls}  # noqa: F401\n",
            encoding="utf-8",
        )
        count += 1
        print(f"  fixed: {rel_path}")

print(f"\nPatched: {count}, Skipped: {skip}")
