---
name: plan-dev-toolchain-standards
overview: 将 MkDocs+mkdocstrings、Ruff D 规则、interrogate、pre-commit 写入 migration-roadmap.md 作为项目规范，同时更新 tech-stack.md
todos:
  - id: update-migration-roadmap
    content: 在 migration-roadmap.md 的 Step 1 前插入 Step 0，并在 Step 7 追加验证项
    status: completed
  - id: update-tech-stack
    content: 在 tech-stack.md 新增文档工具链行，补充 Ruff D 说明
    status: completed
  - id: update-architecture-guide
    content: 在 architecture-guide.md 导航索引中新增工具链文档引用
    status: completed
---

## 需求概述

更新 `migration-roadmap.md` 和 `tech-stack.md`，将开发者工具链（MkDocs + mkdocstrings 文档站、Ruff D pydocstyle 规则、interrogate docstring 覆盖率、pre-commit Git 钩子）写入项目文档规范，确保后续 AI 和开发者在编写 docstring 时有明确的规范和自动化校验工具。

## 核心要求

1. **migration-roadmap.md**：在 Step 1 之前新增 Step 0 "开发者工具链搭建"，包含四部分：

- MkDocs + mkdocstrings 文档站初始化
- Ruff D 规则（Google 风格 pydocstyle）
- interrogate docstring 覆盖率（阈值 >= 80%）
- pre-commit 钩子配置
Step 7 "清理+验证" 中补充「跑 interrogate」和「mkdocs build」验证项

2. **tech-stack.md**：技术选型表新增「文档」层次，包含 MkDocs、mkdocstrings、interrogate、pre-commit；Ruff 已有行补充 D 规则选择说明

3. **architecture-guide.md**：交叉引用索引表中新增工具链文档导航

4. 涉及文件三份：`docs/docs_refactor/migration-roadmap.md`、`docs/docs_refactor/tech-stack.md`、`docs/docs_refactor/architecture-guide.md`

## 技术方案

### 实现方式

直接编辑三份 Markdown 文档，在现有结构中追加内容：

1. **migration-roadmap.md** 改动点：

- 在 Step 1 上方插入新的 Step 0，格式与现有 Steps 一致（动作表格）
- Step 7 表格追加两条验证项

2. **tech-stack.md** 改动点：

- 在「DevOps」行下方新增「文档」层次行（MkDocs + mkdocstrings）
- 在现有 Ruff 行补充 D 规则说明
- 在表格末尾新增 interrogate 和 pre-commit 行

3. **architecture-guide.md** 改动点：

- 在导航索引表中新增一行指向文档工具链规范相关文档

### 无需新依赖

纯 Markdown 编辑，不涉及代码改动。

## 关键设计决策

### 为什么不拆成独立的 toolchain.md？

工具链是项目规范的一部分，不是可独立运行的模块。migration-roadmap.md 本身就是描述"怎么做"的规范文档，工具链放进去最合适。

### Step 0 而非塞进 Step 1

工具链搭建是编码前置条件（装依赖、配规则、装钩子），在 Step 1 "搭骨架"之前做，逻辑清晰。

### Ruff D 的选择

推荐 Google 风格（`convention="google"`），因为：

- Google 风格比 NumPy 风格占行少，适合小方法
- 比 Sphinx 风格更易读
- 与大多数 AI 模型的 docstring 输出习惯一致
- interrogate 不挑风格，只统计覆盖率

## 实现注意事项

- 保持现有关联文档引用行的完整（每个文件顶部的「关联文档」列表）
- 新增内容格式与原有表格/列表格式一致
- 不改动现有内容的任何文字