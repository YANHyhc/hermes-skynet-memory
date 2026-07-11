#!/usr/bin/env python3
"""
记忆系统统一写入入口 — 所有对 assoc_index.json 的修改都经过此脚本
用途: --add / --update / --hit / --calibrate / --list
"""
import json, sys, os, math, shutil
from pathlib import Path
from datetime import datetime, date

HOME = Path.home()
ASSOC = HOME / ".hermes" / "baige" / "cache" / "assoc_index.json"
ARCHIVE = HOME / ".hermes" / "baige" / "cache" / "assoc_index_archive.json"
FOCUS = HOME / ".hermes" / "cache" / "focus_tracker.json"
LOCK = HOME / ".hermes" / "cache" / ".memory_index.lock"

def read_assoc():
    if not ASSOC.exists():
        return []
    return json.loads(ASSOC.read_text("utf-8"))

def write_assoc(data):
    """原子写入：先写tmp再rename"""
    ASSOC.parent.mkdir(parents=True, exist_ok=True)
    tmp = ASSOC.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    shutil.move(str(tmp), str(ASSOC))

def write_focus(data):
    FOCUS.parent.mkdir(parents=True, exist_ok=True)
    tmp = FOCUS.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), "utf-8")
    shutil.move(str(tmp), str(FOCUS))

def read_focus():
    if not FOCUS.exists():
        return {"entries": []}
    return json.loads(FOCUS.read_text("utf-8"))

def find_entry(entries, entry_id):
    for i, e in enumerate(entries):
        if e["id"] == entry_id:
            return i, e
    return None, None

# ─── 子命令 ───

def cmd_add(args):
    """追加新条目（LLM讨论结束后调用）"""
    entries = read_assoc()
    entry_id = args.get("id", f"{datetime.now():%Y%m%d}_manual")
    
    # 去重：已有同id则更新
    idx, existing = find_entry(entries, entry_id)
    new_entry = {
        "id": entry_id,
        "date": args.get("date", datetime.now().strftime("%Y-%m-%d")),
        "topic": args.get("topic", entry_id),
        "subjects": [s.strip() for s in args.get("subjects", "").split(",") if s.strip()],
        "event": [e.strip() for e in args.get("event", "").split(",") if e.strip()],
        "time_vec": args.get("date", datetime.now().strftime("%Y-%m-%d")),
        "ref": args.get("ref", ""),
        "weight": float(args.get("weight", 1.0)),
        "hits": 0,
        "misses": 0
    }
    
    if idx is not None:
        # 保留旧 hit/miss 数据
        new_entry["hits"] = existing.get("hits", 0)
        new_entry["misses"] = existing.get("misses", 0)
        entries[idx] = new_entry
        print(f"✅ 已更新: {entry_id}")
    else:
        entries.append(new_entry)
        print(f"✅ 已新增: {entry_id}")
    
    write_assoc(entries)
    # 写入后更新时间戳，下次skillgen会检测到变更
    (ASSOC.parent / ".assoc_mtime").write_text(datetime.now().isoformat(), "utf-8")

def cmd_update(args):
    """更新已有条目的某个字段"""
    entries = read_assoc()
    idx, entry = find_entry(entries, args.get("id", ""))
    if idx is None:
        print(f"❌ 未找到: {args.get('id')}")
        sys.exit(1)
    
    field = args.get("field", "")
    value = args.get("value", "")
    
    if field in ("subjects", "event"):
        entries[idx][field] = [s.strip() for s in value.split(",") if s.strip()]
    elif field in ("weight",):
        entries[idx][field] = float(value)
    else:
        entries[idx][field] = value
    
    write_assoc(entries)
    (ASSOC.parent / ".assoc_mtime").write_text(datetime.now().isoformat(), "utf-8")
    print(f"✅ 已更新 {args['id']}.{field}")

def cmd_hit(args):
    """记录命中（cron自动检测时调用·无需LLM手动）"""
    entry_id = args.get("id", "")
    focus = read_focus()
    focus.setdefault("entries", []).append({
        "id": entry_id,
        "ts": datetime.now().isoformat(timespec="seconds")
    })
    write_focus(focus)
    print(f"📌 命中记录: {entry_id}")

def cmd_calibrate(args):
    """每周校准：权重调整 + 年度归档"""
    entries = read_assoc()
    today = date.today()
    
    keep = []
    archive_items = []
    
    for entry in entries:
        entry_date = datetime.strptime(entry["date"], "%Y-%m-%d").date()
        days_since = (today - entry_date).days
        
        # 年度归档（>365天）
        if days_since > 365:
            archive_items.append(entry)
            print(f"  📦 归档: {entry['id']} ({days_since}天)")
            continue
        
        # 权重调整（样本量足够时）
        total = entry["hits"] + entry["misses"]
        if total > 3:
            acc = entry["hits"] / total
            if acc < 0.3:
                entry["weight"] = round(entry["weight"] * 0.7, 3)
                print(f"  ⬇ 降权: {entry['id']} (acc={acc:.2f}) → weight={entry['weight']}")
            elif acc > 0.8:
                entry["weight"] = round(min(1.0, entry["weight"] * 1.1), 3)
                print(f"  ⬆ 升权: {entry['id']} (acc={acc:.2f}) → weight={entry['weight']}")
        elif total == 0 and days_since > 30:
            # 30天无任何反馈→缓慢衰减
            old_w = entry["weight"]
            entry["weight"] = round(entry["weight"] * 0.95, 3)
            print(f"  📉 自然衰减: {entry['id']} ({days_since}天无反馈) {old_w}→{entry['weight']}")
        
        keep.append(entry)
    
    # 写回主文件
    write_assoc(keep)
    
    # 追加到归档
    if archive_items:
        old_archive = []
        if ARCHIVE.exists():
            old_archive = json.loads(ARCHIVE.read_text("utf-8"))
        old_archive.extend(archive_items)
        ARCHIVE.write_text(json.dumps(old_archive, ensure_ascii=False, indent=2), "utf-8")
        print(f"  📦 共归档 {len(archive_items)} 条")
    
    print(f"✅ 校准完成 | 活跃: {len(keep)} | 归档: {len(archive_items)}")

def cmd_list(args):
    """列出所有条目"""
    entries = read_assoc()
    print(f"assoc_index: {len(entries)} 条\n")
    for e in entries:
        print(f"  [{e['id']}] {e['topic']}")
        print(f"    日期: {e['date']}  weight: {e['weight']}")
        print(f"    主体: {', '.join(e['subjects'][:4])}...")
        print(f"    命中: hits={e['hits']} misses={e['misses']}")
        print()

def cmd_auto_detect(args):
    """自动检测：扫描state.db最新消息，匹配assoc_index主体→记录focus命中"""
    try:
        import sqlite3
        state_db = HOME / ".hermes" / "state.db"
        if not state_db.exists():
            return
        
        conn = sqlite3.connect(str(state_db))
        recent = conn.execute(
            "SELECT content FROM messages WHERE role='user' ORDER BY rowid DESC LIMIT 10"
        ).fetchall()
        conn.close()
        
        if not recent:
            return
        
        entries = read_assoc()
        all_text = " ".join(r[0] for r in recent).lower()
        hit_count = 0
        
        for entry in entries:
            for subject in entry["subjects"]:
                if subject.lower() in all_text:
                    cmd_hit({"id": entry["id"]})
                    hit_count += 1
                    break
        
        if hit_count > 0:
            print(f"🔍 自动检测: 命中 {hit_count} 条")
    except Exception as e:
        print(f"⚠️ auto_detect: {e}", file=sys.stderr)

# ─── 主入口 ───

def main():
    import argparse
    parser = argparse.ArgumentParser(description="记忆系统统一写入入口")
    parser.add_argument("--add", nargs="*", help="新增条目: id= topic= subjects= event= ref= weight=")
    parser.add_argument("--update", nargs="*", help="更新字段: id= field= value=")
    parser.add_argument("--hit", type=str, help="记录单条命中: id=xxx")
    parser.add_argument("--calibrate", action="store_true", help="每周校准")
    parser.add_argument("--list", action="store_true", help="列出所有条目")
    parser.add_argument("--auto-detect", action="store_true", help="自动检测最近消息匹配")
    
    args = parser.parse_args()
    
    if args.add:
        cmd_add(dict(a.split("=", 1) for a in args.add if "=" in a))
    elif args.update:
        cmd_update(dict(a.split("=", 1) for a in args.update if "=" in a))
    elif args.hit:
        cmd_hit({"id": args.hit})
    elif args.calibrate:
        cmd_calibrate({})
    elif args.auto_detect:
        cmd_auto_detect({})
    elif args.list:
        cmd_list({})
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
