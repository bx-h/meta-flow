import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { backupIfExists, pathExists, removeFileSafe } from "./fs_safe.js";

export const PERSISTENT_START = "<!-- meta-flow:persistent:start -->";
export const PERSISTENT_END = "<!-- meta-flow:persistent:end -->";

export function buildPersistentBlock(targets) {
  const fallback = `python3 ${shellPath(controllerPathForAgents(targets))} --root ${shellPath(runtimeRootForAgents())} resume --format codex`;
  const command = `meta-flow resume --format codex || ${fallback}`;
  return `${PERSISTENT_START}
When a meta-flow task may be active and the user has not explicitly opted out of meta-flow, run:

\`\`\`bash
${command}
\`\`\`

Use the returned META-FLOW RESUME PACK as the workflow source of truth before acting.
Tell the user the current user-facing stage, then perform only the bounded next action.
When the resume pack says \`spawn_agent_required\`, spawn the listed custom agent(s). The main agent must not locally emulate meta-flow roles or write their role-owned artifacts.
If spawning required agents is unavailable or rejected, stop and tell the user instead of continuing locally.
Do not start a new meta-flow task, skip phases, or edit ~/.meta-flow/tasks/*/state.json directly.
If the controller reports no active task, is missing, or returns an error, continue normally and mention the blocker only if it affects the user's request.
${PERSISTENT_END}
`;
}

export async function installPersistentBlock(targets, options = {}) {
  const { dryRun = false, backup = false, logger } = options;
  const filePath = targets.agentsMdTarget;
  const existing = await readTextIfExists(filePath);
  const next = upsertPersistentBlock(existing, buildPersistentBlock(targets));

  if (existing === next) {
    return { installed: false, changed: false, target: filePath };
  }
  if (backup) {
    await backupIfExists(filePath, { dryRun, logger });
  }
  if (dryRun) {
    logger?.info(`DRY-RUN write ${filePath}`);
    return { installed: true, changed: true, target: filePath };
  }
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, next, "utf8");
  return { installed: true, changed: true, target: filePath };
}

export async function uninstallPersistentBlock(targets, options = {}) {
  const { dryRun = false, logger } = options;
  const filePath = targets.agentsMdTarget;
  const existing = await readTextIfExists(filePath);
  if (!existing) {
    return { removed: false, skipped: false, target: filePath };
  }
  const result = removePersistentBlock(existing);
  if (result.error) {
    return { removed: false, skipped: true, target: filePath, error: result.error };
  }
  if (!result.removed) {
    return { removed: false, skipped: false, target: filePath };
  }
  if (!result.content.trim()) {
    await removeFileSafe(path.dirname(filePath), filePath, { dryRun, logger });
    return { removed: true, skipped: false, target: filePath };
  }
  if (dryRun) {
    logger?.info(`DRY-RUN write ${filePath}`);
    return { removed: true, skipped: false, target: filePath };
  }
  await fs.writeFile(filePath, result.content, "utf8");
  return { removed: true, skipped: false, target: filePath };
}

export async function inspectPersistentBlock(targets) {
  const filePath = targets.agentsMdTarget;
  if (!(await pathExists(filePath))) {
    return { target: filePath, exists: false, enabled: false, valid: true, errors: [] };
  }
  const text = await fs.readFile(filePath, "utf8");
  const range = persistentRange(text);
  if (range.error) {
    return { target: filePath, exists: true, enabled: false, valid: false, errors: [range.error] };
  }
  if (!range.exists) {
    return { target: filePath, exists: true, enabled: false, valid: true, errors: [] };
  }
  const block = text.slice(range.start, range.end);
  const errors = [];
  if (!block.includes("meta-flow resume --format codex") || !block.includes("resume --format codex")) {
    errors.push("persistent block does not call meta-flow resume --format codex");
  }
  if (!block.includes("META-FLOW RESUME PACK")) {
    errors.push("persistent block does not instruct Codex to use the resume pack");
  }
  if (!block.includes("spawn_agent_required")) {
    errors.push("persistent block does not enforce spawned role agents");
  }
  return { target: filePath, exists: true, enabled: true, valid: errors.length === 0, errors };
}

export function upsertPersistentBlock(text, block) {
  const range = persistentRange(text);
  if (range.error) {
    throw new Error(range.error);
  }
  if (range.exists) {
    return `${text.slice(0, range.start)}${block.trimEnd()}${text.slice(range.end)}`;
  }
  const trimmed = text.trimEnd();
  return trimmed ? `${trimmed}\n\n${block}` : block;
}

export function removePersistentBlock(text) {
  const range = persistentRange(text);
  if (range.error) {
    return { removed: false, content: text, error: range.error };
  }
  if (!range.exists) {
    return { removed: false, content: text };
  }
  const before = text.slice(0, range.start).trimEnd();
  const after = text.slice(range.end).trimStart();
  const content = before && after ? `${before}\n\n${after}` : `${before}${after}`;
  return { removed: true, content: content ? `${content.trimEnd()}\n` : "" };
}

function persistentRange(text) {
  const start = text.indexOf(PERSISTENT_START);
  const endMarker = text.indexOf(PERSISTENT_END);
  if (start === -1 && endMarker === -1) {
    return { exists: false };
  }
  if (start === -1 || endMarker === -1 || endMarker < start) {
    return { exists: false, error: "AGENTS.md contains an incomplete meta-flow persistent block" };
  }
  return {
    exists: true,
    start,
    end: endMarker + PERSISTENT_END.length
  };
}

async function readTextIfExists(filePath) {
  if (!(await pathExists(filePath))) {
    return "";
  }
  return fs.readFile(filePath, "utf8");
}

function controllerPathForAgents(targets) {
  if (targets.scope === "user") {
    return path.join(targets.scriptsTarget, "controller.py");
  }
  return ".meta-flow/scripts/controller.py";
}

function runtimeRootForAgents() {
  return path.join(os.homedir(), ".meta-flow");
}

function shellPath(filePath) {
  if (/^[A-Za-z0-9_./-]+$/.test(filePath)) {
    return filePath;
  }
  return `'${filePath.replaceAll("'", "'\\''")}'`;
}
