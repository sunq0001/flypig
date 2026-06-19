"""配置加载"""
import os
import sys
import yaml
from pathlib import Path
from typing import List, Optional

from .model_registry import resolve as resolve_model_meta


class Config:
    def __init__(self, config_path: str = None):
        if config_path is None:
            config_path = Path(__file__).parent / "config.yaml"

        self._config_path = Path(config_path)

        with open(self._config_path, "r", encoding="utf-8") as f:
            self.data = yaml.safe_load(f)

        self._resolve_env_vars()

        # 工作区目录 — 运行时覆盖
        self._workspace_override: Optional[str] = None

    def _resolve_env_vars(self):
        """解析环境变量 ${VAR_NAME}"""
        def resolve(value):
            if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
                env_var = value[2:-1]
                return os.environ.get(env_var, "")
            elif isinstance(value, dict):
                return {k: resolve(v) for k, v in value.items()}
            elif isinstance(value, list):
                return [resolve(item) for item in value]
            return value

        self.data = resolve(self.data)

    # ── 模型列表 ──

    @property
    def models(self) -> List[dict]:
        """返回所有已注册模型的完整配置（从 model_registry 读取，同步 config 中的 Key）"""
        from .model_registry import REGISTRY
        result = []
        for name, meta in REGISTRY.items():
            result.append({
                "name": name,
                "provider": meta["provider"],
                "base_url": meta["base_url"],
                "api_key": self._get_provider_key(meta["provider"]),
                "model": meta.get("model", name),
            })
        return result

    @property
    def default_model_name(self) -> str:
        return self.data.get("llm", {}).get("default_model", "")

    @property
    def default_model(self) -> Optional[dict]:
        """返回当前默认模型的完整配置"""
        name = self.default_model_name
        for m in self.models:
            if m["name"] == name:
                return m
        if self.models:
            return self.models[0]
        return None

    # ── API Key ──

    @property
    def api_keys(self) -> dict:
        """按提供商索引的 API Key 表"""
        return self.data.get("api_keys", {})

    def _get_provider_key(self, provider: str) -> str:
        """获取指定提供商已解析的 API Key"""
        return self.api_keys.get(provider, "")

    def save_api_key(self, provider: str, api_key: str):
        """保存 API Key 到 config.yaml"""
        with open(self._config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if "api_keys" not in raw:
            raw["api_keys"] = {}
        raw["api_keys"][provider] = api_key

        with open(self._config_path, "w", encoding="utf-8") as f:
            yaml.dump(raw, f, default_flow_style=False, allow_unicode=True)

        # 内存同步
        self.data = raw
        self._resolve_env_vars()

    # ── 价格 ──

    @property
    def pricing_dict(self) -> dict:
        """返回价格字典 {model_name: {input, output}}，仅供 CostTracker 兜底"""
        return {}  # 价格现在由 pricing_fetcher 动态获取

    # ── Agent ──

    @property
    def system_prompt(self) -> str:
        return self.data.get("agent", {}).get("system_prompt", "")

    @property
    def workspace(self) -> str:
        """工作区目录（绝对路径）：运行时覆盖 > config.yaml > CWD"""
        if self._workspace_override:
            return self._workspace_override
        cfg_ws = self.data.get("agent", {}).get("workspace", ".")
        if cfg_ws and cfg_ws != ".":
            # 相对路径 → 基于 CWD 解析为绝对路径
            p = Path(cfg_ws)
            if not p.is_absolute():
                p = Path(os.getcwd()) / cfg_ws
            return str(p.resolve())
        return os.getcwd()

    def prompt_workspace(self, task_mode: bool = False):
        """交互式工作区管理
        
        行为：
        - headless 模式跳过
        - 每次显示候选菜单供选择
        - 创建新工作区时处理重名（复用/覆盖/改名）
        - 自定义选择持久化到 config.yaml
        """
        if task_mode:
            return

        cwd = Path(os.getcwd())
        default_name = self.data.get("agent", {}).get("workspace", cwd.name or "workspace")

        # ── 收集候选工作区目录（排除代码/系统目录） ──
        _EXCLUDE = {"flypig", "docs", ".git", ".vscode", "__pycache__",
                     ".venv", "node_modules", ".codebuddy"}
        candidates = sorted([
            d.name for d in cwd.iterdir()
            if d.is_dir() and not d.name.startswith(".") and d.name not in _EXCLUDE
        ])
        if not candidates:
            candidates = [default_name]

        # ── 显示菜单 ──
        print()
        print("可用工作区:")
        for i, name in enumerate(candidates, 1):
            flag = " [已存在]" if (cwd / name).exists() else " [新建]"
            print(f"  [{i}] {name}{flag}")
        print(f"  [{len(candidates) + 1}] ✚ 创建新工作区")
        print()

        while True:
            try:
                choice = input(f"选择 (1-{len(candidates) + 1}) 或回车选 [1]: ").strip()
                if not choice:
                    choice = "1"
                idx = int(choice)
                if 1 <= idx <= len(candidates):
                    name = candidates[idx - 1]
                    ws = cwd / name
                    ws.mkdir(parents=True, exist_ok=True)
                    self._workspace_override = str(ws)
                    break
                elif idx == len(candidates) + 1:
                    name = self._prompt_new_workspace(cwd, default_name)
                    if name is None:  # 用户取消
                        continue
                    self._workspace_override = str(cwd / name)
                    break
                else:
                    print(f"  [X] 请输入 1-{len(candidates) + 1}")
            except ValueError:
                print(f"  [X] 请输入数字 1-{len(candidates) + 1}")
            except KeyboardInterrupt:
                print("\n  [X] 已取消")
                sys.exit(0)

        print(f"  工作区: {self._workspace_override}\n")

        # ── 持久化 ──
        self._save_workspace_config(name)

    def _prompt_new_workspace(self, cwd: Path, default_name: str) -> Optional[str]:
        """交互创建新工作区，处理重名"""
        print()
        print(f"新工作区名称 (直接回车默认 '{default_name}', 输入 'q' 取消):")
        name = input("    > ").strip()

        if name.lower() == "q":
            return None
        if not name:
            name = default_name

        ws = cwd / name
        if ws.exists():
            print(f'  [*] "{name}" 已存在')
            print("      [r] 复用现有目录")
            print("      [o] 覆盖清空（删除后重建）")
            print("      [n] 重新起名")
            action = input("  选择 (r/o/n): ").strip().lower()
            if action == "o":
                import shutil
                shutil.rmtree(ws)
                ws.mkdir(parents=True, exist_ok=True)
            elif action == "n":
                return self._prompt_new_workspace(cwd, default_name)
            # action == "r" → 直接复用，不操作
        else:
            ws.mkdir(parents=True, exist_ok=True)

        return name

    def _save_workspace_config(self, name: str):
        """将工作区名称持久化到 config.yaml"""
        if os.environ.get("FLYPIG_TEST"):
            return  # 测试模式不写真实配置
        current = self.data.get("agent", {}).get("workspace", "")
        if name == current:
            return
        try:
            with open(self._config_path, "r", encoding="utf-8") as f:
                raw = yaml.safe_load(f)
            if "agent" not in raw:
                raw["agent"] = {}
            raw["agent"]["workspace"] = name
            with open(self._config_path, "w", encoding="utf-8") as f:
                yaml.dump(raw, f, default_flow_style=False, allow_unicode=True)
            self.data = raw
        except Exception:
            pass

    def find_model(self, name: str) -> Optional[dict]:
        for m in self.models:
            if m["name"] == name:
                return m
        return None

    # ── 沙箱配置 ──

    @property
    def sandbox_config(self) -> dict:
        """返回沙箱原始配置字典（默认为禁用状态）"""
        return self.data.get("sandbox", {})

    @property
    def sandbox_enabled(self) -> bool:
        return self.sandbox_config.get("enabled", False)

    @property
    def sandbox_mode(self) -> str:
        return self.sandbox_config.get("mode", "mixed")

    def build_sandbox_config(self):
        """从 config.yaml 构建 SandboxConfig 实例"""
        from .sandbox import SandboxConfig

        raw = self.sandbox_config
        if not raw:
            return SandboxConfig(enabled=False)

        docker = raw.get("docker", {})
        fs = raw.get("filesystem", {})

        return SandboxConfig(
            enabled=raw.get("enabled", False),
            mode=raw.get("mode", "mixed"),
            image=docker.get("image", "flypig-sandbox:latest"),
            container_name=docker.get("container_name", "flypig-sandbox"),
            cpu_limit=docker.get("cpu_limit", 1.0),
            memory_limit=docker.get("memory_limit", "1g"),
            timeout=docker.get("timeout", 120),
            network=docker.get("network", False),
            cap_drop_all=docker.get("cap_drop_all", True),
            no_new_privileges=docker.get("no_new_privileges", True),
            disk_limit=docker.get("disk_limit", "10g"),
            pids_limit=docker.get("pids_limit", 512),
            nproc_limit=docker.get("nproc_limit", 512),
            nofile_limit=docker.get("nofile_limit", 256),
            read_only_root=docker.get("read_only_root", True),
            idle_timeout=docker.get("idle_timeout", 300),
            auto_cleanup=docker.get("auto_cleanup", True),
            whitelist_readonly=fs.get("whitelist_readonly", []),
            whitelist_readwrite=fs.get("whitelist_readwrite", []),
            block_keywords=fs.get("block_keywords", []),
        )

    def save_sandbox_whitelist(self, path: str, mode: str = "readonly"):
        """保存白名单路径到 config.yaml（运行时 'a' 选项持久化）"""
        with open(self._config_path, "r", encoding="utf-8") as f:
            raw = yaml.safe_load(f)

        if "sandbox" not in raw:
            raw["sandbox"] = {}
        if "filesystem" not in raw["sandbox"]:
            raw["sandbox"]["filesystem"] = {}
        key = f"whitelist_{mode}"
        if "filesystem" not in raw["sandbox"]:
            raw["sandbox"]["filesystem"] = {}
        if key not in raw["sandbox"]["filesystem"]:
            raw["sandbox"]["filesystem"][key] = []

        existing = raw["sandbox"]["filesystem"][key]
        if path not in existing:
            existing.append(path)

        with open(self._config_path, "w", encoding="utf-8") as f:
            yaml.dump(raw, f, default_flow_style=False, allow_unicode=True)

        self.data = raw
        self._resolve_env_vars()
