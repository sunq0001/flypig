# FlyPig - 开发路线图

## Phase 1: MVP (已完成)

**目标**: 可运行的基础 CLI 工具

### TODO

- [x] CLI 框架搭建
- [x] 基础文件操作 (read/edit/write)
- [x] 终端命令执行 (bash) - 支持终端隔离、非阻塞、多环境适配
- [x] DeepSeek API 集成
- [x] 成本追踪显示
- [x] 多模型支持 (OpenAI / Anthropic 配置就绪)
- [x] 模型注册表 (model_registry.py) — 单源模型管理
- [x] 配置重构 (config.yaml 精简 + 配置即代码)
- [x] 终端隔离 (开新终端不阻塞对话)
- [x] 模型价格自动获取 (在线 > 内置参考 > 提示无数据)
- [x] API Key 首次提示录入 (按提供商)
- [x] 文档体系 (docs/)

### 验收标准

```
$ python -m flypig
✓ 显示模型菜单
✓ 选中模型后自动获取价格
✓ API Key 缺失时提示录入
✓ 切换模型 / 查看成本
✓ 终端命令在新窗口/标签页执行
```

---

## Phase 2: 增强版

**目标**: 接近 Claude Code 体验

### TODO

**高优先级（省 Token，直接省钱）**:
- [x] 上下文压缩 (Tree-sitter裁剪) — 裁剪无关代码块，减少输入 token

**安全加固（沙箱隔离）**:
- [ ] 创建沙箱核心模块 (sandbox.py) — SandboxManager (Docker 容器生命周期/命令执行) + PathValidator (路径白名单/运行时审批) + SandboxConfig 数据类
- [ ] 构建沙箱 Docker 镜像 (Dockerfile.sandbox) — 基于 python:3.11-alpine，预装 bash/git/node/gcc/sudo，创建 flypig 非 root 用户 + passwordless sudo
- [ ] 沙箱配置系统 (config.yaml + config.py) — 新增 sandbox 配置段 (enabled/mode/Docker 资源/白名单/审计)
- [ ] 文件工具沙箱集成 (tools.py) — tool_read/write/edit/find/grep 走 PathValidator.check_path()，工作区外路径弹窗审批 (y/N/a)
- [ ] 命令执行沙箱集成 (tools.py) — tool_bash 双模式：阻塞 run_command(docker exec) + 非阻塞 spawn_command(弹终端 docker exec -it)
- [ ] Docker 安全加固 — --cap-drop=ALL / --no-new-privileges / --ulimit nproc=512 / --pids-limit=512 / --storage-opt size=10G / --read-only
- [ ] 闲置回收 + 审计日志 + 退出清理 — 300s 无活动自动 docker stop，所有命令写入 ~/.flypig/audit.log，退出时 docker rm -f

**中优先级（代码理解 + 省 Token）**:
- [ ] 增量Diff (只传变更) — 减少重复上下文
- [ ] LSP 代码智能 — 跳转定义、诊断、补全、悬停信息，让 Agent 具备 IDE 级的代码理解能力
- [ ] 短期记忆 (会话内)
- [ ] CLAUDE.md 支持

**低优先级（体验优化）**:
- [ ] ModelAdapter 多协议支持 (Anthropic 原生 SDK)
- [ ] 流式输出优化

---

## Phase 3: 记忆系统

**目标**: 完整的长期记忆能力

### TODO

- [ ] Qdrant 向量数据库集成
- [ ] RAG 语义检索
- [ ] 自动事实提取
- [ ] 记忆去重/衰减
- [ ] 历史会话恢复

---

## 里程碑

| 版本 | 目标日期 | 核心功能 |
|------|----------|----------|
| v0.1 | Week 2 | CLI + DeepSeek + 成本显示 + 多模型配置 |
| v0.3 | Week 4 | 多Provider + 压缩 |
| v0.5 | Week 8 | 完整记忆系统 |
| v1.0 | Week 12 | Beta 发布 |

---

## 风险与依赖

| 风险 | 缓解 |
|------|------|
| API成本 | 透明展示，用户自控 |
| 上下文幻觉 | 多层记忆验证 |
| API限流 | 指数退避 |
