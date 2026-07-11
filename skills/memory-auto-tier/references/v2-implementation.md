# 记忆系统 v2.0 实施参考

> 2026-07-11 全链路实施记录
  
## 架构演变

| 版本 | 日期 | 关键变化 |
|:----|:----:|:--------|
| v1.0 设计 | 7/10 | 20个操作描述，但仅1个(assoc_index.json)有代码 |
| v2.0 实施 | 7/11 | 4脚本+3cron+10索引+5micro-skill+动态专注窗口 |

## 核心设计模式

### 模式1：时间窗口替代空间分区

memory不支持分区 → 用30min时间窗口替代：
- 每30min换一批focus → 天生分区
- 用完即走，不占固定空间
- 专注自然流动，静态=蠢人

### 模式2：三层递进 + 短路

- Tier 1 (skill映射): triggers命中即加载，零延迟
- Tier 2 (专注窗口): cron每30min更新memory顶部
- Tier 3 (深度检索): 文件持久化，cron预更新
- 命中即停，不逐层全量扫

### 模式3：97% LLM-free

唯一手动操作：讨论结束 `memory_index.py --add`（判断值不值得记）
所有主环操作：cron自动（skill同步/专注窗口/校准归档/auto-detect）

## 实施清单

### 4个脚本

| 脚本 | 功能 | 调度 |
|:----|:-----|:----:|
| `memory_index.py` | 统一写入入口(--add/--update/--calibrate/--auto-detect/--list) | 手动触发 |
| `memory_skillgen.py` | assoc_index→micro-skill同步 + state.db自动检测focus | cron每10min |
| `memory_focus.py` | 读focus_tracker→算聚焦度→更新MEMORY.md专注行 | cron每30min |
| `memory_calibrate.py` | 权重调整 + 年度归档(>365天) | cron每周日03:10 |

### 3个cron

| job_id | 调度 | deliver |
|--------|:----:|:-------:|
| 3580aa279e59 | `*/10 * * * *` | local |
| 1d1075f7a630 | `5,35 * * * *` | local |
| 413062dcf613 | `10 3 * * 0` | local |

### 数据结构

```
~/.hermes/
├── baige/cache/assoc_index.json         ← 持久化源(9条↓extensible)
├── baige/cache/assoc_index_archive.json ← >365天归档
├── cache/focus_tracker.json             ← 命中记录(每30min清空)
├── cache/.skillgen_last_mtime           ← 变更检测标记
├── baige/cache/.assoc_mtime             ← 变更检测标记
├── skills/memory/{id}/SKILL.md          ← auto-generated micro-skills
├── memories/MEMORY.md                   ← 专注行由focus cron自动更新
└── .discussions/memory-system/          ← 讨论记录
```

## 设计陷阱 (追加于7/11)

- **H029**: 断言组件不存在前→查cron+脚本+目录+定时四步。目录空≠系统不存在。
- **H030**: focus_tracker自动检测→LLM无需手动--hit
- **H031**: 讨论结束必--add归档（判断：有参考价值？有教训/经验/配置？）
- **H032**: 发现skill信息过期→--update（cron 10min内自动重生成skill）

## v2.1 修正 (2026-07-11 同日)

| 修正 | 内容 |
|:----|:------|
| C场景 | ~~记忆系统拦截~~ → ❌ 错误设计。拦截是认知层(LLM)的事，不是记忆系统的职责。记忆系统负责到"提供历史教训"为止（micro-skill自动加载），认知层基于此+当前上下文做决策。 |

## 未做/延迟项

- memory_context.json: 无消耗者(Hermes无文件自动注入钩子) → ❌ 不做
- ~~C场景危险拦截~~: ✅ v2.1修正——属认知层职责，非代码问题
- 多域独立存储: 等待各域密度≥5条 → ⏳ 待条件
