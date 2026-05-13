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
