# Changelog

## 0.1.1

- Install `meta-flow` into `.agents/skills/meta-flow` so `$meta-flow` can be discovered directly.
- Install support scripts and templates into `.meta-flow/scripts` and `.meta-flow/templates`.
- Update `doctor` to check the discoverable Skill and runtime support files, not only the plugin bundle.
- Keep `.meta-flow/tasks` during uninstall while removing managed support files.

## 0.1.0

- Initial Codex Plugin and npm installer package.
- Added meta-flow Skill, role references, agent templates, templates, scripts, docs, and sample task.
- Added safe install, uninstall, doctor, verify, and print-paths commands.
