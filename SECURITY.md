# Security Policy

## Reporting Vulnerabilities

Report vulnerabilities through the GitHub Security Advisory flow for `bx-h/meta-flow`, or email the maintainer address that the project owner publishes for security reports.

Do not disclose unresolved vulnerabilities publicly before maintainers have had a reasonable chance to respond.

## Supported Versions

| Version | Supported |
| --- | --- |
| 0.1.x | yes |

## Installer Write Scope

Repo scope writes:

- `<repo>/plugins/meta-flow`
- `<repo>/.agents/skills/meta-flow`
- `<repo>/.meta-flow/scripts`
- `<repo>/.meta-flow/templates`
- `<repo>/.agents/plugins/marketplace.json`
- `<repo>/.codex/agents/*.toml`
- `<repo>/.codex/config.toml`

User scope writes:

- `~/.codex/plugins/meta-flow`
- `~/.agents/skills/meta-flow`
- `~/.meta-flow/scripts`
- `~/.meta-flow/templates`
- `~/.agents/plugins/marketplace.json`
- `~/.codex/agents/*.toml`
- `~/.codex/config.toml`

## What The Installer Does Not Do

- It does not read and upload user source code.
- It does not send telemetry.
- It does not modify the system from `postinstall`.
- It does not silently overwrite unmanaged files.
- It does not download or execute remote scripts.

## Safer Installation

Prefer version pinning:

```bash
npx @bx-h/meta-flow@0.1.2 install --scope repo
```

Preview writes:

```bash
npx @bx-h/meta-flow@latest install --scope repo --dry-run
```

Recommended audit commands:

```bash
npm audit
npm pack --dry-run
meta-flow verify
```

## Implementation Rules

- Keep the package dependency-free unless a dependency has a clear security justification.
- Do not use dynamic `eval`.
- Do not fetch and run remote scripts.
- Do not add `postinstall`.
- Use safe path checks before writes or deletes.
- Limit deletes to meta-flow managed paths.
- Support backups before overwrites.
