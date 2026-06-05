import fs from "node:fs/promises";
import path from "node:path";

export const META_FLOW_MARKER = "# Installed by meta-flow.";
export const AGENT_HEADER = `${META_FLOW_MARKER}
# Source: https://github.com/bx-h/meta-flow
# Do not edit unless you know what you are doing.
`;

export async function pathExists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

export function ensureInside(parent, child) {
  const resolvedParent = path.resolve(parent);
  const resolvedChild = path.resolve(child);
  const relative = path.relative(resolvedParent, resolvedChild);
  if (relative === "" || (!relative.startsWith("..") && !path.isAbsolute(relative))) {
    return resolvedChild;
  }
  throw new Error(`Unsafe path outside ${resolvedParent}: ${resolvedChild}`);
}

export async function readJsonOrDefault(filePath, defaultValue) {
  if (!(await pathExists(filePath))) {
    return structuredClone(defaultValue);
  }
  try {
    return JSON.parse(await fs.readFile(filePath, "utf8"));
  } catch (error) {
    throw new Error(`Invalid JSON at ${filePath}: ${error.message}`);
  }
}

export async function writeJsonPretty(filePath, value, { dryRun = false, logger } = {}) {
  if (dryRun) {
    logger?.info(`DRY-RUN write JSON ${filePath}`);
    return;
  }
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

export function backupPath(filePath, timestamp = timestampForBackup()) {
  return `${filePath}.bak.${timestamp}`;
}

export function timestampForBackup(date = new Date()) {
  return date.toISOString().replace(/[-:]/g, "").replace(/\..+$/, "Z");
}

export async function backupIfExists(filePath, { dryRun = false, logger } = {}) {
  if (!(await pathExists(filePath))) {
    return null;
  }
  const backup = backupPath(filePath);
  if (dryRun) {
    logger?.info(`DRY-RUN backup ${filePath} -> ${backup}`);
    return backup;
  }
  await copyPath(filePath, backup);
  return backup;
}

export async function hasMetaFlowMarker(filePath) {
  if (!(await pathExists(filePath))) {
    return false;
  }
  const head = await fs.readFile(filePath, "utf8");
  return head.slice(0, 512).includes(META_FLOW_MARKER);
}

export async function copyDirSafe(src, dest, { dryRun = false, logger } = {}) {
  if (dryRun) {
    logger?.info(`DRY-RUN copy directory ${src} -> ${dest}`);
    return;
  }
  await fs.mkdir(dest, { recursive: true });
  const entries = await fs.readdir(src, { withFileTypes: true });
  for (const entry of entries) {
    const from = path.join(src, entry.name);
    const to = path.join(dest, entry.name);
    if (entry.isDirectory()) {
      await copyDirSafe(from, to, { dryRun, logger });
    } else if (entry.isFile()) {
      await fs.mkdir(path.dirname(to), { recursive: true });
      await fs.copyFile(from, to);
    }
  }
}

export async function copyPath(src, dest) {
  const stat = await fs.stat(src);
  if (stat.isDirectory()) {
    await fs.mkdir(dest, { recursive: true });
    const entries = await fs.readdir(src, { withFileTypes: true });
    for (const entry of entries) {
      await copyPath(path.join(src, entry.name), path.join(dest, entry.name));
    }
    return;
  }
  await fs.mkdir(path.dirname(dest), { recursive: true });
  await fs.copyFile(src, dest);
}

export async function removeDirSafe(parent, target, { dryRun = false, logger } = {}) {
  const safeTarget = ensureInside(parent, target);
  if (!(await pathExists(safeTarget))) {
    return;
  }
  if (dryRun) {
    logger?.info(`DRY-RUN remove directory ${safeTarget}`);
    return;
  }
  await fs.rm(safeTarget, { recursive: true, force: true });
}

export async function removeFileSafe(parent, target, { dryRun = false, logger } = {}) {
  const safeTarget = ensureInside(parent, target);
  if (!(await pathExists(safeTarget))) {
    return;
  }
  if (dryRun) {
    logger?.info(`DRY-RUN remove file ${safeTarget}`);
    return;
  }
  await fs.rm(safeTarget, { force: true });
}

export async function writeTextSafe(filePath, content, { dryRun = false, logger } = {}) {
  if (dryRun) {
    logger?.info(`DRY-RUN write ${filePath}`);
    return;
  }
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, content, "utf8");
}
