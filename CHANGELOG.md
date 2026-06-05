# Changelog

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
