# 短期记忆：上下文压缩（ContextPipeline）

> **来源**: `architecture-refactor.md` §3.7.3
> **关联文档**: `memories.md`（长期记忆 ConversationStore）、`backend-modules.md`（DI 注册）
> 短期记忆不存储，只在调 LLM 之前压缩。

## 职责

从 ConversationStore 读取原始对话 → 压缩到 token 预算以内 → 喂给 LLM。

```
chat_node:
  1. pipeline.build(store, session_id, input)    ← 读 store，压缩
  2. response = llm.invoke(compressed)
  3. store.save_turn(session_id, turn_id, data)   ← 写 store
```

Pipeline 只读，Store 只存。职责清晰。

## 接口

```python
class IContextPipeline(ABC):
    @abstractmethod
    async def build(
        self,
        store: IConversationStore,
        session_id: str,
        user_input: str,
        budget: int = 100_000,
    ) -> list:
        """返回压缩后的消息列表，直接喂给 LLM"""

class ICompressLayer(ABC):
    @abstractmethod
    def compress(self, messages: list, budget: int) -> list: ...

class CompositePipeline(IContextPipeline):
    def __init__(self, layers: list[ICompressLayer]):
        self.layers = layers

    async def build(self, store, session_id, user_input, budget=100_000):
        recent = await store.get_recent_turns(session_id, 20)
        summaries = await store.get_summaries(session_id, 50)
        messages = self._assemble(recent, summaries, user_input)
        for layer in self.layers:
            if count_tokens(messages) <= budget:
                break
            messages = layer.compress(messages, budget)
        return messages
```

## 内置三层

| 层 | 代码量 | 做什么 | 优先级 |
|----|--------|--------|--------|
| `TruncateResultsLayer` | ~20 行 | 工具结果 > 2000 字截断保留头尾 | 第一层 |
| `FoldOldTurnsLayer` | ~30 行 | 最早几轮折叠成摘要，保留最近 N 轮完整 | 第二层 |
| `TrimMessagesLayer` | 1 行 | 包装 LangGraph 的 `trim_messages` 做保底 | 第三层 |

## Token 优化

### 动态 token 预算

```python
MODEL_TOKEN_BUDGETS = {
    "deepseek-v3":  80_000,
    "gpt-4o":      100_000,
    "claude-3.5":  150_000,
    "local":        32_000,
}
```

### AI 输出 token 预算

```python
response = llm.invoke(
    messages,
    max_tokens=OUTPUT_BUDGETS.get(state["mode"], 4096),
)
```

## 扩展 Layer（P2 可选）

### AiSummaryLayer

```python
class AiSummaryLayer(ICompressLayer):
    """用 LLM 总结工具结果，替代机械截断"""
    def compress(self, messages, budget):
        for msg in messages:
            if msg["role"] == "tool" and len(msg["content"]) > 2000:
                msg["content"] = self._summarize(msg["content"])
        return messages
```

### DedupLayer

```python
class DedupLayer(ICompressLayer):
    """移除对话历史中重复的用户输入"""
    def __init__(self):
        self._seen = set()
    def compress(self, messages, budget):
        for msg in messages:
            if msg["role"] == "user" and msg["content"] in self._seen:
                msg["content"] = "[同上轮]"
            elif msg["role"] == "user":
                self._seen.add(msg["content"])
        return messages
```

### ToolResultSummaryLayer

```python
class ToolResultSummaryLayer(ICompressLayer):
    """超过 N 轮的工具结果替换为摘要"""
    def __init__(self, max_age_turns: int = 5):
        self.max_age = max_age_turns
    def compress(self, messages, budget):
        turn_count = 0
        for msg in reversed(messages):
            if msg["role"] in ("user", "assistant"):
                turn_count += 1
            if msg["role"] == "tool" and turn_count > self.max_age:
                msg["content"] = f"[工具结果摘要：{self._brief(msg['content'])}]"
        return messages
    def _brief(self, text: str) -> str:
        return text[:100].replace("\n", " ") + "..." if len(text) > 100 else text
```

## 与长期记忆的关系

```
短期记忆（运行时）:                    长期记忆（持久化）:
ContextPipeline                         ConversationStore + UsageTracker
  ├── 从 ConversationStore 读取         ├── turns
  ├── 压缩 → 喂 LLM                     ├── tasks + task_status_log
  └── 不存储，只转换                      ├── turn_usage + call_usage
                                         └── checkpoint_mappings
```

> 短期记忆是**函数**（无状态），长期记忆是**数据**（持久化）。
