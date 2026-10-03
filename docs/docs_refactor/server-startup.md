# 服务启动与访问

> **来源**: `dev.py`、`scripts/dev-wsl.sh`、`scripts/setup-wsl.sh`、`start_wsl_flypig.sh`、`flypig/__main__.py`（启动流程整理 + 2026-10-03 实测）
> **关联文档**: `operations.md`（部署运维 / Docker）、`tech-stack.md`（技术选型）、`data-flow.md`（SSE 数据流）、`api-reference.md`（API 端点与事件格式）、`standards-testing-debugging.md`（改动后 MCP 自测流程）
>
> 本文只回答「**怎么把开发环境跑起来、怎么确认它活着、改完为什么不生效**」。
> 生产/容器部署见 `operations.md`；文档站自身的侧边栏登记见文末。

---

## 一、四个服务一览

`dev.py` 一次拉起四个热加载服务：

```text
back   后端 API      :8320   python -m flypig --port 8320 --reload
chat   聊天服务      :8321   node server.js                (在 flypig/interface/chat-server)
front  前端页面      :5173   node node_modules/vite/bin/vite.js --host --force
docs   架构文档站    :8765   python docs/serve_docs.py --port 8765 --watch
```

要点：

- **访问入口是 5173，不是 8320**。前端页面经 Vite 代理访问后端：
  `/api`、`/api/chat`、`/sse` → `http://127.0.0.1:8320`（见 `flypig/interface/web/static_vite/vite.config.js`）
- 当前前端的对话流走 **8320 的 `POST /api/chat`**（`chat_bp`，SSE）。
  8321 的 chat-server 是 AI SDK 的并行/备用通道（同样暴露 `POST /api/chat`），前端暂未接。
- 四个服务全部热加载，**改代码不需要重启**（见「六、热加载矩阵」）。

---

## 二、前置依赖

- **Python ≥ 3.11**，安装项目与开发依赖：

```bash
pip install -e flypig/.[dev]
```

这一步很关键：`dev` extra 里含 `uvicorn[standard]`（`--reload` 与文档热重载所需的 `watchfiles` 都由它带入）、
`import-linter`、`pre-commit`、`pytest`、`ruff`、`bandit`。
主依赖里还有 `watchdog`（文件监听：AI 改文件后推 SSE 通知前端刷新编辑器）。

- **Node.js 20+**（前端 Vite + chat-server），两处各自安装：

```bash
cd flypig/interface/web/static_vite && npm install
cd flypig/interface/chat-server      && npm install
```

- **可选 · 本地模型**：本机装 Ollama（默认 `http://127.0.0.1:11434`），
  在模型下拉里选「💻 本地模型」（实测 `qwen2.5:3b` 可用）。不装不影响云端模型。

- **可选 · 链路追踪**：根目录 `docker-compose.otel.yml` 起 Jaeger。
  **不启动也不会阻塞**：OTLP 导出器设了 1 秒超时，日志里出现 `Failed to export span batch`
  或 `Transient error HTTPConnectionPool(host='localhost', port=4318)` 属正常噪声。

---

## 三、启动方式

### 3.1 推荐：`dev.py` 一键四服务（Windows / 本机）

```powershell
python dev.py          # 或双击 start-dev.bat / dev.bat / dev-wsl.bat
```

- `Ctrl+C` 停止全部
- 启动前先跑两项门禁：架构检查（**不通过会拒绝启动**）、层依赖检查（仅告警）
- 每个服务的输出写入独立日志：`.dev_logs/back.log`、`chat.log`、`front.log`、`docs.log`

### 3.2 WSL（本仓库实际开发环境）

方案 A —— `concurrently` 前台多路输出：

```bash
bash scripts/dev-wsl.sh          # Windows 侧可双击 dev-wsl.bat
```

方案 B —— tmux 常驻（推荐，可随时回看输出）：

```bash
bash start_wsl_flypig.sh         # 内部：tmux new-session -d -s flypig "python3 dev.py"
```

等价的纯手工命令（本次联调使用的就是这套）：

```bash
wsl -e bash -lc "cd /mnt/c/Users/mss/WorkBuddy/Flypig-agent && \
  export PYTHONPATH=/mnt/c/Users/mss/WorkBuddy/Flypig-agent:\$PYTHONPATH && \
  tmux new-session -d -s flypig 'python3 dev.py'"

tmux capture-pane -p -t flypig | tail -30   # 看 dev.py 实时输出
tail -40 .dev_logs/back.log                 # 看后端日志
tmux kill-session -t flypig                 # 停止全部
```

首次在 WSL 里跑，先执行一次环境准备：`bash scripts/setup-wsl.sh`。

### 3.3 只跑后端（单服务调试）

```bash
python -m flypig --port 8320 --reload
```

CLI 只支持三个参数（`flypig/__main__.py`）：

```text
--port    默认 8320
--host    默认 0.0.0.0
--reload  用 uvicorn 跑（只监控 flypig/ 目录）；不带则用 Hypercorn 生产模式
```

### 3.4 Docker

- 根 `Dockerfile`：`python:3.12-slim` + Node 22，`EXPOSE 8320 8321 5173 8765`，`CMD ["python", "dev.py"]`
- 根 `docker-compose.yml`（另有 `flypig/docker-compose.yml`，当前是空占位文件）
- 容器化部署的完整讨论见 `operations.md`

> ⚠️ **根目录 `start.bat` / `stop.bat` / `restart.bat` 已失效**：
> 它们调用 `python -m flypig --web` 和 `python -m flypig --kill-port 8321`，
> 而 CLI 里**不存在** `--web` / `--kill-port` 参数，执行会直接被 argparse 拒绝。
> `stop-dev.bat` 是按端口杀进程的旧脚本，在 `dev.py` 存活时会误杀服务，也不要用。
> 统一用 `dev.py`（或 `start-dev.bat` / `dev.bat` / `dev-wsl.bat`）。

---

## 四、`dev.py` 到底做了什么

1. 校验 `flypig` 包可导入，否则提示 `pip install -e flypig/`
2. 运行 `scripts/architecture_check.py`：**不通过则打印报告并 `exit(1)`**（30 秒超时则跳过；
   缺测试文件属 `WARN` 不算失败）
3. 运行 `lint-imports --config flypig/pyproject.toml`：不通过只打印告警，不拦截
4. 用 `asyncio.create_subprocess_shell` 并发拉起四个服务，输出 `>> .dev_logs/<tag>.log 2>&1`
   （不用 PIPE，规避 Windows 下 `asyncio.subprocess.PIPE` 关闭导致误杀进程的老问题）
5. 每 5 秒探活一次；进程崩溃按 1→5 秒递增延迟自动重启，**最多 10 次**
6. Windows 下把 stdout 重编码为 UTF-8（`chcp`/GBK 乱码问题）
7. Node 优先用 `~/.nvm/versions/node/v22.23.1/bin/node`：WSL 里的 `/usr/local/bin/node`
   常是 Windows 版，用它会导致服务监听到错误的 localhost

---

## 五、访问地址与自检

页面与站点：

```text
前端   http://localhost:5173      ← 日常入口
文档   http://localhost:8765
```

接口自检（全部经 5173 代理，一行验证后端是否活着）：

```bash
curl -o /dev/null -w "%{http_code}\n" http://localhost:5173/api/health      # 期望 200
curl http://localhost:5173/api/config                                       # 模型列表 / 默认模型 / 工作区
```

两条 SSE 通道（前端实时刷新的来源）：

- `GET /api/events/files` —— 文件变更事件（watchdog 监听工作区）。
  连上先收 `event: connected`，之后每条变更推 `data: {"action":"...","name":"..."}`
- `GET /api/chat/tool-events?session=<id>` —— 工具调用事件（`tool-call` / `tool-result`），
  结束推 `data: [DONE]`。与 `/api/chat` 的 ai-sdk 文本流**物理隔离**，避免破坏打字机效果
- 注意：`tool-events` 在没有事件的安静期**不会发首包**（连接已建立但看不到响应头），这是设计如此；
  `events/files` 则会在连上时立即发首包。所以「curl 3 秒没输出」不代表坏掉

对话接口：`POST /api/chat`（SSE），由后端 8320 提供。

---

## 六、热加载矩阵（改完不用重启）

- 前端 `flypig/interface/web/static_vite/src/**` → Vite HMR 即时生效
  （`server.watch.usePolling = true, interval = 500`，WSL 挂载盘必须靠轮询）
- 后端 `flypig/**/*.py` → uvicorn `--reload` 自动重启；**只监控 `flypig/` 目录**
  （根目录临时文件不会触发 reload）
- 文档 `docs/**/*.md` → 8765 的 `--watch` 热重载
- `.dev_logs/*.log` 变化只是日志追加，不会触发任何 reload

**需要手动重启 `dev.py` 的情况**：改了 `dev.py` 自身、改了依赖清单
（`flypig/pyproject.toml`、两个 `package.json`）并重新安装。

---

## 七、WSL 特别注意

1. **从 Windows 直连 8320 可能不通——这不是故障**。后端绑 `0.0.0.0`（IPv4 单栈），
   而 Vite / Node 是双栈监听，所以从 Windows 侧探测常见结果：`5173` ✅、`8321` ✅、`8765` ✅、`8320` ❌。
   前端始终通过 **Vite 代理**（在 WSL 内部执行）访问后端，所以页面功能完全正常。
2. SSE 能推流依赖 `vite.config.js` 里这三项，**别删**：
   `Accept-Encoding: identity`（禁 gzip，否则事件被攒住）、`setNoDelay(true)`（关 Nagle）、`timeout: 0`。
3. Node 必须用 nvm 的 Linux 版；`dev.py` 会自动探测 `~/.nvm/.../v22.23.1/bin/node`，
   装了别的版本就改 `dev.py` 里那行路径常量。
4. 确认服务是否真的起来，看日志而不是只看端口（本页代码块一律顶格书写：
   文档站的 markdown 渲染器只识别顶格的代码围栏）：

```bash
tail -40 .dev_logs/back.log      # 出现 lifecycle startup OK / pricing 预热完成即可用
```

---

## 八、停止与重启

- `dev.py` 前台运行：`Ctrl+C`
- tmux 方式：`tmux kill-session -t flypig`
- **项目约定（重要）**：不要手动 kill/restart 单个 uvicorn/vite 进程，也不要另开一份，
  会和 `dev.py` 抢端口。改动没生效先刷新页面 / 看日志，仍不行就让整个 `dev.py` 会话重启。

---

## 九、故障排查

1. **`dev.py` 启动即退出** → 先跑 `python scripts/architecture_check.py` 看 `[FAIL]` 项
   （`[WARN]` 的缺测试文件不阻塞）。修好再启动。
2. **`Address already in use` / 端口被占** → 上一次的 dev 会话没退干净。
   关掉旧会话（tmux：`tmux kill-session -t flypig`）后重开，不要在半启动状态用旧 bat 脚本乱杀。
3. **前端 504 / `optimizeDeps` 报错** → 清 Vite 缓存：删 `node_modules/.vite`，刷新页面；
   `vite.config.js` 里已带 `--force` 启动参数。
4. **SSE 不推事件** → 确认请求走的是 5173（代理），而不是直连 8320；
   确认代理那三项 SSE 配置没被改回去。
5. **日志刷 `Failed to export span batch`** → OTel collector 没起，1 秒超时后放行，忽略即可（或用
   `docker-compose.otel.yml` 把 Jaeger 起起来）。
6. **本地模型不可用** → `ollama list` 确认模型已拉取；WSL 里连 Windows 宿主的 Ollama
   需用宿主 IP 而非 `localhost`。
7. **文档站看不到新文档** → 新 `.md` 放入 `docs/docs_refactor/` 后，还要在
   `docs/serve_docs.py` 的 `SIDEBAR_ITEMS` 里登记，否则不会出现在左侧导航。
8. **`git push` 报 `Connection closed by <ip> port 22` 或 SSH banner 超时** →
   到 `github.com:22` 的网络被阻断（典型表现：SSH 解析到异常 IP、`Connection timed out
   during banner exchange`、`Could not read from remote repository`）。
   改走 GitHub 的 **SSH-over-443** 通道即可，一次性生效、**不需要改 git 配置**：

```bash
git -c core.sshCommand="ssh -p 443" push \
  ssh://git@ssh.github.com:443/<owner>/<repo>.git <分支名>
```

   推送成功后同步本地跟踪引用（否则 `git status` 会一直显示「领先 N 个提交」）：

```bash
git -c core.sshCommand="ssh -p 443" fetch \
  ssh://git@ssh.github.com:443/<owner>/<repo>.git \
  <分支名>:refs/remotes/origin/<分支名>
```

   本仓库的实际命令（可直接复制）：

```bash
git -c core.sshCommand="ssh -p 443" push ssh://git@ssh.github.com:443/sunq0001/flypig.git architecture-refactor
```

   > 想长期生效：在 `~/.ssh/config` 里为 `github.com` 加 `Hostname ssh.github.com` 与 `Port 443`。

---

## 十、启动相关脚本速查

- `dev.py` —— 一键四服务（含门禁 + 崩溃重启），**首选**
- `dev.bat` / `start-dev.bat` —— Windows 一键调 `dev.py`
- `dev-wsl.bat` —— Windows 侧调 WSL 的 `dev-wsl.sh`
- `scripts/dev-wsl.sh` —— WSL 下用 `concurrently` 前台起四服务
- `scripts/setup-wsl.sh` —— WSL 首次环境准备（Node/npm 依赖等）
- `start_wsl_flypig.sh` —— WSL tmux 常驻启动（session 名 `flypig`）
- `flypig/__main__.py` —— 单服务入口（`--port/--host/--reload`）
- `docs/serve_docs.py` —— 文档站；新增文档记得登记 `SIDEBAR_ITEMS`
- `flypig/interface/web/static_vite/vite.config.js` —— 端口、代理、SSE 调优
- `.dev_logs/{back,chat,front,docs}.log` —— 四个服务的运行日志
