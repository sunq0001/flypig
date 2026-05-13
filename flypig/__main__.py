"""入口点 - 支持 --task 参数"""
import sys
import argparse
from .cli import main as cli_main


def main():
    """支持命令行参数"""
    parser = argparse.ArgumentParser(description="FlyPig - AI Coding Agent")
    parser.add_argument("--task", "-t", type=str, help="Task to execute (headless mode)")
    args = parser.parse_args()

    if args.task:
        # Headless 模式: 执行任务然后退出
        from .config import Config
        from .model import ModelAdapter
        from .cost import CostTracker
        from .tools import ToolExecutor
        from .agent import Agent

        config = Config()

        # 检查 API Key
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
        tools = ToolExecutor(workspace_dir=config.workspace)
        agent = Agent(
            model=model,
            cost_tracker=cost_tracker,
            tools=tools,
            system_prompt=config.system_prompt
        )

        print(f"[*] Executing task: {args.task[:50]}...")
        response = agent.run(args.task)
        print(f"\n[Result]: {response}")
        print(f"\n[Cost Summary]:\n{agent.get_session_summary()}")
    else:
        # 交互模式
        cli_main()


if __name__ == "__main__":
    main()
