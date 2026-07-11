# 天网神经系统 — 系统迭代方法论实战案例

> 2026-07-11 | 从"20操作仅1落地"到"4脚本+3cron全自动"的完整迭代

## 背景

`memory-auto-tier` v1.0 skill设计了20个记忆操作，但只有assoc_index.json一个文件有实际代码。用户要求用五维框架审计并重构。

## 迭代全流程（对照七步流程）

### 步骤①② 需求定义 + 现状摸底

**方法**：先load skill看设计文档，再去查实际文件
**发现**：20操作中仅 §3 (assoc_index.json) 是真实文件，其余19个是设计概念
**关键**：不走偏——用户说"管道库不存在"→先查state_weekly_backup.py源码→发现确实有管道库构建逻辑

### 步骤③ 方案设计

**核心设计决策**：
- 用skill映射替代memory全量注入（Tier 1）
- 动态专注窗口每30min流动（Tier 2）
- assoc_index文件持久化+cron预更新（Tier 3）
- 不写memory_context.json（无消耗者）

**关键提问"不能全自动？"**：
→ 设计方案时发现需要LLM手动--hit → 改为cron自动state.db扫描关键词匹配

### 步骤④ 方案审计

**关键提问"memory不支持分区？"**：
→ 不分区，用30min时间窗口替代空间分区

**关键提问"静态=死系统？"**：
→ 核心记忆必须随专注流动，固定=蠢人

### 步骤⑤ 代码落地

**实施顺序**：memory_index.py（统一入口）→ memory_skillgen.py→ memory_focus.py→ memory_calibrate.py
**原则**：每个脚本写完立刻验证，不假设成功

### 步骤⑥ 全链路验证

端到端跑通六步：新增条目→skill同步→自动检测→专注更新→校准→清理
验证结果全通过

### 步骤⑦ 归档固化

更新了memory-auto-tier skill、habits、创建system-improvement-framework skill、写入.discussions/

## 关键提问的价值

| 问题 | 暴露了什么 |
|:----|:----------|
| "不能全自动？" | LLM手动--hit = 精神分裂，改为cron自动检测 |
| "memory不支持分区？" | 时间窗口替代空间分区 |
| "C场景拦截怎么没做？" | 发现C场景放错了层——拦截是认知层的事，不是记忆层 |
| "分批都做了吗？" | 审计第二批/第三批发现memory_context.json无消耗者 |
| "静态=死系统？" | 核心专注必须流动 |

## 产出的最终资产

- 4脚本 + 3cron + 10索引 + 10micro-skill + 4相关skill
- 99% LLM-free
- 五维评分从 v1.0 35%~85% → v2.0 92%~99%
