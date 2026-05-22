## 用户需求

修复当前 FlyPig Agent 的两个核心问题：

1. **tool_bash 系统性崩溃**：每次调用 bash 工具都返回 `[error] cannot access local variable 'time' where it is not associated with a value`，所有 bash 命令全部失败。这是 Python 作用域 + **pycache** 残留的 bug。

2. **Agent 盲目重试浪费 Token**：用户称为"做事做一半"问题。工具持续报错时，AI 无法识别这是工具自身的系统性故障，而是不断换不同的命令重试（wsl -l -v → wsl --list → wsl --version → ...），连续 8-10 次后才放弃，浪费大量 token。

## 核心功能

- 修复 `tool_bash` 中的 `time` 变量 UnboundLocalError
- 工具异常分类：系统错误（工具代码本身崩溃） vs 命令错误（被执行的命令返回非零）
- Agent 错误计数器：同一工具类型连续失败 N 次后切换策略
- 自愈机制：检测到工具系统性故障后，AI 读取自身源码并尝试修复
- 更新系统提示词：指导 AI 在遇到工具系统性失败时的正确行为
## 技术方案

### 架构概览

```mermaid
graph TD
    A["Agent loop"] --> B["tool_result 返回给 LLM"]
    B --> C{"结果含 [SYSTEM_ERROR]?"}
    C -->|是| D["error_counter[tool_type] += 1"]
    C -->|否| E["error_counter 清零"]
    D --> F{"连续失败 >= 3?"}
    F -->|是| G["触发自愈流程"]
    F -->|否| B
    G --> H["agent._self_heal()"]
    H --> I["AI 读取 tools.py"])
    I --> J["AI 定位 time 作用域问题"]
    J --> K["AI 修复代码 + 清除 __pycache__"]
    K --> L["重试原始用户请求"]
    L -->|成功| M["继续"]
    L -->|失败| N["通知用户并提供诊断"]
```

### 模块设计

#### 模块 1: tools.py — `tool_bash` 防御性编码 + 异常分类

**改动点**：

- 在 `tool_bash` 方法开头添加 `import time`（防御性 import，消除 Python 作用域歧义）
- 修改异常处理（line 310-311）：区分系统异常 vs 命令执行错误
- `UnboundLocalError`, `ImportError`, `TypeError`, `AttributeError` 等 Python 内部异常 → `[SYSTEM_ERROR] 前缀`
- `subprocess.TimeoutExpired`, `FileNotFoundError`, `PermissionError` 等外部异常 → 保持原样
- 返回值格式化为带类型前缀的错误消息

**代码变更**：

```python
# tool_bash 开头添加
import time  # 防御性 import，消除 __pycache__ 残留导致的 UnboundLocalError

# 异常处理（原 line 310-311）
except UnboundLocalError as e:
    return f"[SYSTEM_ERROR] Python UnboundLocalError in tool_bash: {e}"
except (ImportError, TypeError, AttributeError) as e:
    return f"[SYSTEM_ERROR] Python runtime error in tool_bash: {e}"
except subprocess.TimeoutExpired as e:
    return f"[TIMEOUT] {e}"
except FileNotFoundError as e:
    return f"[ERROR] Command not found: {e}"
except PermissionError as e:
    return f"[ERROR] Permission denied: {e}"
except Exception as e:
    return f"[ERROR] {e}"
```

#### 模块 2: agent.py — 错误计数器 + 自愈触发器

**新增属性**：

```python
self.error_counter: Dict[str, int] = {}  # {"bash": 2, "read_file": 0}
self.HEAL_THRESHOLD = 3  # 连续失败阈值
```

**修改 `_execute_tool_call`**（或 run 方法的工具调用部分）：

执行工具调用后，检查 output 是否包含 `[SYSTEM_ERROR]` 前缀：

- 含 `[SYSTEM_ERROR]` → 该类工具计数器 +1
- 不含 → 该类工具计数器清零
- 计数器 >= 阈值 → 触发 `_self_heal(user_input)`

**自愈流程 `_self_heal(user_input)`**：

```
1. 记录修复开始
2. 构造自愈 prompt: 
   "你遇到了工具系统性错误。请读取 flypig/<tool_type>.py 的源码，
   找到 [SYSTEM_ERROR] 对应的异常抛出位置，分析 root cause 并修复。
   修复后清除 __pycache__/ 目录。完成后重试用户的原始请求。
   原始请求: {user_input}"
3. 将自愈 prompt 作为新的 user message 追加到 messages
4. 循环回到 LLM 调用（while 循环的下一轮）
5. LLM 读取源码 → 发现 bug → 用 edit_file 修复 → 清除缓存 → 重试
6. 修复后仍失败 → 返回用户详细诊断信息
```

#### 模块 3: tools.py — 清理 **pycache**

新增辅助方法（在 `_convert_windows_command` 同级）：

```python
@staticmethod
def clear_pycache():
    """清除当前包的所有 __pycache__ 目录"""
    import shutil
    base = Path(__file__).parent
    for pycache in base.rglob("__pycache__"):
        shutil.rmtree(pycache, ignore_errors=True)
    return "[OK] Cleared Python cache"
```

#### 模块 4: config.yaml — 系统提示词规则

添加第 8 条规则：

```
8. 如果看到工具返回 [SYSTEM_ERROR] 前缀，说明工具代码本身有 bug。
   此时不要重复尝试不同参数——工具代码不会因为参数不同而自行修复。
   正确的做法是：读取该工具的源码 → 定位 bug → 修复 → 清除缓存 → 重试。
   这是最高效的修复路径。
```

### 目录结构

```
flypig/
├── tools.py         # [MODIFY] line 205 加防御性 import time
│                    #          line 310 修改异常分类
│                    #          新增 clear_pycache 方法
├── agent.py         # [MODIFY] line 38 run() 内加 error_counter
│                    #          新增 _self_heal() 方法
├── config.yaml      # [MODIFY] 系统提示词加规则 8
```

## 扩展使用

### SubAgent

- **code-explorer**: 在自愈流程中，当 AI 需要跨文件搜索 `time` 作用域问题、查找所有异常处理位置、或需要遍历 `__pycache__` 目录结构时，使用 [subagent:code-explorer] 来加速多文件搜索和分析。预期输出：完整的错误模式报告和修复位置清单。
