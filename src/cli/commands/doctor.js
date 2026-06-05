import fs from "node:fs/promises";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { parseOptions, helpRequested } from "../lib/args.js";
import { AGENT_FILES, validateAgentTemplate } from "../lib/agents.js";
import { inspectCodexConfig } from "../lib/codex_config.js";
import { pathExists, readJsonOrDefault } from "../lib/fs_safe.js";
import { createLogger } from "../lib/logger.js";
import { resolveTargets, sampleTaskRoot } from "../lib/paths.js";

export function doctorHelp() {
  return `Usage: meta-flow doctor --scope repo|user [--target <path>] [--verbose]`;
}

export async function runDoctor(argv = []) {
  if (helpRequested(argv)) {
    console.log(doctorHelp());
    return 0;
  }
  const { options } = parseOptions(argv, {
    scope: "string",
    target: "string"
  });
  const targets = resolveTargets({ scope: options.scope || "repo", target: options.target });
  const logger = createLogger({ verbose: options.verbose });
  const results = [];

  results.push(checkCodexCli());
  results.push(await checkPlugin(targets));
  results.push(await checkMarketplace(targets));
  results.push(await checkAgents(targets));
  results.push(await checkConfig(targets));
  results.push(await checkPythonScripts(targets));
  results.push(await checkSampleTask(targets));

  for (const result of results) {
    logger[result.level.toLowerCase()](`${result.title}${result.message ? ` - ${result.message}` : ""}`);
  }
  const hasFail = results.some((result) => result.level === "FAIL");
  return hasFail ? 1 : 0;
}

function checkCodexCli() {
  const found = spawnSync("codex", ["--version"], { encoding: "utf8" });
  if (found.status === 0) {
    return { level: "PASS", title: "Codex CLI found" };
  }
  return { level: "WARN", title: "Codex CLI not found", message: "Install Codex CLI or use the Codex desktop app plugin loader." };
}

async function checkPlugin(targets) {
  const manifestPath = path.join(targets.pluginTarget, ".codex-plugin", "plugin.json");
  const skillPath = path.join(targets.pluginTarget, "skills", "meta-flow", "SKILL.md");
  if (!(await pathExists(manifestPath))) {
    return { level: "FAIL", title: "plugin manifest missing", message: `Run meta-flow install --scope ${targets.scope}` };
  }
  const manifest = JSON.parse(await fs.readFile(manifestPath, "utf8"));
  if (manifest.name !== "meta-flow") {
    return { level: "FAIL", title: "plugin manifest invalid", message: "Expected name=meta-flow." };
  }
  if (!(await pathExists(skillPath))) {
    return { level: "FAIL", title: "SKILL.md missing", message: "Re-run install." };
  }
  const skill = await fs.readFile(skillPath, "utf8");
  if (!/^---\n[\s\S]*?name:\s*meta-flow[\s\S]*?---/m.test(skill)) {
    return { level: "FAIL", title: "SKILL.md frontmatter invalid", message: "Reinstall plugin files." };
  }
  return { level: "PASS", title: "plugin and skill present" };
}

async function checkMarketplace(targets) {
  if (!(await pathExists(targets.marketplaceTarget))) {
    return { level: "FAIL", title: "marketplace missing", message: "Run install to create marketplace.json." };
  }
  const marketplace = await readJsonOrDefault(targets.marketplaceTarget, {});
  const entry = Array.isArray(marketplace.plugins)
    ? marketplace.plugins.find((plugin) => plugin?.name === "meta-flow")
    : null;
  if (!entry) {
    return { level: "FAIL", title: "marketplace entry missing", message: "Run install to add meta-flow entry." };
  }
  return { level: "PASS", title: "marketplace entry present" };
}

async function checkAgents(targets) {
  const missing = [];
  const invalid = [];
  for (const fileName of AGENT_FILES) {
    const filePath = path.join(targets.agentsTarget, fileName);
    if (!(await pathExists(filePath))) {
      missing.push(fileName);
      continue;
    }
    const result = await validateAgentTemplate(filePath);
    if (result.missing.length) {
      invalid.push(`${fileName}:${result.missing.join(",")}`);
    }
  }
  if (missing.length || invalid.length) {
    return {
      level: "FAIL",
      title: "custom agents incomplete",
      message: `missing=[${missing.join(", ")}] invalid=[${invalid.join(", ")}]`
    };
  }
  return { level: "PASS", title: "custom agents present" };
}

async function checkConfig(targets) {
  const config = await inspectCodexConfig(targets.codexConfigTarget);
  if (!config.exists) {
    return { level: "FAIL", title: "Codex config missing", message: "Run install to create .codex/config.toml." };
  }
  if (!config.hasAgents || !config.hasMaxThreads || !config.hasMaxDepth) {
    return { level: "WARN", title: "Codex agents config incomplete", message: "Run install --force to patch existing settings if desired." };
  }
  return { level: "PASS", title: "Codex agents config present" };
}

async function checkPythonScripts(targets) {
  const scriptsDir = path.join(targets.pluginTarget, "scripts");
  const scriptPath = path.join(scriptsDir, "validate_goal_contract.py");
  if (!(await pathExists(scriptPath))) {
    return { level: "FAIL", title: "Python scripts missing", message: "Reinstall plugin files." };
  }
  const result = spawnSync(resolvePython(), [scriptPath, "--help"], pythonOptions());
  if (result.status !== 0) {
    return { level: "FAIL", title: "Python scripts not runnable", message: result.stderr || result.stdout };
  }
  return { level: "PASS", title: "Python scripts runnable" };
}

async function checkSampleTask(targets) {
  if (!(await pathExists(sampleTaskRoot))) {
    return { level: "WARN", title: "sample task unavailable", message: "Package examples are not present." };
  }
  const python = resolvePython();
  const scripts = path.join(targets.pluginTarget, "scripts");
  const runs = [
    [path.join(scripts, "validate_goal_contract.py"), path.join(sampleTaskRoot, "goal-contract.json")],
    [path.join(scripts, "validate_adjudication.py"), path.join(sampleTaskRoot, "adjudication-report.json")],
    [path.join(scripts, "validate_milestone_plan.py"), path.join(sampleTaskRoot, "milestone-plan.json")],
    [path.join(scripts, "validate_task_list.py"), path.join(sampleTaskRoot, "milestones", "M1", "task-list.json")],
    [
      path.join(scripts, "validate_task_verification.py"),
      path.join(sampleTaskRoot, "milestones", "M1", "tasks", "T1", "verification-report.json")
    ]
  ];
  for (const args of runs) {
    const result = spawnSync(python, args, pythonOptions());
    if (result.status !== 0) {
      return { level: "FAIL", title: "sample task validation failed", message: result.stderr || result.stdout };
    }
  }
  return { level: "PASS", title: "sample task validation passed" };
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
