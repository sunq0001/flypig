# 前端 UI 重构方案

> **来源**：用户反馈"太多 div 看着不舒服"引发的前端 UI 全面审计与重构讨论
> **关联文档**: `frontend-arch.md`（前端架构总览）、`tech-stack.md`（技术栈决策）、`standards-testing-debugging.md`（自动化检查清单）
> 
> 本方案涵盖：div 层级瘦身 → 嵌套组件抽取 → CSS 清理 → 性能优化，采用三阶段渐进式策略，每步可截图验证、可 git 回退。

---

## 一、背景与痛点

用户长期反馈前端页面"太多 div 看着不舒服"。经审计，当前布局组件存在以下问题：

### 1.1 白给 wrapper 层 — "套娃"严重

每层组件都包自己的 `<div>`，累计出大量无实际布局价值的 DOM 层级：

```html
<!-- 最终渲染的 DOM 嵌套（~7层起步） -->
<t-layout>
  <t-layout>
    <t-aside>
      <div class="activity-bar">      <!-- SideBar.vue 模板根 -->
        ...
      </div>
    </t-aside>
    <div class="layout-body">          <!-- MainLayout 包装层 -->
      <div class="panel">              <!-- LayoutPanels 模板根 -->
        <div class="pcontent">         <!-- LayoutPanels 内部包装层 -->
          <div class="resource-bar">   <!-- ResourceBar 模板根 -->
            ...
          </div>
        </div>
      </div>
    </div>
  </t-layout>
  <t-footer>
    <div class="status-bar">           <!-- StatusBar 模板根 -->
      ...
    </div>
  </t-footer>
</t-layout>
```

### 1.2 各文件 div 数量普查

| 文件 | 手写 `<div>` 数 | 其中白给层 | 说明 |
|------|:-:|:-:|------|
| **MainLayout.vue** | 郑州 | 1 (`layout-body` 可用 `<t-content>` 替代) | 弹窗也用 `<div>` 手写 |
| **LayoutPanels.vue** | 2 | 1 (`pcontent` 合并到 `.panel`) | 两层 div 包裹一个 v-if |
| **ViewerBar.vue** | 1 | 1 (`.view-bar` 只加了 `border-left`) | 可合并到面板级 CSS |
| **InteractBar.vue** | 3 | 2 (`.tabs-bar` → `.tab-list` 拆太细) | 手写 tabs 可换 `<t-tabs>` |
| **SideBar.vue** | 2 | 0 | 结构合理 |
| **ResourceBar.vue** | 2 | 0 | 结构合理 |
| **ChatPanel.vue** | 2 | 0 | 弹窗 div 无法避免 |
| **MessageList.vue** | 1 | 0 | 结构合理 |
| **StatusBar.vue** | 1 | 0 | 结构合理 |
| **ResizeHandleLR.vue** | 1 | 0 | 结构合理 |
| **总计（所有 layout + chat 文件）** | **~21** | **~4-5 可删除** | 减少后约 **~16** |

---

## 二、组件嵌套抽取机会

以下位置的嵌套深度 >3 层，适合抽取为独立组件：

### 2.1 手写弹窗 → 通用 `DialogWrapper.vue`

**现状**：两处相同的自定义弹窗代码（MainLayout 的 WorkspacePicker、ChatPanel 的 API Key 弹窗）

```
MainLayout.vue
  └─ <div class="dlg-overlay">          ← 与 ChatPanel.ak-overlay 完全重复
      └─ <div class="dlg-box">
           └─ <div class="dlg-header">
                └─ <button class="dlg-close">
```

**方案**：抽取为 `common/DialogWrapper.vue`（props: title, width）：
- 消除 ~30 行重复 CSS（`.dlg-* / .ak-*` 完全同构）
- 统一样式变更点

### 2.2 InteractBar 标签栏 → `<t-tabs>`

**现状**：手写 `tabs-bar > tab-list > tab` 三层 + `v-show` 切换内容

**方案**：替换为 `<t-tabs>` + `<t-tab-panel>`，单层：
- 删掉 `.tabs-bar`、`.tab-list`、`.tab` 共 ~10 行手写 CSS
- 默认支持切换动画、暗色主题

### 2.3 ViewerBar 包装层合并

**现状**：`.view-bar` 只提供 `border-left` 和 `flex` 布局

**方案**：删掉 `<div class="view-bar">`，`border-left` 合并到父级 `.panel` 的全局 CSS 中：
- 面板容器统一控制边框，不扩散到各子组件

---

## 三、CSS 问题

### 3.1 孤儿 CSS 文件 — 从未被 import

| 文件 | 状态 | 影响 |
|------|------|------|
| `interact/input/mode-select-popper.css` | **未被任何文件 import** | ModeSelect 下拉弹窗暗色主题完全失效（永远是白底） |
| `interact/input/model-select-popper.css` | 间接通过 import | 含 **20+ `!important`**，全局污染严重 |

### 3.2 model-select-popper.css — `!important` 泛滥

```css
/* 20+ 个 !important，覆盖 4 层选择器 */
.modt-select-popper { background: #252526 !important; ... }
.modt-select-popper .t-popup__content { background: #252526 !important; }
.modt-select-popper .t-select-dropdown__item { background: transparent !important; }
.modt-select-popper .t-select-dropdown__item.is-selected { color: #409eff !important; }
```

**问题**：
- `!important` 破坏了 CSS 级联，后续主题切换只能更 `!important`
- `.modt-select-popper`（注意拼写：`modt` 缺字母 `e`）与实际 class 不一致

### 3.3 修复方案

1. **合并两文件** → `style/td-overrides.css`
2. **CSS 变量覆盖替代 `!important`**：
   ```css
   .modt-select-popper,
   .mode-select-popper {
     --td-bg-color-container: #252526;
     --td-bg-color-container-hover: #3c3c3c;
     --td-text-color-primary: #e5e5e5;
     --td-component-stroke: #444;
   }
   ```
3. **修正 class 拼写**：`.modt-select-popper` → `.model-select-popper`（向后兼容保留原名作为 fallback）
4. **`!important` 从 >20 个降到 0**（CSS 变量不需要 `!important`）

### 3.4 全局 CSS 散落问题

当前全局/未隔离 CSS 分布：

| 位置 | 内容 | 层数 |
|------|------|------|
| `MainLayout.vue` `<style>` | `.panel`, `.pcontent`, `.t-layout__content`, `.dlg-*` | 7 个 |
| `ChatPanel.vue` `<style>` | `.message-list` 滚动条, `.ak-*` 弹窗 | 7 个 |
| `interact/input/*.css` | 下拉弹窗覆盖 | 2 个文件 |
| `style/variables.css` | CSS 变量（主题色/间距/字体） | 1 个文件 |

**下一步**：将散布的全局 CSS 按职责归并：
- 布局相关 `.panel` / `.t-layout__content` → `style/layout.css`
- 弹窗相关 `.dlg-*` / `.ak-*` → `style/dialog.css`
- 组件库覆盖 → `style/td-overrides.css`

---

## 四、性能优化

### 4.1 P0 — KeepAlive 缓存

**现状**：InteractBar 用 `v-show` 切换 ChatPanel / TermBar，两个组件 **始终挂载**。

```
InteractBar.vue
  ├─ ChatPanel  (v-show="activeTab === 'chat'")     ← 始终渲染
  └─ TermBar    (v-show="activeTab === 'term'")      ← 始终渲染
```

**问题**：
- TermBar 用 xterm.js，即使隐藏也占用 GPU 纹理 + WebSocket 连接
- ChatPanel 即使不可见也在监听 SSE 轮询

**方案**：`v-if` + `<KeepAlive>`，隐藏时卸载 DOM，缓存状态：
```html
<KeepAlive>
  <ChatPanel v-if="activeTab === 'chat'" :model="model" />
</KeepAlive>
<KeepAlive>
  <TermBar v-if="activeTab === 'term'" />
</KeepAlive>
```

**收益**：
- TermBar 隐藏后释放 xterm.js 实例（GPU 显存 + WebSocket）
- ChatPanel 隐藏后停止 200ms 轮询定时器
- KeepAlive 确保切回时消息列表位置保留

### 4.2 P1 — `shallowRef` 替代 `reactive`

**现状**：panels 数组用 `reactive`，但 `reactive` 会递归包装每层，对只改变 `w` 属性的场景造成不必要的 Proxy 开销：

```javascript
// MainLayout.vue
const panels = reactive([
  { id: 'resource', w: 260 },
  { id: 'viewer', w: 0 },
  { id: 'interact', w: 360 },
])
```

**方案**：改为 `shallowRef`，手动触发替换：
```javascript
const panels = shallowRef([
  { id: 'resource', w: 260 },
  { id: 'viewer', w: 0 },
  { id: 'interact', w: 360 },
])
// 拖拽时替换整个引用
panels.value = panels.value.map((p, i) => ({...p, w: newWidths[i]}))
```

**收益**：
- 拖拽调宽时跳过 Proxy 递归，减少 GC 压力
- panels 本身只读不深改，`shallowRef` 语义更准确

### 4.3 P2 — `:deep(.message-item)` 修复

**现状**：`MessageList.vue` 中：
```css
::deep(.message-item) {
  content-visibility: auto;
  contain-intrinsic-size: 60px;
}
```

**问题**：`:deep()` 在子组件 scoped 外部，对 `<MessageItem>` 内部元素**不生效**。实际 `content-visibility` 从未工作。

**修复**：将样式移到 `MessageItem.vue` 自身的 `scoped` 中：
```css
/* MessageItem.vue */
.message-item {
  content-visibility: auto;
  contain-intrinsic-size: 60px;
}
```

**收益**：长对话列表只有可视区域的 `MessageItem` 被渲染，滚动性能提升数倍。

### 4.4 P3 — Iconify 按需打包

**现状**：Iconify 全量包（~120KB JS），实际只用 3-5 个图标。

**方案**：改为 `@iconify/vue` + 按需导入：
```javascript
import { Icon } from '@iconify/vue'
// 只打包用到的图标
import 'iconify-icon/cache-all'  // 不加载
<Icon icon="mdi:file" />         // 自动按需
```

**收益**：JS 包体积减少 ~100KB。

---

## 五、三阶段渐进式计划

每阶段设计为**可独立验证**的 git commit，用户可随时截图确认、回退重来。

| 阶段 | 内容 | div 减少 | 风险 | 验证方式 |
|------|------|:-------:|:----:|---------|
| **Phase 1** — 白给 wrapper | 删 `layout-body`、`pcontent`、`view-bar`；抽 DialogWrapper | **-4** | 低（只删层不改逻辑） | 截图看布局不变 |
| **Phase 2** — 组件 + CSS | InteractBar 换 `<t-tabs>`；合并 CSS、替换 `!important` | **-2 层嵌套** | 中（tabs 需确认动画/样式） | 截图 + 切换 tab |
| **Phase 3** — 性能优化 | KeepAlive、shallowRef、:deep 修复、Iconify 按需 | **DOM 不变** | 低（行为不改，只改性能） | 控制台看内存/包体积 |

### 5.1 Phase 1 详细步骤

1. **删 `layout-body`** — MainLayout.vue 的 `<div class="layout-body">` 改为 `<t-content>`，CSS 合并
2. **删 `pcontent`** — LayoutPanels.vue 的 `<div class="pcontent">` 去掉，CSS 合并到 `.panel`
3. **删 `view-bar`** — ViewerBar.vue 的 `<div class="view-bar">` 去掉，`border-left` 上提到全局 `.panel`
4. **抽 DialogWrapper** — 新建 `common/DialogWrapper.vue`，替换两处手写弹窗

### 5.2 Phase 2 详细步骤

1. **InteractBar 换 `<t-tabs>`**：
   ```html
   <!-- 改前 -->
   <div class="interact-bar">
     <div class="tabs-bar">...</div>
     <ChatPanel v-show="..." />
     <TermBar v-show="..." />
   </div>
   
   <!-- 改后 -->
   <t-tabs v-model="activeTab" size="small" theme="card" placement="top">
     <t-tab-panel value="chat" label="💬 对话">
       <ChatPanel :model="model" />
     </t-tab-panel>
     <t-tab-panel value="term" label="🖥 终端">
       <TermBar />
     </t-tab-panel>
   </t-tabs>
   ```
2. **合并 CSS**：`mode-select-popper.css` + `model-select-popper.css` → `style/td-overrides.css`，CSS 变量替代 `!important`

### 5.3 Phase 3 详细步骤

1. `<KeepAlive>` 包裹 InteractBar 的 ChatPanel 和 TermBar
2. `panels` 从 `reactive` → `shallowRef`，拖拽回调改为替换引用
3. `:deep(.message-item)` 迁移到 `MessageItem.vue` scoped 样式
4. Iconify 从全量打包改为按需导入

---

## 六、风险与回退策略

| 风险 | 概率 | 后果 | 缓解 |
|------|:----:|------|------|
| `<t-tabs>` 与手写 tabs 样式不一致 | 中 | 右侧面板 UI 偏差 | Phase 2 前截图标样，改后对比截图 |
| DialogWrapper 抽取导致弹窗位置/Bug | 低 | 弹窗不显示 | 抽取前后两组件并存对比，通过后删旧的 |
| KeepAlive 导致消息状态未正确保存 | 低 | 切回 chat 时消息丢失 | `<KeepAlive>` 默认保存 vnode，加 `include` 白名单 |
| `shallowRef` 替换导致 panels 不响应 | 低 | 拖拽不生效 | 先本地验证拖拽再提交，写 2 行测试代码 |

**总体策略**：
- 每阶段都开新分支（`refactor/phase-1`、`refactor/phase-2`、`refactor/phase-3`）
- 每步改完跑截图对比
- 用户不满意直接 `git checkout main`，不影响现有功能

---

## 七、预期收益总结

| 指标 | 改前 | 改后 |
|------|:----:|:----:|
| 手写 `<div>` 总数（layout 层） | ~21 | ~16 |
| DOM 嵌套最大深度 | 6-7 层 | 4-5 层 |
| CSS `!important` 个数 | >20 | 0 |
| 孤儿 CSS 文件 | 1 个 | 0 |
| 全局 CSS 散落点 | 4 处 | 2 处（合并后） |
| 首屏 JS 体积（Iconify） | ~120KB | ~20KB |
| 长对话列表渲染 | 全量渲染 | 仅可见区域（content-visibility） |
| 面板切换 | 始终挂载 | v-if + KeepAlive 按需 |
| 弹窗维护点 | 2 处重复代码 | 1 处通用组件 |

---

## 八、自动化检查覆盖

本文档发现的 UI 问题已纳入 `scripts/frontend_check.py` 的自动化检测中（详见 [standards-testing-debugging.md#53-frontend_checkpy](standards-testing-debugging.md#53-frontend_checkpy)）：

| 文档中的问题 | 自动检查 | 代号 |
|------------|---------|------|
| 孤儿 `mode-select-popper.css` 未被 import | 扫描所有 `.vue`/`.js` 中的 CSS import，反向匹配 `.css` 文件 | F_CSS_ORPHAN |
| `model-select-popper.css` 全局 20+ `!important` | 扩展到扫描 standalone `.css` 文件的 `!important` 数量 | F_CSS_GLOBAL |
| MainLayout 6 层 `<div>` 套娃 | 解析 `.vue` template 中 `<div>` 开闭标签，统计最大嵌套深度 | F_TEMPLATE_DEPTH |
| InteractBar 手写标签栏（`tabs-bar` 类名） | 正则匹配 class 中 `tabs-bar`/`tab-list` 等关键字，提示用 `<t-tabs>` | F_PATTERN |
| ChatPanel 用 `v-show` 切换（不销毁/重建） | 检测 `v-show` 在重型组件（ChatPanel/TermBar 等）上出现 | F_SHOWREF |

> 执行：`python scripts/frontend_check.py`
> 当前检出 9 处违规，其中 5 项来自本文档发现的问题。
