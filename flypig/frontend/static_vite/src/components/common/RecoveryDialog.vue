<!--
RecoveryDialog：崩溃恢复弹窗

为什么做：启动时检测到未正常结束的对话轮次，需要弹窗让用户选择"继续"还是"放弃"。
实现方法：Element Plus dialog 显示恢复信息（session/turn/摘要），用户点继续/放弃。
实现效果：崩溃不丢数据，用户可选择恢复。

技术栈：Vue 3 SFC, Element Plus dialog
层&依赖：frontend.presentation → common 组件群
细节见文档：docs/docs_refactor/resilience.md → §崩溃恢复
-->
