import { runDoctor, doctorHelp } from "./commands/doctor.js";
import { runInstall, installHelp } from "./commands/install.js";
import { runPrintPaths, printPathsHelp } from "./commands/print_paths.js";
import { runRuntimeCommand, runtimeHelp } from "./commands/runtime.js";
import { runUninstall, uninstallHelp } from "./commands/uninstall.js";
import { runVerify } from "./commands/verify.js";
import { META_FLOW_VERSION } from "./lib/version.js";

const COMMANDS = {
  install: { run: runInstall, help: installHelp },
  uninstall: { run: runUninstall, help: uninstallHelp },
  doctor: { run: runDoctor, help: doctorHelp },
  verify: { run: runVerify, help: () => "Usage: meta-flow verify" },
  "print-paths": { run: runPrintPaths, help: printPathsHelp },
  version: { run: runVersion, help: () => "Usage: meta-flow version" }
};

export async function main(argv = []) {
  if (argv.length === 0 || argv.includes("--help") || argv.includes("-h")) {
    printHelp();
    return 0;
  }
  if (argv.includes("--version")) {
    return runVersion();
  }
  const [command, ...rest] = argv;
  const entry = COMMANDS[command];
  if (entry) {
    return entry.run(rest);
  }
  return runRuntimeCommand(command, rest);
}

function printHelp() {
  console.log(topHelp());
}

function topHelp() {
  return `Usage: meta-flow <command> [options]

Commands:
  install       Install plugin, agents, marketplace entry, and config.
  uninstall     Remove managed plugin and marked agents.
  doctor        Check installed state.
  verify        Verify package structure and installer behavior.
  print-paths   Print repo/user scope target paths.
  version       Show package version.
  start         Start a workflow task in ~/.meta-flow.
  resume        Resume the active workflow task.
  status        Print workflow task status.
  advance       Advance through an allowed workflow event.
  gate          Open or decide a human gate.
  artifacts     Validate artifact layout.
  abandon       Mark a workflow task as abandoned.
  deactivate    Clear the active workflow task pointer.
  validate      Validate a workflow artifact file.
  aggregate-reviews
                Aggregate reviewer reports.

Global:
  --help        Show help.
  --version     Show package version.

${runtimeHelp()}`;
}

async function runVersion() {
  console.log(META_FLOW_VERSION);
  return 0;
}
