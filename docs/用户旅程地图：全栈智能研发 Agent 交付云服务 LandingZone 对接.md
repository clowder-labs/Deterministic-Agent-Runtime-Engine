### 用户旅程地图：全栈智能研发 Agent 交付云服务 LandingZone 对接

**User Journey Map: Full-Stack Intelligent Development (STS3 to LandingZone)**

**核心场景**：
研发架构师通过 DARE Framework 驱动 Agent（Super-Dev），在一个长链路、涉及多生态系统（CloudDevOps, CodeHub, Wiki）的复杂任务中，完成从需求分析到生产部署的全过程。

**涉及生态**：

* **需求源**：CloudDevOps (PRD/Tickets)
* **代码源**：CodeHub (Git Repositories)
* **知识源**：Wushan Framework Wiki (RAG Knowledge Base)
* **流水线**：CI/CD Pipeline System

---

#### 阶段一：全景认知与生命周期规划 (Phase 1: Context & Lifecycle)

**—— Layer 1: Session Loop (跨上下文的宏观把控)**

**1. 任务触发与记忆回溯 (Context Assembly)**

* **用户动作**：在 IDE 插件中输入指令：
`> /start_mission --prd="https://clouddevop.internal/prd/LZ-2024-STS3" --repo="git@codehub:infra/sts3-service.git"`
* **Agent 动作 (Session Loop)**：
* **连接 CodeHub**：拉取 `sts3-service` 代码，分析现状。
* *认知结果*：检测到当前使用 `Wushan Framework v1.2`（过时），鉴权模块依赖旧版 IAM SDK，未对接 PDP。


* **连接 Knowledge Base**：检索《Wushan v5.0 升级指南》与《LandingZone 接入标准 v3.0》。
* **连接 CloudDevOps**：读取 PRD，提取核心需求：**"服务无状态化"**、**"对接 PDP5 统一鉴权"**、**"双活容灾"**。



**2. 里程碑拆解 (Milestone Definition)**

* **Agent 产出**：基于 SDLC（软件研发生命周期）将大需求拆解为 5 个顺序里程碑。
* **M1 [环境整理]**：清理依赖，确认测试环境 `env-test-01` 连通性。
* **M2 [技术设计]**：输出改动范围清单与技术方案文档。
* **M3 [方案验证计划]**：**关键步骤**——定义如何证明任务完成（含变异测试策略）。
* **M4 [编码与实施]**：执行代码修改、提交 MR、通过 CI。
* **M5 [验收交付]**：端到端 Alpha Test 与审计证据固化。



---

#### 阶段二：证据驱动的交互式规划 (Phase 2: Evidence-Based Planning)

**—— Layer 3: Plan Loop (格式化校验与契约签订)**

*场景聚焦：Agent 进入 **M4 [编码与实施]** 阶段。*

**1. 计划生成 (Drafting)**

* Agent 根据 M2 的设计文档，生成 M4 的实施计划 `ProposedPlan`。
* **IValidator 介入 (格式校验)**：
* Validator **不检查**代码逻辑（那是 LLM 的事）。
* Validator **强制检查**合规性：“这是一个开发任务，Plan 必须包含证据收集步骤。”
* *判定*：驳回计划，因为缺少 `[MR_Link]` 和 `[CI_Job_ID]` 的占位符。



**2. 交互式 IDE 呈现 (The Dual-Pane Interface)**

* Agent 修正计划后，在用户的 IDE 中呈现**双栏视图**：

| **左栏：Dynamic Task List (战术清单)** | **右栏：Implementation Plan (战略契约)**           |
| ------------------------------- | ------------------------------------------- |
| *Markdown 格式，实时变动*              | *只读/审批模式，包含必须填写的“证据坑位”*                     |
| `[x] 阅读技术方案`                    | **Goal**: Implement PDP5 Auth Adapter       |
| `[ ] 升级 wushan-core 依赖`         | **Evidence Requirements (Validator):**      |
| `[ ] 重构 AuthProvider 类`         | 1. **Code Merge**: `[ 待填: MR Link ]`        |
| `[ ] 提交代码并触发 CI`                | 2. **Quality Gate**: `[ 待填: CI Job ID ]`    |
| `[ ] 运行本地单元测试`                  | 3. **Validation**: `[ 待填: Alpha Test URL ]` |

**3. 用户确认**

* 用户审视右侧 Plan，确认证据要求合理，点击 **"Proceed"**。
* Agent 获得授权，进入执行循环。

---

#### 阶段三：异步执行与自愈闭环 (Phase 3: Async Execution & Remediation)

**—— Layer 4: Execute Loop (执行、反思与动态修正)**

*用户此时切换窗口去开会，Agent 在后台进行异步人机协作。*

**1. 执行受阻 (The Failure)**

* **动作**：Agent 修改完代码，运行本地 UT (Unit Test) 通过。
* **动作**：Agent 调用 `GitCommit` 和 `GitPush` 工具。
* **反馈**：轮询 CI 系统，发现流水线状态：❌ **FAILED**。
* *Log*: `DependencyError: lib-wushan-pdp not found in production base image.`



**2. 自动反思与修复 (Remediate)**

* **Remediator 介入**：分析 CI 日志与本地环境的差异。
* **动态调整 Task List (左栏)**：
* Agent **不修改**右栏的 Plan（战略目标不变，还是要提交 MR）。
* Agent 在左栏自动插入新任务：`[+] Update Dockerfile base image to v1.5`。


* **自愈执行**：Agent 修改 Dockerfile -> 再次 Commit -> 再次 Push。

**3. 任务闭环 (Success)**

* CI 流水线变绿 ✅。
* Agent 自动提取 CI 单号和 MR 链接，**填入右栏 Plan 的空白括号中**。

---

#### 阶段四：金标准交付与审计 (Phase 4: The Golden Record)

**—— Layer 2 & Session Summary (最终交付)**

*所有里程碑完成，Agent 生成最终交付物。*

**交付物文档：LandingZone 接入验收报告 (Session Summary)**

> **📋 任务状态：SUCCESS (已通过审计)**
> **1. 需求溯源 (Context)**
> * **Source**: `CloudDevOps/PRD-2024` (Hash: a1b2c3...)
> * **Scope**: `sts3-service` 仓库
> 
> 
> **2. 完整证据链 (The Audit Trail)**
> * *此处数据来自各个 Milestone 填写的“坑位”*
> * **M2 设计**: [Tech_Design.md](https://www.google.com/search?q=wiki-link) (用户已 Review)
> * **M4 代码**:
> * **CodeHub MR**: [!2391: Feature/PDP5-Connect](https://www.google.com/search?q=link) (Status: Merged)
> * **CI Pipeline**: [Job-99812](https://www.google.com/search?q=link) (Result: Passed, Duration: 12m)
> 
> 
> * **M5 质量**:
> * **Mutation Test**: 变异存活率 0% (证明测试用例有效，非伪造) ✅
> * **Alpha Test**: 访问 `https://stg.landingzone/sts3/health` 返回 200 OK。
> * **Visual Proof**: [Agent_Auto_Test_Replay.mp4] (点击播放前端/接口测试录屏)
> 
> 
> 
> 
> **3. 过程回顾**
> * 共耗时 45 分钟。
> * 自动修复 CI 依赖问题 1 次。
> 
> 

**结语**：
用户只需查看这份 **Golden Record**，即可确认需求已从文档转化为上线代码，且每一步（设计、代码、测试、部署）都有可点击、可验证的第三方系统链接（CodeHub/CI）作为铁证。