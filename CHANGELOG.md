# Changelog

## 0.1.14

- Pass controller subcommand help through the CLI wrapper so commands like `meta-flow gate decide --help` show their real arguments.
- Expand `meta-flow gate --help` with common open/decide forms, including the accepted `--decision` values.

## 0.1.13

- Strengthen the questioner role with decision-tree questioning, repo-first fact discovery, question dependencies, and recommended answers for clarifying questions.
- Extend the questioning report template with optional decision-tree metadata and richer clarifying-question fields.

## 0.1.12

- Rename the public project title and descriptions to Meta Flow instead of a tool-specific Codex-branded title.
- Reframe Codex wording as the current integration and distribution path rather than the project identity.
- Update package, plugin, README, architecture, and legacy distribution wording to avoid tool-specific branding.

## 0.1.11

- Harden milestone selection so accepted plans read the recorded `milestone_plan_created` artifact instead of newer stray root/legacy files.
- Track `current_milestone_id`, `current_task_id`, and `current_repair_root_task_id` through controller transitions, including repair specs that use a new concrete task id while pointing back to the original task.
- Require selected task specs to include a matching `milestone_id` and non-empty `concrete_task_id`, preventing unassigned repair counters and cross-milestone task drift.
- Make `aggregate-reviews` create nested output directories and preserve structured review items while keeping the legacy `all_*` value-array contract.
- Let `meta-flow aggregate-reviews --help` show command-specific options instead of the generic runtime help.
- Add regression coverage for accepted-plan stray files, task-selection validation, repair loop limits, structured review aggregation, and command-specific help.

## 0.1.10

- Add a task-level `delegation_authorization` user gate before spawned role work, so user authorization for sub-agents/delegation/parallel agent work is explicit and recorded in task state.
- Block direct `advance` attempts for role events until delegation authorization is accepted, preventing prompt-only delegation rules from being bypassed.
- Block the task when delegation authorization is rejected instead of allowing the main agent to emulate workflow roles locally.
- Update Skill, persistent AGENTS guidance, docs, and tests for the delegation authorization gate.

## 0.1.9

- Make role delegation an explicit runtime contract: controller resume packs now mark role phases as `spawn_agent_required` and list required custom agents.
- Tighten Skill and persistent instructions so the main agent must not locally emulate meta-flow roles or write role-owned artifacts.
- Require producer metadata on role-owned artifacts and require review aggregates to contain all four expected reviewer agents.
- Change artifact-producing role agent templates to `workspace-write` with narrow write-scope instructions, so spawned roles can produce their own artifacts without main-agent copying.
- Align `TASK_REPAIR` with the `task_decomposer` artifact contract and require role artifacts for role-originated `block` transitions.
- Add tests for reviewer/adjudicator delegation metadata and installed persistent delegation guidance.

## 0.1.8

- Add `meta-flow abandon` / `metaflow abandon` to mark a task as abandoned, close active resume, and retain artifacts for audit.
- Clarify that `deactivate` only clears the active-task pointer without changing task state.

## 0.1.7

- Add `meta-flow version` / `metaflow version` as explicit version subcommands while keeping `--version`.

## 0.1.6

- Require a `clarifying_questions` gate before `goal_contract_drafted` when `questioning-report.json` still contains meaningful questions or cannot safely continue without the user.
- Bias the questioner instructions toward asking users about scope, acceptance, risk, UX, dependency, or implementation-direction uncertainty instead of silently assuming.
- Keep parallel proposal review allowed while tightening only the QUESTIONING-stage clarification boundary.

## 0.1.5

- Default runtime task state to `~/.meta-flow` so task products do not depend on the current repository directory.
- Add `meta-flow` / `metaflow` runtime commands for start, resume, status, advance, gates, artifact validation, artifact validators, and reviewer aggregation.
- Make by-node artifact paths the machine contract for new tasks, removing duplicate canonical business artifacts while preserving legacy lookup support.
- Disable Python bytecode generation for helper scripts and CLI Python invocations.

## 0.1.4

- Add artifact manifest tracking with stable canonical paths and readable by-node views.
- Add `controller.py artifacts validate` for manifest, canonical artifact, by-node display, and gate snapshot checks.
- Require explicit questioning and task-spec artifacts before advancing their workflow nodes.
- Cover artifact layout, legacy migration, gate status validation, and repeated repair-loop artifacts in controller tests.

## 0.1.3

- Add a runtime controller for the Codex integration with active task state, transition enforcement, gates, and resume packs.
- Add opt-in persistent `AGENTS.md` resume instructions.
- Require explicit workflow nodes and accepted confirmation gates for proposal, plan, final, and goal-adjustment decisions.
- Add controller tests and update install, doctor, uninstall, docs, and support wrappers.

## 0.1.2

- Make installed JSON templates pass their matching validation scripts.
- Add template validation to `verify` and `doctor`.
- Propagate command return codes through the CLI entrypoint.
- Tighten `doctor` checks for marketplace, plugin version, support scripts, and CLI-visible failures.
- Make the release workflow skip npm publish when the tag version already exists.

## 0.1.1

- Install `meta-flow` into `.agents/skills/meta-flow` so `$meta-flow` can be discovered directly.
- Install support scripts and templates into `.meta-flow/scripts` and `.meta-flow/templates`.
- Update `doctor` to check the discoverable Skill and runtime support files, not only the plugin bundle.
- Keep `.meta-flow/tasks` during uninstall while removing managed support files.

## 0.1.0

- Initial Codex Plugin and npm installer package.
- Added meta-flow Skill, role references, agent templates, templates, scripts, docs, and sample task.
- Added safe install, uninstall, doctor, verify, and print-paths commands.
