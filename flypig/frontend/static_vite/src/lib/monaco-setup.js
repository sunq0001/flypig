/* monaco-setup：Monaco Editor 初始化
   为什么做：Monaco Editor 需要配置语言/主题/快捷键。
   实现方法：monaco.editor.create 配置 language/theme/autocompletion，注册自定义快捷键。
   实现效果：代码编辑器开箱即用，支持语法高亮和自动补全。
   技术栈：monaco-editor, 语言/主题/快捷键
   层&依赖：frontend.lib
   细节见文档：docs/docs_refactor/frontend-arch.md → §技术栈 */
