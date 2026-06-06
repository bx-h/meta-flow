> **一句话总结**：Meta Flow uses a Codex Plugin for workflow assets and an npm CLI for safe materialization of discoverable Skills, marketplace entries, custom agents, and validation tools.

# Architecture

## Plugin Plus Installer

The Codex Plugin is the distribution unit for Skill assets. The npm package is the installer and manager.

This split keeps runtime workflow assets separate from installation mechanics:

- `plugin/` contains the Codex plugin, Skill, templates, scripts, and agent templates.
- `src/cli/` contains install, uninstall, doctor, verify, and print-paths commands.
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

During install, runtime support files are also copied to `.meta-flow/scripts` and `.meta-flow/templates` so the discoverable Skill can call local validation helpers.

## Runtime Controller

Meta Flow is a long-running workflow, so the Skill is only the entrypoint. The runtime source of truth is `controller.py` plus workspace state files:

- `.meta-flow/active-task.json`: the current resumable task pointer.
- `.meta-flow/task-index.json`: task list and latest known status.
- `.meta-flow/tasks/<task-id>/state.json`: current workflow snapshot.
- `.meta-flow/tasks/<task-id>/events.ndjson`: append-only transition history.
- `.meta-flow/tasks/<task-id>/artifact-index.json`: node-to-artifact manifest.
- `.meta-flow/tasks/<task-id>/artifacts/<name>`: canonical machine-readable artifact paths.
- `.meta-flow/tasks/<task-id>/artifacts/by-node/<order>-<phase>/<status>/`: human-readable node artifact view; repeated attempts use numbered subdirectories under the same node/status.
- `.meta-flow/tasks/<task-id>/gates/*.json`: human confirmation points.

Codex should ask the controller for `resume --format codex` before continuing a meta-flow task. The controller returns the internal phase, user-facing stage, next bounded action, open gate, and allowed user actions. Codex explains that stage to the user and advances only through controller-approved transitions.

Canonical artifact filenames remain stable because validators and role contracts use them as machine contracts. The by-node directory is an indexed view for humans and diagnostics; `controller.py artifacts validate` checks that the manifest and view match the events that have occurred after artifact-index adoption. Legacy tasks without `artifact-index.json` are reported as legacy instead of being treated as corrupt.

Persistent mode is a Codex-native opt-in. `meta-flow install --persistent` writes a managed block to `AGENTS.md` that tells Codex to run `controller.py resume --format codex` whenever `.meta-flow/active-task.json` exists. This is the durable surface that prevents the workflow from depending on a Skill staying sticky across turns. The default install does not modify `AGENTS.md`; users can still continue manually with `$meta-flow resume`.

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
