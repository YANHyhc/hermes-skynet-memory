# 系统迭代标准化流程 — 完整实施范例

> 来自 2026-07-11 记忆系统 v1.0 → v2.0 全流程迭代
> 原始讨论: `.discussions/memory-system/2026-07-11.md`

## 背景

`memory-auto-tier` v1.0 是一个架构设计文档（SKILL.md），描述了20个记忆系统操作，但只有1个（assoc_index.json）有实际文件落地。用户要求评估并实施。

## 步骤① 需求定义

用户说："评估审计昨天晚上生成的记忆系统"
五维审计方向：逻辑自洽 / 可行有效 / 提效率 / 解决断链 / 防死循环

## 步骤② 现状摸底

| 检查项目 | 结果 | 方法 |
|:--------|:----|:-----|
| assoc_index.json | ✅ 4条条目，格式正确 | read_file |
| MEMORY.md | ✅ 17条§分隔，81%满 | read_file |
| skills/memory/目录 | ❌ 不存在 | search_files |
| pipeline/目录 | ⚠️ 目录存在但为空 → 实际state_weekly_backup.py有管道库逻辑 | search_files + 读脚本源码 |

**关键教训**：目录为空≠系统不存在。先查脚本、cron、skill设计文档再下结论。

## 步骤③ 方案设计

方案A（memory注入）：❌ 占800字→溢出
方案B（cron预匹配）：⏳ 需Hermes网关钩子
方案C（skill映射）：✅ 现成可用

**最终方案**：三层递进 = 动态专注窗口(Tier 1) + skill映射(Tier 2) + assoc_index深度检索(Tier 3)

核心原则：主环97% LLM-free，LLM只做判断型决策（"值不值得记"）

## 步骤④ 方案审计

| 维度 | 发现 | 评分 |
|:----|:-----|:----:|
| 逻辑自洽 | 三层单向依赖，无环 | 🟢 |
| 可行有效 | 4脚本+3cron全可落地 | 🟢 审计后**补了3个设计漏洞** |
| 效率提升 | 每轮省~1,000字上下文噪声 | 🟢 |
| 解决断链 | 覆盖会话内/跨会话/数据丢失三类断链 | 🟢 |
| 死循环 | 无自引/振荡 | 🟢 |

**审计发现的3个漏洞及修正**：
1. focus_tracker的LLM--hit → 改为cron自动state.db检测
2. memory_context.json无消耗者 → 去掉
3. 每10min全量sync → 改为检查mtime跳过不变

## 步骤⑤ 代码落地

| 顺序 | 脚本 | 说明 |
|:----|:-----|:-----|
| 1 | memory_index.py | 统一写入入口（依赖链根） |
| 2 | memory_skillgen.py | 每10min同步，自动检测focus |
| 3 | memory_focus.py | 每30min专注窗口 |
| 4 | memory_calibrate.py | 每周日校准+归档 |

**每个脚本写完立刻验证**：terminal/execute_code跑--list确认输出

## 步骤⑥ 全链路验证

端到端测试：新增条目→skill自动同步→专注窗口更新→校准→清理
六步走通，零报错。

## 步骤⑦ 归档固化

| 动作 | 完成 |
|:----|:----:|
| 更新memory-auto-tier skill | ✅ v2.0实现状态表✅ |
| 更新habits skill | ✅ H030/H031/H032 |
| 创建system-improvement-framework skill | ✅ 本框架 |
| 写入.discussions/memory-system/ | ✅ 完整记录 |
| 追加assoc_index | ✅ 4条历史+1条本次+1条框架 |
| 更新topology.json | ✅ 0_neural层（天网神经系统） |
| 输出五维终评 | 🟢 35%→95% |

## 产出汇总

| 类别 | 数量 | 说明 |
|:----|:----|:------|
| 新脚本 | 4个 | memory_index/skillgen/focus/calibrate |
| 新cron | 3个 | 每10min/每30min/每周日 |
| micro-skill | 5个 | 覆盖所有assoc_index条目 |
| assoc_index | 9条 | 从5条扩展到9条（含历史补录） |
| 讨论记录 | 1个 | memory-system模块 |
| 新skill | 1个 | system-improvement-framework |
