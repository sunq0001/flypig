"""选择题卡片工具

为什么做：Explore 模式下 AI 需要通过选择题与用户交互，收集需求信息逐步收敛。这是 FlyPig 的核心 UX 模式。
实现方法：工具返回结构化的 {title, choices: [{id, label, description}]}，前端渲染为选择题卡片。~20 行。
实现效果：用户通过点选卡片与 AI 交互，不需要打字描述需求。
技术栈：结构化 return {choices}, ~20 行

层&依赖：infrastructure.tools.interact 层，零依赖
细节见文档：docs/docs_refactor/langgraph-graph.md → §Explore 模式、mode-matrix.md → §工具可用性
"""

# TODO: 骨架文件占位，待具体实现
