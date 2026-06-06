import fs from "node:fs/promises";
import path from "node:path";
import { parseOptions, helpRequested } from "../lib/args.js";
import { installAgents } from "../lib/agents.js";
import { patchCodexConfig } from "../lib/codex_config.js";
import { backupIfExists } from "../lib/fs_safe.js";
import { createLogger } from "../lib/logger.js";
import { updateMarketplace } from "../lib/marketplace.js";
import { installPersistentBlock } from "../lib/persistent.js";
import { installPlugin } from "../lib/plugin.js";
import { resolveTargets } from "../lib/paths.js";
import { installSkill } from "../lib/skill.js";
import { installSupportFiles } from "../lib/support.js";

export function installHelp() {
  return `Usage: meta-flow install --scope repo|user [options]

Options:
  --target <path>   Target repo path for repo scope. Defaults to cwd.
  --force           Overwrite conflicts after backing them up.
  --dry-run         Print planned actions without writing files.
  --yes             Skip confirmation prompts.
  --no-agents       Do not install custom agent TOML files.
  --no-plugin       Do not install the Codex plugin files.
  --persistent      Add an AGENTS.md managed block so Codex auto-resumes active tasks.
  --backup          Backup existing managed files before update.
  --verbose         Print detailed actions.`;
}

export async function runInstall(argv = []) {
  if (helpRequested(argv)) {
    console.log(installHelp());
    return 0;
  }
  const { options } = parseOptions(argv, {
    scope: "string",
    target: "string"
  });
  const scope = options.scope || "repo";
  const targets = resolveTargets({ scope, target: options.target });
  const logger = createLogger({ verbose: options.verbose });
  const dryRun = Boolean(options.dryRun);
  const force = Boolean(options.force);
  const backup = Boolean(options.backup);
  const installPluginEnabled = options.plugin !== false;
  const installAgentsEnabled = options.agents !== false;
  const installPersistentEnabled = Boolean(options.persistent);

  printInstallPlan(targets, {
    installPluginEnabled,
    installAgentsEnabled,
    installPersistentEnabled,
    dryRun
  });

  if (backup && !dryRun) {
    await fs.mkdir(path.dirname(targets.marketplaceTarget), { recursive: true });
  }

  if (installPluginEnabled) {
    if (backup) {
      await backupIfExists(targets.pluginTarget, { dryRun, logger });
    }
    const result = await installPlugin(targets, { dryRun, force, logger });
    if (result.conflict) {
      logger.warn(`plugin target exists and is not a meta-flow plugin: ${result.conflict}. Re-run with --force to overwrite.`);
    }
  }

  const skillResult = await installSkill(targets, { dryRun, force, backup, logger });
  if (skillResult.conflict) {
    logger.warn(`skill target exists and is not managed by meta-flow: ${skillResult.conflict}. Re-run with --force to overwrite.`);
  }

  const supportResult = await installSupportFiles(targets, { dryRun, force, backup, logger });
  for (const [name, result] of Object.entries(supportResult)) {
    if (result.conflict) {
      logger.warn(`${name} target exists and is not managed by meta-flow: ${result.conflict}. Re-run with --force to overwrite.`);
    }
  }

  await updateMarketplace(targets, { dryRun, logger });

  if (installAgentsEnabled) {
    if (backup) {
      await backupExistingAgents(targets, { dryRun, logger });
    }
    const result = await installAgents(targets, { dryRun, force, logger });
    for (const conflict of result.conflicts) {
      logger.warn(`agent file exists without meta-flow marker; not overwritten: ${conflict}`);
    }
  }

  const configResult = await patchCodexConfig(targets.codexConfigTarget, {
    dryRun,
    force,
    backup,
    logger
  });
  for (const warning of configResult.warnings) {
    logger.warn(warning);
  }

  if (installPersistentEnabled) {
    if (targets.scope === "user") {
      logger.warn("user-scope persistent mode writes AGENTS.md under your home directory and can affect every workspace below it.");
    }
    await installPersistentBlock(targets, { dryRun, backup, logger });
  }

  console.log("\nNext:");
  console.log("1. Restart Codex.");
  console.log(`2. Run: meta-flow doctor --scope ${scope}${scope === "repo" ? ` --target ${targets.target}` : ""}`);
  if (installPersistentEnabled) {
    console.log("3. Codex will auto-check active meta-flow tasks from AGENTS.md.");
  } else {
    console.log("3. In Codex, mention: $meta-flow. For automatic resume, reinstall with --persistent.");
  }
  return 0;
}

function printInstallPlan(targets, options) {
  console.log("Meta Flow install plan:");
  console.log(`- scope: ${targets.scope}`);
  console.log(`- target: ${targets.target}`);
  console.log(`- plugin: ${targets.pluginTarget}`);
  console.log(`- skill: ${targets.skillTarget}`);
  console.log(`- support: ${targets.supportTarget}`);
  console.log(`- marketplace: ${targets.marketplaceTarget}`);
  console.log(`- agents: ${targets.agentsTarget}`);
  console.log(`- config: ${targets.codexConfigTarget}`);
  if (options.installPersistentEnabled) {
    console.log(`- AGENTS.md: ${targets.agentsMdTarget}`);
  }
  console.log("\nActions:");
  if (options.installPluginEnabled) {
    console.log("- copy plugin");
  }
  if (options.installAgentsEnabled) {
    console.log("- install 14 agent templates");
  }
  console.log("- install discoverable skill");
  console.log("- install support scripts and templates");
  console.log("- update marketplace");
  console.log("- ensure Codex agent config");
  if (options.installPersistentEnabled) {
    console.log("- add AGENTS.md persistent resume block");
  }
  if (options.dryRun) {
    console.log("- dry-run only; no files will be written");
  }
}

async function backupExistingAgents(targets, options) {
  const { AGENT_FILES } = await import("../lib/agents.js");
  for (const fileName of AGENT_FILES) {
    await backupIfExists(path.join(targets.agentsTarget, fileName), options);
  }
}
