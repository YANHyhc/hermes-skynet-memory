#!/usr/bin/env python3
"""
memory_methodology_gen.py — 记忆系统使用方法论生成器 (2026-08-08 v1.0)
评测消费通道2: 读评测报告 → 生成/更新普适方法论 skill (memory-usage-guide)
供 LLM 完美贴合使用记忆系统; 模板化, 换系统可复用。

用法: python memory_methodology_gen.py [--round N]
"""
import os
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOME = Path(os.path.expanduser("~/.hermes"))
EVAL_DIR = HOME / "cache/memory_eval"
SKILL_DIR = HOME / "skills" / "methodology" / "memory-usage-guide"

# 模板占位符 (普适: 换系统只需重跑评测)
TEMPLATE = """---
name: memory-usage-guide
description: "记忆系统使用指南 — {system_name}的系统画像/使用地图/检索技巧/使用流程/评测消费。任何LLM加载后即可完美贴合使用该记忆系统。"
triggers:
  - 记忆检索
  - 查历史
  - 找记录
  - 记忆系统使用
  - 怎么查记忆
---

# 记忆系统使用方法论（{system_name}）

> 本方法论由记忆评测系统自动生成（{generated_at}，第{round_num}轮评测）。
> 评测 = 体检，方法论 = 处方。报告给系统优化，方法论给LLM完美应用。

## 使用须知（必读）

```
⚠️ 使用本记忆系统前: 先读本方法论 (skill_view memory-usage-guide)
   → 全知记忆系统 → 高效劳作
   → 每日醒来/新会话/换模型后: 主动读一次 (方法论进云端缓存)
本方法论适用于记忆系统: {system_name} (普适, 其他系统可换名复用)
```

## 1. 系统画像（评测实测）

| 维度 | 得分 | 评价 |
|:-----|:----:|:----:|
| 检索可达 (Recall@5) | {recall} | {recall_comment} |
| 检索排序 (MRR) | {mrr} | {mrr_comment} |
| 认知能力 | {cognitive_avg} | {cognitive_comment} |
| 压力测试 | {stress_avg} | {stress_comment} |

**强项**（≥90%）：{strong_areas}

**待加强**（<90%）：{weak_areas}

**记忆源**（评测识别）：{sources}

## 2. 记忆地图（查什么用什么）

| 记忆类型 | 存在哪 | 何时用 | 怎么查 |
|:---------|:-------|:-------|:-------|
| 事件/历史 | 记忆档案 | 查"什么时候发生了什么" | 按日期/事件名搜目录 |
| 讨论/决策 | 讨论模块 | 查"为什么这么定" | 搜目录名+内容 |
| 修复/交付 | 修复报告 | 查"怎么解决的" | 搜报告文件名+内容 |
| 最新动态 | 24h缓存 | 查"最近发生了什么" | 直接读recent_24h |
| 语义知识 | 向量知识库 | 查"概念/关联" | 语义检索(如可用) |

## 3. 检索技巧（关键）

```
① 关键词: 用【实体词】(三祥/BOM) 而非描述词(持有/卖)
   → 实体词在文件名/内容里, 描述词需要映射
② 中英映射: 同一概念中英都要试
   → 竞彩↔jingcai, 硬盘↔disk, 中标↔EPC, 教训↔learn
③ 多源串联: 跨源问题查【主索引】+ 各源内容
   → 不要只查单源
④ 时间查询: 用【具体日期/事件名】而非"最近/之前"
   → 24h缓存(新) vs 档案(旧)
⑤ 泛词无效: "记录/信息/更新" 无区分度 → 用具体词
```

## 4. 使用流程（4步）

```
Step1 定类型: 事件? 语义? 时间? 跨源?
Step2 选入口: 档案/知识库/24h/多源
Step3 构查询: 实体词 + 中英映射 + 具体时间
Step4 验证: 检查结果是否含目标内容(文件名或内容命中)
```

## 5. 评测消费闭环

```
跑评测 → 2输出:
  ① 报告 → 上帝 → 系统优化依据
  ② 本方法论 → LLM → 系统完美应用指南
  下轮评测: 聚焦薄弱 → 方法论自动更新 → 系统更好用
```

## 6. 注意事项（本系统特有）

{weak_notes}

## 7. 普适性说明

```
本方法论由通用评测框架生成:
  评测框架: 采样/变体/分层/组合 (通用)
  模板: {system_name}/{sources} 占位符
  → 换任何记忆系统: 重跑评测 → 自动生成新方法论
  → 评测=体检工具, 方法论=普适处方
```

## 8. 命名规范（记忆档案·v1.0）

```
【格式】: YYYY-MM-DD_类型-主题[-序号]
【示例】:
  2026-08-09_讨论-档案命名系统
  2026-08-09_讨论-档案命名系统-2 (同日第二个)
  2026-08-10_交付-实盘操盘辅助体系
  2026-08-11_拓扑双检
【类型词表】: 讨论|指令|修复|交付|评测|拓扑双检|记录|学习|其他
【原则】:
  ① 时间优先 (YYYY-MM-DD 索引骨架)
  ② 类型标记 (过滤/统计)
  ③ 主题语义 (文件名即答案)
  ④ 兼容性 (新旧并存, 旧档案不迁移)
  ⑤ 唯一性 (序号 -2/-3 防冲突)
【策略】: 新建档案按规范, 过往档案保留 (渐进式)
```
"""


def parse_report(report_path):
    """解析评测报告 → 结构化数据"""
    text = open(report_path, encoding="utf-8").read()
    data = {}
    m = re.search(r"Recall@5 \| ([\d.]+)", text)
    data["recall"] = float(m.group(1)) if m else 0
    m = re.search(r"MRR \| ([\d.]+)", text)
    data["mrr"] = float(m.group(1)) if m else 0

    # 模块得分 (过滤难度行)
    DIFFICULTY_KEYS = {"中等", "地狱", "基础", "挑战", "极限"}
    modules = {}
    for line in text.split("\n"):
        if line.startswith("- ") and "%" in line:
            try:
                name, rest = line[2:].split(":", 1)
                if name.strip() in DIFFICULTY_KEYS:
                    continue
                hit_str, total_str = rest.strip().split("/")
                hit = int(hit_str)
                total = int(total_str.split(" ")[0])
                modules[name.strip()] = hit / total if total else 0
            except Exception:
                continue
    data["modules"] = modules
    return data


def gen_skill(data, round_num):
    """填充模板 → 生成 SKILL.md"""
    modules = data.get("modules", {})
    strong = [k for k, v in modules.items() if v >= 0.9]
    weak = [k for k, v in modules.items() if v < 0.9]

    cognitive_mods = ["G_多跳推理", "H_记忆更新", "I_冲突消解", "J_记忆串联", "K_语义边界", "M_元认知"]
    cog = [v for k, v in modules.items() if k in cognitive_mods]
    cog_avg = sum(cog) / len(cog) if cog else 0

    stress_mods = ["P_压力测试", "S_场景任务"]
    stress = [v for k, v in modules.items() if k in stress_mods]
    stress_avg = sum(stress) / len(stress) if stress else 0

    weak_notes = (
        "\n".join(f"- {k} ({v:.0%}): 查询时需特别处理" for k, v in modules.items() if v < 0.9) or "- 无显著弱项"
    )

    content = TEMPLATE.format(
        system_name="Hermes",
        generated_at="2026-08-08",
        round_num=round_num,
        recall=f"{data.get('recall', 0):.3f}",
        recall_comment="优秀" if data.get("recall", 0) >= 0.9 else "良好",
        mrr=f"{data.get('mrr', 0):.3f}",
        mrr_comment="优秀" if data.get("mrr", 0) >= 0.8 else "良好",
        cognitive_avg=f"{cog_avg:.0%}",
        cognitive_comment="强" if cog_avg >= 0.9 else "中",
        stress_avg=f"{stress_avg:.0%}",
        stress_comment="强" if stress_avg >= 0.9 else "中",
        strong_areas=", ".join(strong) if strong else "无",
        weak_areas=", ".join(weak) if weak else "无",
        sources="记忆档案(事件) + 讨论模块(决策) + 修复报告(方案) + 24h缓存(最新) + 向量知识库(语义)",
        weak_notes=weak_notes,
    )
    return content


def main():
    round_num = 1
    if "--round" in sys.argv:
        idx = sys.argv.index("--round")
        round_num = int(sys.argv[idx + 1])

    report_path = EVAL_DIR / f"eval_report_r{round_num}.md"
    if not report_path.exists():
        print(f"❌ 评测报告不存在: {report_path}")
        print(f"   ⚠️ 必须先跑评测 (memory_eval.py --round {round_num}) 再生成方法论!")
        sys.exit(1)

    # 顺序铁律: 评测报告必须新于评测集 (确保基于最新评测)
    cases_path = EVAL_DIR / f"test_cases_r{round_num}.json"
    if cases_path.exists():
        report_mtime = report_path.stat().st_mtime
        cases_mtime = cases_path.stat().st_mtime
        if report_mtime < cases_mtime:
            print(f"❌ 评测报告({report_mtime})早于评测集({cases_mtime}) — 报告过期!")
            print(f"   ⚠️ 必须先跑评测 (memory_eval.py --round {round_num}) 再生成方法论!")
            sys.exit(1)

    data = parse_report(report_path)
    content = gen_skill(data, round_num)

    SKILL_DIR.mkdir(parents=True, exist_ok=True)
    out = SKILL_DIR / "SKILL.md"
    out.write_text(content, encoding="utf-8")
    print(f"✅ 方法论 skill 已生成: {out}")
    print(f"   系统画像: Recall={data.get('recall', 0):.3f} 模块{len(data.get('modules', {}))}个")
    strong = [k for k, v in data.get("modules", {}).items() if v >= 0.9]
    weak = [k for k, v in data.get("modules", {}).items() if v < 0.9]
    print(f"   强项({len(strong)}): {strong}")
    print(f"   待加强({len(weak)}): {weak}")


if __name__ == "__main__":
    main()
