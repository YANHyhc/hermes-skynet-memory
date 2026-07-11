# state.db 三层记忆架构

> 晏翔系统的聊天数据库备份/清理/查询方案。设计原则：写一次用永远，零影响运行系统。

## 三层记忆模型

```
层级        时间颗粒    数据源                    查询时机
──────────────────────────────────────────────────────────────
短期记忆    当日        chat_YYYYMMDD.json       问"今天"时
中期记忆    本周        state.db（实时库）        问本周内时
长期记忆    本周前      pipeline/state_pipeline.db 问历史/显式查管道库时

↑ 灾备：E:盘 state_YYYYMMDD.db 保留8周（不参与查询，只用于恢复）
```

## 周日03:00流水线

```
① state_weekly_backup.py → E:盘归档 state_YYYYMMDD.db（保留8周）
② 验证通过 → cp 到 C:.hermes/pipeline/state_pipeline.db（覆盖）
③ 方案A清理实时库 → DELETE messages/sessions（保留最新session）
④ 周一起 state.db 干净轻量
```

## 查询路由

| 用户提问 | 查哪个库 |
|:--------|:--------|
| 本周内的、没提"历史" | state.db（实时库） |
| 提到"历史"、"管道库"、"上个月"、"之前" | pipeline/state_pipeline.db |
| 显式说"查管道库" | pipeline/state_pipeline.db |
| 管道库损坏 | 报错，不影响实时库运行 |

## 关键文件

| 文件 | 位置 | 更新频率 | 用途 |
|:----|:----|:--------:|:----|
| state.db | ~/.hermes/ | 持续 | 实时运行+本周查询 |
| state_pipeline.db | ~/.hermes/pipeline/ | 每周日覆盖 | 历史查询 |
| state_YYYYMMDD.db | E:/Hermes备份文件夹/state_weekly/ | 每周日（保留8周） | 归档灾备 |
| chat_YYYYMMDD.json | ~/.hermes/backups/chat/ + E:盘 | 每日 | 细粒度保底 |

## 恢复技术（Schema兼容合并）

当需要从旧备份恢复数据到新库时（如WAL损坏导致库崩），新旧 Hermes 版本的 sessions 表和 messages 表列序可能不同。不能直接用 `SELECT *` + `INSERT INTO ... VALUES`。

### 正确做法

```python
# 1. 用 PRAGMA table_info 获取两库列序
cur_cols = [r[1] for r in con.execute("PRAGMA table_info(sessions)")]
bak_cols = [r[1] for r in con_bak.execute("PRAGMA table_info(sessions)")]

# 2. 按列名映射（而不是按位置）
def map_row(row, bak_cols, cur_cols):
    bak_idx = {name: i for i, name in enumerate(bak_cols)}
    result = []
    for col in cur_cols:
        if col in bak_idx:
            result.append(row[bak_idx[col]])
        else:
            result.append(None)  # 新库有但旧库没有的列 → NULL
    return result

# 3. 用当前 schema 重建库，插入数据时显式声明列名
con.execute(f"INSERT INTO sessions ({','.join(cur_cols)}) VALUES ({placeholders})", mapped_row)
```

### 常见陷阱

| 陷阱 | 表现 | 原因 |
|:----|:-----|:----|
| NOT NULL constraint failed | 某列在新库有 NOT NULL 约束但在旧库无对应值 | 列序错位导致值赋到错误列 |
| UNIQUE constraint failed | 新旧库 message ID 重叠（都从1开始） | 手动分配新ID：max_id+1 |
| 库中无 kv_store/alembic_version 表 | 你猜的表不存在 | 先 sqlite_master 看实际表再动 |

### hermes_launcher.py 自动换库钩子

在 `WorkBuddy/Claw/hermes/hermes_launcher.py` 的 `clean_locks()` 之后加入：

```python
# 启动前换库：如果有 state.db.recovered → 替换 state.db
recovered = os.path.join(HERMES_HOME, "state.db.recovered")
current  = os.path.join(HERMES_HOME, "state.db")
if os.path.exists(recovered):
    import shutil
    shutil.copy2(recovered, current)
    os.remove(recovered)
```

效果：WorkBuddy 重启 Hermes 时，检测到 `state.db.recovered` 就自动覆盖为最新 state.db，用完即删。

## 数据库实际结构（v17 schema）

| 表 | 列数 | 说明 |
|:---|:---:|:-----|
| messages | 19 | 聊天消息，含 FTS5 全文索引 4 表 + trigram 索引 5 表 |
| sessions | 41 | 会话记录（每次启动一个session） |
| state_meta | 2键 | ghost_session_prune_v1=1, orphaned_compression_finalize_v1=1 |
| schema_version | 1行 | version=17 |
| compression_locks | 0行 | session压缩锁 |

**不含 kv_store、alembic_version。** 清理时只需保留 state_meta + schema_version + compression_locks。
