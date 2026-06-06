> **一句话总结**：上一版 meta-flow 的根本问题不是少了一个恢复脚本，而是把长程工作流误放在一次性 Skill 注入层；应重构为“持久工作流运行时 + 可恢复状态 + 可选持久指令 + Skill 入口”的架构。

# Meta-Flow Redesign Draft

## 1. 背景和目标

用户观察到：开始工作时指定 `$meta-workflow` 或类似入口后，一轮会话之后系统像是忘记了 meta-flow，没有继续按长程 workflow 执行，也没有启动预期的 subagent。

这不是偶发 bug。上一版设计把 meta-flow 定义成一个 Codex Skill：依赖 `$meta-flow` 显式触发，或依赖 description 隐式匹配。Skill 适合“按需加载的一段能力说明”，但 meta-flow 目标是跨轮次、跨阶段、可暂停、可恢复、有人工 gate 的长程控制流。两者抽象层级不一致。

本方案目标：

- 明确上一版设计的根因缺陷。
- 对照 Codex 官方能力边界和外部开源实践。
- 给出可落地的重构方向。
- 在用户确认前不修改实现代码。

## 2. 当前代码理解

源码仓库当前形态：

- `plugin/skills/meta-flow/SKILL.md`：完整 workflow 说明，frontmatter 名称为 `meta-flow`。
- `plugin/agent-templates/*.toml`：14 个角色模板。
- `plugin/templates/*.json`：状态和报告模板。
- `plugin/scripts/*.py`：任务创建、校验、聚合、状态查看脚本。
- `src/cli/*`：npm installer、doctor、verify、uninstall。
- `docs/*`：分发、架构和使用文档。

legacy 背景文件一开始误放在安装副本中，现已迁到源码仓库：

- `legacy-design/要求.md`
- `legacy-design/分发.md`

这次误放暴露出一个风险：源码、安装副本、用户补充背景资料不能长期分散在不同 root。meta-flow 若要成为可靠工作流，运行时状态必须有单一 source of truth，不能靠“某个目录里有一些文件”隐式推断。

本机 user-scope 安装还有版本不一致问题：

- 源码为 `0.1.2`。
- 已安装 plugin manifest 和 marketplace 仍为 `0.1.1`。
- 已安装模板存在校验失败。

但这只是安装健康问题，不是“跨轮忘记”的根因。

## 3. 外部实践结论

Codex 官方文档对 Skill 的描述是“按任务扩展能力”：Codex 只先看到 name、description 和 path，决定使用时才读取完整 `SKILL.md`；触发方式是显式 `$skill` 或基于 description 的隐式匹配。这个机制适合 reusable workflow 的入口，但不保证跨轮 sticky 状态。

Codex 官方文档也给了更适合持久约束的 surfaces：

- `AGENTS.md`：Codex 启动时读取，适合 durable repo conventions。
- Plugin：适合分发 skill、hooks、MCP、assets 等安装包。
- Hooks：可在 session start、user prompt、stop、compact 等生命周期运行脚本。
- Subagents：不会自动 spawn，官方明确要求用户显式要求 subagents 或 parallel agent work。

OpenHands 的持久化实践更接近长程 workflow：用 conversation id 恢复多 session 工作；持久化内容包含 message history、agent configuration、execution state、tool outputs、workspace context、activated skills 等；目录上区分 `base_state.json` 和 `events/`。

LangGraph 的 durable execution 给出更强的工作流原则：必须有 checkpointer、thread id；人机中断后用同一 thread id 恢复；side effects 和非确定操作要放入 task，避免恢复时重复执行。

Spec Kit 和 BMAD 的共同经验是：不要把长程开发流程放在聊天历史里。它们让每个阶段产出文件化 artifact，例如 spec、plan、tasks、PRD、architecture、stories、sprint status。后续阶段读取前序 artifact，而不是依赖模型记得上一轮说过什么。

## 4. 根因诊断

### 4.1 Skill 被误用为 workflow runtime

Skill 是能力注入和说明书，不是运行时。上一版 `SKILL.md` 写了完整状态机，但没有一个可执行 dispatcher 负责：

- 读取当前 task。
- 判定当前 phase。
- 生成下一步 action。
- 执行或提示执行对应 role。
- 校验 artifact。
- 原子更新状态。
- 跨轮恢复。

所以现在的状态机只存在于 prompt 文本里。模型一旦没有重新加载 Skill，流程就断。

### 4.2 没有 active task 指针和可恢复入口

`new_task.py` 会创建 `.meta-flow/tasks/<task-id>/state.json`，但没有工作区级 `active-task.json` 或 index。后续轮次不知道：

- 当前是否已有 active meta-flow task。
- 应该继续哪个 task。
- 是否正在等待用户确认。
- 下一步是角色执行、校验、repair、还是 human gate。

`status.py` 也要求显式传 task。它不能作为“默认恢复当前 workflow”的入口。

### 4.3 人工 gate 是叙述，不是状态

legacy 设计强调 `USER_PROPOSAL_CONFIRMATION`、`USER_PLAN_CONFIRMATION`、`USER_FINAL_CONFIRMATION`。但当前实现没有 gate artifact，例如：

- gate id
- gate type
- prompt shown to user
- accepted choices
- decision
- decided_at
- resume target phase

因此用户确认只能靠聊天上下文维持。跨轮或跨会话时，gate 状态不可恢复。

### 4.4 subagent 预期和 Codex 机制不匹配

agent TOML 被安装了，但这不等于 Codex 会自动运行它们。官方文档和当前环境都表明：subagents 需要用户明确要求，不能被 workflow 隐式假设。

因此上一版“调用 questioner / reviewer / executor”等描述，在实际运行中只是“主 agent 应该扮演这些角色或手动委派”的说明，而不是可执行编排。

### 4.5 安装器和运行时耦合不足

当前 npm CLI 能安装 plugin、skill、templates、agents、marketplace，但运行时依赖仍散落在：

- npx 临时 CLI。
- 安装后的 Python support scripts。
- Skill 文本。
- Codex 自身是否加载 Skill。
- 当前 cwd。

如果用户通过 `npx ... install` 安装但没有全局安装 `meta-flow`，后续 `meta-flow doctor` 或 `meta-flow status` 未必可用。真正可用的是安装到 `.meta-flow/scripts` 或 `~/.meta-flow/scripts` 的 support scripts。

### 4.6 隐式匹配不适合高仪式长流程

meta-flow 的 description 很宽，容易在“模糊、多步骤、高可靠”任务上隐式触发。但长程 workflow 有明显成本：提问、写 proposal、多 reviewer、确认 gate、拆任务。它不应该靠隐式匹配悄悄启动。

推荐默认关闭隐式 invocation，让用户显式 `$meta-flow` 或通过 persistent mode opt-in。

## 5. 反对理由与风险

1. 反对继续“小修小补”：
   加一个 `active-task.json` 能缓解恢复问题，但不能解决 phase transition、gate、subagent、role execution 都靠模型自觉的问题。会继续在错误抽象上堆补丁。

2. 反对直接引入 LangGraph / Temporal：
   它们能解决 durable execution，但会显著改变项目定位、依赖体积和安装复杂度。legacy 明确偏向 Codex-native、低依赖。当前问题可以先用文件状态机和 support scripts 解决。

3. 反对把 meta-flow 写进全局 AGENTS.md 默认启用：
   这会污染所有任务，让小改动也被长程 workflow 拦截。持久模式必须 opt-in，且 repo scope 默认比 user scope 安全。

4. 反对把所有 role 合并成一个 agent：
   这样能简化实现，但会丢掉原设计真正有价值的边界：proposal、review、adjudication、execution、verification、direction evaluation 分离。

5. 反对默认自动 spawn subagents：
   当前 Codex 机制不支持“未被用户明确允许时自动 spawn”。设计必须允许无 subagent 模式正常运行，subagent 只能作为显式授权后的加速路径。

## 6. 可选方案

### 方案 A：小补丁恢复模式

只加 active task 指针，改 `SKILL.md` 提醒下轮继续。

优点：改动小。

缺点：仍依赖 Skill 被加载，仍无 gate/transition/runtime，不能从根上解决。

结论：不推荐。

### 方案 B：Codex-native 文件运行时

保留低依赖。新增 meta-flow runtime controller，核心状态、事件、gate、resume prompt 都写文件。Skill 变成入口，persistent mode 通过 AGENTS managed block 或 hook opt-in 启用。

优点：符合 Codex-native，低依赖，可分阶段落地，能解释并解决当前问题。

缺点：需要较大重构，尤其是 CLI/support scripts/Skill 文档。

结论：推荐。

### 方案 C：引入 LangGraph 类 runtime

用成熟 durable workflow engine 表达状态机、人机 interrupt、checkpoint。

优点：理论上最完整。

缺点：依赖重，偏离当前开源包定位，用户安装和信任成本高。

结论：除非目标升级为“生产级 agent runtime”，否则暂不推荐。

### 方案 D：LangGraph / Agents SDK Hybrid

把 meta-flow 的 workflow spec 保持为文件化定义，但 runtime 提供两种 backend：

- 默认 backend：Codex-native file controller。
- 可选 backend：LangGraph 或 OpenAI Agents SDK + durable workflow integration。

优点：长期可扩展，便于以后支持服务端运行、trace、durable worker。

缺点：短期会显著扩大设计面，需要同时维护两套 runtime 语义。最容易失败的地方是：Codex-native 用户路径还没跑稳，就先被框架抽象拖复杂。

结论：可以作为后续路线，但不应该是第一版重构目标。

## 6.5 框架对比结论

我对比过 LangGraph 和 OpenAI Agents SDK。结论是：

- 如果 meta-flow 要做成独立 agent 应用，LangGraph 更强。
- 如果 meta-flow 要做成 Codex-native 插件，让用户在 Codex 当前 repo 里自然工作，轻量 file controller 更合适。

LangGraph 的优势非常贴近我们的问题：

- 它有 persistence/checkpointer，能在 graph state 上做 checkpoint。
- 它有 thread id，类似我们要的 active task / persistent cursor。
- 它有 interrupt/resume，非常适合 proposal confirmation、plan confirmation、final confirmation 这些 human gate。
- 它天然有 graph node/edge，可以表达 allowed transitions。

但直接采用 LangGraph 的代价也很明确：

- meta-flow 就不再只是 Codex plugin + Skill + support scripts，而会变成一个 Python/JS agent runtime。
- 用户可能需要运行 LangGraph 应用、配置模型 provider、管理 checkpointer backend，而不是只在 Codex repo 里安装插件。
- Codex custom agents/subagents、Skill progressive disclosure、AGENTS.md persistent block 这些 Codex-native surface 仍要额外桥接。
- artifact 仍然要文件化保存，因为用户要看 proposal、plan、task report；LangGraph checkpoint 本身不能替代可审阅、可 diff 的工作产物。
- 框架状态会绑定执行模型。将来如果要换 Codex surface 或别的 runtime，迁移成本更高。

OpenAI Agents SDK 的定位也类似：它适合应用代码拥有 orchestration、tool execution、approvals、state 的场景。它有 handoffs、guardrails、tracing、sessions，也可以通过 Dapr/Temporal/Restate/DBOS 等集成做 durable long-running workflow。但这已经是“构建 agent 应用”，不是“安装一个 Codex workflow plugin”。

因此我的判断是：

1. 第一版重构做 Codex-native file controller。
2. controller 的 transition table、gate、event log、artifact schema 都按 framework-grade 标准设计。
3. 不把 runtime 语义写死在 prompt 里，也不写死在 LangGraph 里。
4. 等验收案例跑通后，如果需要服务端化或多人协作，再考虑把 same workflow spec 编译/迁移到 LangGraph。

换句话说：我们不是否定 LangGraph，而是先实现 LangGraph 给我们的关键思想，但不要一开始就承担 LangGraph 的运行时依赖和产品形态切换。

## 7. 推荐方案

把 meta-flow 重构为四层：

### 7.1 Distribution Layer

继续使用 plugin + npm installer，但安装器要更清楚地区分：

- source package
- installed runtime assets
- workspace task state
- optional persistent instruction

新增或调整：

- `agents/openai.yaml`，设置 `allow_implicit_invocation: false`。
- `meta-flow install --persistent`，仅 repo scope 默认推荐，给 AGENTS.md 写 managed block。
- `doctor` 检查 runtime controller、active pointer、persistent block、版本一致性。

### 7.2 Runtime Layer

新增一个可安装 support script，例如：

```text
.meta-flow/scripts/controller.py
```

核心命令：

```bash
python3 .meta-flow/scripts/controller.py start "<raw request>"
python3 .meta-flow/scripts/controller.py resume
python3 .meta-flow/scripts/controller.py status --json
python3 .meta-flow/scripts/controller.py advance --task <id> --to <phase> --reason <reason>
python3 .meta-flow/scripts/controller.py gate open --type proposal_confirmation ...
python3 .meta-flow/scripts/controller.py gate decide --gate <id> --decision accept|reject --comment ...
python3 .meta-flow/scripts/controller.py deactivate --task <id>
```

User-scope Skill 可以调用 `~/.meta-flow/scripts/controller.py`，但 task state 默认写入当前 workspace 的 `.meta-flow/tasks`，并用显式 `--workspace-root` 避免 cwd 混乱。

controller 必须同时服务机器和用户，但不能把状态理解负担交给用户。它应该输出两类视图：

- `--format json`：给 AI/自动化读取，包含 `task_id`、`phase`、`status`、`current_milestone_id`、`current_task_id`、`open_gate`、`next_action`、`allowed_user_actions`、`blocked_issues`、`artifact_refs`。
- `--format codex`：给 Codex 主 agent 读取，包含一段明确指令：“你现在要告诉用户当前到了哪一步、为什么停在这里、下一步你会做什么、是否需要用户确认”。

用户不需要知道内部节点。`PROPOSAL_REVIEW`、`TASK_VERIFICATION` 这类 phase 是 runtime 和 AI 的内部语言；AI 对用户应翻译为“方案正在评审”、“我正在验收第 1 个具体任务”等自然语言说明。

### 7.3 State and Artifact Layer

新增工作区级文件：

```text
.meta-flow/
  active-task.json
  task-index.json
  tasks/<task-id>/
    state.json
    events.ndjson
    gates/
      <gate-id>.json
    artifacts/
      raw-request.md
      goal-contract.json
      proposal.md
      ...
    runs/
      <timestamp>-<role>.json
```

原则：

- `state.json` 是当前 snapshot。
- `events.ndjson` 是 append-only history。
- `active-task.json` 是默认恢复入口。
- `gates/*.json` 表示可暂停的人机确认点。
- `runs/*.json` 记录 role run、输入文件、输出文件、验证结果、版本。

### 7.4 Interaction Layer

Skill 不再承载完整编排，只做入口：

1. 如果用户说 `$meta-flow start ...`，运行 controller start。
2. 如果存在 active task，运行 controller resume。
3. 读取 resume prompt，只执行提示中的下一步。
4. 完成一个 artifact 后运行 validate/advance。

Interaction layer 的责任是 AI 主导流程，而不是让用户主导状态机。每次启动、恢复、进入 gate、完成阶段、blocked、done 时，AI 都必须向用户说明：

- 当前处于什么用户可理解的阶段。
- 已经完成了什么。
- 为什么现在停在这里。
- 下一步 AI 会做什么，或需要用户做什么决定。
- 用户可用的自然语言操作，例如“继续”、“接受方案”、“修改目标”、“暂停”。

Persistent mode 在 repo `AGENTS.md` 加 managed block：

```md
<!-- meta-flow:persistent:start -->
When `.meta-flow/active-task.json` exists and the user has not explicitly opted out,
run `python3 .meta-flow/scripts/controller.py resume --format codex` before acting.
Follow the returned next action and do not start a new meta-flow task unless instructed.
<!-- meta-flow:persistent:end -->
```

这比依赖 `$meta-flow` 更可靠，因为 AGENTS.md 是 Codex 启动时持久加载的项目指令。

### 7.5 Flow Enforcement Layer

保证 AI 按 legacy-design 里的流程图推进，不能靠“AI 记得流程图”。必须让 controller 成为流程裁判。

legacy-design 的核心 flow 是：

```text
INTAKE
-> QUESTIONING
-> GOAL_CONTRACT_DRAFTED
-> RESEARCH_AND_PROPOSAL
-> PROPOSAL_REVIEW
-> ADJUDICATION
-> PROPOSAL_REWORK
-> PROPOSAL_SUMMARY
-> USER_PROPOSAL_CONFIRMATION
-> PROPOSAL_ACCEPTED
-> PLANNING
-> USER_PLAN_CONFIRMATION
-> MILESTONE_SELECTED
-> TASK_DECOMPOSITION
-> TASK_EXECUTION
-> TASK_VERIFICATION
-> TASK_REPAIR
-> MILESTONE_COMPLETED
-> DIRECTION_EVALUATION
-> CONTINUE_NEXT_MILESTONE | REPLAN | GOAL_ADJUSTMENT_REQUIRED | FINAL_SUMMARY
-> USER_FINAL_CONFIRMATION
-> DONE
```

并且允许这些回环：

- `PROPOSAL_REVIEW -> ADJUDICATION -> PROPOSAL_REWORK -> PROPOSAL_REVIEW`
- `USER_PROPOSAL_CONFIRMATION -> ADJUDICATION -> QUESTIONING | RESEARCH_AND_PROPOSAL`
- `TASK_VERIFICATION -> TASK_REPAIR -> TASK_EXECUTION -> TASK_VERIFICATION`
- `DIRECTION_EVALUATION -> GOAL_ADJUSTMENT_REQUIRED -> QUESTIONING | RESEARCH_AND_PROPOSAL`
- `DIRECTION_EVALUATION -> REPLAN -> PLANNING | TASK_DECOMPOSITION`

controller 应内置 transition table，而不是让 AI 自由写 `state.phase`：

```text
advance(from, event, artifact_refs, gate_decision) -> to | error
```

每次推进都必须检查：

- 当前 `state.phase` 是否允许该 event。
- 下一 phase 是否在 allowed transitions 中。
- 进入下一 phase 所需 artifact 是否存在且 schema 校验通过。
- 如果当前 phase 是 human gate，必须有 gate decision。
- 如果是 repair/rework/direction loop，不能超过上限。
- 如果 task/milestone 状态不一致，不能继续推进。
- 每次推进必须 append event，再更新 snapshot。

AI 的职责不是决定任意路线，而是：

1. 读取 controller 的 `next_action`。
2. 按 `next_action.role` 执行一个 bounded step。
3. 产出或更新指定 artifact。
4. 调用 validate。
5. 请求 controller advance。
6. 把 controller 返回的新阶段解释给用户。

因此后续实现必须禁止以下做法：

- AI 直接手改 `state.phase`。
- AI 跳过 gate 继续执行。
- AI 在没有 proposal 的情况下进入 review。
- AI 在 verifier revise 后直接进入 next task。
- AI 无视 direction evaluator 的 replan/adjust_goal。
- AI 无限 proposal rework 或 repair。

## 8. 执行步骤

### Phase 1：设计修正和最小 runtime

- 新增 `controller.py`。
- 新增 `active-task.json` 和 `task-index.json` 逻辑。
- 让 `new_task.py` 迁移为 controller start 的薄包装或废弃入口。
- `status.py` 支持不传 task 时读取 active task。
- `resume` 输出稳定的 Codex prompt pack。

### Phase 2：gate 和 transition enforcement

- 新增 gates 目录和 gate schema。
- 增加 `advance` 命令，禁止随意修改 phase。
- 在 proposal、plan、final confirmation 处写 gate artifact。
- 校验 next phase 与 artifact/gate 一致。

### Phase 3：Skill 和 docs 重写

- `SKILL.md` 改为运行时入口，不再假设它自身是 sticky workflow。
- 加 `agents/openai.yaml`，默认禁止隐式触发。
- README 明确：
  - `$meta-flow` 是启动/恢复入口，不是会话级魔法。
  - 跨轮自动恢复需要 `--persistent`。
  - subagents 需要用户明确授权。

### Phase 4：installer 和 doctor

- `install --persistent` 支持安全 patch repo AGENTS.md managed block。
- `doctor` 检查：
  - plugin/skill/support script 版本一致。
  - installed templates 能校验。
  - active task 指针合法。
  - persistent block 是否存在和是否过期。
  - `npx` 安装后的后续命令提示是否准确。

### Phase 5：tests and migration

- 测 `start -> active -> resume`。
- 测 `status` 默认 active task。
- 测 gate open/decide/resume。
- 测 phase transition 非法时失败。
- 测旧 `.meta-flow/tasks/*/state.json` 可迁移。
- 测安装副本版本不一致时 doctor 给出明确修复建议。

## 9. 验证方式

自动验证：

```bash
npm test
npm run verify
node bin/meta-flow.js install --scope repo --target <tmp> --yes
python3 <tmp>/.meta-flow/scripts/controller.py start "sample request"
python3 <tmp>/.meta-flow/scripts/controller.py resume
python3 <tmp>/.meta-flow/scripts/controller.py status --json
```

行为验证：

- 不输入 `$meta-flow`，但 repo 开启 persistent mode 且存在 active task 时，AGENTS 指令应要求先 resume。
- 未开启 persistent mode 时，不应污染普通任务。
- 用户显式 opt out 时，不继续 meta-flow。
- 没有 subagent 授权时，workflow 仍能由主 agent 串行执行。
- 用户明确要求 subagents 时，reviewer 可以并行，但返回必须写入标准 artifact。

## 10. 需要保留的设计资产

上一版不是全错。应保留：

- role 分离。
- concrete task 粒度 executor/verifier。
- adjudicator 独立于 reviewer。
- direction_evaluator。
- proposal / plan / final 三类用户 gate。
- 低依赖、Codex-native、标准库脚本优先。
- 安全、幂等、无 postinstall、无 telemetry 的分发原则。

应重构：

- Skill 从 runtime 降级为入口。
- scripts 从校验辅助升级为 workflow controller。
- state 从单 task snapshot 升级为 workspace-level active pointer + event log + gate state。
- installer 从“复制资源”升级为“安装运行时并可选启用持久恢复”。

## 11. Sources

- OpenAI Codex manual, fetched via official docs helper: `https://developers.openai.com/codex/codex-manual.md`
- OpenHands Persistence: `https://docs.openhands.dev/sdk/guides/convo-persistence`
- LangGraph Durable Execution: `https://docs.langchain.com/oss/python/langgraph/durable-execution`
- LangGraph Human-in-the-loop / Interrupts: `https://docs.langchain.com/oss/python/langgraph/human-in-the-loop`
- GitHub Spec Kit docs: `https://github.github.io/spec-kit/`
- GitHub Spec Kit repository: `https://github.com/github/spec-kit`
- BMAD Method workflow map: `https://github.com/bmad-code-org/BMAD-METHOD/blob/main/docs/reference/workflow-map.md`
- BMAD Method getting started: `https://github.com/bmad-code-org/BMAD-METHOD/blob/main/docs/tutorials/getting-started.md`
