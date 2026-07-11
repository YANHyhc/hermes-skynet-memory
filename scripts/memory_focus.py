#!/usr/bin/env python3
"""
记忆专注引擎 v1.0 — 动态焦点窗口
调度: cron 每30min
功能: 读 focus_tracker → 算聚焦度 → 重写 MEMORY.md 顶部专注行
"""
import json, sys, math, shutil
from pathlib import Path
from datetime import datetime, timedelta

HOME = Path.home()
MEMORY_FILE = HOME / ".hermes" / "memories" / "MEMORY.md"
FOCUS = HOME / ".hermes" / "cache" / "focus_tracker.json"
ASSOC = HOME / ".hermes" / "baige" / "cache" / "assoc_index.json"

# 专注行标记（必须与MEMORY.md中格式一致）
FOCUS_PREFIX = "⚡ 专注(30min):"

def read_focus():
    if not FOCUS.exists():
        return {"entries": []}
    try:
        return json.loads(FOCUS.read_text("utf-8"))
    except:
        return {"entries": []}

def read_assoc():
    if not ASSOC.exists():
        return []
    try:
        return json.loads(ASSOC.read_text("utf-8"))
    except:
        return []

def read_memory():
    if not MEMORY_FILE.exists():
        return ""
    return MEMORY_FILE.read_text("utf-8")

def write_memory(content):
    MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    tmp = MEMORY_FILE.with_suffix(".md.tmp")
    tmp.write_text(content, "utf-8")
    shutil.move(str(tmp), str(MEMORY_FILE))

def calc_focus_scores(tracker, entries):
    """按聚焦度公式算分"""
    now = datetime.now()
    entry_map = {e["id"]: e for e in entries}
    
    # 统计每条的命中次数（按时间区间）
    scores = {}
    
    for hit in tracker.get("entries", []):
        eid = hit["id"]
        if eid not in entry_map:
            continue  # 条目已被删除
        try:
            hit_ts = datetime.fromisoformat(hit["ts"])
        except:
            continue
        
        mins_ago = (now - hit_ts).total_seconds() / 60
        
        if mins_ago > 1440:  # >24h
            continue
        elif mins_ago > 60:  # 1h~24h
            weight = 0.3
        else:  # <1h
            weight = 1.0
        
        if eid not in scores:
            scores[eid] = {"count_1h": 0, "count_24h": 0, "base": entry_map[eid]["weight"]}
        
        if mins_ago <= 60:
            scores[eid]["count_1h"] += 1
        else:
            scores[eid]["count_24h"] += 1
    
    # 算总分
    results = []
    for eid, s in scores.items():
        score = s["count_1h"] * 1.0 + s["count_24h"] * 0.3 + s["base"] * 0.1
        results.append((eid, round(score, 3), entry_map[eid]["topic"]))
    
    results.sort(key=lambda x: x[1], reverse=True)
    return results

def update_memory_focus():
    tracker = read_focus()
    entries = read_assoc()
    
    # 计算聚焦度
    ranked = calc_focus_scores(tracker, entries)
    
    # 构建新专注行
    if ranked:
        top = ranked[:3]
        topics = [t[2] for t in top]
        focus_line = f"{FOCUS_PREFIX} {' | '.join(topics)}\n"
    else:
        # 无命中数据：保留上次专注行（不修改）
        current = read_memory()
        if current.startswith(FOCUS_PREFIX):
            print("⏭️ 无新命中数据，保留上次专注")
            return
        # 首次运行
        focus_line = f"{FOCUS_PREFIX} 数据收集中...\n"
    
    # 读当前MEMORY.md
    content = read_memory()
    
    if content.startswith(FOCUS_PREFIX):
        # 替换第一行
        lines = content.split("\n", 1)
        new_content = focus_line + (lines[1] if len(lines) > 1 else "")
    else:
        # 在顶部插入
        new_content = focus_line + content
    
    write_memory(new_content)
    
    # 清空 focus_tracker（老数据已用完）
    FOCUS.write_text('{"entries":[]}', "utf-8")
    
    # 输出摘要
    if ranked:
        for rank, (eid, score, topic) in enumerate(ranked[:5], 1):
            print(f"  #{rank} {topic} ({eid}) score={score}")
    print(f"✅ 专注行已更新: {focus_line.strip()}")

def main():
    print("📊 专注引擎运行中...")
    update_memory_focus()

if __name__ == "__main__":
    main()
