> **一句话总结：** `meta-flow@0.1.10` 已经把长程流程控制收敛到 CLI controller，下一轮完整测试要验证 AI 不靠记忆推进、不本地扮演角色，而是按 controller 指令在显式授权后 spawn 对应角色 Agent，并把所有产物写入 `~/.meta-flow/tasks/<task-id>/artifacts/by-node/...`。

# Meta-Flow 完整流程测试交接

本文档交接给下一个窗口的 AI，用于从头测试 `meta-flow` 的真实运行流程、中间产物和角色边界。

## 背景

用户最初的问题是：把 `$meta-workflow` 或 `$meta-flow` 当成 Skill 触发后，一轮会话后 AI 会忘记正在走长程 workflow。根因判断是：Skill 更像一次性的能力注入，适合触发说明和工具，但不天然保证跨轮、跨阶段的状态推进。因此我们把设计重心改成：

- 由 CLI controller 持久化和驱动状态。
- AI 每轮先问 controller 当前节点、开放 gate、下一步动作。
- AI 只做 controller 允许的下一步，不靠聊天记忆跳节点。
- 角色工作必须交给独立 spawned Agent，主 Agent 只负责编排、校验、推进状态。

## 当前版本状态

仓库路径：

```bash
/data00/home/huangbaixi/SideProject/meta-flow
```

当前 Git 状态：

- 分支：`main`
- 远端：`origin/main`
- 最新提交：`e7ef71f fix: require delegation authorization`
- npm 包：`@bx-h/meta-flow@0.1.10`
- Git tag：`v0.1.10`
- 本地 CLI：
  - `meta-flow version` 输出 `0.1.10`
  - `metaflow version` 输出 `0.1.10`

当前仓库有一个无关未跟踪文件：

```bash
docs/实时节点展示方案-2026-06-06-draft.md
```

测试或提交时不要误动它，除非用户明确要求。

## 已完成的关键改动

### 1. 默认状态根目录固定到用户目录

运行时任务默认写到：

```bash
~/.meta-flow/tasks/<task-id>/
```

不要默认在业务仓库创建 `.meta-flow`。只有显式传 `--root <path>` 做测试、迁移或用户指定 alternate root 时，才应使用其他位置。

### 2. CLI 已收敛为简单命令

优先使用：

```bash
meta-flow <command>
metaflow <command>
```

不要让 AI 每次临时找脚本路径。脚本 fallback 只用于 CLI 不可用时：

```bash
python3 /home/huangbaixi/.meta-flow/scripts/controller.py --root ~/.meta-flow <command>
```

### 3. `__pycache__` 问题已处理

验证脚本不应再在项目目录下产生 `plugin/scripts/__pycache__` 这类副产物。测试结束要检查：

```bash
find /data00/home/huangbaixi/SideProject/meta-flow -name __pycache__ -o -name '*.pyc'
```

预期没有新增缓存副产物。

### 4. 产物目录统一为 by-node

机器契约和人类阅读都以此为准：

```bash
~/.meta-flow/tasks/<task-id>/artifacts/by-node/<order>-<PHASE>/<status>/...
```

不要再维护一份 `tasks/` 下的重复产物作为合同来源。文件名本身是机器契约，不要随意改成编号文件名；编号体现在 by-node 目录层级上。

### 5. QUESTIONING 阶段倾向停下来问用户

如果 `questioning-report.json` 里有任何有意义的 `clarifying_questions`，或 `can_continue_without_user_answer=false`，controller 应要求打开 `clarifying_questions` gate，AI 必须停下来问用户，不能用自己的假设直接跳过。

只有在以下条件同时满足时才可以继续：

- `clarifying_questions=[]`
- `can_continue_without_user_answer=true`
- 剩余低影响假设已经写入 `assumptions_if_user_does_not_answer`

### 6. 子 Agent 授权问题已变成显式 gate

工具层有更高优先级约束：只有用户明确要求 sub-agent/delegation/parallel agent work 时，AI 才能 spawn Agent。

因此 `0.1.10` 新增 `delegation_authorization` gate：

- `$meta-flow` 或 `meta-flow start/resume` 本身不等于授权 spawn。
- 新任务首次需要角色 Agent 时，controller 会先打开 `delegation_authorization` gate。
- 用户显式 accept 后，该任务后续 controller 列出的角色 Agent 都视为已授权。
- 用户 reject/abort/pause/revise 时，主 Agent 不能本地扮演角色，workflow 会进入阻塞或等待状态。

这是为了同时满足 meta-flow 设计和工具平台约束。

## 当前核心契约

### Controller 是唯一状态源

每轮行动前必须运行：

```bash
meta-flow resume --format codex
```

或针对特定任务：

```bash
meta-flow status <task-id> --format json
```

AI 必须根据输出里的 `phase`、`open_gate`、`next_action`、`required_agents` 决定下一步。不要靠聊天记忆判断“应该到哪个节点”。

### Open gate 优先级最高

只要有 open gate：

- AI 应告诉用户当前到了哪个用户确认点。
- AI 应请求用户决定。
- AI 不应继续写角色产物。
- AI 不应 spawn 后续角色 Agent。

### `spawn_agent_required` 是硬约束

当 controller 输出：

```json
{
  "next_action": {
    "execution_mode": "spawn_agent_required",
    "required_agents": ["questioner"]
  }
}
```

主 Agent 必须 spawn 对应 custom Agent。不能自己扮演 `questioner`、`researcher_proposer`、`reviewer`、`adjudicator`、`planner`、`executor`、`verifier` 等角色。

如果当前工具面无法 spawn，正确行为是停下来告诉用户受限，而不是本地模拟。

### 角色产物必须有 producer provenance

JSON 产物必须包含：

```json
{
  "producer": {
    "agent_name": "<role>",
    "execution_mode": "spawned_agent"
  }
}
```

Markdown 角色产物必须以 frontmatter 开头：

```yaml
---
producer_agent: <role>
execution_mode: spawned_agent
---
```

这不是加分项，是 controller 校验和 workflow 边界的一部分。

### 四个 reviewer 必须独立

Proposal review 阶段必须有且只有四类 reviewer：

- `product_reviewer`
- `technical_reviewer`
- `risk_reviewer`
- `verification_reviewer`

每个 reviewer 都必须是 spawned Agent 产物。主 Agent 不能自己 review、自己聚合、自己裁决。主 Agent 可以运行机械聚合命令，但不能伪造 reviewer 结论。

### Adjudicator 也必须独立

review 聚合后必须 spawn `adjudicator`。主 Agent 不能自己做裁决。`adjudication-report.json` 也必须带 spawned producer metadata。

## 常用命令

版本检查：

```bash
meta-flow version
metaflow version
```

健康检查：

```bash
meta-flow doctor --scope user
```

启动新任务：

```bash
meta-flow start "<raw request>" --format codex
```

恢复当前 active task：

```bash
meta-flow resume --format codex
```

查看状态：

```bash
meta-flow status <task-id> --format json
```

决定 gate：

```bash
meta-flow gate decide <task-id> --gate <gate-id> --decision accept --comment "Allow spawned role agents." --format json
```

放弃任务：

```bash
meta-flow abandon <task-id> --reason "<why>"
```

只清 active 指针、不改变任务状态：

```bash
meta-flow deactivate
```

校验 goal contract：

```bash
meta-flow validate goal-contract <path>
```

校验 adjudication：

```bash
meta-flow validate adjudication <path>
```

校验 milestone plan：

```bash
meta-flow validate milestone-plan <path>
```

校验 task list：

```bash
meta-flow validate task-list <path>
```

校验 task verification：

```bash
meta-flow validate task-verification <path>
```

聚合四类 reviewer 报告：

```bash
meta-flow aggregate-reviews --reviews-dir <dir> --output <path>
```

校验 artifact 布局：

```bash
meta-flow artifacts validate <task-id> --format json
```

运行项目测试：

```bash
npm test
npm run verify
git diff --check
```

## 建议的新窗口测试方式

### 测试前准备

1. 进入仓库：

   ```bash
   cd /data00/home/huangbaixi/SideProject/meta-flow
   ```

2. 确认版本：

   ```bash
   meta-flow version
   metaflow version
   meta-flow doctor --scope user
   ```

3. 确认 runtime 任务：

   ```bash
   ls -la ~/.meta-flow/tasks
   meta-flow resume --format codex
   ```

4. 如果有旧 active task，不要直接删除；除非用户明确要求清理，否则用：

   ```bash
   meta-flow abandon <task-id> --reason "reset before end-to-end test"
   ```

### 用户需要给 AI 的显式授权文本

由于工具约束，新窗口里建议用户明确说一次：

```text
我授权这个 meta-flow 测试任务使用 sub-agents/delegation/parallel agent work；当 controller 要求 spawn 某个角色 Agent 时，你可以按要求启动对应子 Agent。
```

即使用户说了这句话，controller 仍应记录 `delegation_authorization` gate 的 accept 决策，不能跳过状态机。

## 推荐模拟需求

### 场景 A：小型代码任务 happy path

用于完整走 proposal、review、adjudication、planning、execution、verification、final confirmation。

```text
请用 meta-flow 在一个临时 demo repo 里实现一个 README 检查 CLI：目标是提供一个 npm script，可以检查 README.md 是否存在、是否包含标题，并输出 JSON 报告。要求先明确目标和验收标准，再设计方案、评审、拆任务、实现、验证。
```

建议 demo repo 放在：

```bash
/tmp/meta-flow-e2e-readme-linter
```

或：

```bash
/data00/home/huangbaixi/tmp/meta-flow-e2e-readme-linter
```

不要在 `SideProject/meta-flow` 自身里实现这个模拟业务需求，避免污染工具仓库。

### 场景 B：QUESTIONING 必须停下来问

用于验证 clarifying gate。

```text
请用 meta-flow 帮我改造一个现有工具的发布流程，但我还没确定目标用户、发布渠道、兼容策略和验收标准。你需要先问清楚关键问题，不要直接做方案。
```

预期：

- `questioner` 产出 `questioning-report.json`，里面有 `clarifying_questions`。
- controller 打开 `clarifying_questions` gate。
- 主 Agent 停下来把问题交给用户。
- 主 Agent 不能自行假设并推进到 proposal。

### 场景 C：四 reviewer 和 adjudicator 边界

用于验证不能自己 review、自己裁决。

```text
请用 meta-flow 为一个小型 CLI 改动写方案，并严格走完整 proposal review。每个 reviewer 必须独立判断，adjudicator 必须独立裁决。
```

预期：

- 四个 reviewer 都是 spawned Agent。
- 每份 reviewer artifact 都有 `producer.agent_name` 和 `execution_mode=spawned_agent`。
- 少一个 reviewer、重复 reviewer、或主 Agent 写 reviewer，都应导致聚合或 controller 推进失败。
- `adjudicator` 单独 spawn，不由主 Agent 裁决。

### 场景 D：TASK_REPAIR 回路

用于验证执行后的修复路径。

可以让 executor 故意漏掉一个验收点，或设计一个可控失败测试。

预期：

- `result_verifier` 返回 `revise`。
- controller 进入 `TASK_REPAIR`。
- spawn `task_decomposer` 根据 verifier 的 minimal repair instructions 更新或重选一个 `task-spec.json`。
- 再 spawn `executor` 执行。
- 最多修复 2 轮，超过应阻塞并问用户。

### 场景 E：abandon/deactivate 语义

用于验证用户中途不想做时的行为。

预期：

- `meta-flow abandon <task-id>`：任务状态变为 abandoned，active resume 不再继续该任务，artifact 保留可审计。
- `meta-flow deactivate`：只清 active 指针，不改变任务状态，适合切换上下文，不等于放弃。

## 完整流程验收清单

测试通过应至少满足以下条件：

- AI 每轮都先通过 `meta-flow resume/status` 获取当前节点。
- AI 会用自然语言告诉用户当前处于哪个用户可理解阶段。
- 第一次需要角色 Agent 前出现 `delegation_authorization` gate。
- 未接受 delegation gate 前，直接 `advance goal_contract_drafted` 会失败。
- 接受 delegation gate 后，`next_action.execution_mode=spawn_agent_required` 并列出所需角色。
- `QUESTIONING` 中只要有关键问题，就打开 `clarifying_questions` gate 并停下来问用户。
- 主 Agent 不写 `questioning-report.json`、`goal-contract.json`、`proposal.md`、reviewer reports、`adjudication-report.json`、`milestone-plan.json`、`task-list.json`、`task-spec.json`、`task-verification.json` 等角色产物。
- 所有角色产物都包含 spawned producer metadata。
- Proposal review 阶段四个 reviewer 完整、独立、角色名正确。
- Adjudicator 独立裁决，主 Agent 不替代裁决。
- Open gate 存在时，controller 输出应压过 spawn 要求，AI 停下来等用户。
- 所有 artifact 在 `~/.meta-flow/tasks/<task-id>/artifacts/by-node/...` 下。
- 没有业务仓库内随机生成 `.meta-flow`。
- 没有新增 `__pycache__` 或 `.pyc`。
- `meta-flow artifacts validate <task-id> --format json` 通过。
- 项目内 `npm test`、`npm run verify`、`git diff --check` 通过。

## 需要特别盯住的失败模式

1. AI 口头说“我来扮演 reviewer/adjudicator”，但没有 spawn 对应 Agent。
2. AI 看到 `spawn_agent_required` 后，因为工具限制就自行完成角色产物。
3. AI 把 `$meta-flow` 误认为已经永久注入 workflow，不再调用 `resume/status`。
4. AI 在 QUESTIONING 里把关键问题标成非阻塞，然后靠假设继续推进。
5. AI 在 gate open 时继续写文件或推进节点。
6. AI 把 artifact 写到业务仓库 `.meta-flow` 或旧的重复目录。
7. AI 为了让校验通过手写 producer metadata，但实际没有 spawn Agent。

第 7 点需要注意：当前 producer metadata 是运行时机器契约，不是密码学证明。真实是否 spawn，只能结合工具调用日志或新窗口执行记录确认。因此完整测试时要同时检查：

- controller/artifact metadata
- 新窗口的实际 subagent 工具调用记录
- reviewer/subagent 的独立输出内容是否有真实独立判断

## 给下个窗口 AI 的执行原则

1. 先读本交接文档，再读 `meta-flow` Skill：

   ```bash
   sed -n '1,220p' /home/huangbaixi/.agents/skills/meta-flow/SKILL.md
   ```

2. 不要直接改 `meta-flow` 仓库代码，除非测试发现缺陷并且用户同意修复。
3. 测试业务需求放到临时 demo repo，不要污染工具仓库。
4. 每轮行动前运行 controller，并把当前阶段说给用户。
5. controller 要求 gate，就先问用户。
6. controller 要求 spawn，就 spawn 对应角色 Agent；不能本地扮演。
7. 每个 role artifact 写完后先验证，再 `advance`。
8. reviewer 和 adjudicator 必须独立。
9. 遇到 controller reject，不要绕过状态机，先解释 blocker。
10. 测试完成后提交一份测试报告，包含任务 id、关键 artifact 路径、每个节点状态、每个 spawned Agent 产物、验证命令和结果。

## 最后已知判断

当前实现仍建议保持轻量 Codex 集成，而不是引入 LangGraph 一类外部 orchestrator。原因是本项目的核心约束不是通用图执行能力，而是让 AI 开发助手在本地开发环境中按 controller、gate、artifact contract 和 subagent 角色边界工作。引入框架会增加部署和心智成本，暂时不能解决工具层显式授权、Skill 一次性注入、主 Agent 自行扮演角色这些关键问题。
