import fs from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { installAgents, validateAgentTemplates } from "../lib/agents.js";
import { runDoctor } from "./doctor.js";
import { runInstall } from "./install.js";
import { runUninstall } from "./uninstall.js";
import { validatePlugin } from "../lib/plugin.js";
import { packageRoot, pluginSource, sampleTaskRoot } from "../lib/paths.js";
import { HELP_SCRIPT_FILES } from "../lib/support.js";
import { META_FLOW_VERSION, PACKAGE_NAME } from "../lib/version.js";

export async function runVerify(argv = []) {
  const lintOnly = argv.includes("--lint-only");
  const checks = [];
  checks.push(await checkPackageJson());
  checks.push(await checkNoForbiddenSourcePatterns());
  if (lintOnly) {
    report(checks);
    return checks.some((check) => check.level === "FAIL") ? 1 : 0;
  }
  checks.push(await checkPlugin());
  checks.push(await checkAgents());
  checks.push(await checkPythonHelp());
  checks.push(await checkTemplates());
  checks.push(await checkSampleTask());
  checks.push(await checkDryRun());
  checks.push(await checkInstallUninstallSimulation());
  report(checks);
  return checks.some((check) => check.level === "FAIL") ? 1 : 0;
}

async function checkPackageJson() {
  const packageJson = JSON.parse(await fs.readFile(path.join(packageRoot, "package.json"), "utf8"));
  const errors = [];
  if (packageJson.name !== PACKAGE_NAME) errors.push("unexpected package name");
  if (packageJson.version !== META_FLOW_VERSION) errors.push(`unexpected package version: ${packageJson.version}`);
  if (packageJson.scripts?.postinstall) errors.push("postinstall must not exist");
  if (packageJson.bin?.["meta-flow"] !== "bin/meta-flow.js") errors.push("bin meta-flow is invalid");
  if (packageJson.type !== "module") errors.push("type must be module");
  return result("package.json", errors);
}

async function checkNoForbiddenSourcePatterns() {
  const files = await collectJsFiles(path.join(packageRoot, "src"));
  files.push(path.join(packageRoot, "bin", "meta-flow.js"));
  const errors = [];
  for (const filePath of files) {
    const text = await fs.readFile(filePath, "utf8");
    if (/\beval\s*\(/.test(text)) errors.push(`dynamic eval found in ${filePath}`);
    if (/https?:\/\/.+exec/i.test(text)) errors.push(`suspicious remote execution pattern in ${filePath}`);
  }
  return result("no eval or remote execution patterns", errors);
}

async function checkPlugin() {
  const plugin = await validatePlugin();
  return result("plugin manifest and skill", plugin.errors);
}

async function checkAgents() {
  const results = await validateAgentTemplates();
  const errors = results
    .filter((item) => item.missing.length)
    .map((item) => `${path.basename(item.filePath)} missing ${item.missing.join(", ")}`);
  return result("agent TOML required fields", errors);
}

async function checkPythonHelp() {
  const python = resolvePython();
  const errors = [];
  for (const script of HELP_SCRIPT_FILES) {
    const run = spawnSync(python, [path.join(pluginSource, "scripts", script), "--help"], pythonOptions());
    if (run.status !== 0) {
      errors.push(`${script} --help failed: ${run.stderr || run.stdout}`);
    }
  }
  return result("Python script --help", errors);
}

async function checkTemplates() {
  const python = resolvePython();
  const scripts = path.join(pluginSource, "scripts");
  const templates = path.join(pluginSource, "templates");
  const runs = [
    [path.join(scripts, "validate_goal_contract.py"), path.join(templates, "goal-contract.json")],
    [path.join(scripts, "validate_adjudication.py"), path.join(templates, "adjudication-report.json")],
    [path.join(scripts, "validate_milestone_plan.py"), path.join(templates, "milestone-plan.json")],
    [path.join(scripts, "validate_task_list.py"), path.join(templates, "task-list.json")],
    [path.join(scripts, "validate_task_verification.py"), path.join(templates, "task-verification-report.json")]
  ];
  const errors = [];
  for (const args of runs) {
    const run = spawnSync(python, args, pythonOptions());
    if (run.status !== 0) {
      errors.push(`${path.basename(args[1])} failed: ${run.stderr || run.stdout}`);
    }
  }
  return result("templates validate against scripts", errors);
}

async function checkSampleTask() {
  const python = resolvePython();
  const tmp = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-verify-"));
  const runs = [
    [path.join(pluginSource, "scripts", "validate_goal_contract.py"), path.join(sampleTaskRoot, "goal-contract.json")],
    [
      path.join(pluginSource, "scripts", "aggregate_reviews.py"),
      "--reviews-dir",
      path.join(sampleTaskRoot, "reviews"),
      "--output",
      path.join(tmp, "review-aggregate.json"),
      "--task-id",
      "sample-health-check"
    ],
    [path.join(pluginSource, "scripts", "validate_adjudication.py"), path.join(sampleTaskRoot, "adjudication-report.json")],
    [path.join(pluginSource, "scripts", "validate_milestone_plan.py"), path.join(sampleTaskRoot, "milestone-plan.json")],
    [path.join(pluginSource, "scripts", "validate_task_list.py"), path.join(sampleTaskRoot, "milestones", "M1", "task-list.json")],
    [
      path.join(pluginSource, "scripts", "validate_task_verification.py"),
      path.join(sampleTaskRoot, "milestones", "M1", "tasks", "T1", "verification-report.json")
    ]
  ];
  const errors = [];
  for (const args of runs) {
    const run = spawnSync(python, args, pythonOptions());
    if (run.status !== 0) {
      errors.push(`${path.basename(args[0])} failed: ${run.stderr || run.stdout}`);
    }
  }
  return result("sample-task validation", errors);
}

async function checkDryRun() {
  const tmp = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-dry-run-"));
  await runInstall(["--scope", "repo", "--target", tmp, "--dry-run"]);
  const entries = await fs.readdir(tmp);
  return result("install --dry-run does not write", entries.length ? [`dry-run wrote files: ${entries.join(", ")}`] : []);
}

async function checkInstallUninstallSimulation() {
  const tmp = await fs.mkdtemp(path.join(os.tmpdir(), "meta-flow-install-"));
  const errors = [];
  const installCode = await runInstall(["--scope", "repo", "--target", tmp, "--yes"]);
  if (installCode !== 0) errors.push("install returned non-zero");
  const secondInstallCode = await runInstall(["--scope", "repo", "--target", tmp, "--yes"]);
  if (secondInstallCode !== 0) errors.push("second install returned non-zero");
  const marketplace = JSON.parse(await fs.readFile(path.join(tmp, ".agents", "plugins", "marketplace.json"), "utf8"));
  const entries = marketplace.plugins.filter((plugin) => plugin.name === "meta-flow");
  if (entries.length !== 1) errors.push(`marketplace has ${entries.length} meta-flow entries`);
  if (!(await exists(path.join(tmp, ".agents", "skills", "meta-flow", "SKILL.md")))) {
    errors.push("discoverable skill was not installed");
  }
  if (!(await exists(path.join(tmp, ".meta-flow", "scripts", "new_task.py")))) {
    errors.push("support scripts were not installed");
  }
  if (!(await exists(path.join(tmp, ".meta-flow", "templates", "state.json")))) {
    errors.push("support templates were not installed");
  }
  const doctorCode = await runDoctor(["--scope", "repo", "--target", tmp]);
  if (doctorCode !== 0) errors.push("doctor returned non-zero after install");
  const uninstallCode = await runUninstall(["--scope", "repo", "--target", tmp, "--yes"]);
  if (uninstallCode !== 0) errors.push("uninstall returned non-zero");
  return result("repo install/doctor/uninstall simulation", errors);
}

async function exists(filePath) {
  try {
    await fs.access(filePath);
    return true;
  } catch {
    return false;
  }
}

async function collectJsFiles(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const files = [];
  for (const entry of entries) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...await collectJsFiles(full));
    } else if (entry.isFile() && entry.name.endsWith(".js")) {
      files.push(full);
    }
  }
  return files;
}

function resolvePython() {
  const python3 = spawnSync("python3", ["--version"], pythonOptions());
  return python3.status === 0 ? "python3" : "python";
}

function pythonOptions() {
  return {
    encoding: "utf8",
    env: {
      ...process.env,
      PYTHONDONTWRITEBYTECODE: "1"
    }
  };
}

function result(title, errors) {
  return errors.length ? { level: "FAIL", title, errors } : { level: "PASS", title, errors: [] };
}

function report(checks) {
  for (const check of checks) {
    if (check.level === "PASS") {
      console.log(`PASS: ${check.title}`);
    } else {
      console.error(`FAIL: ${check.title}`);
      for (const error of check.errors) console.error(`  - ${error}`);
    }
  }
}

const thisFile = fileURLToPath(import.meta.url);
if (process.argv[1] === thisFile) {
  runVerify(process.argv.slice(2)).then((code) => {
    process.exitCode = code;
  }).catch((error) => {
    console.error(error.message);
    process.exitCode = 1;
  });
}
