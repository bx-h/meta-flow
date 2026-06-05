import fs from "node:fs/promises";
import path from "node:path";
import { backupIfExists, copyDirSafe, pathExists, removeDirSafe } from "./fs_safe.js";
import { pluginSource } from "./paths.js";
import { META_FLOW_VERSION } from "./version.js";

async function isMetaFlowPlugin(dir) {
  try {
    const manifest = JSON.parse(await fs.readFile(path.join(dir, ".codex-plugin", "plugin.json"), "utf8"));
    return manifest.name === "meta-flow";
  } catch {
    return false;
  }
}

export async function installPlugin(targets, options = {}) {
  const { dryRun = false, force = false, logger } = options;
  if (await pathExists(targets.pluginTarget)) {
    if (!(await isMetaFlowPlugin(targets.pluginTarget)) && !force) {
      return { installed: false, conflict: targets.pluginTarget };
    }
    if (force) {
      await backupIfExists(targets.pluginTarget, { dryRun, logger });
    }
  }
  await copyDirSafe(pluginSource, targets.pluginTarget, { dryRun, logger });
  return { installed: true, conflict: null };
}

export async function uninstallPlugin(targets, options = {}) {
  if (!(await pathExists(targets.pluginTarget))) {
    return { removed: false, skipped: false };
  }
  if (!(await isMetaFlowPlugin(targets.pluginTarget))) {
    return { removed: false, skipped: true };
  }
  const parent = path.dirname(targets.pluginTarget);
  await removeDirSafe(parent, targets.pluginTarget, options);
  return { removed: true, skipped: false };
}

export async function validatePlugin(root = pluginSource) {
  const manifestPath = path.join(root, ".codex-plugin", "plugin.json");
  const skillPath = path.join(root, "skills", "meta-flow", "SKILL.md");
  const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
  const skill = await fs.readFile(skillPath, "utf8");
  const errors = [];
  if (manifest.name !== "meta-flow") {
    errors.push("plugin manifest name must be meta-flow");
  }
  if (manifest.version !== META_FLOW_VERSION) {
    errors.push(`plugin manifest version must be ${META_FLOW_VERSION}`);
  }
  if (!/^---\n[\s\S]*?name:\s*meta-flow[\s\S]*?---/m.test(skill)) {
    errors.push("SKILL.md frontmatter must contain name: meta-flow");
  }
  return { manifestPath, skillPath, errors };
}
