# 快速部署指南 / Quickstart

## 1. 安装脚本
```bash
cp scripts/*.py ~/.hermes/scripts/
```

## 2. 安装 skills
```bash
cp -r skills/* ~/.hermes/skills/
```

## 3. 初始化 assoc_index
```bash
mkdir -p ~/.hermes/baige/cache
echo '[]' > ~/.hermes/baige/cache/assoc_index.json
```

## 4. 注册 cron（Hermes CLI）
```bash
hermes cron create --schedule "*/10 * * * *" --script "memory_skillgen.py" --name "Skynet Skill Sync"
hermes cron create --schedule "5,35 * * * *" --script "memory_focus.py" --name "Skynet Focus Window"
hermes cron create --schedule "10 3 * * 0" --script "memory_calibrate.py" --name "Skynet Calibration"
```

## 5. 验证
```bash
python ~/.hermes/scripts/memory_index.py --list
# 输出: assoc_index: 0 条（首次为空，用 --add 添加第一条）
```

## 6. 添加第一个条目
```bash
python ~/.hermes/scripts/memory_index.py --add \
  id=20260715_my_first_topic \
  topic="我的第一个记忆条目" \
  subjects="关键词1,关键词2" \
  event="重要讨论的内容摘要" \
  ref="来源/笔记"
```

首次添加后，cron 会在 10 分钟内自动生成 micro-skill，下次提到关键词时自动加载。
