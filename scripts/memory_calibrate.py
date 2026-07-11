#!/usr/bin/env python3
"""
记忆校准引擎 v1.0 — 权重调整 + 年度归档
调度: cron 每周日03:10
"""
import json, sys, shutil
from pathlib import Path
from datetime import datetime, date

HOME = Path.home()
ASSOC = HOME / ".hermes" / "baige" / "cache" / "assoc_index.json"
ARCHIVE = HOME / ".hermes" / "baige" / "cache" / "assoc_index_archive.json"
ASSOC_MTIME = HOME / ".hermes" / "baige" / "cache" / ".assoc_mtime"

def read_assoc():
    if not ASSOC.exists():
        return []
    return json.loads(ASSOC.read_text("utf-8"))

def write_assoc(data):
    ASSOC.parent.mkdir(parents=True, exist_ok=True)
    tmp = ASSOC.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    shutil.move(str(tmp), str(ASSOC))

def main():
    print("📐 校准引擎 v1.0")
    print(f"  时间: {datetime.now():%Y-%m-%d %H:%M}")
    print()
    
    entries = read_assoc()
    if not entries:
        print("⚠️ assoc_index 为空")
        return
    
    today = date.today()
    keep = []
    archive_items = []
    changes = []
    
    for entry in entries:
        try:
            entry_date = datetime.strptime(entry["date"], "%Y-%m-%d").date()
        except:
            entry_date = today
        days_since = (today - entry_date).days
        
        # 年度归档
        if days_since > 365:
            archive_items.append(entry)
            print(f"  📦 归档: {entry['id']} ({days_since}天)")
            continue
        
        before = entry.get("weight", 1.0)
        
        # 校准判定
        total = entry.get("hits", 0) + entry.get("misses", 0)
        if total > 3:
            acc = entry["hits"] / total
            if acc < 0.3:
                entry["weight"] = round(before * 0.7, 3)
                changes.append(f"  ⬇ {entry['id']}: acc={acc:.2f} → weight {before}→{entry['weight']}")
            elif acc > 0.8:
                entry["weight"] = round(min(1.0, before * 1.1), 3)
                changes.append(f"  ⬆ {entry['id']}: acc={acc:.2f} → weight {before}→{entry['weight']}")
        elif total == 0 and days_since > 30:
            entry["weight"] = round(before * 0.95, 3)
            changes.append(f"  📉 {entry['id']}: {days_since}天无反馈 weight {before}→{entry['weight']}")
        
        keep.append(entry)
    
    # 写回
    write_assoc(keep)
    
    # 归档
    if archive_items:
        old = []
        if ARCHIVE.exists():
            old = json.loads(ARCHIVE.read_text("utf-8"))
        old.extend(archive_items)
        ARCHIVE.write_text(json.dumps(old, ensure_ascii=False, indent=2), "utf-8")
    
    # 触发下次skillgen
    if changes or archive_items:
        ASSOC_MTIME.write_text(datetime.now().isoformat(), "utf-8")
    
    # 报告
    for c in changes:
        print(c)
    print()
    print(f"✅ 校准完成")
    print(f"   活跃: {len(keep)} | 归档: {len(archive_items)} | 调整: {len(changes)}")

if __name__ == "__main__":
    main()
