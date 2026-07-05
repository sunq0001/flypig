"""CLI 入口"""

import sys

from .config import Config
from .model import ModelAdapter
from .cost import CostTracker
from .tools import ToolExecutor
from .agent import Agent
from .pricing_fetcher import fetch_pricing
from .model_registry import provider_info


def print_header():
    print("=" * 50)
    print("  FlyPig Agent v0.1")
    print("  Your AI Coding Assistant")
    print("=" * 50)
    print()


def print_model_menu(models: list):
    print("Available Models:")
    print("-" * 50)
    for idx, m in enumerate(models, 1):
        p = m.get("provider", "?")
        print(f"  [{idx}] {m['name']:<28} [{p}]")
    print("-" * 50)
    print()


def select_model(config: Config) -> dict:
    models = config.models
    default_idx = 1
    default_name = config.default_model_name
    for i, m in enumerate(models):
        if m["name"] == default_name:
            default_idx = i + 1
            break

    print(f"Current: {default_name}")
    print()
    print_model_menu(models)

    while True:
        try:
            choice = input(
                f"Select (1-{len(models)}) or Enter for [{default_idx}]: "
            ).strip()
            if not choice:
                choice = str(default_idx)
            idx = int(choice)
            if 1 <= idx <= len(models):
                m = models[idx - 1]
                print(f"\nSelected: {m['name']}\n")
                return m  # 直接返回完整模型配置
            print(f"[X] Invalid choice, enter 1-{len(models)}")
        except ValueError:
            print(f"[X] Invalid input, enter a number 1-{len(models)}")
        except KeyboardInterrupt:
            print("\n\nBye!")
            sys.exit(0)


def _ensure_provider_key(config: Config, provider: str) -> str:
    """检查指定提供商的 API Key，缺失则提示录入"""
    key = config.api_keys.get(provider, "")
    if key:
        return key

    print()
    print("=" * 45)
    print(f"  请设置 {provider} API Key")
    print("=" * 45)
    print()
    info = provider_info(provider)
    url = info.get("console_url", "") if info else ""
    if url:
        print(f"  获取: {url}")
    print()
    user_key = input(f"  输入 {provider} API Key (留空跳过): ").strip()
    if user_key:
        config.save_api_key(provider, user_key)
        print(f"  [OK] {provider} API Key 已保存\n")
        return user_key
    else:
        print(f"  [SKIP] {provider} 跳过，该提供商的模型不可用\n")
        return ""


def main():
    try:
        config = Config()
        config.prompt_workspace(task_mode=False)

        print_header()

        # 选择模型
        llm_config = select_model(config)

        # 确保选中模型的提供商有 Key
        provider = llm_config.get("provider", "")
        api_key = _ensure_provider_key(config, provider)
        if not api_key:
            print(f"[X] {provider} Key 未设置，无法使用该模型")
            sys.exit(1)
        llm_config["api_key"] = api_key

        print(f"  工作区: {config.workspace}\n")

        # ── 沙箱组件初始化 ──
        from .sandbox import create_sandbox_components, PathValidator

        sandbox_cfg = config.build_sandbox_config()
        sandbox_mgr, path_val = create_sandbox_components(sandbox_cfg, config.workspace)

        if sandbox_cfg.enabled and sandbox_mgr is None:
            print("[WARN] 沙箱已启用但 Docker 不可用，将以无沙箱模式运行")
            if sandbox_cfg.mode == "mixed":
                path_val = PathValidator(workspace_dir=config.workspace)
            sandbox_mgr = None

        # 初始化
        model = ModelAdapter(llm_config)
        cost_tracker = CostTracker(config.pricing_dict)
        tools = ToolExecutor(
            workspace_dir=config.workspace,
            path_validator=path_val,
            sandbox_manager=sandbox_mgr,
        )

        if sandbox_mgr:
            print(f"[*] 沙箱模式: {sandbox_cfg.mode}")

        # 获取模型价格并注入到 cost_tracker
        prices, source = fetch_pricing(
            llm_config["name"], llm_config.get("provider", "")
        )
        if prices:
            # 价格同时存显示名和 API 模型名两个 key
            cost_tracker.set_pricing(llm_config["name"], prices)
            api_model = llm_config.get("model", "deepseek-v4-flash")
            if api_model != llm_config["name"]:
                cost_tracker.set_pricing(api_model, prices)
            if source == "online":
                print(
                    f"  [价格] ${prices['input']}/${prices['output']} 每 1M tokens (来自官方定价页)\n"
                )
            elif source == "cached":
                print(
                    f"  [价格] ${prices['input']}/${prices['output']} 每 1M tokens (本地缓存)\n"
                )
            else:
                print(
                    f"  [价格] ${prices['input']}/${prices['output']} 每 1M tokens (参考价，未查到官方数据)\n"
                )
        else:
            print(f"  [价格] 未获取到 {llm_config['name']} 的价格信息\n")

        # 追加工作目录信息到系统提示
        ws_prompt = config.system_prompt + (
            f"\n\nCurrent working directory: {config.workspace}\n"
            f"All file paths in tool results are relative to this directory.\n"
        )
        agent = Agent(
            model=model, cost_tracker=cost_tracker, tools=tools, system_prompt=ws_prompt
        )

        print("[*] Commands: /help /debug /reset /cost /model /exit")
        print()

        # 交互循环
        while True:
            try:
                sys.stdout.flush()
                sys.stderr.flush()

                # ── 有 bash 历史时调整提示 ──
                bash_hint = ""
                if hasattr(agent, "bash_history") and agent.bash_history:
                    bash_hint = " [T] 打开终端"
                user_input = input(f"\n>{bash_hint} ").strip()
                if not user_input:
                    continue

                # ── 终端打开命令 ──
                if user_input.lower() == "t":
                    agent.open_terminal()
                    continue
                elif user_input.lower().startswith("t "):
                    parts = user_input.lower().split()
                    if len(parts) == 2:
                        if parts[1] == "list":
                            for i, cmd in enumerate(agent.bash_history, 1):
                                short = cmd[:80] + "..." if len(cmd) > 80 else cmd
                                print(f"  [{i}] {short}")
                            continue
                        try:
                            idx = int(parts[1])
                            if idx < 1 or idx > len(agent.bash_history):
                                print(
                                    f"  [X] 无效序号，范围为 1-{len(agent.bash_history)}"
                                )
                                continue
                            agent.open_terminal(idx - 1)  # 1-based → 0-based
                            continue
                        except ValueError:
                            pass  # 不是数字，作为普通消息发给 Agent

                if user_input.startswith("/"):
                    cmd = user_input.lower()
                    if cmd == "/help":
                        print("/help   - Show commands")
                        print("/debug  - Toggle debug mode")
                        print("/reset  - Reset conversation")
                        print("/cost   - Show cost summary")
                        print("/model  - Change model")
                        print("/exit   - Exit")
                    elif cmd == "/debug":
                        agent.verbose = not agent.verbose
                        print(f"[*] Debug mode: {'ON' if agent.verbose else 'OFF'}")
                    elif cmd == "/reset":
                        agent.reset()
                        print("[OK] Reset")
                    elif cmd == "/cost":
                        print(agent.get_session_summary())
                    elif cmd == "/model":
                        llm_config = select_model(config)
                        agent.model = ModelAdapter(llm_config)
                        print("[OK] Model changed")
                    elif cmd in ["/exit", "/quit"]:
                        print(agent.get_session_summary())
                        break
                    continue

                print()
                response = agent.run(user_input)
                print(f"\n{response}\n")

            except KeyboardInterrupt:
                print("\n\n" + agent.get_session_summary())
                break
            except Exception as e:
                print(f"\n[X] Error: {e}")

        # 清理沙箱
        if "sandbox_mgr" in locals() and sandbox_mgr:
            sandbox_mgr.cleanup()
    except Exception as e:
        print(f"[X] Fatal error: {e}")
        input("Press Enter to exit...")


if __name__ == "__main__":
    main()
