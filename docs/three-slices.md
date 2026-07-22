# CDASE Three Slices

> **Repo 存真相 → API 管协同 → Spec 即交付**
>
> *Context governs execution; APIs coordinate collaboration; code is delayed, validated materialization.*

---

## Slice 1 — Repo as Single Source of Truth

**一句话**  
仓库不是代码仓，而是工程系统本身。

**主张**  
在 CDASE 中，每个 repo 是其精确契约、需求、设计、进度、测试和代码的真相源（SSOT）。Hub Global API Pool 只聚合跨 repo 的 API 发现索引与来源，不覆盖 owner repo 契约；Hub 消息负责可审计协作传输。

**repo 里有什么**

| 传统工具负责的事 | CDASE 落点 |
|---|---|
| 需求契约 | `scenario.md` · `feature.md` · `function.md` |
| 设计 / 决策 | colocated `design.md`（含全部图）· ADR |
| 门禁 / 证据 | colocated `gates.md` |
| 进度 / 所有权 | colocated `progress.md`（可变执行状态 SSOT） |
| 实施范围 | colocated `code-plan.md` |
| 测试管理 | Contract / Feature tests |
| 人员与信任 | `context/members/<8-hex-user-id>.context.md`（active committed records） |
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
CDASE 的协作底座是 API：每个 repo 保存其 API 契约真相，Hub Global API Pool 聚合所有系统的能力及来源，成为跨系统发现权威。人与 Agent、Agent 与 Agent 通过结构化沟通（意图、约束、确认）推进几乎完整的项目协同——发现、规划、复用、演进，都围绕 API 发生。

**协作如何发生**

1. **发现** — Global API Pool 回答“所有系统已有或正在开发什么能力”
2. **去重** — 每个能力必须解析为 REUSE / EVOLVE / CREATE
3. **占位** — CREATE/EVOLVE 在开发前以 `DEVELOPING` 全局登记
4. **对齐** — 候选条目必须回到 owner repo 验证精确契约
5. **发布** — 验收后 `RELEASED`；升级生成新版本，旧版 `SUPERSEDED`
6. **沟通** — User ↔ Agent / Agent ↔ Agent 传递意图与门禁结果
7. **闭环** — 结果回写 repo 和 Global API Pool，协作痕迹可审计

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
在 CDASE 中，结构化 Spec（Scenario / Feature / Function / Design / API / Test）就是 truth。Feature/Function 的验收条件保留在定义文件中，设计及全部图进入 `design.md`，门禁证据进入 `gates.md`，可变执行状态只进入 `progress.md`。代码是延迟生成、可验证的物化结果——同一份 Spec 可生成不同语言、不同运行时的实现，而 Spec 保持稳定。

**Spec 的地位**

| 旧世界 | CDASE |
|---|---|
| Spec → 中间产物 → 最终交付是代码 | Spec → 交付物；代码是 materialization |
| 改代码即改真相 | 改 Spec 才改真相；代码必须同步 |
| 语言绑定实现 | Spec 中立；多语言可派生 |

**生成关系**  
`Definition + Design (truth)` → `gates.md` / tests / `code-plan.md` → `Code (Java | TS | Python | …)`
换语言，不换 Spec；换实现，不换契约。

**对比**  
文档服务开发；CDASE 让开发服务 Spec。

**落地句**  
*Ship the Spec. Code is validated materialization.*
