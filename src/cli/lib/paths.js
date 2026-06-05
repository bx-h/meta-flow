import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const thisFile = fileURLToPath(import.meta.url);
export const packageRoot = path.resolve(path.dirname(thisFile), "../../..");
export const pluginSource = path.join(packageRoot, "plugin");
export const agentTemplatesSource = path.join(pluginSource, "agent-templates");
export const skillSource = path.join(pluginSource, "skills", "meta-flow");
export const scriptsSource = path.join(pluginSource, "scripts");
export const templatesSource = path.join(pluginSource, "templates");
export const marketplaceSource = path.join(packageRoot, "marketplace", "marketplace.json");
export const examplesRoot = path.join(packageRoot, "examples");
export const sampleTaskRoot = path.join(examplesRoot, "sample-task");

export function resolveTargets({ scope = "repo", target } = {}) {
  if (!["repo", "user"].includes(scope)) {
    throw new Error("--scope must be repo or user");
  }

  const base = scope === "user"
    ? os.homedir()
    : path.resolve(target || process.cwd());

  return {
    scope,
    target: base,
    pluginTarget: scope === "user"
      ? path.join(base, ".codex", "plugins", "meta-flow")
      : path.join(base, "plugins", "meta-flow"),
    skillTarget: path.join(base, ".agents", "skills", "meta-flow"),
    marketplaceTarget: path.join(base, ".agents", "plugins", "marketplace.json"),
    agentsTarget: path.join(base, ".codex", "agents"),
    codexConfigTarget: path.join(base, ".codex", "config.toml"),
    supportTarget: path.join(base, ".meta-flow"),
    scriptsTarget: path.join(base, ".meta-flow", "scripts"),
    templatesTarget: path.join(base, ".meta-flow", "templates"),
    tasksTarget: path.join(base, ".meta-flow", "tasks")
  };
}

export function repoMarketplacePath() {
  return "./plugins/meta-flow";
}
