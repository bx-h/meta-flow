import path from "node:path";
import { hasManagedMarker, installManagedDir, uninstallManagedDir } from "./managed_dirs.js";
import { pathExists } from "./fs_safe.js";
import { scriptsSource, templatesSource } from "./paths.js";

export async function installSupportFiles(targets, options = {}) {
  const scripts = await installManagedDir(scriptsSource, targets.scriptsTarget, options);
  const templates = await installManagedDir(templatesSource, targets.templatesTarget, options);
  return { scripts, templates };
}

export async function uninstallSupportFiles(targets, options = {}) {
  const scripts = await uninstallManagedDir(targets.supportTarget, targets.scriptsTarget, options);
  const templates = await uninstallManagedDir(targets.supportTarget, targets.templatesTarget, options);
  return { scripts, templates };
}

export async function validateSupportFiles(targets) {
  const required = [
    path.join(targets.scriptsTarget, "new_task.py"),
    path.join(targets.scriptsTarget, "validate_goal_contract.py"),
    path.join(targets.templatesTarget, "state.json"),
    path.join(targets.templatesTarget, "goal-contract.json")
  ];
  const errors = [];
  for (const filePath of required) {
    if (!(await pathExists(filePath))) {
      errors.push(`missing ${filePath}`);
    }
  }
  if (!(await hasManagedMarker(targets.scriptsTarget))) {
    errors.push("scripts directory is not managed by meta-flow installer");
  }
  if (!(await hasManagedMarker(targets.templatesTarget))) {
    errors.push("templates directory is not managed by meta-flow installer");
  }
  return { errors };
}
