import fs from "node:fs/promises";
import path from "node:path";
import { backupIfExists, copyDirSafe, pathExists, removeDirSafe } from "./fs_safe.js";

export const MANAGED_MARKER = ".meta-flow-managed.json";

export async function hasManagedMarker(dir) {
  try {
    const marker = JSON.parse(await fs.readFile(path.join(dir, MANAGED_MARKER), "utf8"));
    return marker.installedBy === "meta-flow";
  } catch {
    return false;
  }
}

export async function installManagedDir(source, target, options = {}) {
  const { dryRun = false, force = false, backup = false, logger } = options;
  if (await pathExists(target)) {
    if (!(await hasManagedMarker(target)) && !force) {
      return { installed: false, conflict: target };
    }
    if (force || backup) {
      await backupIfExists(target, { dryRun, logger });
    }
  }

  await copyDirSafe(source, target, { dryRun, logger });
  await writeManagedMarker(target, { dryRun, logger });
  return { installed: true, conflict: null };
}

export async function uninstallManagedDir(parent, target, options = {}) {
  if (!(await pathExists(target))) {
    return { removed: false, skipped: false };
  }
  if (!(await hasManagedMarker(target))) {
    return { removed: false, skipped: true };
  }
  await removeDirSafe(parent, target, options);
  return { removed: true, skipped: false };
}

async function writeManagedMarker(target, { dryRun = false, logger } = {}) {
  const markerPath = path.join(target, MANAGED_MARKER);
  const content = {
    installedBy: "meta-flow",
    source: "https://github.com/bx-h/meta-flow"
  };
  if (dryRun) {
    logger?.info(`DRY-RUN write ${markerPath}`);
    return;
  }
  await fs.mkdir(target, { recursive: true });
  await fs.writeFile(markerPath, `${JSON.stringify(content, null, 2)}\n`, "utf8");
}
