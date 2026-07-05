# 规范与测试 — 质量保障体系

> **来源**：架构重构全流程讨论（architecture_check → pre-commit → CI → mypy → 测试）
> **关联文档**：[architecture-guide.md](architecture-guide.md)、[backend-modules.md](backend-modules.md)、[adversarial-system.md](adversarial-system.md)、[tech-stack.md](tech-stack.md)、[ui-refactor.md](ui-refactor.md)（自动化检查清单由 UI 审计驱动）

---

## 零、完整流程演示

> 下面演示一次完整的代码修改从"写代码"到"合入主分支"的全流程，
> 每一步检查什么、拦截什么、如果失败怎么办。

### 第 1 步：写代码

你在 IDE 里改了 `acl/pricing.py`，新增了一个转换函数，同时不小心引入了一个 bug——忘了定义某个常量。

**此时没有任何拦截**，你甚至可以先不跑任何命令，继续写下一个文件。

### 第 2 步：`git commit`（pre-commit 拦截）

```bash
git add flypig/acl/pricing.py
git commit -m "feat: 新增定价转换函数"
```

commit 时 pre-commit 自动运行 5 个 hook：

```
ruff          → 检查你的代码风格，如果有问题自动修复
ruff-format   → 自动格式化代码
mypy          → ❌ 发现未定义的常量 PRICE_KEY！commit 被阻止
ESLint        → 跳过（只扫前端文件）
Vitest        → 跳过（只扫前端文件）
```

**失败后怎么办**：修复 mypy 报的错误 → 重新 `git add` → 重新 `git commit`

```bash
# 修完 bug 后重新提交
git add flypig/acl/pricing.py
git commit -m "feat: 新增定价转换函数"
# ✅ 这次 pre-commit 全部通过，commit 成功
```

### 第 3 步：`git push`（CI 远程检查）

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

### 第 4 步：全部通过，合并 PR

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
你写代码 ──→ git add ──→ git commit ──→ git push ──→ PR合并
                            │                 │
                        pre-commit          GitHub CI
                            │                 │
                     ┌──────┼──────┐    ┌─────┼──────┐
                     ↓      ↓      ↓    ↓     ↓      ↓
                   ruff  mypy  ESLint  ruff  mypy  pytest
                   │      │     Vitest  │     │     cov
                   └──全部通过才允许─────┘     │     │
                                        import  Vitest
                                        linter
                                        └──全部通过才允许合并──┘
```

### `pre-commit` 和 `CI` 的对比

| 维度 | pre-commit | CI |
|------|-----------|-----|
| 触发时机 | `git commit` 时 | `git push` 后 |
| 运行位置 | 你本地电脑 | GitHub 服务器 |
| 扫描范围 | 只扫 staged 文件 | 全量代码 |
| 运行时间 | <10 秒 | 3-5 分钟 |
| 拦截效果 | 不让劣质代码进入本地仓库 | 不让劣质代码合入主分支 |
| 能绕过吗 | `git commit --no-verify` | 不能（除非修改 CI 配置） |

> **核心原则**：pre-commit 是"快捷过滤"，CI 是"最终裁决"。两者都在才能防止劣质代码流入主分支。

---

## 一、总览：四道防线

```
commit 前（pre-commit） → push 后（CI） → 部署前（门禁） → 线上（监控）
      ↓                    ↓                 ↓               ↓
   10秒内                3-5分钟           可配置          持续
   本地拦截              远程全量检查       硬性门槛        渐进增强
```

---

## 二、第一道防线：pre-commit hook

配置文件：`.pre-commit-config.yaml`

### hook 清单

| hook | 检查内容 | 作用域 | 修复方式 |
|------|---------|--------|---------|
| `ruff` | Python 代码风格（300+ 规则） | 所有 `.py` | `--fix` 自动修复 |
| `ruff-format` | Python 代码格式化 | 所有 `.py` | 自动格式化 |
| `mypy` | Python 静态类型检查 | `domain/` `application/` `acl/` `shared/` | 手动修复 |
| `eslint` | 前端 Vue/JS 规范（200+ 规则） | `static_vite/src/` | 手动修复 |
| `vitest` | 前端单元测试 | `static_vite/src/` | 手动修复 |

### 运行规则

- 只在 **staged 文件** 上运行（快，<10 秒）
- 任何一个 hook 失败 → commit 被阻止
- ruff 自动修复后文件会自动加入 staged

---

## 三、第二道防线：GitHub Actions CI

配置文件：`.github/workflows/ci.yml`

### 执行顺序

```
① Ruff Python 检查        （全量，含所有规则集）
② mypy 静态类型检查        （domain/application/acl/shared）
③ ESLint 前端检查          （全部 src/）
④ 架构合规检查              （architecture_check.py + frontend_check.py）
⑤ 层依赖检查               （import-linter DDD 分层约束）
⑥ Vitest 前端测试          （全部 *.test.js）
⑦ pytest + 覆盖率           （后端单元测试，fail_under=10%）
```

### 触发条件

- `push` → `main`, `architecture-refactor`, `develop`
- `pull_request` → `main`

### 退出规则

- 任何步骤失败 → CI 变红 → 不允许合并
- 覆盖率低于 10% → CI 变红

---

## 四、检测工具详解

### 4.1 ruff — Python 代码风格

配置位置：`flypig/pyproject.toml` → `[tool.ruff]`

```toml
[tool.ruff.lint]
select = ["E","F","I","N","W","B","UP","SIM","RUF100","PL","TRY","PTH","C4","RUF","ASYNC"]
```

覆盖 300+ 条规则，用于替代 flake8 + isort + black。

### 4.2 mypy — Python 静态类型检查

配置位置：`flypig/pyproject.toml` → `[tool.mypy]`

```toml
[tool.mypy]
python_version = "3.11"
check_untyped_defs = true
warn_return_any = true
warn_unreachable = true
```

**重点拦截**：
- 未定义的变量（如 `PRICE_KEY`、`_CLASS_NAME`、`TRUNCATE_LENGTH`）
- None 未判空（`PricingEntry | None` → 取值前必须判断）
- 返回值类型不匹配
- 未使用的 `type: ignore` 注释

> **经验教训**：此前发现 3 个 mypy 能当场抓住的 bug（`PRICE_KEY` 未定义、`_CLASS_NAME` 未定义、`DEFAULT_POP_TIMEOUT` 未定义），但在写代码时未被发现，直到运行测试才暴露。mypy 可以在编码阶段就阻止这类问题。

### 4.3 ESLint — 前端代码规范

配置位置：`flypig/interface/web/static_vite/.eslintrc.json`

使用 `eslint:recommended` + `plugin:vue/vue3-recommended` 规则集。

### 4.4 Vitest — 前端测试框架

配置位置：`flypig/interface/web/static_vite/vitest.config.js`

基于 Vite 的测试框架，兼容 Vue 组件测试。与 Vite 共享同一份配置。

---

## 五、自定义架构检查

### 5.1 architecture_check.py

配置位置：`scripts/architecture_check.py`

共 **12 项** 检查，覆盖 ruff 和 mypy 不覆盖的 FlyPig 特有项：

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
| APICONTRACT | API 契约 | 路由路径是否匹配 `data/api-contracts.json` 定义 |
| DEPSEC | 依赖安全 | 依赖版本是否锁定（`>=` 无上限警告） |
| CONFIG | 配置规范 | `config.yaml` 是否存在、格式是否完整 |
| I18N | 国际化就绪 | 异常 code 是否有 i18n 翻译键 |
| TEST | 测试覆盖 | 每个业务模块是否有对应的测试文件 |

### 5.2 API 契约定义

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

### 5.3 frontend_check.py

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

## 六、测试体系

### 6.1 测试金字塔

```
         ╱─ E2E（端到端）─╲        ← 慢、贵、少（5%）
        ╱   集成测试   ╲
       ╱   单元测试     ╲         ← 快、便宜、多（60%）
```

### 6.2 测试类型

| 类型 | 测什么 | 特点 | 存放位置 |
|------|--------|------|---------|
| **单元测试** | 单个函数/方法的纯逻辑 | 毫秒级，mock 外部依赖 | `tests/unit/` |
| **集成测试** | 跨层交互（API→Service→DB） | 秒级，需要真实/内存依赖 | `tests/integration/` |
| **E2E 测试** | 完整业务流程（启动服务→用户操作→验证结果） | 分钟级，最脆弱 | `tests/e2e/` |
| **快照测试** | 前端 UI 渲染结果对比 | 用于防意外变更 | `src/**/__tests__/` |

### 6.3 测试覆盖率

- 当前阈值：`fail_under = 10%`
- 统计范围：`flypig/` 包（排除 `tests/` 和 `__pycache__/`）
- 随着项目成熟逐步提高：10% → 30% → 60%

### 6.4 编写规则

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

### 6.5 现有测试（截至 2026-07-04）

| 文件 | 数量 | 覆盖内容 |
|------|------|---------|
| `test_pricing_entry.py` | 4 | PricingEntry 值对象不可变性、相等性 |
| `test_portkey_acl.py` | 4 | Portkey 格式 → PricingEntry 转换 |
| `test_pricing.py` | 18 | 单位转换 / 模型匹配 / 价格提取 / default 格式 |
| `test_exceptions.py` | 12 | 统一异常体系 code/message/to_dict |
| `test_chat_response.py` | 12 | ChatResponse DTO 序列化 / 工厂方法 |
| `test_health.py` | 2 | health/ping 路由集成测试 |

**小计：55 个测试，全部通过**

### 6.6 优先补测顺序

```
第 1 优先级：acl/ 层（格式转换、外部系统适配）
第 2 优先级：domain/ 层（值对象、实体、异常体系）
第 3 优先级：application/ 层（DTO、编排逻辑）
第 4 优先级：API 路由（集成测试、响应结构锁定）
第 5 优先级：infrastructure/ 层（需要 mock 外部依赖）
```

---

## 七、AI 编程协作规则

### 7.1 写测试的时机

**不搞 TDD，先实现后立刻补测**：

```
你描述功能 → AI 写实现代码 → 你确认接口 → AI 补测试 → 跑通 → 下一个
```

### 7.2 什么时候用 TDD

只在以下场景值得：
- 计算公式 / 算法类（行为非常确定）
- 安全校验（要"锁死"行为）
- 重构旧代码（先写测试锁住行为再改）

### 7.3 共同的坑

| 问题 | 原因 | 解决方法 |
|------|------|---------|
| 测试挂了 debug 半天 | AI 写的测试本身有 bug | 先确认测试代码没错 |
| 接口改了测试要重写 | 接口没稳定就写了测试 | 确认接口满意后再补测试 |
| 空骨架文件被删除 | AI 以为"没用的空文件" | 骨架文件必须加 `# TODO` 标记 |

---

## 八、防止 AI 写出"一坨代码"的关键机制

```
ruff       → 风格一致，不能乱缩进/命名
mypy       → 类型安全，不能有未定义变量/未判空
architecture_check → 架构约束，不能跨层依赖/不注册
pre-commit → 不让劣质代码进入仓库
CI         → 不让劣质代码合入主分支
coverage   → 不能不写测试
API 契约   → 不能乱改接口
```

**任何一个机制失效 → 有问题的代码会被拦截。**

---

## 九、常见操作

### 运行全部检查

```bash
# 本地
pre-commit run --all-files     # 跑全部 pre-commit hook
python -m pytest tests/ -v     # 跑全部后端测试
python scripts/architecture_check.py  # 架构合规
mypy --config-file=flypig/pyproject.toml flypig/domain flypig/application flypig/acl flypig/shared

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


