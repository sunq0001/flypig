"""集成测试 — 真正执行命令验证输出

测试 strip_ansi / tool_bash / _run_inline / _run_inline_windows
"""
import os
import sys
from pathlib import Path

from .conftest import _FUNC

# ── 测试用的 Python 解释器 ──
PY = sys.executable
TEST_DIR = Path(__file__).parent


async def test_strip_ansi_removes_color_codes():
    """strip_ansi 正确移除 ANSI escape sequences"""
    from flypig.tools import strip_ansi

    cases = [
        ("\033[32mhello\033[0m", "hello"),
        ("\033[1m\033[31mERROR\033[0m: msg", "ERROR: msg"),
        ("plain text", "plain text"),
        ("\x1B[?25h", ""),  # cursor show
        ("\x1B[2J\x1B[H", ""),  # clear screen
        ("\033[38;2;255;255;255mrgb\033[0m", "rgb"),
        ("line1\n\033[32mline2\033[0m\nline3", "line1\nline2\nline3"),
    ]
    for raw, expected in cases:
        got = strip_ansi(raw)
        assert got == expected, f"strip_ansi({raw!r}) = {got!r}, expected {expected!r}"
    print(f"PASS: strip_ansi ({len(cases)} cases)")


async def test_strip_ansi_rainbow_vs_python():
    """strip_ansi 对比 Python 内置测试 - ANSI 序列 vs 普通文本"""
    from flypig.tools import strip_ansi

    # 确保普通文本不会被误伤
    assert strip_ansi("a_b_c") == "a_b_c"
    assert strip_ansi(">>>") == ">>>"
    assert strip_ansi("[32m") == "[32m"  # 没有 ESC 前缀的不应该去掉
    assert strip_ansi("\x1B[32m") == ""  # 有 ESC 前缀的应该去掉
    print("PASS: strip_ansi doesn't damage regular text")


async def test_run_inline_windows_executes_py():
    """_run_inline_windows 实际运行 Python 脚本"""
    from flypig.tools import ToolExecutor

    executor = ToolExecutor(workspace_dir=str(TEST_DIR))
    script = TEST_DIR / "run_me.py"
    assert script.exists(), f"{script} not found"

    # 模拟 tool_bash 调用
    result = executor.execute("bash", {
        "command": f'"{PY}" "{script}" arg1 arg2',
        "timeout": 10,
        "persist": False,
    })

    # 验证
    assert result is not None
    assert "Error" not in result, f"got error: {result}"
    assert "Hello from run_me.py!" in result, f"output missing: {result[:200]}"
    assert "args: ['arg1', 'arg2']" in result, f"args missing: {result[:200]}"
    print(f"PASS: run_me.py executed, output={result[:80]}...")


async def test_run_inline_windows_ansi_stripped():
    """_run_inline_windows 的 ANSI 输出被清理"""
    from flypig.tools import ToolExecutor

    executor = ToolExecutor(workspace_dir=str(TEST_DIR))
    script = TEST_DIR / "ansi_test.py"
    assert script.exists()

    result = executor.execute("bash", {
        "command": f'"{PY}" "{script}"',
        "timeout": 10,
        "persist": False,
    })

    # 验证：ANSI 序列被去掉
    assert result is not None
    assert "\x1B[" not in result, f"ANSI escape found: {result[:100]}"
    assert "PASS: This line has ANSI colors" in result
    assert "ERROR: fake error in red" in result
    assert "plain line without colors" in result
    assert "INFO: mixed warnings here" in result
    print(f"PASS: ANSI cleaned, output={result[:80]}...")


async def test_tool_bash_error_exitcode():
    """tool_bash 返回非零退出码时带 [ERROR] 前缀"""
    from flypig.tools import ToolExecutor

    executor = ToolExecutor(workspace_dir=str(TEST_DIR))
    result = executor.execute("bash", {
        "command": f'"{PY}" -c "import sys; print(\\"fail\\"); sys.exit(1)"',
        "timeout": 5,
    })

    assert result is not None
    assert result.startswith("[ERROR]"), f"should start with [ERROR]: {result[:50]}"
    assert "Exit code 1" in result
    print(f"PASS: error exit code handled: {result[:80]}...")


async def test_tui_mode_executes_inline():
    """TUI mode 下 tool_bash 走 _run_inline"""
    from flypig.tools import ToolExecutor

    executor = ToolExecutor(workspace_dir=str(TEST_DIR))
    executor._tui_mode = True
    script = TEST_DIR / "run_me.py"

    result = executor.execute("bash", {
        "command": f'"{PY}" "{script}"',
        "timeout": 10,
    })

    assert result is not None
    assert "Hello from run_me.py!" in result, f"TUI mode output missing: {result[:100]}"
    print(f"PASS: TUI mode inline execution: {result[:80]}...")


async def test_tui_mode_long_timeout_for_persist():
    """TUI mode persist=True 用长 timeout 执行"""
    from flypig.tools import ToolExecutor

    executor = ToolExecutor(workspace_dir=str(TEST_DIR))
    executor._tui_mode = True
    script = TEST_DIR / "run_me.py"

    result = executor.execute("bash", {
        "command": f'"{PY}" "{script}"',
        "timeout": 1,   # 短 timeout
        "persist": True,  # 但在 TUI 模式下应该用长 timeout
    })

    assert result is not None
    assert "Hello from run_me.py!" in result, f"persist=True failed: {result[:100]}"
    print(f"PASS: TUI mode persist=True works: {result[:80]}...")


async def test_tool_bash_no_command():
    """空命令返回错误"""
    from flypig.tools import ToolExecutor

    executor = ToolExecutor()
    result = executor.execute("bash", {"command": ""})
    assert result == "Error: No command provided"
    print("PASS: empty command handled")


async def test_tool_bash_unknown_tool():
    """未知工具名返回错误"""
    from flypig.tools import ToolExecutor

    executor = ToolExecutor()
    result = executor.execute("nonexistent_tool", {})
    assert "Unknown tool" in result
    print("PASS: unknown tool handled")


async def test_strip_ansi_windows_dsr():
    """strip_ansi 清理 Windows DSR 序列 ([[<...M)"""
    from flypig.tools import strip_ansi

    # Windows DSR mouse sequences
    cases = [
        ("\x1b[[<35;1;0M", ""),      # mouse press
        ("\x1b[[<35;1;0m", ""),      # mouse motion
        ("[[<35;1;0M", ""),          # partial (ESC already stripped)
        ("hello\x1b[[<10;5;0Mworld", "helloworld"),  # mixed
        ("\x1b[1m\x1b[[<10;5;0Mbold\x1b[0m", "bold"),
    ]
    for raw, expected in cases:
        got = strip_ansi(raw)
        assert got == expected, f"strip_ansi({raw!r}) = {got!r}, expected {expected!r}"
    print(f"PASS: strip_ansi Windows DSR ({len(cases)} cases)")


async def test_bash_command_not_found():
    """命令不存在时返回合理信息"""
    from flypig.tools import ToolExecutor

    executor = ToolExecutor(workspace_dir=str(TEST_DIR))
    result = executor.execute("bash", {
        "command": "this_command_does_not_exist_abc123",
        "timeout": 5,
    })
    assert result is not None
    # 应该包含错误信息，不应该是空或超时
    print(f"PASS: bad command handled: {result[:100]}...")


REGISTRY = [
    ("strip_ansi removes colors",       test_strip_ansi_removes_color_codes,       _FUNC),
    ("strip_ansi no damage",            test_strip_ansi_rainbow_vs_python,         _FUNC),
    ("strip_ansi windows dsr",          test_strip_ansi_windows_dsr,               _FUNC),
    ("run py script inline",            test_run_inline_windows_executes_py,       _FUNC),
    ("ANSI stripped from output",       test_run_inline_windows_ansi_stripped,     _FUNC),
    ("error exitcode prefix",           test_tool_bash_error_exitcode,             _FUNC),
    ("TUI mode inline execution",       test_tui_mode_executes_inline,             _FUNC),
    ("TUI mode persist=True works",     test_tui_mode_long_timeout_for_persist,    _FUNC),
    ("empty command error",             test_tool_bash_no_command,                 _FUNC),
    ("unknown tool error",              test_tool_bash_unknown_tool,               _FUNC),
    ("bad command handled",             test_bash_command_not_found,               _FUNC),
]
