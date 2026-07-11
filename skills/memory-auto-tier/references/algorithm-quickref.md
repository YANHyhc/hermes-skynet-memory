# 3D定位快速匹配参考

## assoc_index格式

```json
{
  "id": "YYYYMMDD_topic",
  "date": "2026-07-10",
  "topic": "话题名称",
  "subjects": ["主体1", "主体2", "主体3"],
  "event": ["动词+宾语", "同义表述"],
  "time_vec": "2026-07-10",
  "ref": "引用来源",
  "weight": 1.0,
  "hits": 0,
  "misses": 0
}
```

## 关联分公式

```
关联分 = 主语匹配率 × 0.5 + 事件词重叠率 × 0.3 + 时间衰减 × 0.2
```

## 阈值

| 分 | A场景 | C场景 |
|:--:|:----|:----|
| ≥0.7 | 自动推送 | 警告+确认 |
| 0.4~0.7 | fallback查讨论skill | 无灰色区(按不命中) |
| <0.4 | 不触发 | 不触发 |

## 时间衰减

```python
weight = max(0, 1 - log(days + 1) / log(365))
# Day1: 1.0, Day7: 0.66, Day30: 0.48, Day365: 0.0
```

## 自校准（每周日）

```python
if hits + misses > 3:
    acc = hits / (hits + misses)
    if acc < 0.3: weight *= 0.7
    elif acc > 0.8: weight = min(1.0, weight * 1.1)
```

## 推送规则

- 每3轮最多1条推送
- 多条命中取最高分
- 用户"确认"跳过C场景
- 连续3次无反馈→降权
- 只降权不删条目
