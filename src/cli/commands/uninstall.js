import { parseOptions, helpRequested } from "../lib/args.js";
import { uninstallAgents } from "../lib/agents.js";
import { createLogger } from "../lib/logger.js";
import { uninstallMarketplace } from "../lib/marketplace.js";
import { uninstallPlugin } from "../lib/plugin.js";
import { resolveTargets } from "../lib/paths.js";

export function uninstallHelp() {
  return `Usage: meta-flow uninstall --scope repo|user [options]

Options:
  --target <path>   Target repo path for repo scope. Defaults to cwd.
  --dry-run         Print planned removals without deleting files.
  --yes             Confirm removal.
  --keep-tasks      Keep .meta-flow/tasks. This is the default.
  --verbose         Print detailed actions.`;
}

export async function runUninstall(argv = []) {
  if (helpRequested(argv)) {
    console.log(uninstallHelp());
    return 0;
  }
  const { options } = parseOptions(argv, {
    scope: "string",
    target: "string"
  });
  const scope = options.scope || "repo";
  const targets = resolveTargets({ scope, target: options.target });
  const dryRun = Boolean(options.dryRun);
  const logger = createLogger({ verbose: options.verbose });

  console.log("Meta Flow uninstall plan:");
  console.log(`- scope: ${targets.scope}`);
  console.log(`- target: ${targets.target}`);
  console.log(`- remove plugin: ${targets.pluginTarget}`);
  console.log(`- update marketplace: ${targets.marketplaceTarget}`);
  console.log(`- remove marked agents: ${targets.agentsTarget}`);
  console.log(`- keep tasks: ${targets.tasksTarget}`);

  if (!dryRun && !options.yes) {
    throw new Error("Refusing to delete files without --yes. Re-run with --dry-run first or add --yes.");
  }

  const pluginResult = await uninstallPlugin(targets, { dryRun, logger });
  if (pluginResult.skipped) {
    logger.warn(`plugin target is not a confirmed meta-flow plugin; skipped: ${targets.pluginTarget}`);
  }
  await uninstallMarketplace(targets, { dryRun, logger });
  const agentResult = await uninstallAgents(targets, { dryRun, logger });
  for (const skipped of agentResult.skipped) {
    logger.warn(`agent file has no meta-flow marker; skipped: ${skipped}`);
  }
  console.log("Uninstall complete. User task data was not deleted.");
  return 0;
}
