> **一句话总结**：meta-flow 重构是否成功，不看“模型是否记得”，而看这些用户用法是否都能由持久状态、明确入口、gate artifact 和可恢复 runtime 稳定支撑。

# Meta-Flow Usage And Acceptance Draft

## 1. 目的

这份文档把用户可能的真实用法写成后续重构的验收案例。

它用于回答一个核心问题：新方案是否真正解决“我第一轮指定 meta-flow，后面它忘了”的问题。

我的判断是：方案方向能解决根因，但不能靠口头保证。必须用场景验收。后续代码重构如果不能通过这些案例，就说明方案没有落地。

## 2. 核心承诺

重构后的 meta-flow 必须满足这些承诺：

1. 不依赖聊天历史记忆来维持 workflow。
2. 不依赖 `$meta-flow` 在每一轮都被用户重复提到。
3. 不默认污染普通任务。
4. 长程任务必须有 workspace 级 active task 指针。
5. 每个 workflow 阶段必须能从 artifact 恢复。
6. 人工确认点必须是 gate artifact，而不是聊天里的临时状态。
7. role 执行可以由主 agent 串行完成；subagent 只能作为用户明确授权后的加速路径。
8. 断线、换会话、压缩上下文、从子目录启动，都必须能找到同一个 active task。
9. 安装、卸载、doctor、migration 都必须能解释当前状态，不靠用户猜。
10. 用户不需要知道内部状态机节点；工具告诉 AI 当前节点，AI 负责把节点翻译成用户可理解的阶段、下一步和可选操作。

## 3. 预期交互入口

后续实现可以调整命令名，但至少要支持等价语义。

### Skill 入口

```text
$meta-flow start: 我想重构这个仓库里的鉴权模块，但我不确定从哪里开始
$meta-flow resume
$meta-flow status
$meta-flow stop
```

### 普通语言入口

```text
用 meta-flow 开始这个任务：...
继续当前 meta-flow
查看当前 meta-flow 状态
暂停当前 meta-flow
这次不要用 meta-flow，直接回答
```

### CLI / runtime 入口

```bash
python3 .meta-flow/scripts/controller.py start "<raw request>"
python3 .meta-flow/scripts/controller.py resume
python3 .meta-flow/scripts/controller.py status --json
python3 .meta-flow/scripts/controller.py gate decide --gate <id> --decision accept
python3 .meta-flow/scripts/controller.py resume --format codex
```

### Persistent mode

```bash
meta-flow install --scope repo --persistent
```

Persistent mode 只应写入 repo 级 managed block，例如 `AGENTS.md`，并且必须可卸载、可检查、可禁用。

## 4. 验收状态定义

每个案例的结果分为：

- `PASS`：行为和 artifact 都符合预期。
- `WARN`：功能可继续，但用户需要明确提示或手动处理。
- `FAIL`：workflow 断裂、误触发、状态丢失、越权执行、或无法解释当前状态。

验收时不能只看回复文本。必须同时检查：

- `.meta-flow/active-task.json`
- `.meta-flow/task-index.json`
- `.meta-flow/tasks/<task-id>/state.json`
- `.meta-flow/tasks/<task-id>/events.ndjson`
- `.meta-flow/tasks/<task-id>/gates/*.json`
- `.meta-flow/tasks/<task-id>/artifacts/*`
- doctor/status 输出

## 5. AI 主导流程说明

### S1. AI 每次恢复都说明当前位置

前置：

`.meta-flow/active-task.json` 存在，当前 phase 是任意非 DONE 节点。

用户行为：

```text
继续
```

或：

```text
$meta-flow resume
```

预期：

- AI 先通过 controller 获取当前 task 状态。
- AI 告诉用户当前处于什么用户可理解的阶段，而不是只抛出内部 phase 名。
- AI 说明已经完成了什么、为什么现在停在这里、下一步会做什么。
- 如果需要用户输入，AI 明确给出可选操作。

示例用户可见表述：

```text
当前在“方案确认”阶段。我已经完成目标澄清、方案草稿和多角色评审，现在需要你确认是否接受这个方案。
你可以回复“接受并继续”、“按某个方向修改方案”，或“暂停”。
```

### S2. Tool 输出必须同时适合机器和 AI

用户行为：

```bash
python3 .meta-flow/scripts/controller.py resume --format json
python3 .meta-flow/scripts/controller.py resume --format codex
```

预期：

- JSON 输出包含稳定字段：`task_id`、`phase`、`status`、`current_milestone_id`、`current_task_id`、`open_gate`、`next_action`、`allowed_user_actions`、`blocked_issues`、`artifact_refs`。
- Codex 输出包含面向 AI 的明确指令：告诉用户当前阶段、下一步、是否需要确认。
- 两种输出指向同一个 task 和 phase。

### S3. 用户不需要说出节点名

用户行为：

```text
方案可以，继续
```

当前实际 phase 为 `USER_PROPOSAL_CONFIRMATION`。

预期：

- AI 能根据 open gate 和当前 phase 判断这是 proposal accept。
- AI 不要求用户说 `USER_PROPOSAL_CONFIRMATION accept`。
- gate decision 被正确记录。

### S4. 内部节点名可见但不是必要输入

用户行为：

```text
现在在哪一步？
```

预期：

- AI 可以同时给出用户阶段和内部节点，例如：“用户阶段是方案确认，内部 phase 是 USER_PROPOSAL_CONFIRMATION”。
- 用户不需要理解内部节点也能继续操作。

### S5. 状态错误时 AI 解释问题

前置：

`active-task.json` 指向缺失 task。

用户行为：

```text
继续
```

预期：

- AI 不要求用户自己 debug 文件。
- AI 解释：“我找到了 active task 指针，但对应任务目录不存在。”
- AI 给出可选操作：清理 active 指针、列出现有任务、指定 task id 恢复。

## 6. Flow 推进约束

### T1. AI 不能直接推进 phase

前置：

`state.phase = QUESTIONING`。

AI 尝试直接把 `state.phase` 改成 `PROPOSAL_REVIEW`。

预期：

- 这是失败行为。
- 正确做法是 AI 产出 required artifact 后调用 controller advance。
- controller 拒绝非法 transition，并说明缺少 `goal-contract.json` 和 `proposal.md` 等前置 artifact。

### T2. Controller 内置 allowed transition table

用户行为：

```bash
python3 .meta-flow/scripts/controller.py advance --event proposal_created
```

当前 phase 为 `QUESTIONING`。

预期：

- controller 返回非 0 或 error JSON。
- 错误说明：`proposal_created` 不能从 `QUESTIONING` 触发。
- state snapshot 不变化。
- event log 可以记录 rejected transition，但不能记录为成功推进。

### T3. Artifact prerequisites 阻止跳步

当前 phase 为 `GOAL_CONTRACT_DRAFTED`，但 `goal-contract.json` schema 无效。

用户行为：

```text
继续
```

预期：

- AI 运行 controller resume 后知道当前不能进入 proposal。
- AI 告诉用户：“目标契约文件校验失败，我需要先修复或重新生成目标契约。”
- phase 不推进。

### T4. Gate 阻止自动越过用户确认

当前 phase 为 `USER_PROPOSAL_CONFIRMATION`，proposal gate 未决策。

用户行为：

```text
继续做吧
```

预期：

- AI 不能自动解释为 accept，除非语义明确。
- 如果用户表达不明确，AI 应询问：“你是接受当前方案继续，还是要修改方案？”
- controller 不允许无 gate decision 进入 PLANNING。

### T5. 用户自然语言映射到 gate decision

当前 phase 为 `USER_PROPOSAL_CONFIRMATION`。

用户行为：

```text
这个方案可以，继续下一步
```

预期：

- AI 将自然语言映射为 proposal gate accept。
- controller 记录 gate decision。
- controller 执行 allowed transition 到 `PROPOSAL_ACCEPTED` 或下一明确 phase。
- AI 告诉用户：“方案已确认，接下来进入里程碑规划。”

### T6. Repair loop 上限由 controller 执行

当前 concrete task 已 repair 两次，verifier 再次返回 revise。

预期：

- AI 不能继续第三次 repair。
- controller 标记 task/milestone blocked。
- AI 告诉用户具体阻塞原因和可选决策。

### T7. Proposal rework 上限由 controller 执行

proposal rework 已达到 3 轮，reviewer 仍返回 revise。

预期：

- controller 不允许继续 `PROPOSAL_REWORK -> PROPOSAL_REVIEW`。
- workflow 进入 blocked 或 ask_user。
- AI 向用户解释：“方案已经返工 3 轮仍未收敛，需要你决定降低范围、改变目标或停止。”

### T8. Direction evaluator 路由不可被忽略

direction evaluator 输出 `replan`。

AI 试图继续下一个 milestone。

预期：

- controller 拒绝进入 `CONTINUE_NEXT_MILESTONE`。
- AI 必须进入 `REPLAN`，并向用户说明为什么需要重新规划。

### T9. 每次成功推进都写事件

任一 successful advance。

预期：

- `events.ndjson` 追加一条事件，包含 from_phase、to_phase、event、reason、artifact_refs、actor。
- `state.updated_at` 更新。
- snapshot 和 event log 一致。

### T10. Flow 图作为测试 fixture

预期：

- legacy-design 中的核心状态机要转成 controller transition table。
- tests 应覆盖所有 allowed transitions 和至少一批 disallowed transitions。
- 文档中的 flow、controller transition table、测试 fixture 三者不能漂移。

### T11. Runtime backend 不改变用户用法

前置：

后续如果支持 LangGraph 或其他 backend。

预期：

- 用户入口仍然是 `$meta-flow start/resume/status` 或自然语言继续。
- 用户仍然看到同样的 proposal、plan、task report、gate。
- AI 仍然从 controller 获取当前节点和 next_action。
- backend 只能影响内部执行，不应让用户学习 LangGraph thread id、checkpoint id 或 graph node API。

### T12. Framework-grade 能力必须在 file controller 中体现

预期：

- 即使不用 LangGraph，file controller 也必须具备等价的关键能力：
  - persistent cursor: `active-task.json`
  - checkpoint/snapshot: `state.json`
  - append-only history: `events.ndjson`
  - interrupt/resume: `gates/*.json`
  - allowed transitions: controller transition table
  - human-readable status: `resume --format codex`
- 如果缺少这些能力，不能用“Codex-native”作为降低可靠性的借口。

## 7. 安装与发现

### A1. Repo scope 安装后显式使用

用户行为：

```bash
npx @bx-h/meta-flow@latest install --scope repo
```

然后在该 repo 中输入：

```text
$meta-flow start: 帮我系统性改造错误处理
```

预期：

- repo 下出现 `.agents/skills/meta-flow`、`.meta-flow/scripts`、`.meta-flow/templates`、`.codex/agents`。
- `$meta-flow` 可被发现。
- 新任务写到当前 repo 的 `.meta-flow/tasks`。
- 不写入用户其他 repo。

### A2. User scope 安装后跨 repo 使用

用户行为：

```bash
npx @bx-h/meta-flow@latest install --scope user
```

然后在任一 repo 输入：

```text
$meta-flow start: 帮我规划一个迁移任务
```

预期：

- Skill 和 support script 来自 user scope。
- task state 默认写到当前 workspace 的 `.meta-flow/tasks`，而不是全部写到 `~/.meta-flow/tasks`。
- status/resume 能从当前 workspace 找到 active task。

### A3. npx 安装后没有全局 CLI

用户行为：

```bash
npx @bx-h/meta-flow@latest install --scope repo
```

之后 `meta-flow` 命令不在 PATH。

预期：

- 已安装 support scripts 仍能工作。
- 安装完成提示不能只依赖 `meta-flow doctor`，必须给出可运行替代命令，例如 `npx @bx-h/meta-flow@<version> doctor ...` 或本地 script 路径。
- doctor 能说明 CLI 和 runtime assets 的区别。

### A4. 用户误写 `$meta-workflow`

用户行为：

```text
$meta-workflow start: ...
```

预期：

- 如果不支持 alias，应明确提示：“当前 Skill 名称是 `$meta-flow`”。
- 不应静默开始一个错误 workflow。
- 文档必须统一使用 `$meta-flow`。

### A5. 旧安装版本不一致

前置：

- 源码是 `0.1.2`。
- 已安装 plugin 或 marketplace 是 `0.1.1`。

用户行为：

```bash
meta-flow doctor --scope user
```

预期：

- doctor FAIL 或 WARN，明确指出 plugin、marketplace、templates 哪些版本不一致。
- 给出修复命令。
- 不自动覆盖，除非用户运行 install/force。

### A6. 卸载不删除任务

用户行为：

```bash
meta-flow uninstall --scope repo --yes
```

预期：

- 删除 managed plugin、Skill、agents、marketplace entry。
- 默认保留 `.meta-flow/tasks`。
- 如果 persistent AGENTS block 是 installer 创建的，应移除 managed block。
- 不删除用户手写的 AGENTS 内容。

## 8. 启动与恢复

### B1. 显式启动长程任务

用户行为：

```text
$meta-flow start: 我想改善后端观测性，但不知道从哪里开始
```

预期：

- controller 创建 task id。
- 写入 active task。
- 写入 raw request。
- `state.phase = QUESTIONING`，事件历史保留 `NONE -> INTAKE -> QUESTIONING`。
- 回复用户当前处于 meta-flow，并说明后续可用 `$meta-flow resume` 或 persistent mode 自动恢复。

### B2. 未开启 persistent mode，用户下一轮没提 meta-flow

前置：

- 已启动 active task。
- 未开启 persistent mode。

用户行为：

```text
继续
```

预期：

- 不能把“继续”作为可靠自动恢复的唯一设计。
- 如果模型当前上下文还记得，可以继续，但这不是验收依据。
- 文档和启动提示必须告诉用户：未启用 persistent mode 时，建议用 `$meta-flow resume`。

### B3. 未开启 persistent mode，用户显式 resume

用户行为：

```text
$meta-flow resume
```

预期：

- controller 读取 `.meta-flow/active-task.json`。
- 输出当前 phase、blocked/gate 状态和下一步 action。
- 不新建任务。
- 不重新询问已经完成的步骤。

### B4. 开启 persistent mode，新会话自动恢复

前置：

```bash
meta-flow install --scope repo --persistent
```

并且 `.meta-flow/active-task.json` 存在。

用户行为：

在新 Codex session 中输入：

```text
我们继续
```

预期：

- AGENTS managed block 让 Codex 先运行 resume 或读取 resume prompt。
- 不要求用户再次输入 `$meta-flow`。
- 回复基于 active task 当前 state，而不是基于聊天记忆。

### B5. 从子目录启动

前置：

repo root 有 `.meta-flow/active-task.json`。

用户行为：

从 `src/services/api/` 启动 Codex 并输入：

```text
继续当前 meta-flow
```

预期：

- runtime 能定位 repo root 或 workspace root。
- 读取同一个 active task。
- 不在子目录创建新的 `.meta-flow`。

### B6. 上下文压缩后恢复

前置：

对话很长，发生 compact。

用户行为：

```text
$meta-flow resume
```

预期：

- 仍从文件状态恢复。
- 不依赖 compact summary 是否完整。
- resume 输出包含足够上下文：task id、目标、当前 phase、下一步、等待中的 gate、最近事件。

### B7. 任务完成后不再自动恢复

前置：

`state.status = done`，active task 已 deactivate。

用户行为：

```text
继续
```

预期：

- persistent mode 不应继续已完成任务。
- status 应显示 no active task。
- 如需新任务，要求用户 start。

## 9. 用户确认 Gate

### C1. Blocking question gate

前置：

questioner 判断缺少信息会改变目标。

预期：

- 写入 gate artifact：`type = clarifying_questions`。
- `state.status` 可以保持 active，但 phase 应标记等待用户输入。
- resume 时应重复显示未回答的关键问题。
- 用户回答后 gate 关闭，并写事件。

### C2. 非 blocking 信息缺失

前置：

questioner 发现缺失信息，但可用假设继续。

预期：

- `questioning-report.json` 记录 assumptions。
- 不打开 blocking gate。
- 后续 proposal 必须引用这些假设。

### C3. Proposal confirmation 接受

用户行为：

```text
我接受这个方案，继续
```

预期：

- proposal gate 写入 decision accept。
- phase 从 `USER_PROPOSAL_CONFIRMATION` 进入 `PROPOSAL_ACCEPTED` 或 `PLANNING`。
- event log 记录用户确认。
- 不重新生成 proposal。

### C4. Proposal confirmation 拒绝

用户行为：

```text
我不接受，这个方案太重了，优先最小改动
```

预期：

- proposal gate 写入 decision reject 和用户理由。
- route 进入 adjudicator。
- adjudicator 决定回到 QUESTIONING 或 RESEARCH_AND_PROPOSAL。
- 旧 proposal 不被覆盖，应保留版本或事件。

### C5. Plan confirmation 接受

用户行为：

```text
计划可以，开始第一个 milestone
```

预期：

- plan gate 关闭。
- `current_milestone_id` 设置为 M1。
- 后续进入 task decomposition。

### C6. Final confirmation

用户行为：

```text
最终结果确认
```

预期：

- final gate 关闭。
- `state.status = done`。
- active task deactivated。
- final report 保留。

### C7. Gate 跨会话恢复

前置：

当前停在 proposal confirmation gate。

用户关闭 Codex，之后重新打开并输入：

```text
继续
```

预期：

- persistent mode 恢复到同一个 gate。
- 显示上次 proposal summary 和可选决策。
- 不越过 gate 自动执行。

## 10. 方案、评审和裁决

### D1. Proposal 生成前必须有 goal contract

预期：

- 如果 `goal-contract.json` 缺失或校验失败，不能进入 `RESEARCH_AND_PROPOSAL`。
- resume 应提示修复或重新运行 questioner。

### D2. Reviewer 只评审，不路由

预期：

- reviewer artifact 只能输出 pass/revise/block 和证据。
- 不允许 reviewer 修改 proposal。
- 不允许 reviewer 直接决定下一 phase。

### D3. Aggregator 只机械聚合

预期：

- 任一 block => mechanical block。
- 任一 revise 且无 block => mechanical revise。
- 全 pass => mechanical pass。
- aggregator 不输出最终 route。

### D4. Adjudicator 负责路由

预期：

- adjudication report 包含 decision、rationale、next_phase。
- next_phase 必须由校验脚本验证。
- 当 reviewer 误判时，adjudicator 可以解释并接受。

### D5. Proposal rework 超过上限

前置：

proposal 已 rework 3 次仍不通过。

预期：

- workflow 标记 blocked。
- 写 blocked report 或 adjudication block。
- 向用户请求决策，而不是继续无限循环。

## 11. 执行阶段

### E1. Planner 只产 milestone

预期：

- `milestone-plan.json` 不包含具体代码步骤。
- milestone 有 objective、scope、acceptance_checks、risk、status。
- planner 不生成 task spec。

### E2. Task decomposer 产 concrete task

预期：

- 每个 concrete task 有 allowed_files、forbidden_files、acceptance_checks、dependencies。
- 单个 task 足够小，不能是整个 milestone。
- task-list 校验失败时不能进入 execution。

### E3. Executor 每次只执行一个 concrete task

预期：

- executor 输入明确 task id。
- 只能改 allowed_files。
- 如果需要改 allowed_files 外的文件，必须 block 或请求 replan。
- execution report 记录 changed files 和 evidence。

### E4. Verifier 只验收，不修代码

预期：

- verifier 可以运行测试、lint、typecheck。
- verifier 不修改实现文件。
- pass 时 failed_checks 为空。
- revise/block 时必须给 minimal repair 或 block reason。

### E5. Repair loop

前置：

verifier 返回 revise。

预期：

- repair_attempts +1。
- 回到 executor，只处理 minimal repair。
- 不扩大 task scope。

### E6. Repair 超过上限

前置：

同一 concrete task repair 两次仍失败。

预期：

- task 标记 blocked。
- milestone 暂停。
- route 到 adjudicator 或 ask_user。
- 不继续后续 task。

### E7. 新事实触发 direction evaluation

前置：

verifier 发现新事实，例如原框架不支持目标方案。

预期：

- verification report 设置 `should_trigger_direction_evaluation = true`。
- direction evaluator 运行。
- 决定 continue、replan、adjust_goal、ask_user 或 abort。

### E8. Replan

前置：

direction evaluator 判断目标没变，但计划错误。

预期：

- phase 进入 REPLAN。
- planner 或 task_decomposer 重新生成相关 artifact。
- 旧 plan/task-list 保留版本或事件。

### E9. Adjust goal

前置：

direction evaluator 判断目标需要变化。

预期：

- 生成 contract patch。
- 打开 user confirmation gate。
- 未经用户确认不得修改 goal-contract。

### E10. Milestone 完成

预期：

- 所有 concrete tasks pass。
- milestone status = done。
- direction evaluation 必须运行一次。
- 如果没有下一个 milestone，进入 final summary。

## 12. Subagent 用法

### F1. 用户没有授权 subagents

用户行为：

```text
$meta-flow start: ...
```

但没有提“spawn subagents”。

预期：

- workflow 仍能运行。
- 主 agent 可串行扮演 role 并写 artifact。
- 不以“未启动 subagent”为失败。

### F2. 用户明确要求并行 reviewers

用户行为：

```text
用 meta-flow，并且 reviewers 可以用 subagent 并行
```

预期：

- 可以 spawn product/technical/risk/verification reviewers。
- 每个 subagent 输出标准 reviewer report。
- 主 agent 聚合并交给 adjudicator。
- subagent 中间噪声不污染主线程。

### F3. 禁止 nested subagents

预期：

- executor 不 spawn verifier。
- reviewer 不 spawn 其他 reviewer。
- max_depth 保持 1 或通过工具策略限制。

### F4. Subagent 失败降级

前置：

某个 reviewer subagent 超时或失败。

预期：

- workflow 记录失败。
- 主 agent 可选择串行补跑该 reviewer，或标记 ask_user/block。
- 不因一个 subagent 失败丢失整个 workflow 状态。

## 13. 多任务和切换

### G1. active task 存在时启动新任务

用户行为：

```text
$meta-flow start: 另一个全新任务
```

预期：

- runtime 检测已有 active task。
- 询问用户：切换、新建并暂停旧任务、或取消。
- 不静默覆盖 active-task。

### G2. 列出任务

用户行为：

```text
$meta-flow status
```

预期：

- 显示 active task。
- 显示最近任务列表和状态。
- blocked/done/active 清晰区分。

### G3. 按 task id resume

用户行为：

```text
$meta-flow resume 20260606-xxxx
```

预期：

- 恢复指定 task。
- 如它不是 active task，提示是否切换 active。
- 不误用另一个 task 的 artifact。

### G4. 暂停任务

用户行为：

```text
$meta-flow stop
```

预期：

- active task deactivated 或 status paused。
- persistent mode 下不再自动恢复。
- task artifact 保留。

## 14. Persistent Mode

### H1. 默认不启用 persistent mode

预期：

- 普通 install 不修改 AGENTS.md。
- 未显式 `$meta-flow` 时，不应因为 description 模糊匹配而强行启动长流程。

### H2. Repo persistent 安装

用户行为：

```bash
meta-flow install --scope repo --persistent
```

预期：

- AGENTS.md 出现 managed block。
- block 明确要求有 active task 时先 resume。
- block 明确支持用户 opt out。
- doctor 能检测 block 是否存在。

### H3. 用户显式 opt out

前置：

persistent mode 开启且有 active task。

用户行为：

```text
这轮不要用 meta-flow，直接回答这个问题
```

预期：

- 不 resume。
- 不推进 state。
- 回复可以提示 active task 仍存在。

### H4. Persistent block 可卸载

用户行为：

```bash
meta-flow uninstall --scope repo --yes
```

预期：

- 只移除 managed block。
- 保留 AGENTS.md 其他内容。
- 保留 task data。

### H5. User scope persistent 需要警告

用户行为：

```bash
meta-flow install --scope user --persistent
```

预期：

- 默认应拒绝或强提示风险。
- 因为全局 persistent 会污染所有 repo。
- 如果支持，必须要求额外确认。

## 15. 普通任务不误触发

### I1. 小改动

用户行为：

```text
把 README 里的拼写错误修一下
```

预期：

- 不自动进入 meta-flow。
- 除非用户显式要求 `$meta-flow`。

### I2. 代码解释

用户行为：

```text
解释一下这个函数
```

预期：

- 不进入 meta-flow。

### I3. 没有可执行验收标准的问题

用户行为：

```text
你怎么看这个设计？
```

预期：

- 可以普通回答或建议是否需要 meta-flow。
- 不自动创建 task。

### I4. 已有 active task 但用户问无关问题

前置：

persistent mode 开启。

用户行为：

```text
这段 git output 是什么意思？
```

预期：

- 如果用户未明确继续 meta-flow，系统可提示存在 active task，但不应强行推进 workflow。
- opt-out 语义清晰。

## 16. 错误和异常

### J1. Artifact 缺失

前置：

`state.phase = PROPOSAL_REVIEW`，但 `proposal.md` 不存在。

预期：

- resume 不能继续 review。
- status 报告 artifact 缺失。
- 给出修复路径：回到 proposal 或标记 blocked。

### J2. JSON schema 无效

前置：

`goal-contract.json` 不是合法 JSON。

预期：

- validate 返回非 0。
- resume 显示错误。
- 不推进 phase。

### J3. Support script 缺失

前置：

`.meta-flow/scripts/controller.py` 不存在。

预期：

- doctor FAIL。
- 给出 reinstall 命令。
- Skill 不应假装 workflow 可继续。

### J4. active-task 指向不存在 task

预期：

- status WARN/FAIL。
- 提供清理或选择其他 task 的命令。
- 不创建同名新 task 掩盖问题。

### J5. Event log 损坏

预期：

- state snapshot 仍可读时，status 可降级显示。
- doctor 报告 event log 损坏。
- 不覆盖损坏 log，建议备份/修复。

### J6. 并发启动两个 Codex session

前置：

两个 session 同时 resume 同一 task。

预期：

- runtime 至少通过 lock 文件或 updated_at 检测冲突。
- 后启动的一方提示 task 正在被处理或 state 已变化。
- 不出现两个 phase 同时推进。

## 17. 安全和权限

### K1. 无 postinstall 修改

预期：

- `npm install` 不写 Codex 配置。
- 只有显式 `meta-flow install` 写文件。

### K2. Dry run 不写文件

用户行为：

```bash
meta-flow install --scope repo --dry-run
```

预期：

- 只打印计划。
- 文件系统无变化。

### K3. Unmanaged conflict 不覆盖

前置：

用户已有 `.codex/agents/executor.toml`，且没有 meta-flow marker。

预期：

- install 默认不覆盖。
- doctor 报告 conflict。
- 只有 `--force --backup` 才覆盖。

### K4. Executor 越权修改

前置：

task-spec allowed_files 只允许 `src/a.js`。

executor 尝试修改 `src/b.js`。

预期：

- verifier 或 post-run check 标记失败。
- execution report 必须记录越权。
- workflow 不应 pass。

### K5. 用户要求破坏性操作

用户行为：

```text
删除所有旧数据并继续
```

预期：

- meta-flow 必须进入 risk/adjudication 或 user confirmation。
- 不因 workflow 自动化而跳过安全确认。

## 18. 迁移与兼容

### L1. 旧 `.meta-flow/tasks/<task>/state.json`

前置：

旧版本只有 task state，没有 active-task。

用户行为：

```text
$meta-flow resume
```

预期：

- runtime 检测无 active task。
- 如果只有一个 active/status=active task，提示是否设为 active。
- 如果多个，列出任务让用户选择。

### L2. 旧模板 acceptance_checks 为空

预期：

- doctor 检测 installed templates invalid。
- 给出 reinstall/update 命令。
- 不把旧模板用于新 task。

### L3. 同名 Skill 多份存在

前置：

repo scope 和 user scope 都有 `meta-flow`。

预期：

- doctor 或 status 能提示当前使用的是哪个 Skill path。
- 文档说明优先级和排查方法。
- 不应把 user task 写进错误 repo。

### L4. 从 legacy design 迁移

预期：

- legacy docs 可以保留为参考，但不作为 runtime source of truth。
- 新 docs 明确上一版的运行时缺口。
- 迁移脚本不应把安装副本里的 legacy 文件误认为源码。

## 19. 验收清单

重构完成后至少运行：

```bash
npm test
npm run verify
node bin/meta-flow.js install --scope repo --target <tmp> --yes
node bin/meta-flow.js doctor --scope repo --target <tmp>
python3 <tmp>/.meta-flow/scripts/controller.py start "sample request"
python3 <tmp>/.meta-flow/scripts/controller.py resume
python3 <tmp>/.meta-flow/scripts/controller.py status --json
```

还需要手工模拟：

- 新 session resume。
- persistent mode resume。
- proposal gate accept/reject。
- plan gate accept。
- verifier revise and repair。
- direction evaluator replan。
- user opt out。
- stale install doctor。

## 20. 判定标准

如果实现后仍出现这些情况，则判定方案失败：

- 用户已开启 persistent mode，但新会话不能恢复 active task。
- 用户停在 gate，但 resume 后越过 gate 自动执行。
- 用户没有授权 subagents，workflow 却以“没启动 subagent”为失败。
- 普通小任务被 meta-flow 隐式劫持。
- phase 推进依赖聊天历史而不是 artifact。
- active task 指针丢失后 doctor/status 不能解释。
- repair/review/direction loops 没有上限。
- executor 可以悄悄扩大 scope。

如果以上验收都能通过，才可以说这次重构真正解决了“长程 workflow 被当成一次性 Skill”的问题。
