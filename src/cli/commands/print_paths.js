import { parseOptions, helpRequested } from "../lib/args.js";
import { resolveTargets } from "../lib/paths.js";

export function printPathsHelp() {
  return `Usage: meta-flow print-paths --scope repo|user [--target <path>]`;
}

export async function runPrintPaths(argv = []) {
  if (helpRequested(argv)) {
    console.log(printPathsHelp());
    return 0;
  }
  const { options } = parseOptions(argv, {
    scope: "string",
    target: "string"
  });
  const targets = resolveTargets({ scope: options.scope || "repo", target: options.target });
  console.log(JSON.stringify(targets, null, 2));
  return 0;
}
