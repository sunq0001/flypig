# FlyPig PTY/SSE 重构踩坑记录

> 2026-05-22 · WebSocket → SSE 迁移 + PTY 终端恢复

---

## 1. WebSocket 通道冲突：AI 对话和 PTY 共用一个 WS 连接

**问题**: AI 模型对话第二条消息卡死，终端也连不上。

**过程还原**:
```
原始设计: Flask + SocketIO (一个 WS 连接既传 AI 事件又传 PTY 数据)
         ↓
发现: AI 第二条消息卡死 → 怀疑 WS 多路复用问题
         ↓
尝试: 把 AI 对话改成 SSE，PTY 保留 WS
         ↓
修复后: AI 对话正常，但 PTY 终端被"暂时禁用"(前端函数全空)
         ↓
恢复: 实现 4 个终端函数 + 连接状态反馈
         ↓
        终于可以了 🎉
```

**原因**: SocketIO 的多路复用机制在复杂场景下容易出问题。当 AI 对话流和 PTY 字节流共用同一条 WS 通道时，存在消息交织、顺序错乱、事件处理冲突等风险。

**修复**: 将 AI 对话事件完全迁到 SSE（单向 HTTP 流），WS 仅用于 PTY 终端。两种协议物理上分离，互不影响。

```
❌ 旧方案:
   Agent (WS) ──┐
                 ├── 同一 WebSocket 连接 ── 前端
   PTY    (WS) ──┘

✅ 新方案:
   Agent (SSE) ──── POST /api/chat → text/event-stream
   PTY    (WS) ──── /ws/pty/<term_id> (独立连接)
```

---

## 2. SSE 模式：`asyncio.run_coroutine_threadsafe` 与 `call_soon_threadsafe` 的区别

**问题**: 从 `WsEventHook` 切换到 SSE 时，Agent 事件推不到前端。

**原因**: 原来的代码用 `self._loop.call_soon_threadsafe(self._broadcast_func, data)` 调度广播。但 `_broadcast_func` 是 `async def`，`call_soon_threadsafe` 只会调用函数拿到协程对象然后**丢弃**，协程永远不会被执行！

```python
# ❌ 错误：call_soon_threadsafe 会丢弃 async def 返回的协程
self._loop.call_soon_threadsafe(self._broadcast_func, data)
#                          ↑ 等于调用了:
#                          self._broadcast_func(data) → 拿到协程对象 → 丢弃

# ✅ 正确：使用 run_coroutine_threadsafe 真正调度协程
asyncio.run_coroutine_threadsafe(self._broadcast_func(data), self._loop)
```

**教训**: `call_soon_threadsafe` 只能调度普通函数。对于 `async def`，必须用 `run_coroutine_threadsafe`。

---

## 3. SSE 跨线程 EventEmitter 选择

**问题**: 选择什么机制把 Agent 线程的事件安全地桥接到 Quart 异步协程。

**尝试过的方案**:

| 方案 | 结果 | 问题 |
|------|------|------|
| `call_soon_threadsafe` + `async def` | ❌ 失败 | 协程被丢弃 (见 #2) |
| `run_coroutine_threadsafe` 直接发 SSE | ❌ 不稳定 | 跨线程 write 冲突 |
| `threading.Queue` + executor 轮询 | ✅ 成功 | 数据流清晰可靠 |

**最终方案**:

```python
# Agent 线程 (executor) → Queue → SSE reader 协程 → SSE Response

class _SseHook:
    def push(self, event_type: str, **kw):
        self._queue.put_nowait(json.dumps({"type": event_type, **kw}))

# 在 SSE handler 中:
async def _sse_reader(queue, response):
    while True:
        data = await asyncio.get_event_loop().run_in_executor(None, queue.get)
        await response.write(f"data: {data}\n\n".encode())
```

---

## 4. PTY 启动失败 + 静默关闭 WebSocket

**问题**: 终端面板空白，啥也没显示，但也没有错误。

**原因**: 当 `pywinpty` 未安装时，`Terminal.create()` 返回 `False`，`ws_pty` 处理函数检查到 `term.is_alive() == False` 后**直接 `return` 关闭了 WebSocket**，没有任何错误消息。

```python
# ❌ 旧代码：静默关闭
if not term.is_alive():
    return  # 前端收到 onclose，但不知道为什么

# ✅ 新代码：先发错误消息再关闭
if not term.is_alive():
    await websocket.send(json.dumps({
        "type": "error",
        "msg": "终端启动失败，请确保已安装 pywinpty/winpty (pip install pywinpty)"
    }))
    return
```

**影响**: 前端看不到错误，只有 `onclose` 事件，自动重连触发 → 又失败 → 再重连… 形成无限重试的死循环。

---

## 5. 前端自动重连无限循环

**问题**: WebSocket 断开后，前端自动重连，不停尝试一直不停止。

**原因**: 原始代码的 `ws.onclose` 没有任何重连次数限制：

```javascript
// ❌ 无限重连
ws.onclose = () => {
  setTimeout(() => _connectPtyWs(termId), 2000); // 永远重试
};

// ✅ 限次重连 + 状态反馈
ws.onclose = () => {
  if (_ptyReconnectCount < 3) {
    _ptyReconnectCount++;
    termStatus.value = 'connecting';
    setTimeout(() => _connectPtyWs(termId), 2000);
  } else {
    termStatus.value = 'error';
    _xterm.writeln('\x1b[31m[终端] 重连失败，请点击 ↺ 重试\x1b[0m');
  }
};
```

---

## 6. xterm.js FitAddon 在隐藏容器中失效

**问题**: 终端折叠后重新展开，终端内容显示不全或空白。

**原因**: 当终端面板 `v-show="false"` (CSS `display: none`) 时，xterm 容器的 `clientWidth`/`clientHeight` 为 0，`FitAddon.fit()` 计算出 0 行 0 列。

```javascript
// ❌ 在隐藏容器中初始化，fit 失败
function initTerminal() {
  // 没有检查 termCollapsed
  _xtermFit.fit();  // ← 在 display:none 中返回 0x0
}

// ✅ 折叠状态跳过初始化，展开时再创建
function initTerminal() {
  if (termCollapsed.value) return;  // ← 跳过
}
function toggleTerminal() {
  if (!termCollapsed.value && !_xterm) {
    initTerminal();  // ← 展开时按需初始化
  }
}
```

---

## 7. Quart `@copy_current_websocket_context` 的必要性

**问题**: 从 `pty_reader` 线程向 WebSocket 发送数据时，发送到了错误的客户端或抛出异常。

**原因**: Quart 的 `websocket` 对象是 `context-local proxy`，其真实目标由调用链中的 WS 上下文决定。从独立线程调用时上下文丢失。

```python
# ✅ 必须用 @copy_current_websocket_context 包裹发送函数
@app.websocket("/ws/pty/<term_id>")
async def ws_pty(term_id: str):
    @copy_current_websocket_context
    async def pty_send(data: bytes):
        await websocket.send(data)

    def pty_reader():
        while term.is_alive():
            data = term.read(4096)
            if data:
                # 通过包裹后的函数发送，确保上下文正确
                asyncio.run_coroutine_threadsafe(pty_send(data), loop)
```

---

## 8. pywinpty/winpty 包名不统一

**问题**: `Terminal._start_windows()` 需要根据安装方式尝试两种不同的模块名。

**原因**: pip 安装的包名是 `pywinpty`，conda 安装的是 `winpty`。两者 API 兼容，但 `__import__` 时需分别尝试。

```python
for mod_name in ("pywinpty", "winpty"):
    try:
        pty_mod = __import__(mod_name)
        break
    except ImportError:
        continue
```

---

## 9. SSE `data:` 行解析的留意点

**问题**: SSE 流式数据到达时间不确定，可能一行被拆成多次 `reader.read()`。

**处理方式**: 使用累计 buffer + `split('\n')` + buffer 尾部残留。

```javascript
let buffer = '';
while (true) {
  const {done, value} = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, {stream: true});
  const lines = buffer.split('\n');
  buffer = lines.pop() || '';  // 可能会有未完成的行
  for (const line of lines) {
    if (line.startsWith('data: ')) {
      const data = JSON.parse(line.slice(6));
      handleEvent(data);
    }
  }
}
```

---

## 总结

| 问题 | 原因 | 修复要点 |
|------|------|---------|
| WS 通道冲突 | SocketIO 多路复用 | AI → SSE, PTY → WS |
| 协程被丢弃 | `call_soon_threadsafe` + async def | 改用 `run_coroutine_threadsafe` |
| 静默 WS 关闭 | PTY 失败直接 return | 发错误消息再关闭 |
| 无限重连 | 前端无重连限制 | 最多 3 次 + 错误提示 |
| FitAddon 失效 | display:none 时 fit 返回 0 | 折叠状态跳过初始化 |
| WS 跨线程 | context-local proxy 丢失 | 用 `@copy_current_ws_context` |
| SSE 流式 | buffer 分片 | buffer + split 逐行解析 |
