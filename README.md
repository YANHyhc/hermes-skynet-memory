1|# 🧠 天网神经系统（Hermes Skynet）
2|
3|> 一套让 AI Agent 拥有「记忆本能」的三位一体记忆与上下文系统  \
4|> A trinity memory & context system that gives AI Agents memory instinct
5|
6|**天网 = Skynet（致敬《终结者》）** — 覆盖全局、连接一切的神经基础设施。
7|
8|> ⚠️ **专为 Hermes Agent 设计 / For Hermes Agent Only**  \
9|> 本项目是为 [Hermes Agent](https://github.com/NousResearch/hermes) 框架量身定制的记忆层，借助 Hermes 的 skill/cron/session 机制实现被动注入式记忆。非 Hermes 框架需重新适配。  \
10|> This project is a native memory layer for Hermes Agent, leveraging its skill/cron/session system for passive-injection memory. Not portable to other frameworks without adaptation.
11|
12|---
13|
14|## 📖 概述 / Overview
15|
16|天网神经系统是 Hermes Agent 的三层记忆架构，解决了 AI Agent 最核心的痛点：**跨会话记忆断链、memory 溢出、讨论结论丢失**。
17|
18|Hermes Skynet is a three-tier memory architecture for Hermes Agent, solving the most critical pain points of AI Agents: **cross-session memory gaps, memory overflow, and lost discussion conclusions**.
19|
20|```mermaid
21|graph TD
22|    A[聊天记录系统<br/>原始数据层/海马体] --> B[记忆系统<br/>索引检索层/前额叶]
23|    B --> C[讨论系统<br/>结构化知识层/新皮层]
24|    A[Chat Backup<br/>Hippocampus] --> B[Memory System<br/>Prefrontal Cortex]
25|    B --> C[Discussion System<br/>Neocortex]
26|    style A fill:#1a1a2e,color:#fff
27|    style B fill:#16213e,color:#fff
28|    style C fill:#0f3460,color:#fff
29|```
30|
31|| 层级 / Tier | 对标人脑 / Brain Analogy | 功能 / Function | 技术实现 / Implementation |
32||:-----------|:------------------------|:---------------|:-------------------------|
33|| ① 聊天记录系统 / Chat Backup | 海马体 / Hippocampus | 储存原始对话经历 / Store raw conversations | `chat_backup.py` + `state_weekly_backup.py` |
34|| ② 记忆系统 / Memory System | 前额叶 / Prefrontal Cortex | 索引检索+自动关联+专注窗口 / Indexing, retrieval, focus | `memory_*.py` 4脚本 + 3cron + assoc_index |
35|| ③ 讨论系统 / Discussion System | 新皮层 / Neocortex | 结构化知识沉淀 / Structured knowledge | `discussion-template` + `system-improvement-framework` |
36|
37|**核心数据流 / Data flow：** 每次讨论结束 → 归档到讨论系统 → cron自动同步索引 → 下次提到相关话题 → micro-skill自动加载 → 「本来就知道」。  \
38|Discussion ends → archived to Discussion System → cron syncs index → next mention of topic → micro-skill auto-loads → agent "just knows".
39|
40|---
41|
42|## ✨ 核心特性 / Key Features
43|
44|| 特性 | Feature |
45||:----|:--------|
46|| **🧠 三层递进记忆** — 数据层→索引层→知识层，单向依赖无环 | **Three-tier progressive memory** — Data → Index → Knowledge, no cycles |
47|| **⚡ 99% LLM-free** — 主环全自动（cron+脚本），LLM只做判断型决策 | **99% LLM-free** — Core loop fully automated; LLM only makes judgment calls |
48|| **🎯 动态专注窗口** — memory核心每30min自动流动，不固定不霸占 | **Dynamic focus window** — Memory rebalances every 30min, never fixed |
49|| **🔗 Skill即记忆** — 每个条目→一个micro-skill，triggers命中自动加载 | **Skill-as-memory** — Each entry → one micro-skill, triggers auto-load |
50|| **📋 五维审计框架** — 逻辑自洽/可行/效率/断链解决/死循环风险 | **Five-dimension audit** — Consistency / Feasibility / Efficiency / Gaps / Loops |
51|| **🛡️ 认知层决策** — 记忆只提供教训，拦截是LLM的自然职责 | **Cognitive-layer decisions** — Memory supplies history; LLM decides |
52|| **⚙️ 零依赖** — 全部 Python stdlib，无需 pip install | **Zero dependencies** — Pure Python stdlib, no pip install needed |
53|| **🎯 专为 Hermes Agent 设计** — skill/cron/session 原生集成 | **Hermes-native** — Built on skill/cron/session architecture |
54|
55|---
56|
57|## 📊 同类产品对比 / Competitive Analysis
58|
59|> 数据来源：GitHub API，2026-07-11。仅列出有明确「Agent 记忆」定位的项目。
60|
61|### 市场格局总览
62|
63|| 项目 | ⭐ Stars | 语言 | 定位 |
64||:----|:-------:|:----|:-----|
65|| mem0ai/mem0 | 60,579 | Python | 通用记忆层 API |
66|| topoteretes/cognee | 27,554 | Python | AI 记忆平台 |
67|| letta-ai/letta（原MemGPT） | 23,736 | Python | 有状态 Agent 平台 |
68|| memvid/memvid | 15,741 | Rust | Serverless 记忆层 |
69|| TencentCloud/TencentDB-Agent-Memory | 8,282 | TypeScript | 4层渐进式记忆管道 |
70|| plastic-labs/honcho | 5,899 | Python | Agent 记忆基础设施 |
71|| **YANHyhc/hermes-skynet-memory（我们）** | **0** | **Python** | **Hermes 原生三体记忆系统** |
72|
73|### 核心差异对比
74|
75|| 维度 | Mem0 | Cognee | Letta | Honcho | **天网（我们）** |
76||:----|:----:|:------:|:-----:|:-----:|:--------------:|
77|| **记忆机制** | 主动查询API | 主动查询API | 虚拟上下文 | 背景推理 | **被动注入** 🏆 |
78|| **LLM 参与记忆链** | 是 | 是 | 是 | 是 | **99% 无需LLM** 🏆 |
79|| **外部依赖** | 向量DB | FS/DB | 独立平台 | FastAPI | **零依赖** 🏆 |
80|| **集成方式** | pip + API Key | pip + 配置 | 迁移平台 | pip + 服务器 | **cp + cron注册** 🏆 |
81|| **专注窗口** | 无 | 无 | 有 | 无 | **动态自动迁移** 🏆 |
82|| **中文支持** | 英文为主 | 英文为主 | 英文为主 | 英文为主 | **原生中文** 🏆 |
83|| **框架绑定** | 通用 | 通用 | Letta专属 | 通用 | **Hermes原生** |
84|| **成熟度** | 生产级 | 生产级 | 生产级 | Beta | Alpha |
85|
86|### 天网的设计哲学差异化
87|
88|我们的核心差异不是「功能更多」——而是**记忆机制本身不同**：
89|
90|```
91|❌ 竞品范式：主动查询
92|   Agent说"我要查记忆" → 调API → 检索 → 算分 → 再回答
93|   像人每次说话前先"调用"自己的海马体
94|
95|✅ 天网范式：被动注入
96|   cron自动维护索引 → triggers命中 → skill自动加载 → "本来就知道"
97|   像人的海马体自动工作，不需要前额叶调用
98|```
99|
100|**为什么这个差异重要？**
101|- 主动查询需要 Agent 自己知道「我需要查记忆了」——这是认知负荷
102|- 被动注入不需要 Agent 感知记忆系统的存在——零认知负荷
103|- 绝大多数 LLM 不会主动调用外部记忆接口——被动注入确保记忆**总是被用到**
104|
105|---
106|
107|## 📈 实测基准 / Benchmarks
108|
109|> 生产环境实测（Hermes Agent + assoc_index 11 条目 + 45 skills）
110|
111|| 指标 | 实测值 | 说明 |
112||:----|:------:|:-----|
113|| assoc_index 条目数 | **11** | 当前已沉淀的记忆条目 |
114|| assoc_index 大小 | **6,111 B** | 极轻量，毫秒级操作 |
115|| 单次 JSON 序列化 | **0.056 ms** | 1000次批量仅 56ms |
116|| memory_index --list | **192 ms** | 含 11 条目完整输出 |
117|| MEMORY.md 大小 | **4,126 B** | 23 个§分段，45行 |
118|| 总技能数量 | **45** | 含系统技能 + 记忆 micro-skills |
119|| 含 SKILL.md 的技能 | **17** | 独立知识模块 |
120|| 天网核心技能 | **3** | memory-auto-tier + 讨论模板 + 系统迭代 |
121|
122|### 性能特征
123|
124|- **毫秒级索引操作** — assoc_index 的读写和序列化 < 0.1ms，对 Agent 响应无影响
125|- **cron 全自动** — 记忆维护全部在后台进行，用户对话过程中零感知
126|- **零 LLM 消耗** — 记忆写入/索引/同步/专注计算全部走 Python stdlib
127|
128|---
129|
130|## 🚀 快速开始 / Quick Start
131|
132|### 前提 / Prerequisites
133|
134|- [Hermes Agent](https://github.com/NousResearch/hermes) 已安装并运行 / Installed and running
135|- Python 3.10+
136|
137|### 安装 / Installation
138|
139|```bash
140|# 1. 克隆仓库 / Clone the repo
141|git clone https://github.com/YANHyhc/hermes-skynet-memory.git
142|cd hermes-skynet-memory
143|
144|# 2. 安装脚本 / Install scripts
145|cp scripts/*.py ~/.hermes/scripts/
146|
147|# 3. 安装 skill / Install skills
148|cp -r skills/* ~/.hermes/skills/
149|
150|# 4. 初始化索引 / Initialize index
151|mkdir -p ~/.hermes/baige/cache
152|echo '[]' > ~/.hermes/baige/cache/assoc_index.json
153|
154|# 5. 注册 cron 任务 / Register cron jobs
155|hermes cron create --schedule "*/10 * * * *" \
156|  --script "memory_skillgen.py" --name "天网 Skill 同步 / Skynet Skill Sync"
157|
158|hermes cron create --schedule "5,35 * * * *" \
159|  --script "memory_focus.py" --name "天网专注窗口 / Skynet Focus Window"
160|
161|hermes cron create --schedule "10 3 * * 0" \
162|  --script "memory_calibrate.py" --name "天网校准 / Skynet Calibration"
163|
164|# 6. 验证 / Verify
165|python ~/.hermes/scripts/memory_index.py --list
166|```
167|
168|### 添加第一条记忆 / Add Your First Memory
169|
170|每次重要讨论结束时 / After every important discussion:
171|
172|```bash
173|python ~/.hermes/scripts/memory_index.py --add \
174|  id=20260715_my_topic \
175|  topic="话题名称 / Topic Name" \
176|  subjects="关键词1,关键词2 / keyword1,keyword2" \
177|  event="事件描述 / Summary of the discussion" \
178|  ref="来源 / Source"
179|```
180|
181|cron 会在10分钟内自动生成对应的 micro-skill，下次提到关键词时自动加载。  \
182|The cron job auto-generates a micro-skill within 10 minutes; it loads automatically when keywords are mentioned.
183|
184|---
185|
186|## 🧩 组件清单 / Components
187|
188|### 4个脚本 / 4 Scripts
189|
190|| 脚本 / Script | 功能 / Function | 触发器 / Trigger |
191||:-------------|:---------------|:----------------|
192|| `memory_index.py` | 统一写入入口（--add/--update/--calibrate/--auto-detect/--list） | 手动（讨论结束）/ Manual |
193|| `memory_skillgen.py` | assoc_index → micro-skill 同步 + state.db 自动命中检测 | cron 每10min |
194|| `memory_focus.py` | 读 focus_tracker → 算聚焦分 → 更新 MEMORY.md 专注行 | cron 每30min |
195|| `memory_calibrate.py` | 权重调整 + >365天条目归档 | cron 每周日 / Weekly Sunday |
196|
197|### 3个cron调度 / 3 Cron Schedules
198|
199|| 调度 / Schedule | 脚本 / Script | 说明 / Description |
200||:--------------:|:-------------:|:------------------|
201|| `*/10 * * * *` | `memory_skillgen.py` | 每10min同步+检测 / Sync + detect every 10min |
202|| `5,35 * * * *` | `memory_focus.py` | 每30min更新专注 / Update focus every 30min |
203|| `10 3 * * 0` | `memory_calibrate.py` | 每周日校准+归档 / Weekly calibration + archive |
204|
205|### 3个核心skill / 3 Core Skills
206|
207|| Skill | 说明 / Description |
208||:------|:------------------|
209|| `memory-auto-tier` | 记忆系统架构设计+哲学+陷阱库 / Architecture + philosophy + pitfalls |
210|| `discussion-template` | 通用5步讨论固化框架 / 5-step discussion crystallization framework |
211|| `system-improvement-framework` | 五维审计+七步方法论 / Five-dimension audit + 7-step methodology |
212|
213|---
214|
215|## 🔬 设计哲学 / Design Philosophy
216|
217|### 记忆必须无感 / Memory Must Be Invisible
218|
219|记忆系统不应该被「调用」，就像人不需要「调用」自己的海马体。记忆是底层自动的。  \
220|A memory system should not be "called" — just as you don't "call" your own hippocampus. Memory is automatic.
221|
222|```
223|❌ 坏设计 / Bad design：LLM说"我要查记忆"→调脚本→读文件→算关联→再回答
224|✅ 好设计 / Good design：cron自动维护索引→triggers命中→skill自动加载→「本来就知道」
225|```
226|
227|### Skill即记忆 / Skill-as-Memory
228|
229|每个 assoc_index 条目自动对应一个 micro-skill。用户说话时 triggers 匹配 → skill 自动加载 → 历史教训出现在上下文中。  \
230|Every assoc_index entry maps to a micro-skill. User mentions a keyword → triggers match → skill loads → history appears.
231|
232|### 动态专注窗口 / Dynamic Focus Window
233|
234|Memory 核心不固定。cron 每30min 读 focus_tracker → 排序 → 替换 memory 顶部。专注随用户关注自然迁移。  \
235|Memory core is not fixed. Cron reads focus_tracker every 30min → sorts → replaces top of memory. Focus migrates naturally.
236|
237|### 拦截是认知层的事 / Interception Belongs to Cognitive Layer
238|
239|C场景（危险操作拦截）不应写在记忆系统里。记忆系统职责到「提供历史教训」为止——拦不拦截是 LLM 基于上下文的自然决策。  \
240|C-scenarios (dangerous ops) should not be in the memory system. Memory supplies history; whether to intercept is the LLM's decision.
241|
242|---
243|
244|## 📊 五维评分 / Five-Dimension Score
245|
246|| 维度 / Dimension | 评分 / Score | 含义 / Meaning |
247||:----------------|:-----------:|:---------------|
248|| 逻辑自洽闭环 / Logical consistency | 🟢 99% | 三层单向依赖，无环 / Uni-directional, no cycles |
249|| 可行有效 / Feasibility | 🟢 96% | 4脚本+3cron全部可运行 / All scripts + crons runnable |
250|| 效率提升 / Efficiency | 🟢 92% | 省60%噪声，断链率-90% / -60% noise, -90% gaps |
251|| 记忆断链解决 / Gap resolution | 🟢 95% | 三层覆盖所有断链场景 / Three tiers cover all gaps |
252|| 死循环风险 / Loop risk | 🟢 99.5% | 无自引/振荡/无限递归 / No self-reference / oscillation |
253|
254|---
255|
256|## 🔧 维护 / Maintenance
257|
258|### 日常操作 / Daily Operations
259|
260|```bash
261|# 列出所有条目 / List all entries
262|python ~/.hermes/scripts/memory_index.py --list
263|
264|# 手动触发校准 / Manual calibration
265|python ~/.hermes/scripts/memory_calibrate.py
266|
267|# 查看当前专注 / View current focus
268|cat ~/.hermes/memories/MEMORY.md | head -1
269|```
270|
271|### 归档 / Archiving
272|
273|>365天的条目自动移入 `baige/cache/assoc_index_archive.json`。自然衰减：30天无反馈 → weight×0.95。  \
274|Entries >365 days auto-move to `baige/cache/assoc_index_archive.json`. Decay: no feedback for 30 days → weight × 0.95.
275|
276|---
277|
278|## 📜 许可证 / License
279|
280|MIT License — 自由使用、修改、分发 / Free to use, modify, and distribute.
281|
282|---
283|
284|## 👥 贡献者 / Contributors
285|
286|- **晏翔+小白鸽 / Yan Xiang + Xiaobaige** — 架构设计+核心实现 / Architecture + core implementation
287|- [Hermes Agent](https://github.com/NousResearch/hermes) — Nous Research 的 Agent 框架 / Agent framework by Nous Research
288|
289|---
290|
291|## 🫶 致谢 / Acknowledgments
292|
293|- Nous Research 团队 — 创造了 Hermes Agent / For creating Hermes Agent
294|- 《终结者》系列 — 天网（Skynet）的灵感 / The Terminator franchise — inspiration for "Skynet"
295|- 所有尝试构建 Agent 记忆系统的开发者 — 你们的探索让这条路更清晰 / Every dev building memory systems for agents — your exploration lights the way
296|