# CodeBuddy Agent - 技术方案

## 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                     CLI Interface                       │
└────────────────────────────┬────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────┐
│                      Agent Core                         │
│  ┌──────────┐    ┌──────────┐    ┌──────────────┐       │
│  │ Planner  │    │ Executor │    │   Memory     │       │
│  └──────────┘    └──────────┘    └──────────────┘       │
└────────────────────────────┬────────────────────────────┘
                             │
        ┌────────────────────┼────────────────────┐
        ▼                    ▼                    ▼
┌───────────────┐  ┌───────────────┐  ┌───────────────┐
│ ModelRouter   │  │ CostTracker   │  │ ContextMgr    │
└───────────────┘  └───────────────┘  └───────────────┘
```

---

## 核心模块

### 1. 模型适配层 (ModelAdapter)

**核心原则**: Agent 提供统一接口，用户选择模型

```python
class ModelAdapter:
    """统一接口，支持多种模型"""
    
    def __init__(self, config: ModelConfig):
        self.config = config  # 用户配置
        # 支持: DeepSeek / OpenAI / Anthropic / 本地模型
    
    def chat(self, messages: list) -> str:
        # 统一接口，内部调用用户选择的模型
        return self.client.chat(model=self.config.model, messages=messages)
```

**用户配置示例**:
```yaml
# config.yaml
model:
  provider: deepseek  # 或 openai / anthropic
  name: deepseek-chat  # 或 gpt-4o / claude-3-sonnet
  api_key: "${DEEPSEEK_API_KEY}"
  # 价格由用户提供或自动获取
```

**支持的模型**:
| Provider | 模型示例 |
|----------|----------|
| DeepSeek | deepseek-chat, deepseek-v4-flash, deepseek-v4-pro |
| OpenAI | gpt-4o-mini, gpt-4o, gpt-4-turbo |
| Anthropic | claude-3-5-haiku, claude-3-5-sonnet, claude-3-opus |

### 2. CostTracker (成本追踪)

```python
class CostTracker:
    def record(self, model: str, usage: Usage):
        cost = usage.input * self.prices[model]["input"] + \
               usage.output * self.prices[model]["output"]
```

**输出格式**:
```
[Model: GPT-4o-mini] [Tokens: 1,234] [Cost: $0.0023]
```

### 3. MemoryManager (记忆管理)

**层次结构**:

| 类型 | 存储 | 生命周期 |
|------|------|----------|
| 短期 | Message数组 | 会话结束 |
| 情景 | 向量数据库 | 30天 |
| 语义 | 向量数据库 | 永久 |

**检索流程**:
```
query → embedding → 向量搜索 → 阈值过滤 → Top-K → Prompt注入
```

**存储结构**:
```json
{
  "id": "mem_xxx",
  "content": "用户偏好4空格缩进",
  "embedding": [...],
  "user_id": "xxx",
  "created_at": "2026-05-12"
}
```

### 4. ContextManager (上下文管理)

**压缩技术**:

| 技术 | 实现 | 节省 |
|------|------|------|
| Tree-sitter裁剪 | 只解析函数/类 | 60-80% |
| Diff-only | 只传git diff | 50-90% |
| 对话摘要 | LLM总结 | 30-50% |

**触发规则**: 上下文 > 80% 时压缩

### 5. ToolExecutor (工具执行)

| 工具 | 命令 | 说明 |
|------|------|------|
| Read | `read <file>` | 读取文件 |
| Edit | `edit <file>` | 编辑文件 |
| Write | `write <file>` | 创建文件 |
| Bash | `bash <cmd>` | 执行命令 |
| Grep | `grep <pattern>` | 搜索内容 |
| Find | `find <name>` | 搜索文件 |

---

## 技术选型

| 组件 | 方案 | 备选 |
|------|------|------|
| LLM API | DeepSeek | OpenAI, Anthropic, 本地模型 |
| 向量库 | Qdrant | Chroma, SQLite |
| 代码解析 | Tree-sitter | LSP, regex |
| 依赖 | Python 3.10+ | - |

---

## 数据存储

| 数据 | 存储 | 格式 |
|------|------|------|
| 语义记忆 | Qdrant | 向量+元数据 |
| 会话历史 | JSON文件 | 每会话一个 |
| 项目配置 | CLAUDE.md | Markdown |
| 成本统计 | SQLite | 结构化 |
| 用户配置 | config.yaml | YAML |

---

## 幻觉解决方案

| 方案 | 实现 |
|------|------|
| Top-K限制 | 每次最多5条记忆 |
| 阈值过滤 | 相似度 > 0.7 |
| 矛盾检测 | 检测记忆冲突 |
| 主动总结 | 80%上下文时触发 |

---

## 安全与隐私

- API Key 仅本地存储
- 代码不上传第三方
- 记忆按 user_id 隔离
