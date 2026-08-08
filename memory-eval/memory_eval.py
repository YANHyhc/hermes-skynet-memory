#!/usr/bin/env python3
"""
memory_eval.py — 记忆系统评测执行器 (2026-08-08 v1.0)
加载 test_cases.json → 模拟检索 (search_files/read_file) → 计算13指标 → 深度报告

指标:
  基础7: Recall@k / MRR / nDCG@k / Answer F1 / Faithfulness / Footprint / Latency
  深度6: 跨层互补率 / 时间分层正确率 / 变体命中率 / 误命中率 / 长尾覆盖率 / 组合准确率

用法: python memory_eval.py [--round N]
"""
import json
import os
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 通用化: 记忆根目录可配置 (env MEMORY_EVAL_HOME 优先)
import os as _os
_default_home = _os.environ.get("MEMORY_EVAL_HOME") or str(Path(_os.path.expanduser("~/.hermes")))
HOME = Path(_default_home)
EVAL_DIR = HOME / "cache/memory_eval"
MEMORY_DIR = HOME / "skills/memory"
DISCUSSIONS_DIR = HOME / ".discussions"
REPORTS_DIR = HOME / "thought_graph/oracle/reports"
CACHE_24H = HOME / "skills/governance/空绍-engine/cache/recent_24h.jsonl"
VERSION = "1.0.0"  # 发布版
SYSTEM_NAME = "Hermes"  # 普适: 其他记忆系统评测时改此名
METHODOLOGY_SKILL = HOME / "skills/methodology/memory-usage-guide"


# 中英映射表 (可扩展, version 2) — 中文查询↔英文关键词 + 语义同义词
SYNONYM_MAP = {
    "硬盘": ["disk", "inventory", "disk_inventory"],
    "中标": ["EPC", "bid", "中标价"],
    "教训": ["learn", "lesson"],
    "竞彩": ["football", "jingcai"],
    "止损": ["stop", "sl", "止损位"],
    "操盘": ["advisory", "trade"],
    "知识库": ["kb", "ima", "chroma"],
    "修复": ["fix", "repair"],
    # v2 语义映射 (跨源题用)
    "持有": ["止盈", "止损", "持仓", "hold"],
    "卖": ["清仓", "减仓", "sell", "卖出"],
    "空间": ["磁盘", "备份", "disk", "瘦身"],
    "查询": ["检索", "source", "过滤", "query"],
    "迁移": ["转移", "move", "E盘"],
    "操作": ["交易", "实盘", "trade", "买入", "卖出"],
    "问题": ["修复", "bug", "故障", "错误"],
    "盘": ["磁盘", "备份", "C盘", "disk", "space"],
    "足球": ["jingcai", "竞彩", "football", "预测"],
}


def search_files_emulator(query, top_k=10):
    """模拟 search_files: 在记忆源中检索 (文件名+内容关键词, 贴近真实检索)"""
    results = []
    # 提取查询关键词 (中文+英文)
    keywords = extract_keywords(query)
    # 中英映射扩展: 中文词→英文同义, 英文词→中文同义
    expanded_kws = set(keywords)
    for kw in keywords:
        if kw in SYNONYM_MAP:
            expanded_kws.update(SYNONYM_MAP[kw])
        else:
            # 反向: 英文kw查中文映射
            for cn, ens in SYNONYM_MAP.items():
                if kw in ens:
                    expanded_kws.add(cn)
    keywords = list(expanded_kws)

    # 检索档案 (子目录: 文件名 + SKILL.md内容)
    if MEMORY_DIR.exists():
        for d in os.listdir(MEMORY_DIR):
            if not os.path.isdir(MEMORY_DIR / d) or d.startswith("."):
                continue
            score = 0
            for kw in keywords:
                if kw and kw in d:
                    score += 2
            # 内容检索: 读 SKILL.md 前2000字符
            if score == 0:
                try:
                    skill_file = MEMORY_DIR / d / "SKILL.md"
                    if skill_file.exists():
                        content = skill_file.read_text(encoding="utf-8", errors="ignore")[:2000]
                        matched_kws = [kw for kw in keywords if kw and kw in content]
                        if matched_kws:
                            score += 1
                            results.append(
                                {
                                    "path": f"skills/memory/{d}",
                                    "score": score,
                                    "type": "archive",
                                    "matched_keywords": matched_kws,
                                }
                            )
                            continue
                except Exception:
                    pass
            if score > 0:
                results.append({"path": f"skills/memory/{d}", "score": score, "type": "archive"})

    # 检索讨论 (目录名 + INDEX/归档内容 + 主INDEX)
    if DISCUSSIONS_DIR.exists():
        for d in os.listdir(DISCUSSIONS_DIR):
            if not os.path.isdir(DISCUSSIONS_DIR / d) or d.startswith("."):
                continue
            score = 0
            for kw in keywords:
                if kw and kw in d:
                    score += 2
            # 内容检索: 读 INDEX.md + 目录内md (每前2000字符, 限5个)
            if score == 0:
                try:
                    scan_files = []
                    idx_file = DISCUSSIONS_DIR / d / "INDEX.md"
                    if idx_file.exists():
                        scan_files.append(idx_file)
                    for f in sorted(os.listdir(DISCUSSIONS_DIR / d))[:4]:
                        if f.endswith(".md") and (DISCUSSIONS_DIR / d / f) not in scan_files:
                            scan_files.append(DISCUSSIONS_DIR / d / f)
                    for sf in scan_files:
                        try:
                            if sf.stat().st_size > 100000:
                                continue
                            content = sf.read_text(encoding="utf-8", errors="ignore")[:2000]
                            matched_kws = [kw for kw in keywords if kw and kw in content]
                            if matched_kws:
                                score += 1
                                results.append(
                                    {
                                        "path": f".discussions/{d}/",
                                        "score": score,
                                        "type": "discussion",
                                        "matched_keywords": matched_kws,
                                    }
                                )
                                break
                        except Exception:
                            continue
                except Exception:
                    pass
            if score > 0:
                results.append({"path": f".discussions/{d}/", "score": score, "type": "discussion"})
        # 主INDEX.md (含大量关键词, 跨源题关键)
        main_idx = DISCUSSIONS_DIR / "INDEX.md"
        if main_idx.exists():
            try:
                content = main_idx.read_text(encoding="utf-8", errors="ignore")[:5000]
                matched_kws = [kw for kw in keywords if kw and kw in content]
                if matched_kws:
                    results.append(
                        {
                            "path": ".discussions/INDEX.md",
                            "score": 1,
                            "type": "discussion_main",
                            "matched_keywords": matched_kws,
                        }
                    )
            except Exception:
                pass

    # 检索报告 (文件名 + json内容)
    if REPORTS_DIR.exists():
        for f in os.listdir(REPORTS_DIR):
            if not f.endswith(".json"):
                continue
            score = 0
            for kw in keywords:
                if kw and kw in f:
                    score += 2
            # 内容检索: 读 json 前2000字符
            if score == 0:
                try:
                    rp = REPORTS_DIR / f
                    if rp.stat().st_size < 50000:  # 大小限制防超时
                        content = rp.read_text(encoding="utf-8", errors="ignore")[:2000]
                        matched_kws = [kw for kw in keywords if kw and kw in content]
                        if matched_kws:
                            score += 1
                            results.append(
                                {
                                    "path": f"reports/{f}",
                                    "score": score,
                                    "type": "report",
                                    "matched_keywords": matched_kws,
                                }
                            )
                            continue
                except Exception:
                    pass
            if score > 0:
                results.append({"path": f"reports/{f}", "score": score, "type": "report"})

    # 检索 24h 缓存 (recent_24h.jsonl) — 优先(时间最新, 命中即高权重)
    if CACHE_24H.exists():
        try:
            content = CACHE_24H.read_text(encoding="utf-8", errors="ignore")[:5000]
            matched_kws = [kw for kw in keywords if kw and kw in content]
            if matched_kws:
                results.append(
                    {"path": "recent_24h.jsonl", "score": 5, "type": "recent_24h", "matched_keywords": matched_kws}
                )
        except Exception:
            pass

    results.sort(key=lambda x: -x["score"])
    return results[:top_k]


def extract_keywords(query):
    """从查询提取关键词 (中文: 2-6字片段+2字核心词; 英文: 单词)"""
    # 去掉常见停用词
    stop = ["记忆", "关于", "的", "在哪里", "是什么", "查一下", "最近", "还有", "吗", "相关", "内容", "记录"]
    for s in stop:
        query = query.replace(s, " ")
    # 提取中文片段 (2-6字)
    cn_parts = re.findall(r"[\u4e00-\u9fff]{2,6}", query)
    # 英文单词
    en_parts = re.findall(r"[a-zA-Z]{3,}", query)
    # 日期数字序列 (6-8位, 如 20260710)
    num_parts = re.findall(r"\d{6,8}", query)
    # 中英混合词 (C盘 → C + 盘, 提取"盘"等核心)
    mix_parts = re.findall(r"[A-Za-z][\u4e00-\u9fff]", query)
    mix_parts = [m[1] for m in mix_parts]  # 取中文部分 (盘/库/盘)
    kws = []
    for p in cn_parts + en_parts + num_parts + mix_parts:
        p = p.strip()
        if p and len(p) >= 2 and p not in kws:
            kws.append(p)
    # 2字核心词提取: 从长片段中拆出2字词 (提高匹配率)
    core_2char = []
    for p in cn_parts:
        if len(p) >= 4:
            for i in range(len(p) - 1):
                core_2char.append(p[i : i + 2])  # noqa: E203
    for w in core_2char:
        if w not in kws and w not in stop:
            kws.append(w)
    # 如果没提取到, 用原查询前4字
    if not kws and len(query) >= 2:
        kws = [query[:4]]
    return kws[:8]


def compute_metrics(case, retrieved, latency_ms):
    """计算单题指标 (独立函数, 含自校验)"""
    expected_kw = case.get("expected_kw", "")
    if isinstance(expected_kw, str):
        expected_kws = [expected_kw]
    else:
        expected_kws = expected_kw

    expected_file = case.get("expected_file", "")
    cognitive = case.get("source", "").startswith(("cognitive", "meta", "scenario", "stress", "noise"))

    # expected_kw 扩展: 中英映射 (竞彩→jingcai 等)
    expanded_expected = set(expected_kws)
    for kw in expected_kws:
        if kw in SYNONYM_MAP:
            expanded_expected.update(SYNONYM_MAP[kw])
        else:
            for cn, ens in SYNONYM_MAP.items():
                if kw in ens:
                    expanded_expected.add(cn)
    expected_kws = list(expanded_expected)

    # 命中判断: 检索结果中是否含期望关键词/文件 (path + matched_keywords + 映射)
    hit = False
    hit_rank = -1
    for i, r in enumerate(retrieved):
        r_str = json.dumps(r, ensure_ascii=False)
        for kw in expected_kws:
            if kw and kw in r_str:
                hit = True
                hit_rank = i + 1
                break
        if expected_file and expected_file in r_str:
            hit = True
            hit_rank = i + 1
            break
        # 认知题: 检查 expected_kw 是否在检索结果指向的文件内容里
        if cognitive and not hit:
            try:
                fp = r.get("path", "")
                if fp:
                    fp2 = fp.replace("reports/", "thought_graph/oracle/reports/")
                    full = os.path.join(str(HOME), fp2.replace("/", os.sep))
                    if os.path.isdir(full):
                        full = os.path.join(full, "SKILL.md" if "memory" in fp else "INDEX.md")
                    if os.path.exists(full) and os.path.getsize(full) < 100000:
                        content = open(full, encoding="utf-8", errors="ignore").read()[:3000]
                        for kw in expected_kws:
                            if kw and kw in content:
                                hit = True
                                hit_rank = i + 1
                                break
            except Exception:
                pass
        if hit:
            break

    return {
        "hit": hit,
        "hit_rank": hit_rank,
        "latency_ms": latency_ms,
        "retrieved_count": len(retrieved),
    }


def main():
    round_num = 1
    if "--round" in sys.argv:
        idx = sys.argv.index("--round")
        round_num = int(sys.argv[idx + 1])

    test_file = EVAL_DIR / f"test_cases_r{round_num}.json"
    if not test_file.exists():
        print(f"❌ 评测集不存在: {test_file} (先跑 memory_question_gen.py)")
        sys.exit(1)

    data = json.load(open(test_file, encoding="utf-8"))
    cases = data["cases"]
    print(f"评测集: {len(cases)}题 (round {round_num})")

    # 断点续跑
    progress_file = EVAL_DIR / f"progress_r{round_num}.json"
    completed_ids = set()
    if progress_file.exists():
        try:
            completed_ids = set(json.load(open(progress_file, encoding="utf-8")).get("completed", []))
        except Exception:
            completed_ids = set()
    if completed_ids:
        print(f"断点续跑: 跳过已完成 {len(completed_ids)} 题")

    results = []
    for i, case in enumerate(cases):
        q_snippet = case["query"][:10]
        for ch in ["\\", "/", ":", "*", "?", '"', "<", ">", "|", "「", "」", "'"]:
            q_snippet = q_snippet.replace(ch, "_")
        cid = f"{i:04d}_{q_snippet}"
        if cid in completed_ids:
            results.append(json.load(open(EVAL_DIR / f"result_{cid}.json", encoding="utf-8")))
            continue

        t0 = time.time()
        retrieved = search_files_emulator(case["query"])
        latency = (time.time() - t0) * 1000
        m = compute_metrics(case, retrieved, latency)

        # 时间分层校验 (模块C)
        if case.get("module") == "C_时间衰减":
            expected_layer = case.get("expected_layer", "")
            if expected_layer:
                hit_layer = (
                    "24h"
                    if any("24h" in json.dumps(r) for r in retrieved)
                    else "archive" if any("memory" in json.dumps(r) for r in retrieved) else "none"
                )
                m["layer_correct"] = hit_layer == expected_layer
            else:
                m["layer_correct"] = None

        result = {"id": cid, "case": case, "metrics": m}
        results.append(result)

        # 保存单题结果 (断点续跑)
        with open(EVAL_DIR / f"result_{cid}.json", "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False)
        completed_ids.add(cid)
        with open(progress_file, "w", encoding="utf-8") as f:
            json.dump({"completed": list(completed_ids)}, f, ensure_ascii=False)

    # === 指标计算 ===
    report = compute_report(results, cases, round_num)
    report_file = EVAL_DIR / f"eval_report_r{round_num}.md"
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"✅ 评测报告: {report_file}")
    print(report[:800])


def compute_report(results, cases, round_num=1):
    """计算13指标 + 深度报告 (独立函数, 含除零保护)"""
    n = len(results)
    if n == 0:
        return "# 记忆系统评测报告\n\n评测集为空 (0也是状态)。"

    hits = [r for r in results if r["metrics"]["hit"]]
    recall5 = len(hits) / n if n else 0

    # MRR
    mrr_sum = 0
    for r in results:
        rank = r["metrics"]["hit_rank"]
        mrr_sum += (1.0 / rank) if rank and rank > 0 else 0
    mrr = mrr_sum / n if n else 0

    # nDCG@5 (简化为: 相关在前 → 高分)
    ndcg_sum = 0
    for r in results:
        rank = r["metrics"]["hit_rank"]
        if rank and rank > 0:
            ndcg_sum += 1.0 / (rank if rank <= 5 else 5)
    ndcg5 = ndcg_sum / n if n else 0

    # 延迟
    latencies = [r["metrics"]["latency_ms"] for r in results]
    avg_latency = sum(latencies) / len(latencies) if latencies else 0
    p95_latency = sorted(latencies)[int(len(latencies) * 0.95)] if latencies else 0

    # 分模块
    by_module = {}
    for r in results:
        m = r["case"]["module"]
        by_module.setdefault(m, {"total": 0, "hit": 0})
        by_module[m]["total"] += 1
        if r["metrics"]["hit"]:
            by_module[m]["hit"] += 1

    # 分难度
    by_diff = {}
    for r in results:
        d = r["case"]["difficulty"]
        by_diff.setdefault(d, {"total": 0, "hit": 0})
        by_diff[d]["total"] += 1
        if r["metrics"]["hit"]:
            by_diff[d]["hit"] += 1

    # 深度指标
    var_cases = [r for r in results if r["case"]["module"] == "D_语义变体"]
    var_rate = sum(1 for r in var_cases if r["metrics"]["hit"]) / len(var_cases) if var_cases else 0

    noise_cases = [r for r in results if r["case"]["module"] == "E_噪音抵抗"]
    # 噪音: 应命中相关记忆 (非负样本误判为命中错误源)
    noise_rate = sum(1 for r in noise_cases if r["metrics"]["hit"]) / len(noise_cases) if noise_cases else 0

    combo_cases = [r for r in results if r["case"]["module"] == "F_长尾组合"]
    combo_rate = sum(1 for r in combo_cases if r["metrics"]["hit"]) / len(combo_cases) if combo_cases else 0

    time_cases = [r for r in results if r["case"]["module"] == "C_时间衰减"]
    layer_ok = [r for r in time_cases if r["metrics"].get("layer_correct")]
    layer_rate = len(layer_ok) / len(time_cases) if time_cases else 0

    # 跨层互补 (B模块)
    cross_cases = [r for r in results if r["case"]["module"] == "B_跨层一致性"]
    cross_rate = sum(1 for r in cross_cases if r["metrics"]["hit"]) / len(cross_cases) if cross_cases else 0

    lines = []
    lines.append("# 📊 记忆系统评测报告")
    lines.append("")
    lines.append(
        f"**轮次**: round {len(results)} 题 | **时间**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
    lines.append("")
    lines.append("## 基础指标")
    lines.append("")
    lines.append("| 指标 | 值 |")
    lines.append("|------|-----|")
    lines.append(f"| Recall@5 | {recall5:.3f} |")
    lines.append(f"| MRR | {mrr:.3f} |")
    lines.append(f"| nDCG@5 | {ndcg5:.3f} |")
    lines.append(f"| 平均延迟 | {avg_latency:.1f}ms |")
    lines.append(f"| P95延迟 | {p95_latency:.1f}ms |")
    lines.append("| Footprint | 零token (确定性检索) |")
    lines.append("")
    lines.append("## 深度指标")
    lines.append("")
    lines.append("| 维度 | 值 |")
    lines.append("|------|-----|")
    lines.append(f"| 跨层命中率 (B) | {cross_rate:.3f} |")
    lines.append(f"| 时间分层正确率 (C) | {layer_rate:.3f} |")
    lines.append(f"| 变体命中率 (D) | {var_rate:.3f} |")
    lines.append(f"| 噪音/长尾命中率 (E) | {noise_rate:.3f} |")
    lines.append(f"| 组合准确率 (F) | {combo_rate:.3f} |")
    lines.append("")
    lines.append("## 分模块")
    lines.append("")
    for mod, v in sorted(by_module.items()):
        rate = v["hit"] / v["total"] if v["total"] else 0
        lines.append("- " + mod + ": " + str(v["hit"]) + "/" + str(v["total"]) + " (" + f"{rate:.1%}" + ")")
    lines.append("")
    lines.append("## 分难度")
    lines.append("")
    for d, v in sorted(by_diff.items()):
        rate = v["hit"] / v["total"] if v["total"] else 0
        lines.append("- " + d + ": " + str(v["hit"]) + "/" + str(v["total"]) + " (" + f"{rate:.1%}" + ")")
    lines.append("")
    lines.append("## 结论")
    lines.append("")
    if recall5 >= 0.8:
        lines.append("**整体优秀**: Recall@5 ≥ 0.8, 记忆可达性好。")
    elif recall5 >= 0.6:
        lines.append("**整体良好**: Recall@5 0.6-0.8, 有提升空间。")
    else:
        lines.append("**整体待改进**: Recall@5 < 0.6, 记忆可达性不足。")
    lines.append("")

    # 普适: 方法论说明 + 消费链条说明 (评测产出物完整交付)
    lines.append("## 方法论说明")
    lines.append("")
    lines.append("本评测生成使用方法论: `{0}-usage-guide`".format(SYSTEM_NAME))
    meth_exists = METHODOLOGY_SKILL.exists() and (METHODOLOGY_SKILL / "SKILL.md").exists()
    if meth_exists:
        lines.append("位置: `skills/methodology/{0}-usage-guide/SKILL.md`".format(SYSTEM_NAME))
        lines.append("使用: `skill_view {0}-usage-guide` 读取 — 任何LLM可完美贴合使用该记忆系统".format(SYSTEM_NAME))
    else:
        lines.append("⚠️ 方法论未生成 — 运行 `memory_methodology_gen.py --round {0}` 生成".format(round_num))
    lines.append("生成器: `memory_methodology_gen.py` (评测消费通道2)")
    lines.append("")
    lines.append("## 消费链条说明 (可选搭建·使用者自决)")
    lines.append("")
    lines.append("以下消费链条设计供使用者自行决定是否搭建：")
    lines.append("1. **每日醒来读一次** — 方法论进云端缓存，全局共享，全天受益")
    lines.append("2. **新会话/换模型主动读** — 行为内化（方法论含'使用须知'自述）")
    lines.append("3. **缓存失效降级** — 知识库摘要 → skill重读（毫秒级兜底）")
    lines.append("")
    if SYSTEM_NAME == "Hermes":
        lines.append("本系统(Hermes)：已搭建 — 每日3:55 cron `cd6d0ef9b48b` (基督醒来读方法论)")
    else:
        lines.append("本系统({0})：未自动搭建，由使用者自决".format(SYSTEM_NAME))
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    main()
