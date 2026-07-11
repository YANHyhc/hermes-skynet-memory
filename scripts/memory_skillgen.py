#!/usr/bin/env python3
"""
记忆技能同步引擎 v1.0 — assoc_index → micro-skill 双向同步
调度: cron 每10min（但只检查mtime，无变更则跳过）
产出: skills/memory/{id}/SKILL.md
       cache/focus_tracker.json（自动检测更新）
"""
import json, sys, os, shutil, math
from pathlib import Path
from datetime import datetime, date

HOME = Path.home()
ASSOC = HOME / ".hermes" / "baige" / "cache" / "assoc_index.json"
ASSOC_MTIME = HOME / ".hermes" / "baige" / "cache" / ".assoc_mtime"
SKILL_DIR = HOME / ".hermes" / "skills" / "memory"
FOCUS = HOME / ".hermes" / "cache" / "focus_tracker.json"
STATE_DB = HOME / ".hermes" / "state.db"
CACHE = HOME / ".hermes" / "cache"

MTIME_FILE = CACHE / ".skillgen_last_mtime"

def should_skip():
    """检查assoc_index是否有变化"""
    if not ASSOC.exists():
        print("⚠️ assoc_index.json 不存在")
        return True
    
    # 读上次记录的时间戳
    last = ""
    if MTIME_FILE.exists():
        last = MTIME_FILE.read_text("utf-8").strip()
    
    # 读当前时间戳
    current = ""
    if ASSOC_MTIME.exists():
        current = ASSOC_MTIME.read_text("utf-8").strip()
    
    if current and current == last:
        return True  # 无变化
    
    return False

def save_mtime():
    """保存当前时间戳"""
    CACHE.mkdir(parents=True, exist_ok=True)
    current = ""
    if ASSOC_MTIME.exists():
        current = ASSOC_MTIME.read_text("utf-8").strip()
    MTIME_FILE.write_text(current or datetime.now().isoformat(), "utf-8")

def read_assoc():
    return json.loads(ASSOC.read_text("utf-8"))

def write_file_atomic(path, content):
    """原子写入"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(content, "utf-8")
    shutil.move(str(tmp), path)

def skill_path(entry_id):
    return SKILL_DIR / entry_id / "SKILL.md"

def generate_skill_md(entry):
    """从assoc_index条目生成SKILL.md内容"""
    triggers_str = ", ".join(entry["subjects"])
    events_str = "\n".join(f"- {e}" for e in entry["event"])
    
    return f"""---
name: memory-{entry['id']}
description: 记忆: {entry['topic']}
triggers: [{triggers_str}]
memory_tier: long
category: memory
---

# {entry['topic']}

**{entry['date']}** | {entry['ref']}

{events_str}

_权重: {entry['weight']} | 命中: {entry.get('hits',0)} | 未中: {entry.get('misses',0)}_
"""

def sync_skills(entries):
    """同步技能：增/删/改"""
    entry_ids = {e["id"] for e in entries}
    
    # 新增或更新
    for entry in entries:
        sp = skill_path(entry["id"])
        if sp.exists():
            # 已存在，检查是否需要更新
            old = sp.read_text("utf-8")
            new = generate_skill_md(entry)
            if old == new:
                continue  # 内容未变
        # 创建或更新
        write_file_atomic(sp, generate_skill_md(entry))
        print(f"  📝 skill: {entry['id']} ({entry['topic']})")
    
    # 删除不存在的条目对应的skill
    if SKILL_DIR.exists():
        for child in SKILL_DIR.iterdir():
            if child.is_dir() and child.name not in entry_ids:
                shutil.rmtree(child, ignore_errors=True)
                print(f"  🗑️ 删除: {child.name}")

def auto_detect_focus(entries):
    """扫描state.db最近用户消息，匹配subject→追加focus_tracker"""
    try:
        import sqlite3
        if not STATE_DB.exists():
            return
        
        conn = sqlite3.connect(str(STATE_DB))
        recent = conn.execute(
            "SELECT content FROM messages WHERE role='user' ORDER BY rowid DESC LIMIT 10"
        ).fetchall()
        conn.close()
        
        if not recent:
            return
        
        all_text = " ".join(r[0] for r in recent).lower()
        
        # 读当前focus_tracker
        focus = {"entries": []}
        if FOCUS.exists():
            focus = json.loads(FOCUS.read_text("utf-8"))
        
        now_ts = datetime.now().isoformat(timespec="seconds")
        hit_count = 0
        
        for entry in entries:
            for subject in entry["subjects"]:
                if subject.lower() in all_text:
                    focus.setdefault("entries", []).append({
                        "id": entry["id"],
                        "ts": now_ts
                    })
                    hit_count += 1
                    break
        
        if hit_count > 0:
            FOCUS.parent.mkdir(parents=True, exist_ok=True)
            tmp = FOCUS.with_suffix(".tmp")
            tmp.write_text(json.dumps(focus, ensure_ascii=False, indent=2), "utf-8")
            shutil.move(str(tmp), str(FOCUS))
            print(f"  🔍 自动检测: +{hit_count} 命中")
    except Exception as e:
        print(f"  ⚠️ auto_detect: {e}", file=sys.stderr)

def main():
    # 跳过无变更
    if should_skip():
        print("⏭️ assoc_index 无变更")
        return
    
    entries = read_assoc()
    print(f"📦 同步 {len(entries)} 条 assoc_index → skill...")
    
    # 同步技能
    sync_skills(entries)
    
    # 自动检测focus
    auto_detect_focus(entries)
    
    # 保存时间戳
    save_mtime()
    
    print(f"✅ skillgen 完成")

if __name__ == "__main__":
    main()
