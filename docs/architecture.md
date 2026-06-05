> **一句话总结**：Meta Flow uses a Codex Plugin for workflow assets and an npm CLI for safe materialization of plugin files, marketplace entries, custom agents, and validation tools.

# Architecture

## Plugin Plus Installer

The Codex Plugin is the distribution unit for Skill assets. The npm package is the installer and manager.

This split keeps runtime workflow assets separate from installation mechanics:

- `plugin/` contains the Codex plugin, Skill, templates, scripts, and agent templates.
- `src/cli/` contains install, uninstall, doctor, verify, and print-paths commands.
- `marketplace/` contains an example marketplace entry.
- `examples/` contains the sample task used by source verification.

## Why Agent Templates Need Installation

Codex custom agents are loaded from:

- user scope: `~/.codex/agents/`
- repo scope: `.codex/agents/`

The plugin manifest does not automatically materialize these TOML files. The installer copies `plugin/agent-templates/*.toml` into the target agent directory and adds a marker so uninstall can safely remove only files it owns.

## Plugin Asset Roles

- `plugin/skills/meta-flow/SKILL.md`: workflow entrypoint.
- `plugin/skills/meta-flow/references/`: role, review, adjudication, execution, and direction-evaluation policies.
- `plugin/templates/`: task state and report schemas.
- `plugin/scripts/`: standard-library Python helpers for new tasks, validation, aggregation, and status.
- `plugin/agent-templates/`: source TOML for custom agents.

## Repo Scope Versus User Scope

Repo scope is for one project. It writes to the selected repository and makes the workflow available there.

User scope is for the current user. It writes under the user's home directory and makes the workflow available broadly.

Both scopes install custom agents and ensure Codex `[agents]` configuration exists. Existing `max_threads` and `max_depth` values are not overwritten unless `--force` is used.

## Safety Model

All writes are explicit. `npm install` does not modify Codex. Only `meta-flow install` writes files.

The installer:

- checks paths before deletion
- merges marketplace JSON without dropping other entries
- refuses to overwrite unmanaged agent files without `--force`
- backs up overwritten files when requested or forced
- keeps task data on uninstall
