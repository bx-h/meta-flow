import fs from "node:fs/promises";
import path from "node:path";
import {
  AGENT_HEADER,
  backupIfExists,
  hasMetaFlowMarker,
  pathExists,
  removeFileSafe,
  writeTextSafe
} from "./fs_safe.js";
import { agentTemplatesSource } from "./paths.js";

export const AGENT_FILES = [
  "questioner.toml",
  "researcher-proposer.toml",
  "product-reviewer.toml",
  "technical-reviewer.toml",
  "risk-reviewer.toml",
  "verification-reviewer.toml",
  "adjudicator.toml",
  "proposal-summarizer.toml",
  "planner.toml",
  "direction-evaluator.toml",
  "task-decomposer.toml",
  "executor.toml",
  "result-verifier.toml",
  "final-summarizer.toml"
];

export async function installAgents(targets, options = {}) {
  const { dryRun = false, force = false, logger } = options;
  const installed = [];
  const conflicts = [];

  for (const fileName of AGENT_FILES) {
    const source = path.join(agentTemplatesSource, fileName);
    const target = path.join(targets.agentsTarget, fileName);
    const sourceText = await fs.readFile(source, "utf8");
    const targetExists = await pathExists(target);
    if (targetExists && !(await hasMetaFlowMarker(target))) {
      if (!force) {
        conflicts.push(target);
        continue;
      }
      await backupIfExists(target, { dryRun, logger });
    }
    await writeTextSafe(target, `${AGENT_HEADER}${sourceText.replace(/^# Installed by meta-flow\.[\s\S]*?developer_instructions/m, "developer_instructions")}`, { dryRun, logger });
    installed.push(target);
  }

  return { installed, conflicts };
}

export async function uninstallAgents(targets, options = {}) {
  const removed = [];
  const skipped = [];
  for (const fileName of AGENT_FILES) {
    const target = path.join(targets.agentsTarget, fileName);
    if (!(await pathExists(target))) {
      continue;
    }
    if (!(await hasMetaFlowMarker(target))) {
      skipped.push(target);
      continue;
    }
    await removeFileSafe(targets.agentsTarget, target, options);
    removed.push(target);
  }
  return { removed, skipped };
}

export async function validateAgentTemplate(filePath) {
  const text = await fs.readFile(filePath, "utf8");
  const missing = [];
  for (const key of ["name", "description", "developer_instructions"]) {
    if (!new RegExp(`^\\s*${key}\\s*=`, "m").test(text)) {
      missing.push(key);
    }
  }
  return { filePath, missing };
}

export async function validateAgentTemplates(root = agentTemplatesSource) {
  const results = [];
  for (const fileName of AGENT_FILES) {
    results.push(await validateAgentTemplate(path.join(root, fileName)));
  }
  return results;
}
