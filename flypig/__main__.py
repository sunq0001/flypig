"""入口点 - 支持 --task 头戴模式和 --web UI 模式"""
import sys
import argparse
from .cli import main as cli_main


def main():
    """支持命令行参数"""
    parser = argparse.ArgumentParser(description="FlyPig - AI Coding Agent")
    parser.add_argument("--task", "-t", type=str, help="Task to execute (headless mode)")
    parser.add_argument("--web", action="store_true", default=True,
                        help="Use Web UI (default)")
    parser.add_argument("--no-web", action="store_true",
                        help="Use classic terminal interface")
    parser.add_argument("--port", type=int, default=8321,
                        help="Web UI port (default: 8321)")
    parser.add_argument("--host", type=str, default="127.0.0.1",
                        help="Web UI host (default: 127.0.0.1)")
    args = parser.parse_args()

    if args.task:
        _headless_main(args.task)
    elif args.no_web:
        cli_main()
    else:
        _web_main(args.host, args.port)


def _web_main(host: str = "127.0.0.1", port: int = 8321):
    """启动 Web 服务器（默认模式），工作区/模型选择在浏览器中完成"""
    from .config import Config

    config = Config()

    from .web.server import start_server
    try:
        start_server(config, host=host, port=port, open_browser=True)
    finally:
        # 服务器退出后清理沙箱
        from .tools import ToolExecutor
        if hasattr(ToolExecutor, 'sandbox_manager') and ToolExecutor.sandbox_manager:
            ToolExecutor.sandbox_manager.cleanup()


def _headless_main(task: str):
    """Headless 模式：执行任务然后退出"""
    from .config import Config
    from .model import ModelAdapter
    from .cost import CostTracker
    from .tools import ToolExecutor
    from .agent import Agent
    from .pricing_fetcher import fetch_pricing

    config = Config()
    config.prompt_workspace(task_mode=True)

    default_cfg = config.default_model
    if not default_cfg:
        print("[X] 没有可用的模型配置")
        sys.exit(1)

    provider = default_cfg.get("provider", "")
    api_key = default_cfg.get("api_key", "") or config.api_keys.get(provider, "")
    if not api_key:
        print(f"[X] {provider} API Key 未设置")
        print("请先运行交互模式 (python -m flypig) 设置 API Key")
        print("或编辑 config.yaml 中 api_keys.{provider}")
        sys.exit(1)

    default_cfg["api_key"] = api_key
    model = ModelAdapter(default_cfg)

    cost_tracker = CostTracker(config.pricing_dict)
    prices, _ = fetch_pricing(default_cfg["name"], default_cfg.get("provider", ""))
    if prices:
        cost_tracker.set_pricing(default_cfg["name"], prices)
        api_model = default_cfg.get("model", "deepseek-chat")
        if api_model != default_cfg["name"]:
            cost_tracker.set_pricing(api_model, prices)

    from .sandbox import create_sandbox_components, PathValidator
    sandbox_cfg = config.build_sandbox_config()
    sandbox_mgr, path_val = create_sandbox_components(sandbox_cfg, config.workspace)

    if sandbox_cfg.enabled and sandbox_mgr is None:
        print("[WARN] 沙箱已启用但 Docker 不可用，将以无沙箱模式运行")
        if sandbox_cfg.mode == "mixed":
            path_val = PathValidator(workspace_dir=config.workspace)
        sandbox_mgr = None

    tools = ToolExecutor(
        workspace_dir=config.workspace,
        path_validator=path_val,
        sandbox_manager=sandbox_mgr,
    )

    if sandbox_mgr:
        print(f"[*] 沙箱模式: {sandbox_cfg.mode} (容器将在首次命令时启动)")

    ws_prompt = config.system_prompt + (
        f"\n\nCurrent working directory: {config.workspace}\n"
        f"All file paths in tool results are relative to this directory.\n"
    )
    if sandbox_mgr:
        ws_name = Path(config.workspace).name or "workspace"
        ws_prompt += (
            "\nCommands execute inside a Linux Docker container (flypig-sandbox).\n"
            "Use Linux/bash syntax: ls, cat, grep, && to chain commands.\n"
            f"The workspace folder '{ws_name}' is mounted at /workspace.\n"
            "To access subdirectories, use: cd /workspace/<subfolder_name>\n"
                "Use forward slashes / for paths.\n"
                "IMPORTANT: Always use the correct container path. If a directory "
                "is not found, check 'ls /workspace/' for available subdirectories.\n"
                "CRITICAL: You CANNOT run interactive programs that need user input "
                "(e.g., scripts with input(), while True loops waiting for stdin, "
                "python -i, node REPL). These will hang forever because stdin is "
                "not connected. Instead, tell the user to open the terminal panel "
                "and run the command there manually.\n"
        )

    agent = Agent(
        model=model,
        cost_tracker=cost_tracker,
        tools=tools,
        system_prompt=ws_prompt
    )

    print(f"[*] Executing task: {task[:50]}...")
    response = agent.run(task)
    print(f"\n[Result]: {response}")
    print(f"\n[Cost Summary]:\n{agent.get_session_summary()}")

    if hasattr(tools, 'sandbox_manager') and tools.sandbox_manager:
        tools.sandbox_manager.cleanup()


if __name__ == "__main__":
    main()
