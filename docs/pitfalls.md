# FlyPig 开发踩坑记录

## 1. PowerShell `&&` 运算符兼容性

**问题**: `subprocess.Popen` 用 `shell=True` 在 Windows 执行命令时，如果父进程是 PowerShell 5.1，含 `&&` 的命令会报错。

**错误信息**:
```
标记“&&”不是此版本中的有效语句分隔符。
```

**原因**: `&&` 是 cmd.exe 语法（条件执行），PowerShell 5.1 **不支持**（PS 7+ 才支持）。

**修复**: 将 Windows 路径中的 `&&` 改为 `&`。

| 运算符 | cmd.exe | PowerShell 5.1 |
|--------|---------|----------------|
| `&&` | ✅ 条件执行 | ❌ 不支持 |
| `&` | ✅ 无条件执行 | ✅ 调用运算符 |
| `;` | ❌ 不支持 | ✅ 顺序执行 |

**参考**: `tools.py` 中所有 `subprocess.Popen(..., shell=True)` 的 Windows 命令。

---

## 2. VS Code `terminal.sendSequence` CLI 问题

**问题**: 用 `code --command "workbench.action.terminal.sendSequence" --args '{"text":"cmd"}'` 试图向新终端发送命令，结果打开了 VS Code 的命令面板对话框。

**原因**: `code --command` 对 `sendSequence` 传参不可靠，VS Code 无法从 CLI 正确传递复杂参数给该命令。

**修复**: 改用"创建临时脚本 + 打开新终端 + 提示用户 `source`" 的方式。

```python
# 错误做法 - 打开对话框
code --command "workbench.action.terminal.sendSequence" --args '{...}'

# 正确做法
code --command "workbench.action.terminal.new"          # 开新标签页
# 用户在新终端中执行: source /tmp/flypig/cmd_xxx.sh     # 运行脚本
```

---

## 3. `subprocess.run()` 阻塞对话终端

**问题**: `subprocess.run()` 是阻塞调用，命令执行期间 flypig 无法继续工作。

**修复**: 始终改用 `subprocess.Popen()`（非阻塞），在新终端或后台运行命令。

---

## 4. WSL 路径转换

**问题**: 在 WSL 中需要将 Linux 路径转为 Windows 路径才能传给 `cmd.exe`。

**修复**: 使用 `wslpath -w /path/to/file` 转换。

```python
win_path = subprocess.run(
    ['wslpath', '-w', workspace],
    capture_output=True, text=True
).stdout.strip()
```

---

## 5. VS Code 终端检测

**检测方式**: 通过 `TERM_PROGRAM` 环境变量判断是否在 VS Code 终端中运行。

```python
self.is_vscode = os.environ.get('TERM_PROGRAM', '') == 'vscode'
```

**注意**: Cursor 等 VS Code 系 IDE 可能设置不同的值，需要额外适配。

---

## 6. WSL 中 Python 环境检测

**问题**: `platform.system()` 在 WSL 中返回 `"Linux"`，`os.name` 返回 `"posix"`，容易误判。

**检测方式**: 通过 `uname -r` 输出是否包含 `"microsoft"` 来判断 WSL。

```python
def _is_wsl(self) -> bool:
    try:
        return 'microsoft' in subprocess.run(
            ['uname', '-r'], capture_output=True, text=True, timeout=2
        ).stdout.lower()
    except Exception:
        return False
```

---

## 7. Windows 环境变量 `PSModulePath` 检测 PowerShell

**检测方式**: `os.environ.get('PSModulePath')` 在 PowerShell 会话中始终存在。

**注意**: 如果在非 PowerShell 环境中运行 Python（如从 CMD 启动），该变量不存在，回退到 cmd.exe 模式。

---

## 8. `timeout` 变量未定义 bug

**问题**: `tools.py` 原始代码中 `subprocess.run(timeout=timeout)` 使用了未定义的变量 `timeout`。

**修复**: 改为 `args.get("timeout", 60)` 获取。

---

## 9. 抓取大模型定价页的困境

**问题**: 试图自动抓取 DeepSeek/OpenAI/Anthropic 官方定价页提取价格，但不同页面结构差异大且可能随时变化。

**尝试方案**:
1. 用 `urllib` 下载页面，正则匹配 `$X.XX` 模式
2. 根据模型名附近的上下文提取对应价格

**遇到的问题**:
- OpenAI 定价页用 JS 渲染，静态 HTML 抓不到数据
- Anthropic 页面结构频繁变动
- 解析逻辑脆弱，维护成本高

**最终方案**: 采用"在线抓取 + 内置参考表"分层策略。
```
在线抓取成功 → 显示"来自官方定价页"
在线失败，内置表有 → 显示"参考价，未查到官方数据"
都没有 → 显示"未获取到价格信息"
```

**内置价格表**位于 `pricing_fetcher.py` 的 `BUILTIN_PRICES`，覆盖主流模型。更新价格只需改这一个地方。

---

## 10. 模型配置的冗余问题

**问题**: 模型列表同时在 `config.yaml` 和 Python 代码中维护，加模型需要改两处。

**演进过程**:
```
v1: cli.py 硬编码 MODELS                → 改代码
v2: config.yaml 完整模型配置               → 改 YAML（冗余字段多）
v3: config.yaml 只写名字 + model_registry → 改 registry 一处
```

**最终方案**: `model_registry.py` 作为单一模型来源，`config.yaml` 只记录用户偏好（default_model, api_keys）。

---

## PTY/SSE 架构重构 (2026-05)

> WebSocket → SSE 迁移 + PTY 终端恢复 · 本次重构解决了 AI 对话和 PTY 终端共用 WebSocket 通道导致的一系列问题。

### 1. WebSocket 通道冲突

**问题**: AI 模型对话第二条消息卡死，终端也连不上。

**原因**: SocketIO 的多路复用机制下，AI 对话流和 PTY 字节流共用同一条 WS 通道，消息交织、顺序错乱。

**修复**: AI 对话完全迁移到 SSE（单向 HTTP 流），WS 仅用于 PTY 终端，物理上分离。

```
❌ 旧: Agent(POST) + SSE ← WebSocket ──┐
                                        ├── 前端
    PTY(WS) ──────────────────────────────┘
✅ 新: Agent(POST) → SSE (text/event-stream)   (分离通道)
    PTY(WS) → /ws/pty/<term_id>                (分离通道)
```

---

### 2. `call_soon_threadsafe` 与 `run_coroutine_threadsafe` 的区别

**问题**: Agent 事件推不到前端。

**原因**: `call_soon_threadsafe` 调度 `async def` 时，只调用函数拿到协程对象然后丢弃，协程不会被 await。

```python
# ❌ call_soon_threadsafe → async def → 协程被丢弃
self._loop.call_soon_threadsafe(self._broadcast_func, data)

# ✅ run_coroutine_threadsafe → 真正调度协程
asyncio.run_coroutine_threadsafe(self._broadcast_func(data), self._loop)
```

---

### 3. SSE 跨线程 EventEmitter 选择

**问题**: Agent 线程安全桥接到 Quart 异步协程。

**尝试方案**: `call_soon_threadsafe` ❌ / `run_coroutine_threadsafe` 直接发 SSE ❌

**最终方案**: `threading.Queue` + executor 轮询 ✅

```python
class _SseHook:
    def push(self, event_type: str, **kw):
        self._queue.put_nowait(json.dumps({"type": event_type, **kw}))
```

---

### 4. PTY 启动失败 + 静默关闭 WebSocket

**问题**: 终端面板空白无任何反馈。

**原因**: `pywinpty` 未安装时 `Terminal.create()` 返回 `False`，`ws_pty` 直接 `return` 关闭 WS，**不发任何错误消息**，前端陷入无限重连循环。

**修复**: 先发 `{"type":"error","msg":"..."}` 再关闭。

---

### 5. 前端自动重连无限循环

**问题**: WebSocket 断开后一直重试永不停。

**修复**: 限制最多 3 次，超限后显示"重连失败，请点击 ↺ 重试"。

---

### 6. xterm.js FitAddon 在隐藏容器中失效

**问题**: 终端折叠后展开，内容显示不全或空白。

**原因**: CSS `display:none` 时 `clientWidth/clientHeight` 为 0，`FitAddon.fit()` 算出 0 行。

**修复**: 折叠状态跳过初始化，展开时按需创建。

---

### 7. `@copy_current_websocket_context` 的必要性

**问题**: `pty_reader` 线程向 WS 发送数据失败或发错客户端。

**原因**: Quart 的 `websocket` 是 context-local proxy，独立线程调用时上下文丢失。

**修复**: 用装饰器包裹发送函数。

```python
@copy_current_websocket_context
async def pty_send(data: bytes):
    await websocket.send(data)
```

---

### 8. pywinpty/winpty 包名不统一

**问题**: pip 安装用 `pywinpty`，conda 安装用 `winpty`。

**修复**: 循环尝试两种模块名。

```python
for mod_name in ("pywinpty", "winpty"):
    try:
        pty_mod = __import__(mod_name)
        break
    except ImportError:
        continue
```

---

### 9. SSE `data:` 行分片解析

**问题**: SSE 流式数据可能一行被拆成多次 `reader.read()`。

**修复**: 累计 buffer + `split('\n')` + 尾部残留处理。

```javascript
buffer += decoder.decode(value, {stream: true});
const lines = buffer.split('\n');
buffer = lines.pop() || '';
for (const line of lines) {
  if (line.startsWith('data: ')) JSON.parse(line.slice(6));
}
```

---
