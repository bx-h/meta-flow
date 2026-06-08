import os from "node:os";
import path from "node:path";
import { spawnSync } from "node:child_process";
import { helpRequested } from "../lib/args.js";
import { pluginSource } from "../lib/paths.js";

const CONTROLLER_COMMANDS = new Set(["start", "resume", "status", "advance", "gate", "artifacts", "abandon", "deactivate"]);
const VALIDATE_SCRIPTS = {
  "questioning-report": "validate_questioning_report.py",
  "goal-contract": "validate_goal_contract.py",
  adjudication: "validate_adjudication.py",
  "milestone-plan": "validate_milestone_plan.py",
  "task-list": "validate_task_list.py",
  "task-verification": "validate_task_verification.py"
};

export function runtimeHelp() {
  return `Usage: meta-flow <runtime-command> [options]

Runtime commands:
  start "<request>"              Start a task in the runtime root.
  resume [task]                  Print the active task resume pack.
  status [task]                  Print task status.
  advance [task] --event <event> Advance through a controller-approved event.
  gate open|decide ...           Open or decide a human gate.
  artifacts validate [task]      Validate artifact index and by-node layout.
  abandon [task]                 Abandon a task and keep artifacts for audit.
  deactivate [task]              Only clear the active task pointer.
  validate <kind> [path]         Validate an artifact file.
  aggregate-reviews [options]    Aggregate reviewer reports.

Options:
  --root <path>                  Runtime root. Defaults to META_FLOW_ROOT or ~/.meta-flow.
  --format text|json|codex       Output format where supported.

Aliases:
  The package also installs the bin alias: metaflow`;
}

export async function runRuntimeCommand(command, argv = []) {
  if (command === "validate") {
    return runValidate(argv);
  }
  if (command === "aggregate-reviews") {
    return runPython("aggregate_reviews.py", argv);
  }
  if (CONTROLLER_COMMANDS.has(command)) {
    const { root, rest } = extractRoot(argv);
    return runPython("controller.py", ["--root", root, command, ...rest], { root, prog: "meta-flow" });
  }
  if (helpRequested(argv)) {
    console.log(runtimeHelp());
    return 0;
  }
  throw new Error(`Unknown runtime command: ${command}`);
}

function runValidate(argv) {
  if (helpRequested(argv) || argv.length === 0) {
    console.log(`Usage: meta-flow validate <kind> [path]

Kinds:
  questioning-report
  goal-contract
  adjudication
  milestone-plan
  task-list
  task-verification`);
    return 0;
  }
  const [kind, ...rest] = argv;
  const script = VALIDATE_SCRIPTS[kind];
  if (!script) {
    throw new Error(`Unknown validation kind: ${kind}`);
  }
  return runPython(script, rest);
}

function runPython(scriptName, args, options = {}) {
  const python = resolvePython();
  const script = path.join(pluginSource, "scripts", scriptName);
  const result = spawnSync(python, [script, ...args], {
    encoding: "utf8",
    env: {
      ...process.env,
      META_FLOW_ROOT: options.root || process.env.META_FLOW_ROOT || defaultRuntimeRoot(),
      ...(options.prog ? { META_FLOW_PROG: options.prog } : {}),
      PYTHONDONTWRITEBYTECODE: "1"
    }
  });
  if (result.stdout) process.stdout.write(result.stdout);
  if (result.stderr) process.stderr.write(result.stderr);
  return result.status ?? 1;
}

function extractRoot(argv) {
  const rest = [];
  let root = null;
  for (let index = 0; index < argv.length; index += 1) {
    const token = argv[index];
    if (token === "--root") {
      if (index + 1 >= argv.length) {
        throw new Error("Missing value for --root");
      }
      root = argv[index + 1];
      index += 1;
      continue;
    }
    if (token.startsWith("--root=")) {
      root = token.slice("--root=".length);
      continue;
    }
    rest.push(token);
  }
  return {
    root: root || process.env.META_FLOW_ROOT || defaultRuntimeRoot(),
    rest
  };
}

function defaultRuntimeRoot() {
  return path.join(os.homedir(), ".meta-flow");
}

function resolvePython() {
  const python3 = spawnSync("python3", ["--version"], {
    encoding: "utf8",
    env: {
      ...process.env,
      PYTHONDONTWRITEBYTECODE: "1"
    }
  });
  return python3.status === 0 ? "python3" : "python";
}
