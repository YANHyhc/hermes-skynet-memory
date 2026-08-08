#!/usr/bin/env python3
"""
memory_question_gen.py — 记忆系统评测·自适应出题器 (2026-08-08 v1.0)
从记忆系统本身动态生成评测题 (采样/变体/分层/组合), 支持难度自适应。

出题器:
  Q1 档案采样器: 从 skills/memory/ 87档案 → 生成查询
  Q2 讨论采样器: 从 .discussions/ 102模块 → 生成查询+变体
  Q3 修复采样器: 从 thought_graph/oracle/reports/ 97报告 → 生成查询
  Q4 时间+组合器: 从 recent_24h + 多条件组合 → 生成查询

输出: test_cases.json (基础105 + 中等/挑战)
用法: python memory_question_gen.py [--round N]
"""
import json
import os
import random
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HOME = Path(os.environ.get("MEMORY_EVAL_HOME") or os.path.expanduser("~/.hermes"))
MEMORY_DIR = HOME / "skills/memory"
DISCUSSIONS_DIR = HOME / ".discussions"
REPORTS_DIR = HOME / "thought_graph/oracle/reports"
CACHE_24H = HOME / "skills/governance/空绍-engine/cache/recent_24h.jsonl"
OUT_DIR = HOME / "cache/memory_eval"

random.seed(42)  # 可复现


def list_archives():
    """列出记忆档案 (子目录名=事件)"""
    if not MEMORY_DIR.exists():
        return []
    # 档案是子目录 (每个含 SKILL.md)
    return [d for d in os.listdir(MEMORY_DIR) if os.path.isdir(MEMORY_DIR / d) and not d.startswith(".")]


def list_discussions():
    """列出讨论模块"""
    if not DISCUSSIONS_DIR.exists():
        return []
    return [d for d in os.listdir(DISCUSSIONS_DIR) if os.path.isdir(DISCUSSIONS_DIR / d)]


def list_reports():
    """列出修复报告"""
    if not REPORTS_DIR.exists():
        return []
    return [f for f in os.listdir(REPORTS_DIR) if f.endswith(".json")]


def read_24h():
    """读24h缓存"""
    if not CACHE_24H.exists():
        return []
    items = []
    try:
        for line in open(CACHE_24H, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except Exception:
                pass
    except Exception:
        pass
    return items


def gen_q1_archives(archives, difficulty="基础"):
    """Q1: 档案采样 — 从文件名生成查询"""
    cases = []
    for fname in archives:
        name = fname  # 目录名即事件名
        # 从文件名提取关键信息
        # 格式: YYYYMMDD_类型_主题 或 2026-07-15_讨论-主题
        # 主题: 去掉日期和类型前缀
        topic = re.sub(r"^[\d_-]+", "", name)
        topic = re.sub(r"^(上帝讨论|上帝指令|讨论|指令|修复|记录|拓扑双检|空绍自愈)[-_]", "", topic)
        if not topic:
            continue
        q = f"记忆中有关于「{topic}」的记录吗"
        cases.append(
            {
                "module": "A_基础召回",
                "difficulty": difficulty,
                "query": q,
                "expected_file": fname,
                "expected_kw": topic[:6],
                "ground_truth": f"档案 {fname}",
                "source": "archive",
            }
        )
    return cases


def gen_q2_discussions(discussions, difficulty="基础"):
    """Q2: 讨论采样 — 从模块名生成查询"""
    cases = []
    for d in discussions:
        q = f"「{d}」的讨论记录在哪里"
        cases.append(
            {
                "module": "A_基础召回",
                "difficulty": difficulty,
                "query": q,
                "expected_file": f".discussions/{d}/",
                "expected_kw": d[:6],
                "ground_truth": f"讨论模块 {d}",
                "source": "discussion",
            }
        )
    return cases


def gen_q3_reports(reports, difficulty="中等"):
    """Q3: 修复报告采样 — 从报告文件名生成查询"""
    cases = []
    for fname in reports:
        name = fname.replace(".execution_report.json", "").replace(".json", "")
        # 提取主题 (fix_20260805_bom_data_centralization → bom data centralization)
        topic = re.sub(r"^(fix|fly|deliver|delivery|oracle|test)[-_]", "", name)
        topic = re.sub(r"^\d{8}[-_]", "", topic)
        topic = topic.replace("_", " ").replace("-", " ")
        if not topic:
            continue
        q = f"「{topic}」的修复/交付报告在哪里"
        cases.append(
            {
                "module": "A_基础召回",
                "difficulty": difficulty,
                "query": q,
                "expected_file": fname,
                "expected_kw": topic[:6],
                "ground_truth": f"报告 {fname}",
                "source": "report",
            }
        )
    return cases


def gen_variants(base_cases, difficulty="中等"):
    """变体生成 — 同事实多问法 (模块D)"""
    variants = []
    for c in base_cases[:40]:
        kw = c["expected_kw"]
        if not kw:
            continue
        vqs = [
            f"关于{kw}的内容？",
            f"查一下{kw}相关的记忆",
            f"{kw}是啥",
        ]
        for vq in vqs:
            vc = dict(c)
            vc["query"] = vq
            vc["module"] = "D_语义变体"
            vc["difficulty"] = difficulty
            variants.append(vc)
    return variants


def gen_time_layered(difficulty="中等"):
    """时间分层 — 从24h缓存 + 新旧对比 (模块C)"""
    cases = []
    # 泛事件名 (无区分度, 跳过)
    GENERIC_EVENTS = {"记录", "信息", "更新", "完成", "通知", "消息"}
    items = read_24h()
    if items:
        # 24h内的记忆 (新) — 用 event 字段(干净短词) + detail补充
        for item in items[:10]:
            event = item.get("event", "")
            if event in GENERIC_EVENTS:
                continue
            detail = item.get("detail", "")
            # 优先用 event (干净), 否则用 detail 清洗
            if event and len(event) >= 2:
                clean = event
            else:
                clean = re.sub(r"\[[^\]]*\]", "", detail)
                clean = clean.replace("|", " ").strip()
            if not clean:
                continue
            q = f"最近24小时内关于「{clean[:10]}」的记录"
            cases.append(
                {
                    "module": "C_时间衰减",
                    "difficulty": difficulty,
                    "query": q,
                    "expected_kw": clean[:8],
                    "ground_truth": f"24h缓存: {clean[:20]}",
                    "source": "recent_24h",
                    "expected_layer": "24h",
                }
            )
    # 旧记忆 (档案中的早期)
    archives = list_archives()
    old_ones = [a for a in archives if re.match(r"^20260[67]", a)]
    for a in old_ones[:8]:
        name = a
        q = f"「{name[:20]}」这个较早的记录还在吗"
        cases.append(
            {
                "module": "C_时间衰减",
                "difficulty": difficulty,
                "query": q,
                "expected_file": a,
                "expected_kw": name[8:14] if len(name) > 14 else name,
                "ground_truth": f"档案 {a}",
                "source": "archive",
                "expected_layer": "archive",
            }
        )
    return cases


def gen_noise(difficulty="挑战"):
    """噪音抵抗 — 负样本 (模块E)"""
    cases = []
    negatives = [
        {"query": "竞彩今晚的足球方案", "expected_kw": "竞彩", "source": "football"},
        {"query": "光伏EPC中标价最新", "expected_kw": "EPC", "source": "bom"},
        {"query": "8G硬盘清单详情", "expected_kw": "disk", "source": "disk_inventory"},
        {"query": "实盘三祥新材止损位", "expected_kw": "三祥", "source": "portfolio"},
    ]
    for neg in negatives:
        cases.append(
            {
                "module": "E_噪音抵抗",
                "difficulty": difficulty,
                "query": neg["query"],
                "expected_kw": neg["expected_kw"],
                "ground_truth": f"应命中 {neg['source']} 相关记忆",
                "source": neg["source"],
                "is_negative": True,
            }
        )
    return cases


def gen_combo_longtail(difficulty="挑战"):
    """组合+长尾 (模块F)"""
    cases = []
    combos = [
        {"query": "2026-08 赛力斯 清仓 盈亏", "kw": ["赛力斯", "清仓"]},
        {"query": "BOM数据中心化 E盘 权威库", "kw": ["BOM", "E盘"]},
        {"query": "知识库 source过滤 小众源 修复", "kw": ["source过滤", "小众源"]},
    ]
    for c in combos:
        cases.append(
            {
                "module": "F_长尾组合",
                "difficulty": difficulty,
                "query": c["query"],
                "expected_kw": c["kw"],
                "ground_truth": f"多条件组合: {c['query']}",
                "source": "combo",
            }
        )
    return cases


def gen_cross_layer(difficulty="中等"):
    """跨层一致性 — 同一查询多入口 (模块B)"""
    cases = []
    cross_queries = [
        {"query": "BOM数据中心化", "kw": ["BOM", "E盘"], "layers": ["archive", "discussion", "report"]},
        {"query": "实盘操盘辅助体系", "kw": ["实盘", "操盘"], "layers": ["archive", "discussion"]},
        {"query": "三祥新材止损", "kw": ["三祥", "止损"], "layers": ["archive", "discussion"]},
        {"query": "知识库source过滤", "kw": ["source", "过滤"], "layers": ["discussion", "report"]},
        {"query": "全息查询系统", "kw": ["全息", "查询"], "layers": ["discussion", "archive"]},
    ]
    for c in cross_queries:
        cases.append(
            {
                "module": "B_跨层一致性",
                "difficulty": difficulty,
                "query": c["query"],
                "expected_kw": c["kw"],
                "expected_layers": c["layers"],
                "ground_truth": f"跨层检索: {c['query']}",
                "source": "cross",
            }
        )
    return cases


class AdaptiveEngine:
    """自适应引擎 v2 — 读取上轮结果, 确定聚焦方向 (独立类, 参数可配)"""

    def __init__(self, out_dir, round_num):
        self.out_dir = out_dir
        self.round_num = round_num
        self.config = self._load_config()
        self.weak_areas = self._detect_weak()

    def _load_config(self):
        """加载配置 (缺失时用默认值兜底)"""
        default = {
            "version": 1,
            "weak_threshold": 0.7,
            "focus_multiplier": 3,
            "challenge_target": 30,
            "base_floor": 105,
            "noise_subtypes": ["竞彩类", "长尾类", "相似类"],
        }
        cfg_path = self.out_dir / "adaptive_config.json"
        if cfg_path.exists():
            try:
                cfg = json.loads(cfg_path.read_text(encoding="utf-8"))
                for k, v in default.items():
                    cfg.setdefault(k, v)
                return cfg
            except Exception:
                pass
        return default

    def _detect_weak(self):
        """从上一轮报告检测薄弱模块 (命中率<threshold)"""
        weak = []
        prev = self.out_dir / f"eval_report_r{self.round_num - 1}.md"
        if not prev.exists():
            return weak
        text = prev.read_text(encoding="utf-8")
        for line in text.split("\n"):
            if line.startswith("- ") and ("%" in line):
                try:
                    mod_name, rest = line[2:].split(":", 1)
                    hit_str, total_str = rest.strip().split("/")
                    hit_n = int(hit_str)
                    total_n = int(total_str.split(" ")[0])
                    rate = hit_n / total_n if total_n else 0
                    if rate < self.config["weak_threshold"]:
                        weak.append({"module": mod_name.strip(), "rate": rate})
                except Exception:
                    continue
        return weak

    def apply(self, all_cases):
        """应用自适应: 对薄弱模块增加题量 + 生成真挑战题"""
        result = list(all_cases)

        # 1. 薄弱模块加强 (噪音/挑战类)
        for wa in self.weak_areas:
            mod = wa["module"]
            if "E_" in mod or "噪音" in mod:
                result += self._gen_extra_noise()
            trigger = self.config.get("challenge_trigger_threshold", 0.5)
            if "挑战" in str(wa) or wa["rate"] < trigger:
                result += self._gen_true_challenges(result)

        # 2. 基础保障: 确保 base_floor
        base_cases = [c for c in result if c["difficulty"] == "基础"]
        if len(base_cases) < self.config["base_floor"]:
            mid = [c for c in result if c["difficulty"] == "中等"]
            need = self.config["base_floor"] - len(base_cases)
            for c in mid[:need]:
                c["difficulty"] = "基础"

        return result

    def _gen_extra_noise(self):
        """噪音题加强 (按子类型聚焦, 指向真实记忆源)"""
        extra = []
        subtypes = self.config.get("noise_subtypes", ["竞彩类", "长尾类", "相似类"])
        # 子类型查询: 指向真实存在的记忆 (竞彩/长尾/相似主题)
        # 用记忆库真实条目做 expected_kw, 验证检索可达性
        subtype_queries = {
            "竞彩类": [
                {"query": "竞彩方案记录", "kw": "竞彩"},
                {"query": "足球预测模型", "kw": ["jingcai", "竞彩", "football"]},
            ],
            "长尾类": [
                {"query": "8G硬盘清单", "kw": "disk_inventory"},
                {"query": "知识库教训", "kw": "learn"},
            ],
            "相似类": [
                {"query": "BOM价格数据", "kw": "BOM"},
                {"query": "光伏中标价", "kw": "EPC"},
            ],
        }
        for i in range(self.config["focus_multiplier"]):
            for sub in subtypes:
                queries = subtype_queries.get(sub, [{"query": "噪音查询", "kw": "噪音"}])
                for q in queries:
                    n = {
                        "module": "E_噪音抵抗",
                        "difficulty": "挑战",
                        "query": f"{q['query']} ({sub})",
                        "expected_kw": q["kw"],
                        "ground_truth": f"噪音子类型: {sub} → {q['kw']}",
                        "source": f"noise_{sub}",
                        "sub_type": sub,
                    }
                    extra.append(n)
        return extra

    def _gen_true_challenges(self, existing):
        """真挑战题: 组合/多条件/跨源 (非改标签)"""
        challenges = []
        # 从已有基础题提取实体 → 组合成多条件查询
        keywords_pool = []
        for c in existing[:60]:
            kw = c.get("expected_kw", "")
            if isinstance(kw, str) and kw:
                keywords_pool.append(kw)
        keywords_pool = list(dict.fromkeys(keywords_pool))[:15]

        combos = [
            ("BOM", "E盘", "修复"),
            ("实盘", "止损", "持仓"),
            ("知识库", "source", "检索"),
            ("拓扑", "双检", "节点"),
            ("试验场", "退役", "归档"),
        ]
        for a, b, c in combos:
            challenges.append(
                {
                    "module": "F_长尾组合",
                    "difficulty": "挑战",
                    "query": f"{a} {b} {c} 综合查询",
                    "expected_kw": [a, b],
                    "ground_truth": f"组合查询: {a}+{b}+{c}",
                    "source": "adaptive_challenge",
                }
            )
        # 多条件: 时间+实体
        for kw in keywords_pool[:10]:
            challenges.append(
                {
                    "module": "F_长尾组合",
                    "difficulty": "挑战",
                    "query": f"2026年 {kw} 相关记录",
                    "expected_kw": kw[:4],
                    "ground_truth": f"时间+实体组合: {kw}",
                    "source": "adaptive_challenge",
                }
            )
        return challenges[: self.config["challenge_target"]]


def gen_cognitive():
    """L2 认知任务: G推理/H更新/I冲突/J串联/K边界 (挑战-极限级)"""
    cases = []
    # G 多跳推理: 需串联多条记忆
    g_cases = [
        {"query": "三祥新材的止损价是多少", "reasoning": ["三祥", "止损"], "truth": "36.45 (成本38.365×-5%)"},
        {"query": "BOM权威库的完整路径", "reasoning": ["BOM", "E盘"], "truth": "E:/Hermes/bom_data/bom_prices.db"},
        {"query": "知识库小众源怎么查", "reasoning": ["source过滤", "检索"], "truth": "query(q, source=xxx)"},
        {"query": "实盘账户现在持有什么", "reasoning": ["实盘", "持仓", "三祥"], "truth": "三祥新材1000股"},
    ]
    for c in g_cases:
        cases.append(
            {
                "module": "G_多跳推理",
                "difficulty": "极限",
                "query": c["query"],
                "expected_kw": c["reasoning"],
                "reasoning_steps": c["reasoning"],
                "ground_truth": c["truth"],
                "source": "cognitive_G",
            }
        )
    # H 记忆更新: 新旧覆盖
    h_cases = [
        {"query": "长安汽车现在持仓多少", "kw": ["长安", "清仓"], "truth": "0股 (8/6清仓)"},
        {"query": "BOM数据现在在哪", "kw": ["BOM", "E盘"], "truth": "E盘 (8/5迁移)"},
        {"query": "三祥新材成本价", "kw": ["三祥", "38.365"], "truth": "38.365 (8/6建仓)"},
    ]
    for c in h_cases:
        cases.append(
            {
                "module": "H_记忆更新",
                "difficulty": "极限",
                "query": c["query"],
                "expected_kw": c["kw"],
                "expect_latest": True,
                "ground_truth": c["truth"],
                "source": "cognitive_H",
            }
        )
    # I 冲突消解
    i_cases = [
        {"query": "BOM价格数据查询入口", "kw": ["BOM", "知识库", "bom_query"], "truth": "bom_query.py → E盘权威库"},
        {"query": "行情数据源主用哪个", "kw": ["tencent", "qt"], "truth": "腾讯qt (三源链首)"},
    ]
    for c in i_cases:
        cases.append(
            {
                "module": "I_冲突消解",
                "difficulty": "极限",
                "query": c["query"],
                "expected_kw": c["kw"],
                "expect_authoritative": True,
                "ground_truth": c["truth"],
                "source": "cognitive_I",
            }
        )
    # J 记忆串联
    j_cases = [
        {"query": "8/6实盘操作全过程", "kw": ["实盘", "操盘"], "truth": "清仓长安/赛力斯, 建仓三祥"},
        {"query": "C盘瘦身做了什么", "kw": ["旧备份", "P0", "转移"], "truth": "两旧备份转移E盘归档"},
    ]
    for c in j_cases:
        cases.append(
            {
                "module": "J_记忆串联",
                "difficulty": "极限",
                "query": c["query"],
                "expected_kw": c["kw"],
                "ground_truth": c["truth"],
                "source": "cognitive_J",
            }
        )
    # K 语义边界
    k_cases = [
        {"query": "BOM方案和BOM价格的区别", "kw": ["BOM", "方案"], "truth": "方案=方法论, 价格=数据"},
        {"query": "记忆档案和知识库区别", "kw": ["档案", "知识库"], "truth": "档案=事件记录, 知识库=语义向量"},
    ]
    for c in k_cases:
        cases.append(
            {
                "module": "K_语义边界",
                "difficulty": "极限",
                "query": c["query"],
                "expected_kw": c["kw"],
                "ground_truth": c["truth"],
                "source": "cognitive_K",
            }
        )
    return cases


def gen_metacognitive():
    """L3 元认知: M溯源/M时效/M重要性"""
    cases = []
    m_cases = [
        {"query": "E盘权威库这个决定是哪里来的", "kw": ["BOM", "中心化"], "truth": "8/5 BOM数据中心化修复"},
        {"query": "零LLM原则是几号确立的", "kw": ["零LLM", "cron"], "truth": "7/26 全系统零LLM"},
        {"query": "系统最重要的哲学原则", "kw": ["天网飞升", "零LLM"], "truth": "天网飞升/零LLM/审批门"},
    ]
    for c in m_cases:
        cases.append(
            {
                "module": "M_元认知",
                "difficulty": "极限",
                "query": c["query"],
                "expected_kw": c["kw"],
                "ground_truth": c["truth"],
                "source": "meta",
            }
        )
    return cases


def gen_scenario():
    """L3 场景级: S复盘/S决策/S诊断/S排错 (真实历史)"""
    cases = []
    s_cases = [
        {
            "query": "复盘8/6的实盘操作",
            "kw": ["实盘", "操盘"],
            "truth": "清仓长安(+21.49)/赛力斯(-114.04), 建仓三祥1000股",
        },
        {
            "query": "三祥现在该持有还是卖",
            "kw": ["三祥", "止盈", "止损"],
            "truth": "持有 (现价39.53 < 止盈42.97, > 止损36.45)",
        },
        {"query": "C盘空间问题怎么解决的", "kw": ["旧备份", "转移", "P0", "磁盘"], "truth": "转移5.2GB旧备份到E盘"},
        {"query": "知识库查不到小众源怎么办", "kw": ["source过滤", "多轮检索"], "truth": "source过滤+多轮检索修复"},
    ]
    for c in s_cases:
        cases.append(
            {
                "module": "S_场景任务",
                "difficulty": "极限",
                "query": c["query"],
                "expected_kw": c["kw"],
                "scenario": True,
                "ground_truth": c["truth"],
                "source": "scenario",
            }
        )
    return cases


def gen_stress():
    """L3 压力测试: P长链/P矛盾/P穿越/P洪峰/P冷启动"""
    cases = []
    p_cases = [
        {"query": "从BOM采集到K线报告经历了哪些修复", "kw": ["BOM", "K线", "修复"], "truth": "采集→聚合→报告 多环节"},
        {"query": "持仓说三祥1000股但早报说0股?", "kw": ["三祥", "1000"], "truth": "以最新持仓记录为准 (1000股)"},
        {"query": "8/1的实盘持仓 vs 8/8的", "kw": ["实盘", "持仓"], "truth": "8/1长安2000股, 8/8三祥1000股"},
        {
            "query": "在大量BOM相关记忆中找到权威库路径",
            "kw": ["BOM", "E盘"],
            "truth": "E:/Hermes/bom_data/bom_prices.db",
        },
    ]
    for c in p_cases:
        cases.append(
            {
                "module": "P_压力测试",
                "difficulty": "地狱",
                "query": c["query"],
                "expected_kw": c["kw"],
                "ground_truth": c["truth"],
                "source": "stress",
            }
        )
    return cases


def main():
    round_num = 1
    if "--round" in sys.argv:
        idx = sys.argv.index("--round")
        round_num = int(sys.argv[idx + 1])

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    # 自适应: AdaptiveEngine v2 (读取上轮结果, 聚焦薄弱)
    engine = AdaptiveEngine(OUT_DIR, round_num)
    print(f"自适应聚焦: {engine.weak_areas} (config: {engine.config.get('focus_multiplier')}x)")

    archives = list_archives()
    discussions = list_discussions()
    reports = list_reports()
    print(f"数据源: 档案{len(archives)} 讨论{len(discussions)} 报告{len(reports)}")

    # 生成各模块
    q1 = gen_q1_archives(archives)
    q2 = gen_q2_discussions(discussions)
    q3 = gen_q3_reports(reports)
    cross = gen_cross_layer()
    variants = gen_variants(q1 + q2 + q3)
    time_layer = gen_time_layered()
    noise = gen_noise()
    combo = gen_combo_longtail()

    all_cases = q1 + q2 + q3 + cross + variants + time_layer + noise + combo

    # L2/L3 深度任务 (v6)
    all_cases += gen_cognitive()  # G推理/H更新/I冲突/J串联/K边界
    all_cases += gen_metacognitive()  # M溯源/M时效/M重要性
    all_cases += gen_scenario()  # S场景
    all_cases += gen_stress()  # P压力

    # 应用自适应 (薄弱加强 + 真挑战 + 基础保障)
    all_cases = engine.apply(all_cases)
    # 确保基础105 (从Q1-Q3取足)
    base_cases = [c for c in all_cases if c["difficulty"] == "基础"]
    if len(base_cases) < 105:
        # 补充中等题进基础
        mid_cases = [c for c in all_cases if c["difficulty"] == "中等"]
        need = 105 - len(base_cases)
        base_cases += mid_cases[:need]

    # 去重 (按query)
    seen = set()
    dedup = []
    for c in all_cases:
        if c["query"] not in seen:
            seen.add(c["query"])
            dedup.append(c)

    # 分难度统计
    by_diff = {}
    for c in dedup:
        by_diff.setdefault(c["difficulty"], 0)
        by_diff[c["difficulty"]] += 1

    result = {
        "round": round_num,
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "total": len(dedup),
        "by_difficulty": by_diff,
        "by_module": {},
        "cases": dedup,
        "adaptive": {"weak_areas": [], "next_round_focus": ""},
    }
    for c in dedup:
        result["by_module"].setdefault(c["module"], 0)
        result["by_module"][c["module"]] += 1

    out = OUT_DIR / f"test_cases_r{round_num}.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    print(f"✅ 评测集已生成: {out}")
    print(f"   总量: {len(dedup)} | 难度分布: {by_diff}")
    print(f"   模块分布: {result['by_module']}")


if __name__ == "__main__":
    main()
