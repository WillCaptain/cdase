# CDASE Three Slices

> **Repo 存真相 → API 管协同 → Spec 即交付**
>
> *Context governs execution; APIs coordinate collaboration; code is delayed, validated materialization.*

---

## Slice 1 — Repo as Single Source of Truth

**一句话**  
仓库不是代码仓，而是工程系统本身。

**主张**  
在 CDASE 中，repo 是唯一真相源（SSOT）。代码、文档、进度、人员、沟通全部落在同一个可版本化的仓库里——而不是散落在 Jira、Confluence、Notion、Slack、测试平台等多套在线工具中。

**repo 里有什么**

| 传统工具负责的事 | CDASE 落点 |
|---|---|
| 需求 / 进度 | Scenario · Feature · Stage gates |
| 设计 / 决策 | Design · ADR |
| 测试管理 | Contract / Feature tests |
| 人员与信任 | `users.context.md` |
| 协同沟通 | Hub 消息（可审计、可追溯） |
| 实现 | Source code（实现物，非推理源） |

**对比**  
多工具：真相分裂，同步靠人。  
CDASE：真相只有一份，Git 即历史，文档权威于代码。

**落地句**  
*Open the repo. Everything that matters is already there.*

---

## Slice 2 — API Is the Collaboration Base

**一句话**  
协同不靠工单流转，靠 API 契约与 Agent/User 对话完成。

**主张**  
CDASE 的协作底座是 API：能力地图、契约边界、跨人/跨 Agent 的对接面。人与 Agent、Agent 与 Agent 通过结构化沟通（意图、约束、确认）推进几乎完整的项目协同——发现、规划、复用、演进，都围绕 API 发生。

**协作如何发生**

1. **发现** — API Index 回答“系统已有什么能力”
2. **对齐** — 新需求先对契约，再谈实现
3. **分工** — Feature / Function 挂在 API 边界上，避免暗改
4. **沟通** — User ↔ Agent / Agent ↔ Agent 传递意图与门禁结果
5. **闭环** — 结果回写 repo，协作痕迹可审计

**对比**  
传统：看板 + 会议 + 口头对齐。  
CDASE：API 是公共语言；对话是执行通道；repo 是落账本。

**落地句**  
*APIs coordinate collaboration; agents execute the conversation.*

---

## Slice 3 — Spec as Deliverable

**一句话**  
Spec 不是过程草稿，而是交付物本身。

**主张**  
在 CDASE 中，结构化 Spec（Scenario / Feature / Function / API / Test）就是 truth。代码是延迟生成、可验证的物化结果——同一份 Spec 可生成不同语言、不同运行时的实现，而 Spec 保持稳定。

**Spec 的地位**

| 旧世界 | CDASE |
|---|---|
| Spec → 中间产物 → 最终交付是代码 | Spec → 交付物；代码是 materialization |
| 改代码即改真相 | 改 Spec 才改真相；代码必须同步 |
| 语言绑定实现 | Spec 中立；多语言可派生 |

**生成关系**  
`Spec (truth)` → gate / test / plan → `Code (Java | TS | Python | …)`  
换语言，不换 Spec；换实现，不换契约。

**对比**  
文档服务开发；CDASE 让开发服务 Spec。

**落地句**  
*Ship the Spec. Code is validated materialization.*
