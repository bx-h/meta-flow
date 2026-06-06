# Changelog

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

- Add a Codex-native runtime controller with active task state, transition enforcement, gates, and resume packs.
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
