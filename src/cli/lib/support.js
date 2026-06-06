import path from "node:path";
import { hasManagedMarker, installManagedDir, uninstallManagedDir } from "./managed_dirs.js";
import { pathExists } from "./fs_safe.js";
import { scriptsSource, templatesSource } from "./paths.js";

export const REQUIRED_SCRIPT_FILES = [
  "_common.py",
  "aggregate_reviews.py",
  "controller.py",
  "new_task.py",
  "status.py",
  "validate_adjudication.py",
  "validate_goal_contract.py",
  "validate_milestone_plan.py",
  "validate_task_list.py",
  "validate_task_verification.py"
];

export const HELP_SCRIPT_FILES = REQUIRED_SCRIPT_FILES.filter((fileName) => fileName !== "_common.py");

export const REQUIRED_TEMPLATE_FILES = [
  "adjudication-report.json",
  "direction-evaluation.json",
  "final-report.md",
  "goal-contract.json",
  "milestone-plan.json",
  "proposal-summary.md",
  "proposal.md",
  "questioning-report.json",
  "raw-request.md",
  "review-aggregate.json",
  "reviewer-report.json",
  "state.json",
  "task-execution-report.json",
  "task-list.json",
  "task-spec.json",
  "task-verification-report.json"
];

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
  const errors = [];
  for (const fileName of REQUIRED_SCRIPT_FILES) {
    const filePath = path.join(targets.scriptsTarget, fileName);
    if (!(await pathExists(filePath))) {
      errors.push(`missing ${filePath}`);
    }
  }
  for (const fileName of REQUIRED_TEMPLATE_FILES) {
    const filePath = path.join(targets.templatesTarget, fileName);
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
