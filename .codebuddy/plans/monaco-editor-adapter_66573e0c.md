---
name: monaco-editor-adapter
overview: 将 CodeMirror 5 替换为 Monaco Editor，并通过 EditorAdapter 解耦设计，方便未来切换到 OpenSumi 等完整 IDE 框架。
todos:
  - id: create-branch
    content: 创建 feat/monaco-editor 分支
    status: completed
  - id: replace-editor-engine
    content: "替换 index.html: 移除 CodeMirror CDN(8-20行), 引入 Monaco CDN loader"
    status: completed
    dependencies:
      - create-branch
  - id: add-editor-adapter
    content: 添加 EditorAdapter 抽象 + MonacoEditorAdapter 实现类
    status: completed
    dependencies:
      - create-branch
  - id: rewrite-editor-functions
    content: 重写 _initEditor 和 getMode, 更新 _editor 类型注释
    status: completed
    dependencies:
      - add-editor-adapter
  - id: update-editor-css
    content: 替换 CodeMirror CSS(108-112行) 为 Monaco CSS
    status: completed
    dependencies:
      - replace-editor-engine
  - id: wire-up-verify
    content: 验证 switchTab, _refreshFileTab, openFile 与 adapter 的协作, 修复样式
    status: completed
    dependencies:
      - rewrite-editor-functions
      - update-editor-css
  - id: commit-push
    content: git add/commit/push feat/monaco-editor 分支
    status: completed
    dependencies:
      - wire-up-verify
---

用 Monaco Editor 替换 CodeMirror 5。解耦设计编辑器层，通过 EditorAdapter 接口隔离，方便未来替换为 OpenSumi 等完整 IDE 框架。文件树、标签页、终端、对话面板不动。

需求：

- 移除 CodeMirror 5 的 10 个 CDN 脚本和 2 个 CSS
- 引入 Monaco Editor (CDN v0.55.1) 作为编辑器引擎
- 定义 EditorAdapter 抽象接口，将 Monaco 封装在适配器内部
- 重写 _initEditor、getMode，更新 _editor 变量和 CSS
- 确保 switchTab、_refreshFileTab、openFile 通过适配器工作
- 新建分支 feat/monaco-editor

## 技术栈

- 编辑器核心: Monaco Editor 0.55.1 (CDN AMD loader)
- Vue 3 + xterm.js 保持不动

## 架构设计

### EditorAdapter 接口

```
MonacoEditorAdapter (实现)
┌─────────────────────────┐
│ init(container, content,  │
│   language): Promise     │
│ setContent(content): void│
│ setLanguage(lang): void  │
│ resize(): void           │
│ destroy(): void          │
└─────────────────────────┘
         ▲ 使用
    ┌────┴────┐
    │ Vue App │  (switchTab / _initEditor / _refreshFileTab)
    └─────────┘
```

### Monaco 加载方式

- 使用 Monaco 的 AMD loader CDN
- `require.config` 指向 jsdelivr CDN
- 初始化时通过 Promise 等待 Monaco 就绪

### 语言映射调整

CodeMirror 的 mode 名与 Monaco 的 language ID 不完全一致，需要调整映射表：

| 扩展名 | CodeMirror | Monaco |
| --- | --- | --- |
| html/vue | htmlmixed | html |
| sh | shell | shell |
| bat | powershell | powershell |
| 其余 | 一致 | 一致 |


### 编辑器配置

- theme: 'vs-dark' (类似 material-darker)
- readOnly: true
- minimap: disabled (保持简洁)
- lineNumbers: on
- fontSize: 13px

## 性能

- Monaco wasm 和 worker 文件约 3MB gzip，首次加载稍慢于 CodeMirror，但后续体验远超
- 使用 `editor.getModel()` 管理多文件状态，避免反复创建/销毁实例
- 考虑后续使用 `monaco.editor.createModel()` 预加载多个文件

## 实施要点

- Monaco 的 AMD loader 是异步的，需要处理加载时序
- _initEditor 改为 async 函数，等待 Monaco 就绪
- 保持 _editor 变量名不变，但类型改为 adapter 实例
- Destroy 旧 editor 时调用 adapter.destroy() 而非 toTextArea()
- 新分支 feat/monaco-editor，从 master 创建