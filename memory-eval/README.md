# 🧠 记忆系统评测体系 / Memory System Evaluation Suite

**零LLM · 双消费通道 · 普适自适应** / **Zero-LLM · Dual Consumption · Universal Adaptive**

> 评测 = 体检，方法论 = 处方。报告给系统优化，方法论给LLM完美应用。
> Evaluation = Checkup, Methodology = Prescription. Report for optimization, Methodology for perfect application.

## 📖 概述 / Overview

记忆系统评测体系是一套**零LLM（确定性）**的记忆系统健康评测工具。它从记忆系统本身自适应生成评测题（采样/变体/分层/组合），测量检索可达性、认知能力和极限压力，并产出**双消费通道**：评测报告（系统优化依据）+ 使用方法论 skill（LLM 完美应用指南）。

The Memory System Evaluation Suite is a **zero-LLM (deterministic)** health-check toolkit for memory systems. It adaptively generates test cases from the memory system itself (sampling/variants/layering/combination), measures retrieval reachability, cognitive capability, and stress limits, and produces **dual consumption channels**: evaluation report (for system optimization) + usage methodology skill (for LLM perfect application).

## ✨ 核心特性 / Key Features

| 特性 / Feature | 说明 / Description |
|:--------------|:-----------------|
| **零LLM确定性** / Zero-LLM | 纯脚本评测, 无LLM调用, 零token, 可复现 |
| **自适应出题** / Adaptive | 从记忆库采样生成, 每轮聚焦薄弱区 |
| **14模块评测** / 14 Modules | 检索/认知/压力全覆盖 (G-K/M/S/P等) |
| **双消费通道** / Dual Output | 报告(优化) + 方法论skill(应用) |
| **普适** / Universal | 任意记忆系统可测, {system_name}占位符 |

## 🚀 快速开始 / Quick Start

```bash
# 环境: Python 3.10+, 标准库 (无需第三方依赖)

# 1. 生成评测集 (自适应出题)
python memory_question_gen.py --round 1

# 2. 执行评测
python memory_eval.py --round 1

# 3. 生成使用方法论 (消费通道2)
python memory_methodology_gen.py --round 1
```

## 📁 文件结构 / Files

| 文件 / File | 作用 / Role |
|:-----------|:-----------|
| `memory_question_gen.py` | 自适应出题器 (4类出题器) |
| `memory_eval.py` | 评测执行器 (13指标+深度报告) |
| `memory_methodology_gen.py` | 方法论生成器 (普适skill) |
| `SKILL.md` | 社区skill: 评测方法论 (LLM可读) |

## 🔧 配置 / Configuration

```bash
# 记忆根目录 (默认 ~/.hermes, 可覆盖)
export MEMORY_EVAL_HOME=/path/to/your/system
```

## 📊 评测输出 / Outputs

```
评测报告: 数据(结果) + 方法论说明 + 消费链条说明 (使用者自决)
方法论skill: 系统画像/记忆地图/检索技巧/使用流程/评测消费/普适性/命名规范
```

## 📄 License

MIT

## 🙏 致谢 / Credits

由 Hermes 记忆评测体系 (2026-08) 提炼发布。Extracted from Hermes memory evaluation system (2026-08).
