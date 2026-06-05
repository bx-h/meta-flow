import fs from "node:fs/promises";
import { backupIfExists, pathExists, writeTextSafe } from "./fs_safe.js";

const DEFAULT_AGENTS_CONFIG = "[agents]\nmax_threads = 6\nmax_depth = 1\n";

function sectionBounds(lines, sectionName) {
  const header = `[${sectionName}]`;
  const start = lines.findIndex((line) => line.trim() === header);
  if (start < 0) {
    return null;
  }
  let end = lines.length;
  for (let index = start + 1; index < lines.length; index += 1) {
    if (/^\s*\[[^\]]+\]\s*$/.test(lines[index])) {
      end = index;
      break;
    }
  }
  return { start, end };
}

function setOrInsert(lines, bounds, key, value) {
  const pattern = new RegExp(`^\\s*${key}\\s*=`);
  for (let index = bounds.start + 1; index < bounds.end; index += 1) {
    if (pattern.test(lines[index])) {
      lines[index] = `${key} = ${value}`;
      return { changed: true, existed: true };
    }
  }
  lines.splice(bounds.end, 0, `${key} = ${value}`);
  bounds.end += 1;
  return { changed: true, existed: false };
}

export async function patchCodexConfig(filePath, { force = false, dryRun = false, backup = false, logger } = {}) {
  if (!(await pathExists(filePath))) {
    await writeTextSafe(filePath, DEFAULT_AGENTS_CONFIG, { dryRun, logger });
    return { changed: true, warnings: [] };
  }

  const content = await fs.readFile(filePath, "utf8");
  const lines = content.split(/\r?\n/);
  const warnings = [];
  let changed = false;
  let bounds = sectionBounds(lines, "agents");

  if (!bounds) {
    if (lines.at(-1) !== "") {
      lines.push("");
    }
    lines.push("[agents]", "max_threads = 6", "max_depth = 1");
    changed = true;
  } else {
    const section = lines.slice(bounds.start + 1, bounds.end).join("\n");
    if (/^\s*max_threads\s*=/m.test(section)) {
      if (force) {
        setOrInsert(lines, bounds, "max_threads", "6");
        changed = true;
      } else {
        warnings.push("config already contains [agents].max_threads; leaving it unchanged");
      }
    } else {
      setOrInsert(lines, bounds, "max_threads", "6");
      changed = true;
    }

    bounds = sectionBounds(lines, "agents");
    const refreshed = lines.slice(bounds.start + 1, bounds.end).join("\n");
    if (/^\s*max_depth\s*=/m.test(refreshed)) {
      if (force) {
        setOrInsert(lines, bounds, "max_depth", "1");
        changed = true;
      } else {
        warnings.push("config already contains [agents].max_depth; leaving it unchanged");
      }
    } else {
      setOrInsert(lines, bounds, "max_depth", "1");
      changed = true;
    }
  }

  if (changed) {
    if (force || backup) {
      await backupIfExists(filePath, { dryRun, logger });
    }
    await writeTextSafe(filePath, `${lines.join("\n").replace(/\n*$/, "")}\n`, { dryRun, logger });
  }

  return { changed, warnings };
}

export async function inspectCodexConfig(filePath) {
  if (!(await pathExists(filePath))) {
    return { exists: false, hasAgents: false, hasMaxThreads: false, hasMaxDepth: false };
  }
  const content = await fs.readFile(filePath, "utf8");
  const lines = content.split(/\r?\n/);
  const bounds = sectionBounds(lines, "agents");
  const section = bounds ? lines.slice(bounds.start + 1, bounds.end).join("\n") : "";
  return {
    exists: true,
    hasAgents: Boolean(bounds),
    hasMaxThreads: /^\s*max_threads\s*=/m.test(section),
    hasMaxDepth: /^\s*max_depth\s*=/m.test(section)
  };
}
