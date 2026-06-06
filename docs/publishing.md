> **一句话总结**：发布前确认 npm scope 和 GitHub 仓库权限，跑完整验证，再通过 GitHub tag 触发 npm 与 GitHub Release 发布。

# Publishing

## Rename The Package

Update `package.json`:

```json
{
  "name": "@bx-h/meta-flow"
}
```

The current planned npm package name is `@bx-h/meta-flow`. Before publishing, confirm that your npm account or organization can publish under the `@bx-h` scope.

Also update README examples, plugin manifest repository URLs, marketplace docs, and agent install marker source URL if the GitHub repository changes.

## Set Up npm Scope

Create the npm organization or use your personal npm scope. For a public scoped package, publish with:

```bash
npm publish --access public
```

## GitHub Actions Release

The release workflow is triggered by tags:

```bash
git tag v0.1.7
git push origin v0.1.7
```

It runs CI, creates an npm pack tarball, computes SHA256, publishes to npm, and creates a GitHub Release.

## npm Provenance

Prefer GitHub Actions trusted publishing. Configure the npm package to trust this repository and workflow.

If trusted publishing is unavailable, create an `NPM_TOKEN` GitHub secret. Do not commit `.npmrc` tokens.

## GitHub Release

Release notes should cite `CHANGELOG.md`. Upload:

- npm package tarball
- SHA256 checksum file

## Version Pinning

Document pinned installs:

```bash
npx @bx-h/meta-flow@0.1.7 install --scope repo
```

## Codex Marketplace Distribution

You can distribute through marketplace metadata:

```bash
codex plugin marketplace add bx-h/meta-flow --ref v0.1.7
```

The npm installer still performs custom-agent installation and validation support, so do not rely on marketplace installation alone unless Codex gains first-class agent-template loading.

## Pre-Publish Checklist

```bash
npm ci
npm test
npm run verify
npm pack --dry-run
```

Inspect the pack output before publishing.
