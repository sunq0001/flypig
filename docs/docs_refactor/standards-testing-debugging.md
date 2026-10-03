# 规范 · 测试 · 调试 — 质量保障体系

> **来源**：架构重构全流程讨论（architecture_check → pre-commit → CI → mypy → 测试）
> **关联文档**：[architecture-guide.md](architecture-guide.md)、[backend-modules.md](backend-modules.md)、[adversarial-system.md](adversarial-system.md)、[tech-stack.md](tech-stack.md)、[ui-refactor.md](ui-refactor.md)（自动化检查清单由 UI 审计驱动）
>
> **IDE 配置**：`.vscode/settings.json`、`.vscode/extensions.json`、`.vscode/tasks.json`

---

## 零、完整流程演示

> 下面演示一次完整的代码修改从"写代码"到"合入主分支"的全流程，
> 每一步检查什么、拦截什么、如果失败怎么办。

### 第 1 步：写代码

你在 IDE 里改了 `acl/pricing.py`，新增了一个转换函数，同时不小心引入了一个 bug——忘了定义某个常量。

**IDE 实时拦截**：
- Ruff 扩展立即在代码上标出红色波浪线（未定义变量、格式问题）
- ESLint 扩展在 Vue/JS 文件上同样标出波浪线
- 保存时 ruff 自动修复可修复的问题（排序 import、格式化等）

**通常你还没保存到文件，就已经看到错误了。** 此时不阻塞开发，你完全可以继续写，等写完了再一并修复。

### 第 2 步：`python dev.py`（启动时自动检查）

每次启动 dev.py 时自动运行两道检查，不过不放行：

```bash
python dev.py
# [check] 架构合规检查 → ✅ 通过
# [lint] 层依赖检查   → ✅ 通过
# ╔══ 启动服务 ══╗
```

**特点**：这是第二道"不可绕过"的防线（除非不跑 dev.py），在启动服务前就排除架构违规。

### 第 3 步：`git commit`（pre-commit 拦截）

```bash
git add flypig/acl/pricing.py
git commit -m "feat: 新增定价转换函数"
```

commit 时 pre-commit 自动运行 5 个 hook：

```
ruff              → 检查你的代码风格，如果有问题自动修复
ruff-format       → 自动格式化代码
eslint            → 检查前端 Vue/JS 规范
lint-imports      → DDD 层依赖方向检查
architecture-check → ❌ 发现未注册新文件！commit 被阻止
```

**失败后怎么办**：修复 architecture-check 报的错误 → 重新 `git add` → 重新 `git commit`

```bash
# 修完 bug 后重新提交
git add flypig/acl/pricing.py
git commit -m "feat: 新增定价转换函数"
# ✅ 这次 pre-commit 全部通过，commit 成功
```

### 第 4 步：`git push`（CI 远程检查）

```bash
git push
```

代码到达 GitHub，CI 自动触发，按顺序跑 7 个步骤：

```
① Ruff          → ✅ 通过
② mypy          → ✅ 通过
③ ESLint        → ✅ 通过
④ 架构检查       → ❌ 失败！
                   - [REGISTER] 新文件 tool_calc.py 未在 __init__.__all__ 中导出
                   - [APICONTRACT] 新路由 /api/calc 未在 api-contracts.json 中定义
⑤ import-linter → 不执行（上一步失败）
⑥ Vitest        → 不执行
⑦ pytest+cov    → 不执行
```

**失败后怎么办**：修复架构检查报的问题 → 重新 `git add` `git commit`（跳过 pre-commit 可加 `--no-verify`，但不推荐）→ `git push`

### 第 5 步：全部通过，合并 PR

```
① Ruff          → ✅
② mypy          → ✅
③ ESLint        → ✅
④ 架构检查       → ✅（注册检查通过 + API 契约检查通过）
⑤ import-linter → ✅
⑥ Vitest        → ✅（7 passed）
⑦ pytest+cov    → ✅（55 passed, coverage 12% > 10%）
```

GitHub 显示 ✅ 全部通过 → 可以合并 PR 到 `main`。

### 流程图

```
你写代码 ──→ IDE实时波浪线 ──→ dev.py启动检查 ──→ git add ──→ git commit ──→ git push ──→ PR合并
        （ruff/eslint 标注）      │       │                     │                    │
                          architecture_check  architecture_check          GitHub CI
                          lint-imports        lint-imports                    │
                                          ┌──────┬──────┬──────┐    ┌──────┬──────┬──────┐
                                          ↓      ↓      ↓      ↓    ↓      ↓      ↓      ↓
                                        ruff  eslint  lint-  arch   ruff  mypy  eslint  pytest
                                        +fmt          import check   │     │     vitest  cov
                                                         └─全部通过才allow──┘     │       │
                                                                                import  vitest
                                                                                linter   │
                                                                                └─全部通过才允许合并─┘
```

### 四层防线对比

| 维度 | IDE（实时） | dev.py（启动） | pre-commit（提交） | CI（推送） |
|------|-----------|----------------|-------------------|------------|
| 触发时机 | 敲键盘时 | `python dev.py` | `git commit` 时 | `git push` 后 |
| 运行位置 | 本地 IDE | 本地命令行 | 本地 git hook | GitHub 服务器 |
| 扫描范围 | 单文件 | 全量 | 只扫 staged 文件 | 全量代码 |
| 运行时间 | 实时 | ~5 秒 | <10 秒 | 3-5 分钟 |
| 检查项 | ruff/eslint/mypy | architecture_check + lint-imports | ruff + eslint + lint-imports + arch_check | ruff → mypy → eslint → arch_check → lint-imports → vitest → pytest |
| 拦截效果 | 写代码时就提醒 | 不让启动带违规服务 | 不让劣质代码进入本地仓库 | 不让劣质代码合入主分支 |
| 能绕过吗 | 不装 VSCode 扩展 | 不跑 dev.py | `git commit --no-verify` | 不能（除非修改 CI 配置） |

> **核心原则**：越靠右越不可绕过，越靠左反馈越即时。四层都在才能防止劣质代码流入主分支。

---

## 一、总览：四道防线

```
写代码时（IDE 实时） → 启动时（dev.py） → 提交前（pre-commit） → 推送后（CI）
     ↓                    ↓                  ↓                    ↓
  实时波浪线               ~5 秒             10 秒内              3-5 分钟
  ruff/eslint/mypy       架构+层依赖        本地拦截              远程全量检查
```

| # | 防线 | 配置文件 | 检查项 | 反馈速度 |
|---|------|---------|--------|---------|
| 1 | **IDE 实时 linting** | `.vscode/settings.json` | ruff / eslint / mypy | **实时**（< 1 秒） |
| 2 | **dev.py 启动检查** | `dev.py` (内嵌) | `architecture_check.py` + `lint-imports` | ~5 秒 |
| 3 | **pre-commit hook** | `.pre-commit-config.yaml` | ruff + eslint + lint-imports + architecture_check | < 10 秒 |
| 4 | **GitHub Actions CI** | `.github/workflows/ci.yml` | 8 项全量检查（含测试 + 覆盖率） | 3-5 分钟 |

---

## 二、第一道防线：IDE 实时 linting（新增）

配置文件：`.vscode/settings.json`、`.vscode/extensions.json`

### 前置条件

安装 VSCode 推荐扩展（打开项目时会弹出提示）：
- **Ruff** (`charliermarsh.ruff`) — Python 实时 lint + 格式化
- **ESLint** (`dbaeumer.vscode-eslint`) — JS/Vue 实时 lint
- **Pylance**（随 `ms-python.python` 自动安装）— Python 类型检查（`strict` 模式）
- **Even Better TOML** — TOML 配置高亮

> **为什么不推荐 mypy 扩展**：`matangover.mypy` 在 Windows 上会扫描整个工作区根目录（包括 `aider/`、`deepseek-tui/`、`dist/` 等），遇到 Windows 虚拟设备路径（`\\\\.\\nul`）时崩溃。改用 Pylance 做编辑器实时类型检查（已配 `strict` 模式），mypy 只在 CI 和 pre-commit 中手动运行。

### 效果

| 操作 | 触发行为 |
|------|---------|
| 敲键盘 | Ruff 实时标出语法/风格问题（红色/黄色波浪线） |
| 保存 `.py` | Ruff 自动修复可修复问题 + 排序 import |
| 保存 `.vue` / `.js` | ESLint 自动格式化 |
| 鼠标悬停波浪线 | 显示错误信息和修复建议 |

### 关键配置

```jsonc
{
  "[python]": {
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": "explicit",
      "source.fixAll.ruff": "explicit"
    },
    "editor.defaultFormatter": "charliermarsh.ruff"
  },
  "ruff.lint.run": "onType",
  "eslint.validate": ["javascript", "vue"],
  "eslint.workingDirectories": [{ "directory": "flypig/interface/web/static_vite", "changeProcessCWD": true }]
}
```

---

## 三、第二道防线：dev.py 启动检查（新增）

dev.py 在启动四个服务之前（第 107-151 行）会顺序跑两道检查：

```python
# ① 架构合规检查（含 DDD/死代码/契约等 13 项）
await asyncio.create_subprocess_exec("python", "scripts/architecture_check.py", ...)
# ② 层依赖检查
await asyncio.create_subprocess_exec("lint-imports", "--config", "flypig/pyproject.toml", ...)
```

任何一项未通过 → dev.py 打印错误并 `sys.exit(1)`，**服务不会启动**。这是 CI 之外本地最不可绕过的防线。

> **死代码检测**：Vulture 扫描整个 `flypig/` 目录（排除 `node_modules/`），只报告置信度 ≥ 60% 的结果。
> 白名单过滤路由函数（装饰器绑定）、ABC 接口抽象方法、`*_stub.py` 桩文件、`shared/kernel/` DDD 基建等已知误报。
> 当架构检查报告 `[DEADCODE]` 时，运行 `vulture flypig/ --min-confidence 60` 查看完整结果。

---

## 四、第三道防线：pre-commit hook

配置文件：`.pre-commit-config.yaml`

### hook 清单

| hook | 检查内容 | 作用域 | 修复方式 |
|------|---------|--------|---------|
| `ruff` | Python 代码风格（400+ 规则） | 所有 `.py` | `--fix` 自动修复 |
| `ruff-format` | Python 代码格式化 | 所有 `.py` | 自动格式化 |
| `eslint` | 前端 Vue/JS 规范（200+ 规则） | `static_vite/src/` | 手动修复 |
| `lint-imports` | DDD 层依赖方向 | 全量 | 手动修复 |
| `bandit` | 安全扫描（硬编码密码、eval、subprocess） | `flypig/` | 手动修复 |
| `architecture-check` | DDD 继承/注册/契约 13 项检查 | 全量 | 手动修复 |

> **注意**：mypy、bandit 和 vitest 不在 pre-commit 中运行——mypy 运行较慢（全量类型推断），bandit 安全扫描较耗时，vitest 需要完整前端环境。三者由 CI 覆盖。IDE 中类型检查由 Pylance（`strict` 模式）替代。

### 运行规则

- 本地 hook 只跑 staged 文件（快，<10 秒）；lint-imports 和 architecture-check 跑全量
- 任何一个 hook 失败 → commit 被阻止
- ruff 自动修复后文件会自动加入 staged

---

## 五、第四道防线：GitHub Actions CI

配置文件：`.github/workflows/ci.yml`

### 执行顺序

```
① Ruff Python 检查        （全量，含所有规则集）
② mypy 静态类型检查        （domain/orchestration/acl/shared）
③ ESLint 前端检查          （全部 src/）
④ 架构合规检查              （architecture_check.py + frontend_check.py）
⑤ 层依赖检查               （import-linter DDD 分层约束）
⑥ Vitest 前端测试          （全部 *.test.js）
⑦ pytest + 覆盖率           （后端单元测试，fail_under=10%）
```

> **不可绕过**：CI 运行在 GitHub 服务器上，本地任何 bypass 操作（`--no-verify`、跳过 dev.py）都不影响 CI 执行。PR 必须全部通过才能合并。

### 触发条件

- `push` → `main`, `architecture-refactor`, `develop`
- `pull_request` → `main`

### 退出规则

- 任何步骤失败 → CI 变红 → 不允许合并
- 覆盖率低于 10% → CI 变红

---

## 六、检测工具详解

### 6.1 IDE 集成 — VSCode 配置

配置文件：`.vscode/settings.json`、`.vscode/extensions.json`

除 CLI 检查和 pre-commit 外，每个工具还作为 VSCode 扩展实时工作：

| 工具 | VSCode 扩展 | 工作方式 | 检查范围 |
|------|------------|---------|---------|
| Ruff | `charliermarsh.ruff` | `onType` 实时标注 + `onSave` 自动修复 | 全部 `.py` |
| ESLint | `dbaeumer.vscode-eslint` | 保存时格式化 + 实时标注 | `static_vite/src/` |
| Pylance | 内置（Python 扩展） | 实时标注 + 补全 + 类型检查（`strict`） | 全部 `.py` |
| mypy | ❌ **已禁用**（Windows `\\\\.\\nul` 崩溃） | 仅在 CI / 手动运行 | 仅 `flypig/` |

> **即装即用**：打开项目时 VSCode 弹出提示安装推荐扩展，装好后无需额外配置。

### 6.2 ruff — Python 代码风格

配置位置：`flypig/pyproject.toml` → `[tool.ruff]`

```toml
[tool.ruff.lint]
select = ["E","F","I","N","W","B","UP","SIM","RUF100",
         "PL","TRY","PTH","C4","RUF","ASYNC",
         "PERF","FURB","ARG"]
```

覆盖 400+ 条规则，用于替代 flake8 + isort + black + pylint + vulture（部分）。

**ignore 策略（三条原则）**：

1. **项目设计决策** — `N818`（Exception 命名）、`B024`（ABC 无抽象方法）、`PLW0603`（global 单例）、`RUF006`（后台 task）、`ASYNC109/240`（async 风格）等——这些是 FlyPig 架构的有意选择，全局 ignore
2. **中文误报** — `RUF001/002/003`（全角/混淆字符）直接全局 ignore
3. **1~2 处违规加 `# noqa: RULECODE`** — `PLR1714`、`PLW2901`、`RUF012` 等仅在少数位置触发，直接在代码上加 `# noqa`，不全局 ignore

查看完整 ignore 列表：`flypig/pyproject.toml` → `[tool.ruff.lint] → ignore`。
每个 ignore 项都有分类注释（必须保留 / 已加 noqa）。

### 6.3 类型检查双轨制

#### IDE 实时：Pylance（Pyright）

配置位置：`.vscode/settings.json` + `pyrightconfig.json`

```json
"python.analysis.typeCheckingMode": "strict"
```

Pylance 是 VSCode Python 扩展内置的类型检查器，原生支持 Windows，不会遇到 mypy 的 `\\\\.\\nul` 崩溃问题。
`strict` 模式覆盖的类型检查范围比 `basic` 更全面（隐式 None、未标注返回值、泛型参数匹配等）。

#### CI / 手动：mypy

配置位置：`.mypy.ini`、`flypig/pyproject.toml` → `[tool.mypy]`

```toml
[tool.mypy]
python_version = "3.11"
check_untyped_defs = true
warn_return_any = true
warn_unreachable = true
```

**运行方式**（仅 CI + 手动，不在 IDE 扩展中运行）：

```bash
# 运行范围限定到 flypig/（避免扫到 aider/ deepseek-tui/ 等触发 Windows bug）
mypy flypig/

# 或指定子包
mypy flypig/domain flypig/orchestration flypig/acl flypig/shared
```

**重点拦截**：
- 未定义的变量
- None 未判空（`PricingEntry | None` → 取值前必须判断）
- 返回值类型不匹配
- 未使用的 `type: ignore` 注释

> **注意**：`.mypy.ini` 设置了 `exclude` 排除所有非核心目录，并配置了 `follow_imports = silent`、`no_site_packages = true` 以减少扫描范围。IDE 中已通过 `"mypy.enabled": false` 禁用 matangover.mypy 扩展，避免 Windows `\\\\.\\nul` 崩溃。当 Pylance 和 mypy 行为不一致时，以 CI（mypy）为准。

### 6.4 ESLint — 前端代码规范

配置位置：`flypig/interface/web/static_vite/.eslintrc.json`

使用 `eslint:recommended` + `plugin:vue/vue3-recommended` 规则集。

### 6.5 Vitest — 前端测试框架

配置位置：`flypig/interface/web/static_vite/vitest.config.js`

基于 Vite 的测试框架，兼容 Vue 组件测试。与 Vite 共享同一份配置。

---

## 七、自定义架构检查

### 7.1 architecture_check.py

配置位置：`scripts/architecture_check.py`

共 **13 项** 检查，覆盖 ruff 和 mypy 不覆盖的 FlyPig 特有项：

| 代号 | 名称 | 检查内容 |
|------|------|---------|
| LAYER | 层依赖方向 | domain → application → infrastructure → interface 依赖方向是否正确 |
| DDD | DDD 基类继承 | domain 层的类是否继承 Entity/ValueObject/AggregateRoot 等 |
| CIRCULAR | 循环依赖 | A → B → C → A 不允许 |
| SKEL | 骨架文件标记 | 骨架文件必须有 TODO 标记，防止 AI 误删 |
| REGISTER | 新文件注册 | domain 类必须在 `__init__.__all__` 导出，routes 蓝图必须在 `app_factory` 注册 |
| DOC | 文件级 docstring | 每个 `.py` 文件第一行必须是 docstring |
| DOCQ | docstring 质量 | 必须包含「为什么做 / 实现方法 / 层&依赖」三段 |
| COUPLE_PKG | 包耦合度 | 单个文件依赖 >2 个层，提示职责过宽 |
| CONTRACT | 接口契约 | domain/interfaces 的 ABC 在 infrastructure 中是否有实现 |
| APICONTRACT| API 契约 | 路由路径是否匹配 `data/api-contracts.json` 定义 |
| **DEADCODE** | **死代码检测** | **Vulture 扫描未使用的函数/类/变量（置信度 ≥60%），排除 node_modules/ 和已知误报** |
| DEPSEC | 依赖安全 | 依赖版本是否锁定（`>=` 无上限警告） |
| CONFIG | 配置规范 | `config.yaml` 是否存在、格式是否完整 |
| I18N | 国际化就绪 | 异常 code 是否有 i18n 翻译键 |
| TEST | 测试覆盖 | 每个业务模块是否有对应的测试文件 |

### 7.2 API 契约定义

配置位置：`flypig/data/api-contracts.json`

```json
{
  "contracts": {
    "GET /api/health": {
      "response_200": {
        "required": ["status", "version"]
      }
    },
    "POST /api/chat": {
      "response_200": {
        "type": "text/event-stream"
      }
    }
  }
}
```

**作用**：
- 后端改路由路径 / 方法时，如果忘记更新 JSON，CI 会拦截
- 前后端联调时，前端可以直接读 JSON 了解 API 结构
- 新加路由必须先在 JSON 中声明

### 7.3 死代码检测（DEADCODE）

配置位置：`scripts/architecture_check.py` → `check_dead_code()`

**工具**：Vulture（`pip install vulture`）

**工作原理**：
- 在 `python dev.py` 启动时自动运行
- 扫描 `flypig/` 目录，排除 `node_modules/`
- 只报告置信度 ≥ 60% 的结果
- 内置白名单过滤已知误报：
  - 路由函数（Flask/Quart 装饰器绑定）
  - ABC 接口抽象方法
  - `*_stub.py` 桩文件（预留实现）
  - `shared/kernel/` DDD 基建
  - `shared/specification.py` / `validation.py` / `result.py`（工具类）
  - `domain/prompts/multirole_manager.py` / `domain/change_score.py` / `domain/mode.py`（未来预留）
  - `graph_routes.py` 中 `return` 后的 `yield`（类型签名需要）

**手动运行**：
```bash
# 全量扫描
vulture flypig/ --min-confidence 60

# 排除 node_modules
vulture flypig/ --min-confidence 60 --exclude "*node_modules*"

# 只看 100% 置信度的（没有误报，但可能漏报）
vulture flypig/ --min-confidence 100
```

### 7.4 frontend_check.py

配置位置：`scripts/frontend_check.py`

检查前端特有的规范（共 16 项）：

**一、API 规范**
- F_API — 禁止直接 `fetch()`，应通过 `utils/api.js` 或 store

**二、代码质量**
- F_COMPLEX — computed/watch 回调超 15 行，建议提取具名函数
- F_LONGFUNC — 函数体 > 50 行，建议拆分
- F_RETURNS — 函数 return 点 > 6 个，流程过于复杂
- F_MSTR — 魔法字符串重复 5+ 次，建议定义常量
- F_COUPLE — import 超 25 条，高耦合

**三、健壮性**
- F_ROBUST — async 函数有 await 但无 try/catch

**四、样式规范**
- F_CSS — `.vue`/`.js` 中 `!important` 超 15 个
- F_CSS_GLOBAL — 全局 `.css` 文件中 `!important` 超 15 个
- F_CSS_ORPHAN — 未被任何 `.vue`/`.js` import 的孤儿 `.css` 文件

**五、模板规范**
- F_TEMPLATE_DEPTH — `<div>` 嵌套超 4 层，建议简化 DOM
- F_PATTERN — 手写 tabs-bar/tab-list 等，建议用 `<t-tabs>`

**六、性能**
- F_SHOWREF — `v-show` 搭配重型组件，建议改 `v-if` + `<KeepAlive>`

**七、文档规范**
- F_DOC — 文件缺少文件级注释
- F_SKEL — 骨架文件缺少 TODO 标记

**八、数据分离**
- F_DATA — 组件内嵌大型数据对象（> 12 个键值对），应外移到 config/

---

## 八、测试体系

### 8.1 测试金字塔

```
         ╱─ E2E（端到端）─╲        ← 慢、贵、少（5%）
        ╱   集成测试   ╲
       ╱   单元测试     ╲         ← 快、便宜、多（60%）
```

### 8.2 测试类型

| 类型 | 测什么 | 特点 | 存放位置 |
|------|--------|------|---------|
| **单元测试** | 单个函数/方法的纯逻辑 | 毫秒级，mock 外部依赖 | `tests/unit/` |
| **集成测试** | 跨层交互（API→Service→DB） | 秒级，需要真实/内存依赖 | `tests/integration/` |
| **E2E 测试** | 完整业务流程（启动服务→用户操作→验证结果） | 分钟级，最脆弱 | `tests/e2e/` |
| **快照测试** | 前端 UI 渲染结果对比 | 用于防意外变更 | `src/**/__tests__/` |

### 8.3 测试覆盖率

- 当前阈值：`fail_under = 10%`
- 统计范围：`flypig/` 包（排除 `tests/` 和 `__pycache__/`）
- 随着项目成熟逐步提高：10% → 30% → 60%

### 8.4 编写规则

**一个函数 = 一组测试，不是一条**：

| 用例类型 | 含义 | 例子 |
|---------|------|------|
| Happy Path | 正常输入，预期输出 | 传正确参数，返回正确结果 |
| Edge Case | 边界值 | 空列表、0、None、超大值 |
| Error Case | 非法输入 | 传 None、传错误类型 |
| Exception Path | 预期抛异常 | 文件不存在、网络超时 |

**文件命名**：
- 后端：`tests/unit/test_{module_name}.py`
- 前端：`src/{module}/__tests__/{filename}.test.js`

### 8.5 现有测试（截至 2026-07-04）

| 文件 | 数量 | 覆盖内容 |
|------|------|---------|
| `test_pricing_entry.py` | 4 | PricingEntry 值对象不可变性、相等性 |
| `test_portkey_acl.py` | 4 | Portkey 格式 → PricingEntry 转换 |
| `test_pricing.py` | 18 | 单位转换 / 模型匹配 / 价格提取 / default 格式 |
| `test_exceptions.py` | 12 | 统一异常体系 code/message/to_dict |
| `test_chat_response.py` | 12 | ChatResponse DTO 序列化 / 工厂方法 |
| `test_health.py` | 2 | health/ping 路由集成测试 |

**小计：55 个测试，全部通过**

### 8.6 优先补测顺序

```
第 1 优先级：acl/ 层（格式转换、外部系统适配）
第 2 优先级：domain/ 层（值对象、实体、异常体系）
第 3 优先级：orchestration/ 层（DTO、编排逻辑）
第 4 优先级：API 路由（集成测试、响应结构锁定）
第 5 优先级：infrastructure/ 层（需要 mock 外部依赖）
```

---

## 九、AI 编程协作规则

### 9.1 写测试的时机

**不搞 TDD，先实现后立刻补测**：

```
你描述功能 → AI 写实现代码 → 你确认接口 → AI 补测试 → 跑通 → 下一个
```

### 9.2 什么时候用 TDD

只在以下场景值得：
- 计算公式 / 算法类（行为非常确定）
- 安全校验（要"锁死"行为）
- 重构旧代码（先写测试锁住行为再改）

### 9.3 共同的坑

| 问题 | 原因 | 解决方法 |
|------|------|---------|
| 测试挂了 debug 半天 | AI 写的测试本身有 bug | 先确认测试代码没错 |
| 接口改了测试要重写 | 接口没稳定就写了测试 | 确认接口满意后再补测试 |
| 空骨架文件被删除 | AI 以为"没用的空文件" | 骨架文件必须加 `# TODO` 标记 |

---

## 十、防止 AI 写出"一坨代码"的关键机制

```
IDE ruff/eslint → 写代码时实时红/黄波浪线，不等提交
dev.py 启动检查  → architecture_check + lint-imports，不过不放行服务
pre-commit       → ruff + eslint + lint-imports + arch_check，不让劣质代码进入仓库
CI               → 8 项全量检查，不让劣质代码合入主分支
coverage         → 不能不写测试
API 契约         → 不能乱改接口
```

**任何一个机制失效 → 有问题的代码会被拦截。越靠近左侧的防线反馈越快。**

---

## 十一、常见操作

### 安装 IDE 扩展

```bash
# 打开项目 VSCode 会自动弹出推荐扩展
# 或手动安装：Ruff、ESLint、Pylance（随 Python 扩展）、Even Better TOML
# ⚠ 不要安装 matangover.mypy，已禁用并加入 unwantedRecommendations
```

### 安装 pre-commit hooks

```bash
pre-commit install    # 安装 git hooks
pre-commit run --all-files  # 手动触发全部检查
```

### 运行全部检查

```bash
# 本地
python dev.py                                            # 启动时自动跑架构+层依赖检查
pre-commit run --all-files                               # 跑全部 pre-commit hook
python -m pytest tests/ -v                               # 跑全部后端测试
python scripts/architecture_check.py                     # 架构合规
mypy flypig/                                             # 静态类型检查（仅 flypig/）
bandit -c .bandit -r flypig                              # 安全扫描
pytest --hypothesis-show-statistics tests/               # 含 Hypothesis 属性测试

# 前端
cd flypig/interface/web/static_vite
npm test                       # 前端测试
npx eslint src/                # 前端风格
```


### 触发 CI

```bash
git commit -m "feat: xxx"    # pre-commit 先跑
git push                      # GitHub Actions 再跑
```

---

## 十二、运行时调试工作流

> **来源**：合并自 [debug-workflow.md](debug-workflow.md)
> **关联文档**：[mcp.md](mcp.md)、[data-flow.md](data-flow.md)、[subprocess-and-tools.md](subprocess-and-tools.md)
>
> **MCP 配置**：`.codebuddy/mcp.json`

前十一章覆盖了**写代码时→提交前→推送后**的全链路质量保障。
本章覆盖**运行时出问题后**怎么用 MCP 工具链系统化诊断。

### 12.1 Debug MCP 工具链

| 工具 | 用途 | 启动方式 |
|------|------|----------|
| **Chrome DevTools MCP** | 控制台错误、网络请求、DOM 检查 | 内置（连接 Chrome:9222） |
| **Playwright MCP** | 浏览器自动化、API 测试、E2E | 内置（自动启动浏览器） |
| **Glimpse MCP** | 前端 UI 对比、截图、交互 | 内置 |
| **autotel-mcp** | OpenTelemetry 追踪查询、性能分析 | 内置（端口 4318） |
| **python-analyzer** | Python 代码分析、类型检查 | 内置 |
| **Ruff MCP** | Python lint / format | 内置 |

### 12.2 预定义调试工作流

#### Workflow 1: 服务崩溃
**场景**: dev.py 启动后服务（back/front/chat/docs）反复崩溃。

| 步骤 | 操作 | 工具 | 期望结果 |
|------|------|------|----------|
| 1 | 查 `back.log` 最新错误 | `read_file .dev_logs/back.log -Tail 20` | 确认异常类型 |
| 2 | 根据错误装缺包/修代码 | 对应修复 | 包安装成功 |
| 3 | 重启 dev.py | 终端执行 | 所有服务 running |
| 4 | 验证 API 是否响应 | Playwright `fetch('/api/config')` | 200 OK |

**常见根因**:
- 缺依赖包（`ModuleNotFoundError`）→ `pip install <pkg>`
- 架构检查未通过 → 修复违规后重试
- 端口被占用 → `taskkill /F /PID <pid>` 清理

#### Workflow 2: 前端白屏/渲染错误
**场景**: 页面打开但空白、组件不渲染、样式异常。

| 步骤 | 操作 | 工具 | 期望结果 |
|------|------|------|----------|
| 1 | 查控制台错误 | Chrome DevTools `list_console_messages` | 无 error |
| 2 | 查网络请求 | Playwright `browser_network_requests` / `fetch` | 关键 API 200 |
| 3 | 截图看实际渲染 | Playwright `browser_take_screenshot` | UI 正常 |
| 4 | 查 DOM 结构 | Chrome DevTools `evaluate_script` DOM 查询 | 组件挂载正常 |
| 5 | 检查 Vue 状态（如需） | `__vue_app__` 调试 | 数据正确 |

**常见根因**:
- Vite HMR 未更新 → 刷新页面
- JS 编译错误 → 看 dev.py 的 front.log
- API 配置返回异常 → 检查 `/api/config`

#### Workflow 3: SSE 数据流中断
**场景**: 发送消息后 AI 不回复、回复卡住、流中断。

| 步骤 | 操作 | 工具 | 期望结果 |
|------|------|------|----------|
| 1 | 查网络请求中 SSE 连接 | Chrome DevTools `list_network_requests` | SSE 连接正常 |
| 2 | 查后端日志 SSE 事件流 | `read_file .dev_logs/back.log \| grep SSE` | `[sse] 流开始` → `流结束` |
| 3 | 查 OTel 追踪（如果可以） | autotel-mcp `search_traces` | 完整 trace |
| 4 | 查控制台错误 | Chrome DevTools `list_console_messages` | 无 error |

**常见根因**:
- API Key 不合法 → 配置正确 key
- SSE `[DONE]` 缺失 → 后端 error 路径补全
- 模型返回空 → 切换模型

#### Workflow 4: API 错误
**场景**: 后端 API 返回 4xx/5xx 或响应格式错误。

| 步骤 | 操作 | 工具 | 期望结果 |
|------|------|------|----------|
| 1 | 查 OTel 追踪完整链路 | autotel-mcp `search_traces` | 含所有 span |
| 2 | 查后端日志异常 | `read_file .dev_logs/back.log \| grep ERROR\|WARNING` | 明确异常信息 |
| 3 | Playwright 直接调 API | Playwright `fetch(url)` | 200 + 正确格式 |
| 4 | 查请求参数 | 检查调用方代码 | 参数正确 |

#### Workflow 5: 工作区/文件操作
**场景**: 工作区选择后文件树不显示、文件操作失败。

| 步骤 | 操作 | 工具 | 期望结果 |
|------|------|------|----------|
| 1 | 查 `/api/config` 返回 | Playwright `fetch('/api/config')` | workspace 路径正确 |
| 2 | 查 `/api/config/workspace` POST | Chrome DevTools 网络 | 200，含 recent 列表 |
| 3 | 查文件系统访问权限 | 后端日志 | 无 PermissionError |

#### Workflow 6: 死代码分析与清理
**场景**: 多次重构后遗留无用的函数、类、变量、桩文件。

| 步骤 | 操作 | 工具 | 期望结果 |
|------|------|------|----------|
| 1 | 启动 dev.py（自动跑 Vulture） | dev.py architecture_check | 看到 DEADCODE 报告 |
| 2 | 手动全量扫描确认范围 | `vulture flypig/ --min-confidence 60` | 确认哪些是真死代码 |
| 3 | 分类：历史遗留 / 未来预留 / 误报 | 人工判断 | 明确删还是留 |
| 4 | 清理历史遗留代码 | `Remove-Item` 或代码编辑 | 文件删除/代码精简 |
| 5 | 更新 architecture_check 白名单 | `check_dead_code()` | 误报不再重复 |
| 6 | 重启 dev.py 验证 | dev.py | DEADCODE 报告减少 |

### 12.3 快速诊断入口

```bash
# 查所有服务最新日志
tail -5 .dev_logs/back.log
tail -5 .dev_logs/front.log
tail -5 .dev_logs/chat.log

# 查端口占用
netstat -ano | findstr "8320 8321 5173 8765"

# 重启全部
Ctrl+C → python dev.py
```

### 12.4 调试原则

1. **先复现** — 确保能稳定复现问题
2. **查证据** — 用 MCP 工具收集数据，不猜测
3. **最小修复** — 只改解决问题的最小代码
4. **全验证** — 修复后：查控制台 + 查网络 + 截图
5. **清理** — 修复后删除调试代码


---
