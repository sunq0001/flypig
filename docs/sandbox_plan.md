## 产品概述

为 Flypig Agent 添加沙箱安全隔离层，确保 AI 执行的命令和文件操作不会危害主机系统。沙箱覆盖命令执行和文件系统两个维度，基于 Docker 容器实现命令隔离，基于路径白名单实现文件系统访问控制。

## 核心特性

### 命令执行沙箱

- 所有 tool_bash 命令在 Docker 容器内执行，与主机系统隔离
- **容器文件系统边界**：仅挂载工作区目录 `-v WORKSPACE:/workspace`，容器内无法访问宿主机任何其他路径（Docker 的 volume 机制是天然白名单）
- 容器资源限制（CPU/内存/超时），防止资源耗尽
- 可选的网络隔离（默认禁用容器网络，按需开启）
- 自动构建沙箱镜像（首次使用无感构建）
- 容器内以 `flypig` 非 root 用户运行，配置 passwordless sudo，`apt install` 等提权命令无缝执行
- **高危命令拦截**：`rm -rf /`、`dd`、`mkfs`、`chmod 777` 等模式匹配，弹窗要求用户确认后才放行
- **容器逃逸预防**：禁止 `--privileged`、`--pid=host` 等 docker in docker 参数
- **防御降级（Docker 加固）**：
  - `--cap-drop=ALL` — 丢弃所有 Linux capabilities，不给容器进程任何特权能力
  - `--security-opt=no-new-privileges:true` — 禁止通过 suid 等方式提权
  - `--ulimit nproc=512` — 限制进程数，防 fork bomb
  - `--ulimit nofile=256` — 限制文件描述符
  - `--pids-limit=512` — 限制总 PID 数
  - `--storage-opt size=10G` — 磁盘配额，防止 dd 填满磁盘
  - `--read-only --tmpfs /tmp:size=100m,noexec,nosuid` — 容器根文件系统只读，仅 /tmp 可写
- **审计日志**：所有执行的命令 + 时间戳 + SHA256 摘要 + 退出码 + 耗时，存储在 `~/.flypig/audit.log`
- **闲置自动回收**：容器 300 秒无活动自动 stop（不删除），下次使用时自动 restart，不占后台资源
- **会话清理**：Flypig 退出时自动 `docker rm -f` 销毁容器，不留残余文件和进程
- Docker Desktop 不可用时自动降级（禁用沙箱 + 提示）

### 文件系统沙箱

- 默认限制：文件读写操作只能访问工作区目录
- 混合模式：支持白名单扩展（区分只读和读写权限）
- **运行时审批**：访问被 PathValidator 拒绝时，弹窗询问用户是否临时放行，放行后加入会话级临时白名单
- 关键词黑名单：硬编码系统敏感路径（如 /etc/shadow, C:\\Windows\\System32），即使白名单配置失误也能兜底，**黑名单路径运行时审批也不会放行**
- 路径规范化：自动 resolve 路径，防御 ../ 等路径穿越攻击

### 配置体系

- 沙箱总开关（enabled: true/false）
- 模式选择（strict/mixed/disable）
- Docker 资源配置（CPU/内存/超时/网络）
- 白名单管理（readonly/readwrite 两级别）

## 技术选型

| 组件 | 方案 | 理由 |
| --- | --- | --- |
| 容器引擎 | Docker Desktop | 用户已安装，跨平台，隔离性强 |
| 基础镜像 | python:3.11-alpine | 轻量(~50MB)，预装 git/bash |
| 命令执行 | docker exec（持久容器模式） | 避免每次启动容器开销 |
| 路径验证 | 独立 PathValidator 类 | 可测试、可扩展、支持白名单 |
| 配置文件 | YAML（扩展 config.yaml） | 与现有配置体系一致 |


## 实现方案

### 系统架构

新增沙箱隔离层，所有工具调用先经过沙箱验证再执行：

```
Agent Core --> ToolExecutor --> SandboxManager --> Docker exec（命令执行）
                              --> PathValidator --> 白名单检查（文件操作）
```

### 核心模块设计

**SandboxManager (flypig/sandbox.py)**

- 管理 Docker 容器生命周期（启动/停止/健康检查）
- 自动构建沙箱镜像（检测本地是否存在，不存在则 build）
- `run_command(command, timeout, workdir)` — **阻塞模式**：`docker exec` 执行命令并返回 stdout/stderr（适合一次性命令：git/pip/compile）
- `spawn_command(command, workdir)` — **非阻塞模式**：在新终端窗口运行 `docker exec -it CONTAINER bash -c "cd /workspace && CMD"`（适合长驻命令：npm run dev / python server.py / tail -f）
- `_ensure_container()` 惰性初始化容器（首次使用时启动）
  - `docker create` 参数**硬编码**，完整示例：
    ```
    docker create
      --name flypig-sandbox
      -v WORKSPACE:/workspace:rw          # 工作区读写挂载
      -w /workspace
      --network none                       # 默认断网
      --user flypig
      --cap-drop=ALL                       # 丢弃所有capability
      --security-opt=no-new-privileges:true # 禁止suid提权
      --ulimit nproc=512                   # 防fork bomb
      --ulimit nofile=256                  # 文件描述符限制
      --pids-limit=512                     # PID总数限制
      --storage-opt size=10G               # 磁盘配额
      --read-only                          # 根文件只读
      --tmpfs /tmp:size=100m,noexec,nosuid # 仅/tmp可写
      --tmpfs /home/flypig/.cache:size=50m # npm/pip缓存
      flypig-sandbox:latest
      tail -f /dev/null                    # 保持容器运行
    ```
  - 启动后校验：`docker inspect` 确认 Mounts 列表长度=1 且 Source=WORKSPACE
  - 校验 `docker inspect --format '{{.HostConfig.Privileged}}'` 必须为 `false`
- 资源限制：CPU 1核 / 内存 1GB / 超时 120秒（可配置）
- 网络策略：默认 `--network none`，开启后使用 `--network bridge`
- **多终端并发**：每个 `spawn_command` 开独立终端窗口，所有命令共享同一个容器的文件系统状态（`npm install` 后再 `npm run dev` 无缝衔接）
- `_is_dangerous_command(command)` **高危命令检测**：正则匹配 `rm -rf /`、`dd if=`、`mkfs`、`> /dev/`、`chmod 777 /` 等模式，命中后触发用户确认弹窗
- `_request_user_approval(command)` **用户确认机制**：弹终端窗口/PowerShell 提示框，展示高危命令内容，用户输入 `y` 才放行，`n` 则拒绝
- `_audit_log(command, result)` **审计日志**：记录每个命令的时间戳、执行用户、命令内容、退出码、执行耗时，追加到 `~/.flypig/audit.log`
- `_idle_timeout_monitor()` **闲置回收**：记录最后一次命令执行时间，超过 `config.docker.idle_timeout`（默认300s）自动 `docker stop`；下次命令调用时 `docker start` 唤醒
- `cleanup()` **退出清理**：Flypig 进程退出时调用 `docker rm -f flypig-sandbox`

**PathValidator (flypig/sandbox.py)**

- `check_path(path, mode='read')` 验证路径是否允许访问
- 验证流程：resolve 规范化 → 黑名单拦截(硬拒绝) → 工作区检查 → 配置白名单检查 → 会话临时白名单检查
- 白名单支持只读(readonly)和读写(readwrite)两种权限级别，来源有两层：
  - **配置层**（config.yaml）：持久化白名单，可预配置 `~/.ssh`、`~/Downloads` 等常用路径
  - **会话层**（内存）：运行时审批通过后自动加入，会话结束后丢弃
- `request_path_approval(path, mode)` 拦截时触发用户确认：
  - 弹 PowerShell 提示框："AI 请求访问 C:\xxx，是否允许？(y/N/a)"
  - `y` = 本次放行 + 加入会话级临时白名单
  - `a` = always = 写入 config.yaml 持久化白名单 + 放行
  - `n` / 超时 = 拒绝
- 黑名单硬编码系统敏感路径，**任何模式均不放过**
- 返回值：通过返回 None，拒绝返回拒绝原因字符串

### 关键设计决策

| 决策 | 选择 | 理由 |
| --- | --- | --- |
| 容器模式 | docker exec（持久单容器） | 避免每次执行新容器的启动延迟(~2s vs ~50ms) |
| 命令执行模式 | 双模式：阻塞(`run_command`) + 非阻塞(`spawn_command`) | 一次性命令直接返回输出不弹窗；长驻命令开独立终端的 UX 不变 |
| 多终端并发 | 共享容器 + 各自终端 | `npm install` + `npm run dev` + `tail -f logs` 同时跑，互不干扰 |
| 系统敏感路径保护 | 关键词黑名单硬编码 | 即使白名单配置失误，也能兜底防破坏 |
| 降级策略 | Docker 不可用时禁用沙箱 + 提示用户 | 保持可用性，不阻塞用户工作 |
| 镜像构建 | 首次使用自动构建 + 可手动构建 | 零手动操作，同时提供灵活选项 |
| 容器内用户 | flypig 非 root + passwordless sudo | `apt install` 等提权命令走 sudo 执行，文件权限与容器隔离 |
| 高危命令 | 模式匹配 + 用户确认弹窗 | 无法自动判断的操作让用户最后把关 |
| 外部路径审批 | 弹窗 `y/N/a` + 会话/持久双级白名单 | 合法需求一键放行，黑名单硬编码兜底永远不放 |
| Docker 安全加固 | `--cap-drop=ALL --no-new-priv --ulimit --read-only` | 对标生产级容器安全配置 |
| 资源防滥用 | CPU/内存/磁盘/PID 四重限制 | 防 cryptominer、fork bomb、磁盘填满 |
| 闲置回收 | 300s 无活动自动 stop | 不占用后台资源 |
| 审计日志 | 时间戳 + 命令 + SHA256 + 退出码 | 事后追溯和取证 |


### 边界情况处理

- **Docker Desktop 未运行**: 捕获 docker 命令异常，降级为无沙箱模式，打印警告
- **白名单路径不存在**: readwrite 自动创建父目录；readonly 跳过
- **命令超时**: 使用 `docker stop --timeout x` + 读取已有输出，返回部分结果 + 超时提示
- **路径穿越攻击**: PathValidator 使用 `Path.resolve()` 规范化后再判断
- **合法访问外部路径**: PathValidator 拒绝后弹出确认框，用户选 `y` 则临时放行（加入会话白名单），选 `a` 则持久化到 config.yaml。用户也可以提前在 config.yaml 里配好 `whitelist_readonly: ["C:\\Users\\mss\\.ssh"]` 实现无感通过
- **容器内访问外部路径**: 白名单中的路径在容器启动时自动以额外 `-v` 挂载进容器（如 `-v C:\Users\mss\.ssh:/host-ssh:ro`），使容器内 bash 也能访问
- **Windows 路径**: 统一转换为 POSIX 风格，支持 `C:\xxx` 和 `C:/xxx` 两种格式
- **容器内文件编码**: 通过 volume 挂载工作区，文件编码与主机一致（UTF-8）
- **容器无法访问宿主其他路径**: Docker volume 是硬隔离，仅挂载 WORKSPACE 时容器内 `ls /mnt/c`、`ls /host` 等路径不存在，`cd ..` 也退不出 `/workspace` 边界
- **挂载点篡改防护**: `_ensure_container()` 启动后用 `docker inspect` 校验挂载列表，若发现非预期挂载（如多加了 `-v /:/host`）则立即销毁容器并报错
- **高危命令确认**: SandboxManager 检测到高危模式后阻塞执行，弹出 PowerShell 提示框要求用户输入 `y/N`；超时 30 秒无响应自动拒绝
- **容器内提权**: 容器内 `sudo` 命令走 passwordless sudo，无额外确认——因为容器本身已与宿主隔离，提权不会影响宿主
- **fork bomb 防御**: Docker `--ulimit nproc=512 --pids-limit=512`，`:(){ :|:& };:` 最多 512 进程后触发 OOM kill
- **磁盘填充防御**: `--storage-opt size=10G` 配合 `--read-only`，`dd if=/dev/zero of=bigfile` 撑爆 10G 后自动报错，不影响宿主磁盘
- **容器逃逸内核层面**: `--cap-drop=ALL --security-opt=no-new-privileges:true`，即使容器内有 suid 二进制也无法利用
- **闲置容器回收**: 300 秒无命令自动 `docker stop`，释放 CPU/内存；有命令到达时 `docker start` 自动唤醒
- **审计日志防篡改**: `audit.log` 记录每条命令的 SHA256 摘要，可事后交叉验证日志是否被修改
- **退出不留痕**: `cleanup()` 在进程退出时 `docker rm -f`，容器和临时文件彻底销毁

## 目录结构

```
flypig/
├── sandbox.py           # [NEW] 沙箱核心模块
│                        #   - SandboxManager: Docker 容器管理 + 命令执行
│                        #   - PathValidator: 文件系统路径白名单验证
│                        #   - 定义 SandboxConfig 数据类
├── Dockerfile.sandbox   # [NEW] 沙箱 Docker 镜像
│                        #   - 基于 python:3.11-alpine
│                        #   - 预装 bash, git, nodejs, npm, gcc, sudo
│                        #   - 创建 flypig 用户（非 root）+ passwordless sudo
│                        #   - 挂载 /workspace 作为工作目录
├── tools.py             # [MODIFY] 集成沙箱
│                        #   - __init__ 接收 sandbox_mgr 和 path_validator 参数
│                        #   - _resolve_path 加 path_validator.check_path 验证
│                        #   - tool_bash 在沙箱启用时走 sandbox_mgr.run_command
│                        #   - tool_read/write/edit/find/grep 都走路径验证
│                        #   - get_tools_schema 更新 bash 工具描述
├── config.py            # [MODIFY] 添加沙箱配置解析
│                        #   - Config.sandbox 属性
│                        #   - Config.sandbox_enabled 等快捷属性
├── config.yaml          # [MODIFY] 添加 sandbox 配置段
├── __main__.py          # [MODIFY] ToolExecutor 初始化时传入沙箱组件
docs/
├── requirement.md       # [MODIFY] 新增沙箱安全需求条目
├── prd.md               # [MODIFY] 新增沙箱技术方案章节
└── roadmap.md           # [MODIFY] 更新路线图（沙箱纳入 Phase 2）
```

## 配置内容

```
# config.yaml 新增
sandbox:
  enabled: true
  mode: "mixed"                     # strict / mixed / disable
  docker:
    image: "flypig-sandbox:latest"
    cpu_limit: 1.0
    memory_limit: "1g"
    timeout: 120
    network: false
    cap_drop_all: true                # 丢弃所有capability
    no_new_privileges: true            # 禁止suid提权
    disk_limit: "10g"                  # 磁盘配额
    pids_limit: 512                    # PID上限
    nproc_limit: 512                   # 进程上限
    nofile_limit: 256                  # 文件描述上限
    read_only_root: true               # 根文件系统只读
    idle_timeout: 300                  # 闲置回收秒数(0=禁用)
    auto_cleanup: true                 # 退出时清理容器
  filesystem:
    whitelist_readonly: []           # 只读白名单，也会以 -v 挂入容器供 bash 访问
    whitelist_readwrite: []          # 读写白名单，仅宿主侧文件工具可用，不挂入容器
    block_keywords:
      - "C:\\Windows\\System32"
      - "C:\\Windows\\System"
      - "C:\\Windows\\config"
      - "C:\\Program Files"
      - "/etc/shadow"
      - "/etc/passwd"
      - "/etc/sudoers"
      - "/root"
      - "/home"
```

## 数据流

1. 用户启动 Flypig，Config 加载 sandbox 配置
2. **main**.py 实例化 SandboxManager + PathValidator
3. 若 sandbox.enabled=True，SandboxManager 自动构建镜像 + 启动容器
4. 工具调用时：

- 文件操作（tool_read/write/edit）：
ToolExecutor 调用 PathValidator.check_path()
├─ 命中黑名单 → 直接拒绝（硬编码敏感路径永远不放行）
├─ 工作区/白名单内 → 放行
└─ 工作区外 + 非黑名单 → 弹窗用户审批
├─ y（本次+会话）→ 添加临时白名单 → 放行
├─ a（始终）→ 写入 config.yaml → 放行
└─ n / 超时 → 拒绝
- 命令执行（一次性/超时类，如 git/pip/compile）：
ToolExecutor 调用 SandboxManager.run_command()
├─ 高危检测 → 命中 → 弹窗用户确认 → 拒绝则返回错误
└─ 通过 → docker exec（阻塞）→ 返回 stdout
*注：容器内命令仅能访问挂载的工作区 + 白名单额外挂载的路径*
- 命令执行（长驻/交互类，如 dev server / watcher）：
ToolExecutor 调用 SandboxManager.spawn_command() → 弹新终端运行 docker exec -it（非阻塞）→ 返回终端已打开提示

5. 验证/执行结果返回给 Agent，Agent 继续处理

## 与现有代码的集成点

| 现有文件 | 修改点 | 影响范围 |
| --- | --- | --- |
| tools.py: `__init__` | 新增 sandbox_mgr, path_validator 参数 | 仅实例化时 |
| tools.py: `_resolve_path` | 调用 path_validator.check_path | 所有文件操作 |
| tools.py: `tool_bash` | 沙箱模式下：有timeout走sandbox_mgr.run_command(阻塞)，无timeout/标记持久走sandbox_mgr.spawn_command(弹终端) | 仅 bash 工具 |
| tools.py: `get_tools_schema` | 更新 bash 描述，添加 sandbox 信息 | 仅工具定义 |
| config.py | 新增 sandbox 属性 | 仅新增 |
| __main__.py | 构造 ToolExecutor 时传入沙箱组件 | 仅入口处 |


# Agent Extensions

文档更新阶段，使用 [subagent:code-explorer] 验证文档格式一致性，确保新需求条目编号与现有体系不冲突。
