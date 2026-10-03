# 打字机效果实现 — Lesson Learnt

> **来源**: 2026-06-29 深度调试记录（前后端流式输出）
> **关联文档**: `chat-ux.md`（§6.3 打字机效果设计规格）、`frontend-arch.md`（前端架构）、`api-reference.md`（SSE 事件格式）、`data-flow.md`（SSE 数据流）、`operations.md`（热加载说明）

---

## 一、背景

FlyPig 需要实现"打字机效果"——AI 对话响应逐段/逐行显示，而非等待全部生成后一次性展示。这个功能在 Cursor、CodeBuddy、Claude 等主流工具中已是标配，用户期待值很高。

**调试耗时**：从发现问题到稳定运行，经历了约 30+ 轮调试，涉及前后端 5 个组件/模块，排查了 4 个不同的故障点。

---

## 二、关键发现（按排查顺序）

### 发现 1：AI SDK v7 API 变更

`@ai-sdk/vue` v7 中，`pipeDataStreamToResponse` 已废弃，应使用 `pipeUIMessageStreamToResponse`。前者的缺失是后端返回空内容的直接原因。

```
// ❌ v6 API（已不存在）
pipeDataStreamToResponse(res)

// ✅ v7 API
pipeUIMessageStreamToResponse(res)
```

### 发现 2：useChat shallowRef + in-place mutation（**根因**）

`@ai-sdk/vue` 的 `useChat` 使用 Vue `shallowRef` 管理消息数组。当流式数据到达时，`useChat` 内部通过 `replaceMessage` **原地修改** 已有消息对象的 `parts` 数组——**不改数组引用，不改消息对象的引用**。

```
// useChat 内部伪代码：
const msg = messages.value[messages.value.length - 1]
msg.parts.push(newPart)   // ← 改的是对象内部，不影响 messages.value 引用
```

Vue `shallowRef`**只跟踪 `.value` 层面的引用变化**，对象内部字段变动不会被检测到。因此下游组件（`MessageList`、`MessageItem`）收不到更新通知，UI 永远不会重渲染。

**结果**：后端逐 token 推送一切正常（`[sse]` 时间戳可以确认），但前端 Vue 不渲染，用户看到的就是"等待几十秒，内容一起出现"。

### 发现 3：修复方案 — 强制轮询换引用

解决方案是在 `ChatPanel.vue` 中，监听 `isStreaming` 状态，每当处于流式状态时，以 **固定间隔** 浅拷贝 messages 数组：

```javascript
// ChatPanel.vue
let forcePoll = null
watch(isStreaming, (v) => {
  if (v) {
    const poll = () => {
      messages.value = messages.value.map(m => ({...m}))
    }
    poll()
    forcePoll = setInterval(poll, 200)
  } else {
    if (forcePoll) { clearInterval(forcePoll); forcePoll = null }
  }
})
```

**为什么是 200ms 而不是更短**：
- 后端 SSE token 到达间隔大约 50-100ms
- 200ms 让每次轮询能 batch 到 2-4 个 token，呈现"每 200ms 跳一段"的效果
- 不会让浏览器被 16ms rAF 空转消耗
- 用户视觉上接近"逐行显示"（CodeBuddy 风格）

### 发现 4：双保险 — MessageItem 层再轮询

由于 Vue 的异步渲染机制，即使 `ChatPanel` 更新了数组引用，`MessageItem` 的 `props.message` 可能在同一次 tick 内还没拿到最新内容。额外在 `MessageItem` 内设一个 100ms 的 `setInterval` 兜底读取：

```javascript
// MessageItem.vue
const dataTimer = setInterval(() => {
  if (isUser.value) return
  const cur = getFullText(props.message)
  if (cur.length > lastKnown.length) {
    displayText.value = cur
    lastKnown = cur
  }
}, 100)
```

**效果**：`ChatPanel` 每 200ms 通知 Vue 重新分发 props → `MessageItem` 每 100ms 检查并显示最新内容。

### 发现 5：requestAnimationFrame 不适合此场景

最初尝试用 `requestAnimationFrame`（60fps，约 16ms 间隔）做轮询，结论是 **浪费性能、毫无意义**：
- 数据源（SSE token）每隔 50-100ms 才到达一条
- rAF 60fps 意味着每个数据更新之间有 3-6 个空转帧
- 相比 `setInterval(200)`，多消耗了约 10 倍的 JS 调用次数

**适用场景区分**：

| 方案 | 适用场景 | 不适合 |
|------|---------|--------|
| `setInterval(200-300ms)` | 数据源来自 SSE/网络，更新频率 ≤ 10Hz | 高频动画（60fps） |
| `requestAnimationFrame` | 动画、Canvas、持续运动 | SSE 驱动的数据流 |
| `watch + nextTick` | 单次响应式变化 | useChat in-place mutation |

### 发现 6：内容格式兼容

`useChat` v7 在流式过程中，文本内容存储在 `message.parts[].text` 中，而非 `message.content`。而 `message.content` 只有在流式**结束后**才会被填充。

```javascript
// 兼容两种格式的提取函数
function getFullText(m) {
  if (!m) return ''
  if (m.content) return m.content       // 流结束后
  if (m.parts?.length)
    return m.parts.filter(p => p.type === 'text').map(p => p.text).join('')  // 流进行中
  return ''
}
```

建议将此函数提取为 `composables/useMessageText.js` 共享。

### 发现 7：SSE 格式差异

后端 `server.js` 使用的是 **plain text** 流（`res.write(delta)`），不是真正的 `text/event-stream`。前端 `useChat` 使用的是 **AI SDK 协议**（SSE 格式，事件类型 + JSON payload）。

两者差异导致：
- 如果用 `useChat` + `pipeUIMessageStreamToResponse`，后端必须返回 AI SDK 规定的 SSE 事件格式
- 如果用 `server.js` 的 plain text 流，前端不能使用 `useChat`，需要手写 `fetch` + `ReadableStream` 解析

当前架构选择：后端返回 AI SDK SSE 格式 → 前端 `useChat` 原生消费（保持与 LangGraph 生态兼容）。

### 发现 8：输入框 `t-textarea` 兼容性

TDesign 的 `<t-textarea>` 组件存在 keydown 事件代理 bug，表现为：

```
Cannot use 'in' operator to search for 'key' in ...
```

当用户在输入框打字时，`t-textarea` 的内部 keydown handler 抛出异常，导致输入字符不显示。**这不是打字机效果的问题，但与它同时出现干扰了调试**。

**修复**：替换为原生 `<textarea>`，配合 CSS 保持视觉一致。

---

## 三、最终架构图

```
                   后端 server.js                         前端 ChatPanel.vue
                ┌───────────────────┐               ┌─────────────────────────┐
                │ OpenAI SDK        │               │ useChat(@ai-sdk/vue)    │
  User Send ──► │ stream: true      │── SSE ──────► │ shallowRef messages[]   │
                │ for await(chunk)  │  token-by-    │ (in-place mutation)     │
                │   res.write(delta)│  token        │                         │
                └───────────────────┘               │ ┌───────────────────┐   │
                                                    │ │ forcePoll [200ms] │──►├── 浅拷贝数组
                                                    │ │ map(m => ({...m}))│   │  触发 Vue 渲染
                                                    │ └───────────────────┘   │
                                                    └──────────┬──────────────┘
                                                               │ props(新引用)
                                                               ▼
                                              ┌─────────────────────────────┐
                                              │ MessageItem.vue             │
                                              │ ┌───────────────────────┐   │
                                              │ │ dataTimer [100ms]     │──►├── 提取最新文本
                                              │ │ getFullText(props.msg) │   │  → displayText
                                              │ └───────────────────────┘   │
                                              └──────────┬──────────────────┘
                                                         │ 渲染
                                                         ▼
                                              ┌─────────────────────────┐
                                              │ 模板: {{ displayText }}  │
                                              └─────────────────────────┘
```

### 关键时序

```
时间轴 (ms):    0        200       400       600       800
后端 token:     ┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───┬───
                │   │   │   │   │   │   │   │   │   │   │
forcePoll:      ──┬──────┬──────┬──────┬──────┬──────┬──
                  │  batch 1   │  batch 2   │  batch 3
dataTimer:      ─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─┬─
                 10ms tick，发现新内容立即显示
```

后端 token 密集到达 → forcePoll 每 200ms batch 一批 → MessageItem 每 100ms 检测并显示。

---

## 四、处理过的故障汇总

| # | 故障现象 | 根因 | 修复 |
|---|---------|------|------|
| 1 | 后端报 `pipeDataStreamToResponse is not a function` | AI SDK v7 API 变更 | 改为 `pipeUIMessageStreamToResponse` |
| 2 | 前端等几十秒内容一起出现 | `useChat` shallowRef + in-place mutation，Vue 不渲染 | 加 `setInterval(forcePoll, 200)` 浅拷贝数组 |
| 3 | 输入框打字不显示 | TDesign `t-textarea` keydown bug | 替换为原生 `<textarea>` |
| 4 | 发送后新消息无内容 | MessageItem `displayText` 初始化时未读取已有文本 | mount 时调用 `getFullText()` |
| 5 | rAF 方案下内容跳跃不稳 | rAF 16ms 空转，数据源 50-100ms 才到达 | 改为 `setInterval(200)` |
| 6 | 逐字显示（用户要逐行） | 间隔太短+动画逻辑 | 移除逐字动画，仅实时显示最新全文 |
| 7 | 自适应算法不稳定 | 算法基于历史延迟动态调间隔 | 退回到固定 200ms 间隔 |

---

## 五、教训总结

### 5.1 技术判断

1. **不要假设框架会帮你处理所有响应式场景**。`@ai-sdk/vue` 的 `useChat` 封装度高，但内部实现细节（shallowRef + replaceMessage）与 Vue 的响应式假设相冲突。**高封装度的组件库 = 容易忽略内部实现。**

2. **日志 + 时间戳是最有效的调试武器**。在前后端各关键节点加时间戳（`[sse]`、`[stream]`、`[fe]`），一眼看出数据在哪里卡住：

   ```
   // 后端示例
   console.log(`[stream] ${Date.now()} write: "${delta}"`)

   // MessageList 示例
   console.log(`[fe] ${Date.now()} +${added} total=${val.length}`)
   ```

3. **不要在生产代码中追求"自适应算法"**。尝试过根据历史延迟动态调整轮询间隔（类似 TCP BBR），结果是算法本身引入了更多不确定性。固定间隔 + 合理值（200ms）比任何动态方案都稳定。

4. **用 setInterval 而不是 watch 做数据同步**。当数据源不是标准响应式时（如 in-place mutation），轮询是最简单可靠的方案。不要试图用 `watch` + `deep: true` 去追踪多层嵌套对象的变动——Vue 开发者自己都说不清 deep watch 的性能开销。

5. **setInterval 200ms 不会消耗性能**。每条消息只设一次 interval，流结束后清除，不会影响应用的其他部分。

### 5.2 协作判断

6. **用户说的"我试过了"往往是真的——先相信用户再找根因。** 最初多轮用户反复说"没有流式"，我们一直在后端找问题，但其实后端一直在正常工作。如果更早信任用户的反馈、更早在前端加日志时间戳，能节省一半时间。

7. **不要在一个 bug 没确认时引入第二个变更。** 打字机效果调试过程中，`t-textarea` 的 bug 和流式不显示的 bug 同时出现 → 分不清哪个现象对应哪个根因。应隔离环境（先用原生 textarea 排除一个变量）。

### 5.3 架构判断

8. **Vercel AI SDK 的 useChat + shallowRef 是已知的响应式陷阱**。如果未来遇到类似"数据源确定在跑，但 UI 不更新"的问题，优先怀疑：
   - 是不是 shallowRef？
   - 是不是 in-place mutation？
   - 要不要 force update？

9. **如果追求极致流畅的打字机效果，应该考虑替换 useChat 为手写 fetch + ReadableStream + deepRef**。但当前方案在 200ms 粒度下已经达到 CodeBuddy 级别的体验，不值得为 10% 的流畅度提升再投入工程时间。

---

## 六、可复用的代码片段

### ChatPanel 轮询

```javascript
// ChatPanel.vue — 打字机效果核心
let forcePoll = null
watch(isStreaming, (v) => {
  if (v) {
    const poll = () => {
      messages.value = messages.value.map(m => ({...m}))
    }
    poll()
    forcePoll = setInterval(poll, 200)
  } else {
    if (forcePoll) { clearInterval(forcePoll); forcePoll = null }
  }
})
```

### MessageItem 文本提取 + 轮询

```javascript
// MessageItem.vue
function getFullText(m) {
  if (!m) return ''
  if (m.content) return m.content
  if (m.parts?.length)
    return m.parts.filter(p => p.type === 'text').map(p => p.text).join('')
  return ''
}

// 立即显示已有文本
const initial = getFullText(props.message)
if (initial || isUser.value) displayText.value = initial

// 轮询检测新文本
let lastKnown = initial
const dataTimer = setInterval(() => {
  if (isUser.value) return
  const cur = getFullText(props.message)
  if (cur.length > lastKnown.length) {
    displayText.value = cur
    lastKnown = cur
  }
}, 100)

onBeforeUnmount(() => { clearInterval(dataTimer) })
```

### 后端 SSE 日志（调试用）

```javascript
// server.js — 可选：流式时间戳日志
for await (const chunk of stream) {
  const delta = chunk.choices?.[0]?.delta?.content
  if (delta) {
    console.log(`[sse] ${Date.now()} batch: ${delta.length} chars`)
    res.write(delta)
  }
}
```

---

## 七、未来展望

1. **考虑替换 useChat 为轻量方案**：如果打字机效果的粒度需求提升（需要精确控制每几个字一跳），可以考虑手写 `WebStream` 解析 + Vue `reactive` array + `ref` deep 替代 shallowRef。

2. **通用 composable**：将 `forcePoll` 逻辑提取为 `useForcePoll(messages, isStreaming, interval=200)`，供其他用到 `useChat` 的组件共享。

3. **多模型兼容**：当前后端 `server.js` 的 plain text SSE 格式与前端 `useChat` 的 AI SDK 协议不完全兼容。LangGraph 集成后需要统一为 AI SDK 的 SSE 事件格式。

4. **后端写流优化**：当前每个 token 都 `res.write()`，建议改为 batch write（每 50ms 攒一批），减少 Node.js 的 I/O 调用次数。

---

> **一句话总结**：`useChat` 的 shallowRef + in-place mutation 是打字机效果不显示的根因，`setInterval(200ms)` 浅拷贝数组是最简单可靠的修复方案。不是所有问题都需要复杂算法——有时候一个定时器就够了。
