> **一句话总结**：Meta Flow uses a Codex Plugin for workflow assets and an npm CLI for safe materialization of discoverable Skills, marketplace entries, custom agents, and validation tools.

# Architecture

## Plugin Plus Installer

The Codex Plugin is the distribution unit for Skill assets. The npm package is the installer and manager.

This split keeps runtime workflow assets separate from installation mechanics:

- `plugin/` contains the Codex plugin, Skill, templates, scripts, and agent templates.
- `src/cli/` contains install, uninstall, doctor, verify, runtime controller facade, and print-paths commands.
- `marketplace/` contains an example marketplace entry.
- `examples/` contains the sample task used by source verification.

## Why Agent Templates Need Installation

Codex Skills and custom agents are loaded from:

- skills: `.agents/skills/meta-flow/`
- user agents: `~/.codex/agents/`
- repo agents: `.codex/agents/`

The plugin manifest does not automatically materialize these files for `$meta-flow` and custom-agent discovery. The installer copies `plugin/skills/meta-flow/` into the target `.agents/skills/` directory, copies `plugin/agent-templates/*.toml` into the target agent directory, and adds markers so uninstall can safely remove only files it owns.

## Plugin Asset Roles

- `plugin/skills/meta-flow/SKILL.md`: workflow entrypoint.
- `plugin/skills/meta-flow/references/`: role, review, adjudication, execution, and direction-evaluation policies.
- `plugin/templates/`: task state and report schemas.
- `plugin/scripts/`: standard-library Python helpers for controller routing, new tasks, validation, aggregation, and status.
- `plugin/agent-templates/`: source TOML for custom agents.

During install, support files are also copied to `.meta-flow/scripts` and `.meta-flow/templates` for repo scope, or `~/.meta-flow/scripts` and `~/.meta-flow/templates` for user scope, so the discoverable Skill has a local fallback. The preferred runtime surface is the npm CLI: `meta-flow ...` or the equivalent `metaflow ...` alias.

## Runtime Controller

Meta Flow is a long-running workflow, so the Skill is only the entrypoint. The runtime source of truth is the CLI facade plus `controller.py`, with state rooted at `~/.meta-flow` by default:

- `~/.meta-flow/active-task.json`: the current resumable task pointer.
- `~/.meta-flow/task-index.json`: task list and latest known status.
- `~/.meta-flow/tasks/<task-id>/state.json`: current workflow snapshot.
- `~/.meta-flow/tasks/<task-id>/events.ndjson`: append-only transition history.
- `~/.meta-flow/tasks/<task-id>/artifact-index.json`: node-to-artifact manifest.
- `~/.meta-flow/tasks/<task-id>/artifacts/by-node/<order>-<phase>/<status>/`: machine-readable and human-readable business artifact paths; repeated attempts use numbered subdirectories under the same node/status.
- `~/.meta-flow/tasks/<task-id>/gates/*.json`: human confirmation points.

Codex should ask the controller for `meta-flow resume --format codex` before continuing a meta-flow task. The controller returns the internal phase, user-facing stage, next bounded action, open gate, and allowed user actions. Codex explains that stage to the user and advances only through controller-approved transitions.

Delegation authorization is a task-level gate because tool policy may require explicit user permission before sub-agents/delegation/parallel agent work. Before the first role action, `status_payload()` opens a `delegation_authorization` gate and reports `execution_mode=user_gate`. On accept, the controller records `delegation_authorization.status=approved` in `state.json`; on reject, it moves the task to `BLOCKED`. `advance_task()` also checks this state so a caller cannot skip the gate by writing artifacts and advancing directly.

Role execution is a delegation contract. For every non-user workflow role, `status_payload()` enriches `next_action` with `execution_mode=spawn_agent_required`, `required_agents`, `parallel_allowed`, and `main_agent_may_execute=false`. The main agent may orchestrate, run validators, aggregate reviewer files, and call `advance`, but it must not write role-owned artifacts or emulate role personas locally. If the spawn/subagent surface is unavailable, the correct behavior is to stop and report the blocker.

Open gates override role delegation in `next_action`: while a gate is open, the controller reports `execution_mode=user_gate` and no required agents. New tasks also enforce producer metadata on role-owned artifacts before advancing. This is not cryptographic proof of process, but it turns role ownership into a machine contract: empty local `{}` reports, missing reviewer reports, or aggregates without all four reviewer agents are rejected by the controller/aggregator.
Artifact-producing custom agents are installed with `workspace-write` because they must write their own role artifact. Their templates constrain writes to assigned artifacts; only the executor role is allowed to edit implementation files, and only within the current task spec.
Role-originated `block` transitions also require the current role artifact where the phase has one. This prevents a main agent from bypassing reviewer, adjudicator, verifier, or evaluator ownership by advancing directly to `BLOCKED`.

Task abandonment is distinct from deactivation. `meta-flow abandon [task-id]` records a terminal `task_abandoned` event, marks state as `status=abandoned` and `phase=ABANDONED`, closes open gates as aborted, removes the active resume pointer, updates `task-index.json`, and leaves artifacts in place for audit. `meta-flow deactivate [task-id]` only removes `active-task.json` when it points at that task; it is for context switching, not for changing the task's lifecycle state.

By-node artifact paths are now the machine contract. Validators and role contracts still use stable artifact names, but the controller provides the exact required by-node path for each node/event. `meta-flow artifacts validate` checks that the manifest and by-node files match the events that have occurred after artifact-index adoption. Legacy tasks without `artifact-index.json` or with the earlier `by-node-v1` layout are accepted for migration/inspection instead of being treated as corrupt.

Persistent mode is a Codex-native opt-in. `meta-flow install --persistent` writes a managed block to `AGENTS.md` that tells Codex to run `meta-flow resume --format codex` before acting when a task may be active. This is the durable surface that prevents the workflow from depending on a Skill staying sticky across turns. The default install does not modify `AGENTS.md`; users can still continue manually with `$meta-flow resume`.

## Repo Scope Versus User Scope

Repo scope is for one project. It writes to the selected repository and makes the workflow available there.

User scope is for the current user. It writes under the user's home directory and makes the workflow available broadly.

Both scopes install the discoverable Skill, support scripts/templates, custom agents, and ensure Codex `[agents]` configuration exists. Existing `max_threads` and `max_depth` values are not overwritten unless `--force` is used.

## Safety Model

All writes are explicit. `npm install` does not modify Codex. Only `meta-flow install` writes files.

The installer:

- checks paths before deletion
- merges marketplace JSON without dropping other entries
- refuses to overwrite unmanaged skill, support, plugin, or agent files without `--force`
- backs up overwritten files when requested or forced
- keeps task data on uninstall
