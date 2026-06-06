> **一句话总结**：Meta Flow 只在用户显式执行安装命令时写入 Codex plugin、marketplace、custom agents 和 agents 配置，并提供 dry-run、doctor 与可回滚卸载路径。

# Installation

## Repo Scope

Install into the current repository:

```bash
npx @bx-h/meta-flow@latest install --scope repo
```

Install into a specific repository:

```bash
npx @bx-h/meta-flow@latest install --scope repo --target /path/to/repo
```

Repo scope writes:

- `<repo>/plugins/meta-flow`
- `<repo>/.agents/skills/meta-flow`
- `<repo>/.meta-flow/scripts`
- `<repo>/.meta-flow/templates`
- `<repo>/.agents/plugins/marketplace.json`
- `<repo>/.codex/agents/*.toml`
- `<repo>/.codex/config.toml`

Add automatic active-task resume for the repository:

```bash
npx @bx-h/meta-flow@latest install --scope repo --persistent
```

Persistent mode appends a managed block to `<repo>/AGENTS.md`. The default install does not change `AGENTS.md`.

## User Scope

Install for the current user:

```bash
npx @bx-h/meta-flow@latest install --scope user
```

User scope writes:

- `~/.codex/plugins/meta-flow`
- `~/.agents/skills/meta-flow`
- `~/.meta-flow/scripts`
- `~/.meta-flow/templates`
- `~/.agents/plugins/marketplace.json`
- `~/.codex/agents/*.toml`
- `~/.codex/config.toml`

User-scope persistent mode is supported but broad:

```bash
npx @bx-h/meta-flow@latest install --scope user --persistent
```

It writes a managed block to `~/AGENTS.md`, which can affect every workspace under the home directory. Prefer repo-scope persistent mode unless that broad behavior is intentional.

## Dry Run

Preview writes without modifying files:

```bash
meta-flow install --scope repo --dry-run
```

## Force And Backup

The installer does not overwrite unmanaged custom agent files. Use `--force` only after inspecting conflicts:

```bash
meta-flow install --scope repo --force --backup
```

When overwriting, backups use `.bak.<timestamp>` suffixes.

## Doctor

Check installed state:

```bash
meta-flow doctor --scope repo
meta-flow doctor --scope user
```

Doctor reports PASS, WARN, or FAIL with repair suggestions. It does not modify files.

## Uninstall

Preview:

```bash
meta-flow uninstall --scope repo --dry-run
```

Remove managed files:

```bash
meta-flow uninstall --scope repo --yes
meta-flow uninstall --scope user --yes
```

Uninstall removes:

- the managed plugin directory
- the managed discoverable Skill directory
- managed support scripts and templates
- the meta-flow marketplace entry
- agent TOML files with the meta-flow marker
- the meta-flow managed block in `AGENTS.md`, if present

It does not delete task data by default. Runtime task data defaults to `~/.meta-flow/tasks`.

## Common Issues

If Codex does not show the Skill, restart Codex after installing.

If `doctor` reports missing agents, re-run install. Existing unmanaged agent files may require manual review or `--force`.

If `doctor` reports incomplete `[agents]` config, inspect `.codex/config.toml`; install does not overwrite existing `max_threads` or `max_depth` unless `--force` is used.
