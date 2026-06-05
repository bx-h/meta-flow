> **一句话总结**：Meta Flow's installer is designed to be explicit, local-only, non-telemetry, non-postinstall, and bounded to known Codex plugin and agent paths.

# Security

## Installer Security Model

The npm package does not change user systems during package installation. Files are written only when the user runs:

```bash
meta-flow install
```

There is no telemetry, remote code execution, or source upload.

## File Boundaries

Repo scope writes only under the selected target path:

- `plugins/meta-flow`
- `.agents/plugins/marketplace.json`
- `.codex/agents`
- `.codex/config.toml`

User scope writes only under `os.homedir()` equivalents:

- `.codex/plugins/meta-flow`
- `.agents/plugins/marketplace.json`
- `.codex/agents`
- `.codex/config.toml`

Delete operations are limited to confirmed meta-flow plugin directories and marked meta-flow agent files.

## Supply Chain Risks

Use version pinning for reproducibility:

```bash
npx @bx-h/meta-flow@0.1.0 install --scope repo
```

Run dry-run before installing:

```bash
npx @bx-h/meta-flow@latest install --scope repo --dry-run
```

Audit package contents:

```bash
npm pack --dry-run
npm audit
meta-flow verify
```

## Maintainer Release Checklist

1. Confirm no `postinstall`.
2. Confirm no `.npmrc` token.
3. Run `npm ci`.
4. Run `npm test`.
5. Run `npm run verify`.
6. Run `npm pack --dry-run`.
7. Inspect packed files.
8. Publish with trusted publishing or `NPM_TOKEN` GitHub secret.
9. Upload tarball and SHA256 checksum to GitHub Release.
