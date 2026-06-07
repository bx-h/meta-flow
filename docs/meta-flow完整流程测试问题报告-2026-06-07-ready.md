> **一句话总结：** 本轮 meta-flow 端到端模拟任务已走到 `DONE`，核心流程可跑通；reviewer 指出的可修问题已修复并补测试，历史运行产物中的不可逆偏差已记录为后续流程约束风险。

# Meta-Flow 完整流程测试问题报告

## 背景

- 交接文档：`/data00/home/huangbaixi/SideProject/meta-flow/docs/meta-flow完整流程测试交接-2026-06-07-ready.md`
- 测试任务：模拟一个 README checker CLI 需求，完整走 meta-flow 的 questioning、proposal、review、adjudication、plan、task execution、verification、repair、direction evaluation、final confirmation。
- runtime task id：`20260607-012134-meta-flow-demo-repo-readme-cli-npm-script-readme`
- runtime task dir：`/home/huangbaixi/.meta-flow/tasks/20260607-012134-meta-flow-demo-repo-readme-cli-npm-script-readme`
- demo repo：`/data00/home/huangbaixi/tmp/meta-flow-e2e-readme-linter`
- 最终状态：`status=done`，`phase=DONE`
- final gate：`20260607-022617-final-confirmation`，作为本轮端到端测试模拟接受。

## 端到端结果

meta-flow 主流程已完整跑通，运行产物使用 by-node layout，最终 artifact validate 通过：

```text
ok=true
artifact_count=35
warnings=[]
errors=[]
```

demo repo 当前 smoke 结果：

```json
{"schemaVersion":1,"tool":"check-readme","target":"README.md","exists":true,"hasTitle":true,"title":"Meta Flow README Linter Demo","titleLine":1,"pass":true,"issues":[]}
```

## 已修复问题

| 编号 | 严重性 | 问题 | 修复 |
| --- | --- | --- | --- |
| `DEMO-001` | High | README checker 对正常校验失败场景返回非零退出码，和 proposal 中“缺 README/缺 H1 是正常 JSON 结果”不一致。 | 在 meta-flow repair loop 中修复 demo checker，使预期校验失败仍输出 JSON 并退出 0。 |
| `ARTIFACT-001` | Medium | 早期 questioner 产物缺少 `task_id` / `raw_user_request`。 | 由对应 role subagent 修复运行产物。 |
| `ARTIFACT-002` | Medium | 早期 executor report 使用了不符合契约的 status 值。 | 由对应 role subagent 修复为契约允许值。 |
| `MF-001` | High | `aggregate-reviews --output <nested path>` 不会创建父目录，by-node 输出路径会失败。 | `aggregate_reviews.py` 写文件前创建 output parent，并新增 nested output 测试。 |
| `MF-002` | High | controller 没有稳定记录当前 milestone/task，repair 计数可能落到 `__unassigned__`，且未记录的 root/legacy `milestone-plan.json` 可能按 mtime 干扰 accepted plan。 | `plan_accepted` / `milestone_selected` 只读取 artifact-index 中 `milestone_plan_created` 记录的计划；`task_selected` 必须有非空 `concrete_task_id`；缺 current task 时 `verification_revise` 直接失败。 |
| `MF-002B` | High | `task_selected` 校验 task id 但未强制 `task-spec.json.milestone_id` 必填，缺 milestone 的 task spec 仍可能进入执行。 | `task_selected` 现在要求 `milestone_id` 非空且等于当前 milestone；补缺 milestone 和错误 milestone 两个负向测试。 |
| `MF-003` | Medium | review aggregate 把结构化 `suggested_changes` / issues 转成 Python 风格字符串，丢失结构和来源。 | `all_*` 字段保持旧契约的 value array，并按 value 去重；新增 `*_by_reviewer` 字段保存 `{reviewer,value}` 来源信息。 |
| `MF-004` | Low | `meta-flow aggregate-reviews --help` 被顶层/runtime 通用 help 拦截，看不到 `--reviews-dir` / `--output` / `--task-id`。 | 调整 CLI 分发顺序，让 `aggregate-reviews` 和 `validate` 先处理自己的 help。 |
| `MF-005` | High | repair spec 可以使用新的 `concrete_task_id`，并用 `repairs_concrete_task_id` 指向原任务；如果按当前 repair id 计数，会绕过原任务最多 2 次 repair 的限制。 | 新增 `current_repair_root_task_id`，`task_selected` 将其设为 `repairs_concrete_task_id || concrete_task_id`；`verification_revise` 按 repair root 计数，并补第三次 repair 超限测试。 |
| `ENV-001` | High | reviewer 发现源码已修，但真实全局 `meta-flow` 和 `/home/huangbaixi/.meta-flow/scripts` fallback 仍是旧代码。 | 用 `npm install -g . --prefix /home/huangbaixi/.npm-global` 更新全局包，并用 `meta-flow install --scope user --force --no-agents --no-plugin` 更新 support scripts。 |
| `ENV-002` | Low | 直接 `npm install -g .` 会尝试写 `/usr/local/node` 并因权限失败。 | 记录为本机 prefix 问题；实际更新使用当前用户 prefix `/home/huangbaixi/.npm-global`。 |

## 历史残留与限制

| 编号 | 严重性 | 现象 | 处理 |
| --- | --- | --- | --- |
| `HIST-001` | High | M1 的 `result_verifier` 曾临时修改 demo repo 的 `README.md` 做场景验证，虽然最后恢复了文件，但这违反了 verifier “不修改 implementation files”的角色边界。 | 历史运行产物不能伪装修掉；已记录为流程问题。M2 改用 executor 收集场景证据、verifier 审核报告的模式。后续可在 execution policy 或 verifier 模板中进一步强调只读验证。 |
| `HIST-002` | Medium | 已完成 runtime `state.json` 中仍保留 `task_repair_attempts.__unassigned__ = 1`，这是修复前 controller 运行时留下的历史状态。 | 不回写历史 state，避免篡改审计轨迹。源码已修复未来任务的计数归属，并补测试防止 `verification_revise` 被 stray `task-spec.json` 重新归类。 |
| `LIMIT-001` | Low | demo repo 不是 git repo，不能用 git diff/status 作为 demo 变更证据。 | 验证依赖 execution report、当前文件清单、SHA-256 和动态命令输出。 |
| `LIMIT-002` | Low | proposal/plan/final gates 是端到端测试中的模拟接受，不是真实业务用户逐步确认。 | 已在 runtime gate comment 和本报告中明示。 |
| `LIMIT-003` | Low | 本轮未 bump package version。 | 当前只是本地测试和用户环境修复；发布前应单独评估版本号、changelog 和 tag。 |

## 代码改动

- `plugin/scripts/aggregate_reviews.py`
  - 创建嵌套 output parent。
  - `all_*` 继续输出去重后的原始 value array。
  - 新增 `*_by_reviewer` 保留 reviewer issue/suggestion 的结构化值和来源。
- `plugin/scripts/controller.py`
  - 增加 current milestone/task 同步。
  - 拆分 first milestone selection 和 next milestone selection。
  - accepted plan 只读取 artifact-index 记录的 milestone plan，避免 root/legacy stray 文件按 mtime 干扰。
  - `task_selected` 要求非空 `concrete_task_id`。
  - `task_selected` 要求非空 `milestone_id`，且必须匹配当前 milestone。
  - repair 计数依赖 `current_repair_root_task_id`，不再被后续 stray/root `task-spec.json` 或新的 repair task id 改写。
- `src/cli/index.js`
  - 只在首个 argv 是 `--help` / `-h` / `--version` 时处理全局参数。
- `src/cli/commands/runtime.js`
  - 让 `validate` / `aggregate-reviews` 优先处理自己的命令级 help。
- `tests/cli/controller.test.js`
  - 用真实状态机路径覆盖 milestone 选择。
  - 覆盖 root stray milestone plan 不会影响 accepted plan。
  - 覆盖缺 `concrete_task_id` 的 task spec 会被拒绝。
  - 覆盖缺 `milestone_id` 和错误 `milestone_id` 的 task spec 会被拒绝。
  - 覆盖 repair attempts 按原始 repair root task 计数，并验证 stray root `task-spec.json` 和新 repair task id 不会污染计数。
  - 覆盖第三次 repair 超出上限会被阻断。
- `tests/cli/runtime.test.js`
  - 覆盖 nested aggregate output。
  - 覆盖结构化 suggested change 在 `all_*` 和 `*_by_reviewer` 中都被保留。
  - 覆盖 `aggregate-reviews --help` 命令级帮助。

## 验证记录

已通过：

```bash
node --test tests/cli/runtime.test.js
node --test tests/cli/controller.test.js
npm test
npm run verify
node bin/meta-flow.js artifacts validate 20260607-012134-meta-flow-demo-repo-readme-cli-npm-script-readme --format json
git diff --check
find /data00/home/huangbaixi/SideProject/meta-flow \( -name __pycache__ -o -name '*.pyc' \) -print
meta-flow aggregate-reviews --help
meta-flow doctor --scope user
```

真实全局命令验证：

```bash
meta-flow aggregate-reviews --reviews-dir <tmp>/reviews --output <tmp>/artifacts/by-node/05-PROPOSAL_REVIEW/done/review-aggregate.json --task-id T-global
```

结果：嵌套 `review-aggregate.json` 成功写入，`overall_mechanical_result=pass`，`reviewers=4`。

重复结构化建议验证：

```text
all_suggested_changes.length=1
suggested_changes_by_reviewer.length=4
```

含义：`all_*` 按 value 去重，`*_by_reviewer` 保留来源。

全局包和 fallback support 脚本均已包含：

```text
args.output.parent.mkdir(parents=True, exist_ok=True)
collect_review_items
recorded_artifact_path(task_dir, "milestone-plan.json"
current_repair_root_task_id
suggested_changes_by_reviewer
```

## Reviewer 轮次

第一轮 reviewer 结论：

- `workflow_artifact_reviewer`：Fail，指出 M1 verifier 修改 README、历史 `__unassigned__`、结构化聚合丢失。
- `code_quality_reviewer`：Fail，指出 milestone selection 语义混用、`verification_revise` stray task-spec 风险、`repairs_concrete_task_id` 语义冲突。
- `cli_practice_reviewer`：Fail，指出真实全局 CLI/support 未更新、命令级 help 被拦截。
- `final_acceptance_reviewer`：Pass，但要求补齐问题报告文档。

第二轮 reviewer 结论：

- `cli_practice_reviewer`：Pass。
- `final_acceptance_reviewer`：Pass。
- `code_quality_reviewer`：Fail，指出 accepted plan 仍可能被 root stray `milestone-plan.json` 干扰，缺 `concrete_task_id` 仍可能导致 `__unassigned__`，以及 `all_*` 字段兼容性问题。
- `workflow_artifact_reviewer`：Fail，指出 repair spec 新 `concrete_task_id` + `repairs_concrete_task_id` 会绕过原任务 repair 上限，且报告未单独记录该问题。

第三轮 reviewer 结论：

- `workflow_artifact_reviewer`：Pass。
- `cli_practice_reviewer`：Pass。
- `final_acceptance_reviewer`：Pass。
- `code_quality_reviewer`：Fail，指出 `task_selected` 未强制要求 `task-spec.json.milestone_id` 必填。

第四轮 reviewer 结论：

- `code_quality_reviewer`：Pass，确认 `task_selected` 已强制 `milestone_id` 非空且匹配当前 milestone，负向测试覆盖缺 `concrete_task_id`、缺 `milestone_id`、错误 `milestone_id`。

当前状态：全部 reviewer 已通过。
