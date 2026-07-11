---
name: memory-auto-tier
description: 三维记忆定位系统——自动分层检索+主动关联推送+自校准+动态专注窗口
memory_tier: auto
version: 2.0
created: 2026-07-10
updated: 2026-07-11
author: 晏翔+小白鸽
triggers: 
  - 用户提到历史话题时自动关联
  - 讨论结束后自动归档索引
  - 审计三维记忆系统
  - 评估记忆是否断链
  - 实施记忆系统代码化
  - 动态专注窗口
  - memory溢出
  - 静态记忆
  - 记忆系统审计
---

# 三维记忆定位系统 v2.0

> **属于天网神经系统（layer_0）** — Hermes记忆/漂移/讨论三位一体最高级独立板块。
> 三子体系：聊天记录系统（原始数据）→ 记忆系统（索引指挥）→ 讨论系统（结构化知识）。
> 拓扑位：`0_neural`。本skill对应记忆系统子层。

## 一、设计哲学

### 人类记忆逻辑 → AI检索策略

| 层级 | 人类 | AI对应 | 存储介质 | 查询代价 |
|:----|:----|:----|:---------|:--------:|
| 短期 | 秒~分钟，快速想起 | 当前会话 + state.db 实时库 | SQLite内存 | 低（ms级） |
| 中期 | 天~周，想想就想起 | 管道库 + 每周全量备份 | `pipeline/state_pipeline.db` | 中（s级） |
| 远期 | 月~年，提醒后想起 | 讨论归档 + E盘长期备份 | `.discussions/` + `E:/.../state_YYYYMMDD.db` | 高（min级） |
| **记忆好的人** | 自己提醒自己 | 主动推送 + skill映射 | assoc_index + micro-skill | 后台常驻 |

### v2.0核心原则

- **记忆必须无感** — 我不应该"调用"记忆系统，就像我不应该"调用"我的海马体。记忆是底层自动的。
- **静态记忆=死人** — memory核心不是固定不变的。专注30min流动一次，我关注什么memory就记什么。死守上周的专注=死系统。
- **不霸占** — 记忆系统不住在memory里。memory只有2-3行动态专注摘要。全量索引在skill和文件中。
- **命中就停** — 不逐层全量扫描
- **自动降级** — 当前/日查不到→自动查中期→查不到→查讨论skill→查不到→查长期
- **不刷屏** — 每3轮对话最多1条推送
- **不自杀** — 自校准只降权不删除
- **不扫盘** — 长期查询也通过索引，不扫原始备份
- **内外优先级（铁律）** — 查询永远先内后外

### 为什么v1.0不好

| v1.0 | 问题 | 类比 |
|:----|:----|:----|
| memory固定17行 | 死守上周专注，不随用户关注流动 | 7/5做完PV引擎→7/11还在专注PV |
| LLM手动操作记忆系统 | 每次调用前需要先"想起来要查记忆" | 人脑里住了个记忆操作员=精神分裂 |
| memory全量注入 | 17域混装→80%不相关→token浪费 | 肺里进气+进水一起吸 |
| 无专注窗口 | 高频条目无自动流动 | 短期记忆不转长期 |

### v2.0解决

| 问题 | v2.0方案 | 机制 |
|:----|:---------|:----|
| 静态记忆 | 动态专注窗口（cron每30min） | focus_tracker → 排序 → 写入MEMORY.md |
| 记忆操作员 | 三层自动（skill映射+预计算+pre-inject） | 我（LLM）被动读取，不主动调用 |
| memory溢出 | 移出80%至skill + 保留2-3行动态核心 | zero总容量压力 |
| 效率 | Tier 1-3 97% LLM-free | cron驱动，我只是被服务方 |

---

## 二、v2.0定位链（三层递进）

```
你说话
  │
  ├── Tier 1: skill映射（自动·零延迟）
  │   ├── 每个 assoc_index 条目 → 1个 micro-skill
  │   ├── triggers命中 → skill自动加载 → 我"本来就知道"
  │   └── 命中→回答→停
  │
  ├── Tier 2: 动态专注窗口（cron每30min更换）
  │   ├── memory顶部的2-3行 = 当前30min内我最高频提到的话题
  │   ├── 不固定的·自动流动
  │   ├── 专注自然迁移
  │   └── 命中→回答→停
  │
  ├── Tier 3: assoc_index深度检索（cron预计算）
  │   ├── cron每10min读assoc_index → 算关联分+时间衰减
  │   ├── 结果写入 cache/memory_context.json
  │   └── 命中→回答→停
  │
  └── Tier 4: 管道库/讨论归档/E盘备份（手动深查）
      └── 仅Tier 1-3全未命中时触发
```

**LLM参与度：Tier 1-3主环 97% LLM-free。** 唯一需要LLM判断的是讨论结束时决定"值不值得记"（`memory_index.py --add`，≤3次/天）。

---

---

## 十一、动态专注窗口（v2.0 核心创新）

### 为什么需要动态专注

**静态memory核心 = 蠢人。** 如果7/5的PV引擎校准一直占着memory核心不挪窝，到7/11还在"专注"PV——但用户明明在讨论记忆系统·竞彩·Kindle·数据库恢复。

**人脑健康的专注曲线是流动的：**

```
专注区
  │ ████████ Bot部署
  │          ████████ PV引擎校准
  │                    ████████ 记忆系统设计
  │                              ████████ 当前讨论
  └──────────────────────────────────────→ 时间
    7/2        7/5        7/10       7/11
    住进去     移过去      再移        还在移
    不霸占     腾给新      再腾         健康的流动
```

**持续专注是损耗精神的。** 固定占memory空间=每次对话加载无关信息→注意力分散→token浪费→系统不健康。

### 实现机制

```
cron每10min（memory_skillgen.py内auto_detect_focus）:
  1. 读state.db最近10条用户消息
  2. 对assoc_index每条，检查subjects中是否有词出现在消息中
  3. 命中→自动在focus_tracker.json中append一条（含id+时间戳）

cron每30min（memory_focus.py）:
  1. 读 focus_tracker.json
  2. 计算 focus_score:
       - 过去1h内命中数 × 1.0  ← 最近高频
       - 过去1h~24h内命中数 × 0.3   ← 日维度
       - 原始weight × 0.1      ← 历史权重兜底
  3. 取前2-3条 → 替换MEMORY.md中的旧专注区
  4. 清空focus_tracker（为下个30min准备）
```

**自动检测示例**：用户说"Kindle打不开"→state.db中有"Kindle"→assoc_index中20260710_kindle的subjects匹配→focus_tracker中+1→下一轮30min#1计入聚焦分。

**LLM零参与。** 全程cron驱动，无手动操作。

### 动态示例

```
7/10 15:00 专注: Kindle看板配置 → memory核心: Kindle｜state.db恢复｜内外优先级
7/10 22:00 专注: 记忆系统设计   → memory核心: 记忆系统｜内外优先级｜Kindle（降）
7/11 08:00 专注: 自适应备份修复 → memory核心: 备份修复｜记忆系统｜讨论模式
7/11 08:30 专注: 记忆系统审计   → memory核心: 记忆系统审计｜动态专注窗口｜自适应备份
```

**每次更换都不是"丢失"，而是"进步"** — 你昨天讨论Kindle，今天讨论记忆系统，明天讨论什么memory就跟着转。这才是活的系统。

### 为什么不用memory分区变通

用户正确指出"memory不支持分区"——确实。但动态专注窗口不需要分区，它用**时间窗口替代空间分区**：

- 30min换一批 → 天生分区（这30min Batch A，下30min Batch B）
- 不跟其他系统抢memory空间
- 专注用完即走，不霸占

---

## 十二、实现架构（v2.0 完整组件）

### 4个脚本

| 脚本 | 功能 | 触发器 | LLM参与 |
|:----|:-----|:------|:-------:|
| `memory_focus.py` | 读focus_tracker→排序→重写MEMORY.md | cron每30min | ❌ 无 |
| `memory_skillgen.py` | 读assoc_index→生成/更新micro-skill | cron每10min | ❌ 无 |
| `memory_calibrate.py` | 读hits/misses→调weight→归档>365天 | cron每周日03:10 | ❌ 无 |
| `memory_index.py` | --add：追加条目 / --update：更新条目 | 手动（讨论结束） | ✅ 仅此步 |

### 3个cron

| cron | 调度 | 脚本 | 产出 |
|:----|:----:|:----|:-----|
| 专注窗口刷新 | **每30min** | `memory_focus.py` | 更新MEMORY.md顶部专注行 |
| 技能同步+关联预计算 | **每10min** | `memory_skillgen.py` | 同步micro-skill + 写入cache/memory_context.json |
| 校准+归档 | **每周日03:10** | `memory_calibrate.py` | 权重调整 + >365天移入archive |

### 新增数据结构

```
~/.hermes/cache/
├── focus_tracker.json           ← 我每次关联hit时追加时间戳
├── memory_context.json          ← cron每10min写入的预计算关联结果
├── assoc_index.json (已有)      ← 持久化源
└── assoc_index_archive.json     ← >365天条目移入
```

### 新增skill目录

```
skills/memory/
├── kindle-config/SKILL.md       ← Kindle看板配置
├── db-recovery/SKILL.md         ← state.db崩溃恢复
├── 3d-system/SKILL.md           ← 三维记忆系统设计
├── internal-first/SKILL.md      ← 内外优先级铁律
└── ...                          ← 后续每新增1条assoc_index→1个skill
```

### 数据流全景

```
讨论中（我）
  │ 提到相关话题
  ├→ focus_tracker append（我顺手+1）
  ├→ 对应的micro-skill自动加载（Hermes系统层·察觉不到）
  └→ 回答中自然提及关联记忆

讨论结束（我判断"值"）
  └→ memory_index.py --add ...（≤3次/天）

cron每30min（memory_focus.py）
  └→ 读focus_tracker → 算聚焦度 → 写入MEMORY.md顶部2-3行
      → 旧的专注行自然滑落

cron每10min（memory_skillgen.py）
  ├→ 读assoc_index.json
  ├→ 对比skills/memory/目录 → 增/删/改 skill
  └→ 算关联分+时间衰减 → 写入memory_context.json

cron每周日（memory_calibrate.py）
  ├→ 读每条的hits/misses
  ├→ acc<0.3降权 / acc>0.8升权
  └→ >365天的条目移入archive
```

**97% LLM-free。** 唯一需要LLM判断：讨论结束决定"值不值得记"。

---

### 3.1 文件位置

`~/.hermes/baige/cache/assoc_index.json`

### 3.2 格式

```json
[
  {
    "id": "timestamp_topic",
    "date": "2026-07-10",
    "topic": "话题名称",
    "subjects": ["主体1", "主体2"],
    "event": "事件描述（动词+宾语）",
    "time_vec": "2026-07-10",
    "ref": "引用来源（文件路径/讨论ID）",
    "weight": 1.0,
    "hits": 0,
    "misses": 0
  }
]
```

### 3.3 维护时机

每次重要讨论结束时，自动追加一行。**不是cron。** 因为我知道什么值得记。

追加操作：
```python
# 讨论结束时自动执行
assoc_index.append({
  "id": f"{today}_{topic_abbr}",
  "subjects": [从讨论中提取的主体列表],
  "event": 从讨论中提取的事件描述,
  "time_vec": today,
  ...
})
```

### 3.4 同义词扩展

每个条目存储多组同义词，避免不同模型抽词不一致：
```json
"subjects": ["Kindle", "Kindle看板", "看板", "电子书浏览器"],
"event": ["配置+重定向IP", "修改绑定地址", "改IP"]
```

---

## 四、关联分算法

### 4.1 三维向量匹配

从用户一句话中提取：
- **主体向量** — 谁？什么板块？什么系统？什么文件？
- **事件向量** — 什么事？发生/运动/轨迹
- **时间向量** — 何时？今天/昨天/上周/模糊时间

### 4.2 关联分公式

```
关联分 = 主语匹配率 × 0.5 + 事件词重叠率 × 0.3 + 时间衰减权重 × 0.2
```

各维度说明：

| 维度 | 权重 | 原理依据 |
|:----|:----:|:----|
| 主语匹配 | 0.5 | TF-IDF核心实体匹配——同一事物在不同讨论出现，关联度最高 |
| 事件重叠 | 0.3 | 语义相似度——动宾结构泛化匹配 |
| 时间衰减 | 0.2 | 艾宾浩斯遗忘曲线——第1天衰减50%，第7天衰减80% |

时间衰减函数：
```
时间权重 = max(0, 1 - log(days_since + 1) / log(365))
  → 第1天: 1.0
  → 第7天: 0.66
  → 第30天: 0.48
  → 第365天: 0.0
```

### 4.3 推送阈值

| 关联分 | 行为 | 场景 |
|:----:|:----|:----|
| ≥0.7 | **自动推送**：回答前弹出关联提醒 | A场景（话题关联） |
| 0.4~0.7 | **触发第二层查询**：查discussion-template skill补充匹配 | 仅在A场景使用 |
| <0.4 | 不触发 | 正常回答 |

---

## 五、三层主动推送（A/B/C场景）

### 5.1 A场景：话题关联

**触发时机：你说话了，我准备回答**

流程：
```
你说话 → 提取[主体+事件+时间] → 扫描assoc_index →
  ├─ ≥0.7: 回答前弹出 🗂 关联提醒
  ├─ 0.4~0.7: 降级查discussion-template skill补充
  └─ <0.4: 正常回答
```

推送格式：
> **🗂 关联：** 7月10日讨论过Kindle看板
> IP=<your-server>:<port>，PV重定向已改，服务已重启
>
> (回答你的问题...)

### 5.2 B场景：关联话题（新话题与旧话题相关）

**触发时机：你的新话题与assoc_index某条的主语匹配但事件不同**

与A场景共用同一算法，不做区分。A算法已覆盖。

### 5.3 ~~C场景：决策风险拦截~~ 已删除

**记忆系统不负责拦截。拦截是认知层的事。**

记忆系统的职责到"提供历史教训"为止——当用户提及危险操作对象时，对应的micro-skill自动加载，历史教训（如"之前rm删过备份""改这配置出过问题"）自然出现在我的上下文中。

**认知层（我——LLM）基于这些数据做决策：** 这次和上次情况一样吗？需要警告用户吗？直接执行还是先问？

这就是天网神经系统的正确分工：

```
聊天记录系统 → 存原始数据
记忆系统     → 提供历史教训（micro-skill自动加载）
认知层（LLM）→ 基于教训+当前上下文做拦截决策
```

> ❌ v1.0错误：把C场景写在记忆系统skill里，等于让海马体做前额叶的决策
> ✅ v2.1修正：记忆系统只负责"当你提危险操作时，自动显示相关历史教训"——拦截不拦截是LLM的事

---

## 六、自校准机制

### 6.1 反馈收集（自动判断）

从用户的下一条回复推断推送效果：

| 用户回复 | 判定 | 操作 |
|:----|:----|:----|
| "对"/"正是"/"就这个" | ✅ 正反馈 | hits += 1 |
| "不是"/"不对"/"没关系" | ❌ 负反馈 | misses += 1 |
| 跳过推送直接回答后面内容 | ⚠️ 无反馈 | hits不变 |
| 连续3次无反馈 | 🗑 降权 | weight × 0.5 |

### 6.2 权重调整（每周日）

```python
for entry in assoc_index:
    if entry.hits + entry.misses > 3:  # 样本量足够
        accuracy = entry.hits / (entry.hits + entry.misses)
        if accuracy < 0.3:
            weight *= 0.7  # 降权但不删除
        elif accuracy > 0.8:
            weight = min(1.0, weight * 1.1)  # 加分不超上限
```

### 6.3 刷新抑制

- 每3轮对话最多1条推送。多条命中时只推关联分最高的那条。
- 降权条目不删除——保留可逆性。如果用户后续对降权条目有正面反馈，可恢复。

---

## 七、效率保障

| 路径 | 成本 | 频率 | 方案 |
|:----|:----:|:----:|:----|
| assoc_index内存扫描 | ~0ms | 每次对话 | 纯内存，<5KB |
| 讨论skill fallback | 稍慢 | 少（仅0.4~0.7时） | 可接受 |
| 长期备份扫描 | 慢 | 极少（仅认知层深度检索） | 半年以内不走这条路径 |
| 自校准统计 | 稍慢 | 每周1次 | 低频无影响 |

同义词扩展走内存映射表，不额外读盘。

---

## 八、风险规避

| # | 风险 | 后果 | 解法 |
|:-:|:----|:----|:----|
| 1 | 一次对话推多条 | 刷屏导致用户关闭 | 3轮最多1条，多条命中取最高分 |
| 2 | 自校准误杀有用条目 | 好记忆永不出现 | 只降权不删除，可逆 |
| 3 | 危险操作不自知 | 旧教训未归档→认知层缺乏判断依据 | micro-skill的triggers覆盖危险操作关键词，历史教训自动加载 |
| 4 | 讨论结束忘了加索引 | assoc_index漏记 | 你提旧话题时我查不到→下次讨论结束补上 |
| 5 | assoc_index越积越大 | 几年后膨胀 | 年度归档：>365天的存档单独文件 |
| 6 | 写入时文件损坏 | 索引丢失 | 先写tmp再rename，原子操作 |

---

## 九、v2.0完整决策树

```
你说话/让我做事
  |
  +-- 让我做事？（即将调用工具）
  |   |
  |   +-- 记忆系统提供历史教训（micro-skill自动加载）:
  |   |   - 若操作对象有历史教训→自然出现在我上下文
  |   |   - 认知层(LLM)基于此做决策
  |   |
  |   +-- 认知层决策:
  |       - 判断是否危险 -> 决定拦截/警告/直接执行
  |       - 如判断需要确认 -> 问你"确定吗"
  |       - 你确认 -> 执行
  |
  +-- 你说话（需要回答）
      |
      +-- Tier 1: skill自动加载（我已经知道）
      +-- Tier 2: memory专注窗口摘要
      |   +-- 我自动记得最近高频话题
      +-- Tier 3: assoc_index深度检索
      +-- Tier 4: 手动深查（管道库/讨论/E盘）

LLM只做两件记忆相关的事：
  1. 讨论结束 -> memory_index.py --add（判断值不值得记）
  2. 自然判断拦截（基于记忆系统提供的历史教训·非系统强制）
```

---

## 十、初始化

首次使用：

```bash
mkdir -p ~/.hermes/baige/cache
echo '[]' > ~/.hermes/baige/cache/assoc_index.json
```

然后建立第一批索引条目（本skill讨论积累的三条）：

| id | topic | subjects |
|:----|:----|:----|
| 20260710_kindle | Kindle看板配置 | Kindlle,泰坦,看板,局域网 |
| 20260710_db | state.db崩溃恢复 | state.db,WAL,备份,恢复 |
| 20260710_3d | 三维记忆系统设计 | 记忆,分层,3D定位,主动推送,自校准 |

---

## 十三、实现状态（v2.0 已上线 ✅）

> 2026-07-11 实施完成。4脚本+3cron覆盖全流程。全链路验证通过。

| 组件 | 状态 | 说明 |
|:----|:----:|:----|
| assoc_index.json | ✅ 已有 | 5条条目（7/10原4条+7/11新增1条） |
| focus_tracker.json | ✅ cron每10min自动写入 | memory_skillgen.py自动检测state.db用户消息→keyword匹配 |
| memory_focus.py + cron | ✅ 每30min(job:1d1075f7a630) | 读focus_tracker→算聚焦分→更新MEMORY.md顶部行 |
| memory_skillgen.py + cron | ✅ 每10min(job:3580aa279e59) | assoc_index→micro-skill自动同步+state.db自动命中检测 |
| memory_calibrate.py + cron | ✅ 每周日03:10(job:413062dcf613) | 权重调整+年度归档 |
| memory_index.py | ✅ 讨论结束手动--add | 统一写入入口，支持add/update/calibrate/auto-detect/list |
| skills/memory/目录 | ✅ 5个micro-skill | 20260710_kindle, _db, _3d, _internal_first, 20260711_memory_v2 |
| MEMORY.md动态专注区 | ✅ 专注行已注入 | 第1行`⚡ 专注(30min): ...` |

**LLM-free度：** 4脚本+3cron全部自动运行，仅有1个手动步（memory_index.py --add）。

| # | 操作 | 章节 | 实现状态 | 说明 |
|:-:|:----|:----:|:--------:|:----|
| 1 | focus_tracker自动检测 | 十一 | ✅ cron自动 | memory_focus.py每30min + memory_skillgen.py每10min state.db扫描 |
| 2 | 动态专注窗口更新MEMORY.md | 十一 | ✅ cron自动 | memory_focus.py每30min重写顶部行 |
| 3 | assoc_index→micro-skill自动同步 | 十二 | ✅ cron自动 | memory_skillgen.py每10min+检查mtime跳过不变 |
| 4 | 手动追加assoc_index条目 | 十二 | ✅ memory_index.py | python memory_index.py --add id=... subjects=... |
| 5 | 手动更新条目字段 | 十二 | ✅ memory_index.py | python memory_index.py --update id=... field=... value=... |
| 6 | 自动关联命中检测 | 十二 | ✅ cron自动 | memory_skillgen.py扫state.db最近10条用户消息做keyword match |
| 7 | 每周日权重调整+年度归档 | 十二 | ✅ cron自动 | memory_calibrate.py每周日03:10 |
| 8 | 聚焦分计算（1h×1.0+24h×0.3+weight×0.1） | 十一 | ✅ cron自动 | memory_focus.py内部 |
| 9 | 时间衰减（mem_calibrate自然衰减） | 六 | ✅ cron自动 | memory_calibrate.py 30天无反馈→weight×0.95 |
| 10 | 原子写入（先tmp再rename） | 十二 | ✅ 全部脚本 | 所有memory_*.py均使用tmp+shutil.move |
| 11 | C场景认知决策 | 五·5.3 | ✅ 认知层自然覆盖 | 记忆系统负责提供历史教训（micro-skill自动加载），认知层（LLM）基于此+当前上下文做拦截决策。非代码强制，而是自然认知流程。 |
| 12 | 年度归档（>365天） | 十二 | ✅ cron自动 | memory_calibrate.py每周日执行 |
| 13 | 校准反馈收集 | 六 | ✅ 存档字段 | assoc_index条目的hits/misses字段已定义 |
| 14 | 推送控制（3轮1条） | 六 | 🔲 待实施 | 低优先级（skill映射已取代推送需求） |

**图例：** ✅ 有完整代码 / ⚡ 有文件但手动 / 📄 仅设计文档 / 🔲 未实现

**实现顺序建议：** 第1批（查询引擎#1~#7）→ 第2批（C场景#8~#12）→ 第3批（校准+#13~#17）→ 第4批（维护#18~#20）

**详细计划：** `references/implementation-plan.md`

---

## 十四、陷阱

| # | 陷阱 | 后果 | 解法 |
|:-:|:----|:----|:----|
| H012 | 静态核心不流动 | 上周的专注一直占memory，新专注无空间 | 每次新会话检查MEMORY.md顶部的专注行——如果还是上周的，说明focus cron没跑 |
| H013 | 记忆系统本身不记忆 | 声明memory_tier: auto意味着它自己也会按使用频率降级，如果几个月不用应退到被动 | 自校准只降权不删除，保留可逆性 |
| H014 | 审计系统时只看文件存在不看设计完整性 | 文件/目录空就下结论系统不存在 | 检查系统完整性前先查cron调度和脚本源码确认触发机制 |
| H015 | memory溢出不预警 | 90%+的memory导致其他领域被压缩 | 达到85%即主动将可skill化的条目移出至skills/memory/ |
| H016 | 讨论结束忘了加索引 | assoc_index漏记，下次提旧话题查不到 | 每次讨论结束最后一步：memory_index.py --add |
| H017 | 拦截放错了层 | 把决策拦截写在记忆系统skill里，让海马体做前额叶的事 | C场景已从记忆系统删除。记忆系统只提供历史教训（micro-skill自动加载），拦截决策是认知层（LLM）的自然职责。|
| H018 | 同义词存单组 | 不同模型抽词不一致导致匹配失败 | subjects和event数组存多组同义词 |
| H019 | 内外优先级反了 | 第一时间想外部工具而不是内部 | skills > scripts > cron > 文件系统 > 才到外部 |
| H020 | LLM主动调用记忆系统=精神分裂 | 设计记忆系统时止步于"半自动+LLM手动补位"=设计失败 | **记忆主环必须100%自动（cron+脚本），LLM只做判断型决策（"值不值得记"），不参与运行链。** 任何需要LLM主动查文件/调脚本/算关联分的系统都是在人脑里住了个记忆操作员。 |

---

**快速参考**: `references/algorithm-quickref.md` — assoc_index格式·关联分公式·阈值·自校准\n**实施记录**: `references/v2-implementation.md` — 4脚本·3cron·9条索引·5micro-skill全链路明细
