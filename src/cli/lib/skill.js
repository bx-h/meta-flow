import fs from "node:fs/promises";
import path from "node:path";
import { hasManagedMarker, installManagedDir, uninstallManagedDir } from "./managed_dirs.js";
import { pathExists } from "./fs_safe.js";
import { skillSource } from "./paths.js";

export async function installSkill(targets, options = {}) {
  const result = await installManagedDir(skillSource, targets.skillTarget, options);
  if (result.conflict || options.dryRun) {
    return result;
  }

  const skillPath = path.join(targets.skillTarget, "SKILL.md");
  const text = await fs.readFile(skillPath, "utf8");
  await fs.writeFile(skillPath, materializeSkillText(text, targets), "utf8");
  return result;
}

export async function uninstallSkill(targets, options = {}) {
  return uninstallManagedDir(path.dirname(targets.skillTarget), targets.skillTarget, options);
}

export async function validateInstalledSkill(targets) {
  const skillPath = path.join(targets.skillTarget, "SKILL.md");
  const errors = [];
  if (!(await pathExists(skillPath))) {
    errors.push("discoverable SKILL.md missing");
    return { skillPath, errors };
  }
  if (!(await hasManagedMarker(targets.skillTarget))) {
    errors.push("discoverable skill is not managed by meta-flow installer");
  }
  const skill = await fs.readFile(skillPath, "utf8");
  if (!/^---\n[\s\S]*?name:\s*meta-flow[\s\S]*?---/m.test(skill)) {
    errors.push("discoverable SKILL.md frontmatter invalid");
  }
  if (!skill.includes("meta-flow resume --format codex")) {
    errors.push("discoverable SKILL.md does not use the meta-flow runtime CLI");
  }
  if (!skill.includes("controller.py --root ~/.meta-flow resume --format codex")) {
    errors.push("discoverable SKILL.md does not include the local controller fallback");
  }
  if (!skill.includes("validate_goal_contract.py")) {
    errors.push("discoverable SKILL.md does not include local validation fallback");
  }
  if (!skill.includes("aggregate_reviews.py")) {
    errors.push("discoverable SKILL.md does not include local review aggregation fallback");
  }
  return { skillPath, errors };
}

function materializeSkillText(text, targets) {
  const supportRoot = shellPath(targets.supportTarget);
  return text
    .replaceAll(".meta-flow/scripts/", `${supportRoot}/scripts/`)
    .replaceAll(".meta-flow/templates/", `${supportRoot}/templates/`);
}

function shellPath(filePath) {
  if (/^[A-Za-z0-9_./-]+$/.test(filePath)) {
    return filePath;
  }
  return `'${filePath.replaceAll("'", "'\\''")}'`;
}
