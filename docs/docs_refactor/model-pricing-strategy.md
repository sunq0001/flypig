# 模型目录与定价策略

> 状态：**策略已定，待实施** ｜ 调研日期：2026-10-04 ｜ 适用分支：`architecture-refactor`
>
> 本文回答两个问题：**价格为什么和官方不一致**，以及**模型清单为什么总会过期、怎么才能不再手工维护**。

---

## 一、问题

### 1.1 价格与官方不一致

界面（中文环境走 `currency=CNY`）显示的 DeepSeek 价格与官方定价页对不上。实测追溯后确认是**两层叠加**：数据源本身是错的，而我们的代码又把错的默认值盖在最上面。

**单位统一为 USD / 1M tokens 对照**（官方英文页即 USD，避免汇率干扰）：

| 指标 | 官方·空闲 | 官方·高峰 | registry 当前值 | 差异 |
|---|---|---|---|---|
| flash 输入（缓存未命中） | 0.15 | 0.30 | 0.14 | 只等于空闲档，无高峰档 |
| flash 输入（缓存命中） | 0.003 | 0.006 | 0.0028 | 只等于空闲档 |
| flash 输出 | 0.60 | 1.20 | 0.28 | **仅为空闲档的 47%** |
| pro 输入（缓存未命中） | 0.66 | 1.32 | 0.435 | 仅为空闲档的 66% |
| pro 输入（缓存命中） | 0.022 | 0.044 | 0.003625 | **仅为空闲档的 16.5%** |
| pro 输出 | 1.98 | 3.96 | 0.87 | **仅为空闲档的 44%** |

**溯源链路**：

1. `PricingService._scrape_pricing()`（`flypig/infrastructure/usage/pricing.py:184`）从 Portkey 抓价，但末尾 `prices.update(self._load_defaults())`（**同文件 L201**）让 `model_registry.json` 的 `default_pricing` **无条件覆盖**抓取结果 —— 抓取对已配 `default_pricing` 的模型等于不生效。
2. 实测 Portkey 数据本身就是错的：`deepseek-chat` / `deepseek-reasoner` / `deepseek-v4-flash` 三行**完全同价**（`request 1.4e-05`、`response 2.8e-05`、`cache_read 2.8e-07` cents/token），是 V3.2 时代的旧价且列对不上。
3. 因此缓存里 `deepseek-v4-pro = 0.435/0.87` 并非来自抓取，而是来自 registry 的 `default_pricing`（Portkey 对 pro 也返回 flash 那一行）。
4. ACL 的模糊匹配 `api_model_name in key`（`flypig/acl/pricing.py:33-36`）在转售商林立的聚合源上极易串行。

**影响面**：**目前仅影响前端模型选择器的价格提示**。`get_pricing()` 无任何调用方，`usage_handler` / `sqlite_tracker` 只统计 token 数、不参与计费，所以尚未污染成本统计。

### 1.2 模型清单代际落后

比价格问题更严重 —— registry 里的条目比当前在售模型落后 2~5 代：

| registry 当前条目 | 源上的当前模型（release_date） | 落后程度 |
|---|---|---|
| `gpt-4o` / `gpt-4o-mini` | `gpt-6.1-sol`(09-29)、`gpt-6-luna`(09-22)、`gpt-6-astra`、`gpt-5.6` | 2 个大代 |
| `claude-3-5-sonnet` | `claude-sonnet-5-5`(09-28)、`claude-opus-5-5`、`claude-fable-5` | 约 5 代（2024 → 2026） |
| `qwen-turbo/plus/max` | `qwen3.8-max`(08-03)、`qwen3.8-flash`、`qwen3.7-plus` | 3 代 |
| `kimi-k2.5` / `moonshot-v1-8k` | `kimi-k3`(07-16)、`kimi-k2.7-code`；`moonshot-v1-8k` 已从源中消失 | 2 代 + 1 个已淘汰 |
| `glm-4-plus` / `glm-4-air` | `glm-5.3`(08-14)、`glm-5.3-flash`、`glm-5.3-flashx` | GLM-4 代已不在官方列表 |
| `hunyuan-pro/standard` | 腾讯系仅收录 `hy4-preview`(08-28)、`hy3` | 名称与代际全变 |
| `doubao-pro-32k/lite-32k` | `doubao-seed-2-1-pro-260628`、`-turbo`、`doubao-seed-evolving` | 名称与代际全变 |
| `deepseek-v4-flash/v4-pro` | `deepseek-flash` / `deepseek-v4-pro` | `api_model` 名称错误 |

### 1.3 工程层面的三个欠账

1. **价格与清单写死在仓库代码里** → 上游一更新就得改代码、提交、发版，形成"维护跑步机"。
2. **数据模型维度不足**：`PricingEntry` 只有 `input_price / output_price / input_cache_hit` 三个字段，装不下时段、上下文分档、缓存写价、币种、来源。
3. **死代码**：`ModelRegistry.get_portkey_provider()`（`flypig/domain/registry.py:81`）与 registry 里的 `portkey_provider: "dashscope"`（`flypig/data/model_registry.json:92`）存在，但 `_scrape_pricing` 用的是 `provider.lower()` 拼 URL（`flypig/infrastructure/usage/pricing.py:193`）→ 该函数从未被调用，Qwen 抓取必然落到不存在的 `pricing/qwen.json`，只能吃 `default_pricing`。

---

## 二、数据源调研结论（2026-10-04 实测）

### 2.1 源对比

| 源 | 形态 | 可抓 | 权威性 | 覆盖度 | 结论 |
|---|---|---|---|---|---|
| **DeepSeek 官方定价页** | 静态 HTML `<table>` | ✅ | ★★★★★ | 仅 DeepSeek | **首选（L1）** |
| **models.dev `/api.json`** | JSON（5.3MB），免鉴权 | ✅ | ★★★★（官方 provider 与官方页一致） | 广 | **首选聚合（L2）** |
| OpenRouter `/api/v1/models` | JSON API，免鉴权 | ✅ | ★★ | 中 | 备选 |
| LiteLLM 价格库 | JSON（3MB） | ✅ | ★ | 广但多为第三方托管价 | 备选 |
| Portkey（当前使用） | JSON | ⚠️ | ✗ | 国产模型滞后 | **弃用** |

### 2.2 官方定价页可以直接解析（首选源）

- URL：`https://api-docs.deepseek.com/quick_start/pricing`（中文页加 `/zh-cn/` 前缀）
- **是静态 HTML**：实测 `http 200`、24KB、`<table>` × 1、`<td>` × 63，`httpx + 正则`即可解析，无需 headless 浏览器
- 中文页给 CNY，英文页给 USD（同一份数据，两边各自取整，**不要混用**）

**解析结果（官方原文，CNY / 1M tokens）**：

| 指标 | flash 空闲 | flash 高峰 | pro 空闲 | pro 高峰 |
|---|---|---|---|---|
| 输入（缓存命中） | 0.02 元 | 0.04 元 | 0.15 元 | 0.30 元 |
| 输入（缓存未命中） | 1 元 | 2 元 | 4.5 元 | 9.0 元 |
| 输出 | 4 元 | 8 元 | 13.5 元 | 27.0 元 |

**官方脚注（两条关键规则，原文）**：

> （1）模型名请使用 `deepseek-flash`。旧模型名 `deepseek-v4-flash`、`deepseek-v4-flash-vision-exp` 仍可调用，但对应模型已下线，请求将由 DeepSeek-V4.1-Flash 模型提供服务，并按 Flash 价格计费。
>
> （2）空闲时段价格为高峰时段价格的一半。北京时间周一至周五（不含中国法定节假日）9:00 - 12:00、14:00 - 18:00 为高峰时段；其余时段，包括周末及中国法定节假日全天均为空闲时段。

⇒ **时段可按时间自动判定，不需要用户选择**；且"高峰价 = 空闲价 × 2"，二档只需存一份。

### 2.3 models.dev 作为聚合源

- 有**官方 provider**（非转售）：`openai`、`anthropic`、`deepseek`、`alibaba`（+ `alibaba-cn`）、`moonshotai`（+ `moonshotai-cn`）、`zhipuai`、`volcengine`、`tencent-tokenhub`
- 实测其 `deepseek` provider 的值与官方页**完全一致**：`deepseek-flash` = 0.15 / 0.6 / 0.003，`deepseek-v4-pro` = 0.66 / 1.98 / 0.022
- 每个模型带 `release_date`、`limit.context`、`tool_call` / `attachment` 标记 → **可用于判断"是否有新版"**
- 缺点：只给**单一档位**（取的是空闲档），拿不到高峰档；上下文分档通过 `tiers` 表达

**覆盖度（针对 registry 的 14 个云端模型）**：

| 模型 | models.dev 官方 provider | 备注 |
|---|---|---|
| gpt-4o / gpt-4o-mini | ✅ `openai` | 需精确匹配 provider id |
| claude-3-5-sonnet | ✅ `anthropic` | 含 `cache_write` |
| qwen-turbo / plus / max | ✅ `alibaba` | 值与官方一致 |
| deepseek-flash / v4-pro | ✅ `deepseek` | 与官方页一致 |
| kimi-k2.5 | ✅ `moonshotai` | |
| glm-4-plus / glm-4-air | ⚠️ 官方 provider 已无 | 只有转售商，价错（nano-gpt 报 9.996） |
| doubao-pro-32k / lite-32k | ✅ `volcengine` | 但名字已是 `doubao-seed-2-1-*` |
| hunyuan-pro / standard | ⚠️ 仅 `tencent-tokenhub` 收录 `hy3`/`hy4-preview` | `tencent-coding-plan` 里价格全 0（套餐制） |
| moonshot-v1-8k | ❌ | 已从源中消失 |

### 2.4 转售商污染必须正视

- `gpt-4o` 在 models.dev 里命中 **84 条**（poe / nano-gpt / deepinfra / azure_ai / helicone / qiniu-ai …），价格各不相同
- 结论：**只能按"官方 provider id + 精确模型名"取值，禁止子串模糊匹配**

### 2.5 同一模型不同供应商价差巨大

| 模型 | 官方 | 火山（volcengine） |
|---|---|---|
| `deepseek-v4-flash` | 0.15 / 0.60 | `deepseek-v4-flash-ga-260731` = **0.4453 / 1.3359**（约 3 倍） |
| `glm-5.3-flash` | 0.15 / 0.50 | `glm-5-3-flash-260828` = 0.11875 / 0.41563 |

⇒ 价格必须绑定"我们实际调用的那家"（由 registry 的 `base_url` 决定），不能跨供应商取数。

### 2.6 计价维度已实测出四种

| 维度 | 实例 | 官方原始形态 |
|---|---|---|
| 时段 | DeepSeek 空闲 / 高峰 | 两列表格 |
| 上下文分档 | `doubao-seed-2-0-pro`、`qwen3.7-flash` | `tiers: [{size: 32000}, {size: 128000}]` |
| 缓存写价 | Anthropic、Qwen | `cache_write` |
| 套餐制 | 腾讯 `tencent-coding-plan` 全部为 0 | 订阅价，不代表免费 |

⇒ 三字段数据模型彻底不够用。

### 2.7 稳定别名（决定"能不能不改代码"）

| 厂商 | 有稳定别名 | 实测 |
|---|---|---|
| DeepSeek | ✅ | `deepseek-flash`、`deepseek-v4-pro` |
| OpenAI | ✅ | `gpt-4o`、`gpt-5.4`、`gpt-5.6`（不带日期） |
| Qwen | ✅ | `qwen-max`、`qwen-plus`、`qwen-flash` |
| Moonshot / Zhipu | ✅ | `kimi-k3`、`glm-5.3` |
| Anthropic | ❌ | 全是带日期的（`claude-3-5-sonnet-20241022`） |
| 火山豆包 | ❌ | 全是带日期的（`doubao-seed-2-1-pro-260628`） |
| 腾讯混元 | ⚠️ | `hy3` / `hy4-preview`（未形成代际序列） |

---

## 三、策略

### 原则 1：分层数据源，各做擅长的事

| 层 | 源 | 职责 |
|---|---|---|
| **L1 官方页解析** | DeepSeek 官方定价页（已跑通）；其他厂商官方文档页按需 | 权威值 + 厂商特有维度（时段） |
| **L2 官方聚合** | models.dev，按官方 provider id 精确取 | 覆盖大多数厂商，结构化、带 `release_date` |
| **L3 手工兜底** | registry 的 `default_pricing` | 只补 L1/L2 拿不到的（混元、豆包部分、已淘汰模型） |
| **L4 来源与时效** | 每条价带 `source` + `updated` | 前端展示"来源 / 数据日期"，**取不到就显示"未收录"，绝不用转售商的价** |

### 原则 2：显式映射，禁止模糊匹配

每个模型条目显式声明取值位置，匹配不上宁可留空：

```json
"gpt-6-luna": {
  "provider": "OpenAI",
  "api_model": "gpt-6-luna",
  "price_ref": { "source": "models_dev", "provider_id": "openai", "model_id": "gpt-6-luna" },
  "verified": true
}
```

### 原则 3：内容与代码分离（这是"跑得下去"的关键）

```text
model_registry.json   （repo 内，结构稳定、极少改动）
  ├─ providers:  { base_url, key_attr, price_source }
  ├─ models:     精选 + 实际在用（尽量用稳定别名）
  └─ sync_rules: 声明式规则
                 openai:     { source: models_dev, provider_id: openai,     family: "gpt-6*" }
                 alibaba:    { source: models_dev, provider_id: alibaba,    family: "qwen3.8*" }
                 volcengine: { source: models_dev, provider_id: volcengine, family: "doubao-seed-2-1*" }

catalog_cache.json    （运行时产物，gitignored）
  └─ 刷新结果：候选模型 + 价格 + tiers + source + updated

my_models.json        （用户级覆盖，gitignored）
  └─ 用户勾选后写入，合并进最终清单
```

**验收标准（判断这套是否成功）**：上游出了新模型 → 用户点一次"检查更新" → 新模型出现在"可添加"列表 → 勾选即可用。**全程不修改仓库代码、不发版。**

### 原则 4：优先稳定别名，但要防"静默换模型"

- 能用别名的用别名 → 上游换代时 registry 不用改（`qwen-max` 从 3.8 跳 4 也无需改动）
- 代价：供应商可在别名下静默切换 snapshot，导致**输出风格与账单悄然变化**
- 对策：别名条目必须带 `verified_at` 时间戳，并允许用户"锁定具体版本号"

### 原则 5：不追求最新，只追求不误导

- 界面显示"数据日期 / 来源"（如"2026-10-04 · models.dev"）
- 提供"检查更新"输出三张表：**新增可用 / 疑似下线 / 价格变动（>10%）**
- 过期不可怕，误导才可怕

### 原则 6：本地模型恒为 0

Ollama 本地模型不进价格链路，固定显示为本地免费。

---

## 四、数据结构设计（草案）

```python
@dataclass(frozen=True)
class PriceTier:
    """一档价格（统一单位：per 1M tokens）"""
    input: float | None
    output: float | None
    cache_read: float | None = None
    cache_write: float | None = None


@dataclass(frozen=True)
class PricingEntry:
    """模型定价值对象"""
    currency: str = "USD"           # USD | CNY
    source: str = "manual"          # official | models_dev | manual
    updated: str | None = None      # 数据日期（YYYY-MM-DD）
    # 档位键：default / off_peak / peak / over_context_32k ...
    tiers: dict[str, PriceTier] = field(default_factory=dict)
```

**向后兼容**：`input_price` / `output_price` / `input_cache_hit` 三个旧字段保留为 `tiers["default"]` 的只读投影，避免前端与既有测试一起大改。

---

## 五、落地步骤

| 步骤 | 内容 | 是否改变调用行为 | 是否需要 API Key 验证 |
|---|---|---|---|
| **① 价格修对** | L1 官方页解析 + L2 models.dev 精确映射 + 两档/币种 + `source`/`updated` 展示；`default_pricing` 降级为 L3（`update` 改 `setdefault` 语义）；修复 `get_portkey_provider` 死代码 | 否（纯展示） | 不需要 |
| **② 数据外置** | 目录与价格挪到 `catalog_cache.json`；registry 只留基线 + `sync_rules`；能换稳定别名的换别名 | 否 | 不需要 |
| **③ 自助上新** | `models --check`（dry-run 三张表）+ 界面"可添加的模型"勾选写入 `my_models.json` | 是（新模型可被选用） | 勾选后按需验证 |

**关于"换上新代际"**：不再由人工批量改 registry 实现，而是由步骤 ③ 让用户自助完成 —— 这正是不再陷入"不停更新"循环的原因。

**每步独立提交、独立可回滚**；步骤 ① 完成即可先消掉"输出价差一倍"这类明显错误。

---

## 六、边界与非目标

- **不做全自动默认收录**：未经人工确认的模型只出现在"可添加"里，不自动进主清单
- **不保证实时**：刷新按天/按需触发，界面上必须能看见数据日期
- **不为未验证模型担保**：有 key 才能验证的厂商，条目标 `verified: false`
- **不弃用离线可用性**：仓库内基线保证 `clone` 后无网络也能跑

---

## 附录 A：官方定价原文（英文页，USD / 1M tokens）

| 指标 | flash 空闲 | flash 高峰 | pro 空闲 | pro 高峰 |
|---|---|---|---|---|
| 输入（缓存命中） | $0.003 | $0.006 | $0.022 | $0.044 |
| 输入（缓存未命中） | $0.15 | $0.30 | $0.66 | $1.32 |
| 输出 | $0.60 | $1.20 | $1.98 | $3.96 |

## 附录 B：各厂商当前在售模型（按 release_date 倒序，节选）

| 厂商 | 当前模型（release_date / USD 输入-输出 / 上下文） |
|---|---|
| OpenAI (`openai`) | `gpt-6.1-sol`(09-29 / 2-10)、`gpt-6-sol`(09-22 / 2-10)、`gpt-6-luna`(09-22 / 0.1-0.5)、`gpt-6-astra`(09-04 / 10-50)、`gpt-5.6`(07-09 / 4-20 / 1050K) |
| Anthropic (`anthropic`) | `claude-sonnet-5-5`(09-28 / 2-10)、`claude-opus-5-5`(09-22 / 4-20)、`claude-fable-5-1`(09-01 / 10-50)、`claude-sonnet-5`(06-29 / 2-10) |
| DeepSeek (`deepseek`) | `deepseek-flash`(09-10 / 0.15-0.6)、`deepseek-v4-pro`(08-12 / 0.66-1.98) |
| 阿里 (`alibaba`) | `qwen3.8-omni-flash`(09-17 / 0.15-0.47)、`qwen3.8-flash`(08-26)、`qwen3.8-max`(08-03 / 2-6)、`qwen3.7-plus`(06-02 / 0.4-1.6) |
| Moonshot (`moonshotai`) | `kimi-k3`(07-16 / 3-15)、`kimi-k2.7-code`(06-12 / 0.95-4)、`kimi-k2.6`(04-21) |
| 智谱 (`zhipuai`) | `glm-5.3-flashx`(09-18 / 0.37-1.25)、`glm-5.3-flash`(08-26 / 0.15-0.5)、`glm-5.3`(08-14 / 1.4-4.4) |
| 火山 (`volcengine`) | `doubao-seed-2-1-pro-260628`(06-23 / 0.89-4.45)、`doubao-seed-2-1-turbo-260628`(0.45-2.23)、`doubao-seed-evolving`(06-23) |
| 腾讯 (`tencent-tokenhub`) | `hy4-preview`(08-28 / 0.834-2.501)、`hy3`(07-06)、`hy3-preview`(04-20) |

## 附录 C：实测命令

```bash
# 1. 官方定价页是否静态可解析
python -c "import httpx; h=httpx.get('https://api-docs.deepseek.com/quick_start/pricing/',follow_redirects=True).text; print(h.count('<table'), h.count('<td'))"
# → 1 63

# 2. Portkey 对 deepseek 各模型的实际返回（证明其数据错误）
python -c "import httpx,json; d=httpx.get('https://configs.portkey.ai/pricing/deepseek.json').json(); [print(k, json.dumps(d[k]['pricing_config']['pay_as_you_go'])) for k in d]"
# → deepseek-chat / deepseek-reasoner / deepseek-v4-flash 三行同价

# 3. models.dev 官方 deepseek provider 的值（证明其与官方页一致）
python -c "import httpx,json; d=httpx.get('https://models.dev/api.json').json()['deepseek']['models']; [print(k, json.dumps(v['cost'])) for k,v in d.items()]"
# → deepseek-flash {'input': 0.15, 'output': 0.6, 'cache_read': 0.003}

# 4. 转售商污染程度
python -c "import httpx; d=httpx.get('https://models.dev/api.json').json(); n=[1 for p in d.values() for m in (p.get('models') or {}) if 'gpt-4o' in m]; print(len(n))"
# → 84
```

---

## 相关文档

- [后端模块](backend-modules.md) — `PricingService` / `ModelRegistry` 的定位
- [演进路线图](migration-roadmap.md)
- [服务启动与访问](server-startup.md) — 推送与部署排障
