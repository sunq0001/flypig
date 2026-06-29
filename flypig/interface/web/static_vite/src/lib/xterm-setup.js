/** xterm-setup：xterm.js 初始化
 * @module xterm-setup
   为什么做：xterm.js 需要配置 terminal options、加载 addons、应用主题。
   实现方法：创建 Terminal 实例 + addon-fit + addon-web-links + 主题加载。
   实现效果：终端开箱即用，窗口自适应。
   技术栈：xterm.js, addon-fit/addon-web-links, 主题加载
   层&依赖：frontend.lib
   细节见文档：docs/docs_refactor/frontend-arch.md → §技术栈 */
