import path from "node:path";
import { readJsonOrDefault, writeJsonPretty } from "./fs_safe.js";
import { repoMarketplacePath } from "./paths.js";

export function marketplaceEntry(targets) {
  return {
    name: "meta-flow",
    version: "0.1.0",
    source: {
      source: "local",
      path: targets.scope === "repo" ? repoMarketplacePath() : targets.pluginTarget
    },
    policy: {
      installation: "AVAILABLE",
      authentication: "ON_INSTALL"
    },
    category: "Productivity"
  };
}

export function mergeMarketplace(existing, entry) {
  const marketplace = existing && typeof existing === "object" ? structuredClone(existing) : {};
  if (!marketplace.name) {
    marketplace.name = "meta-flow-marketplace";
  }
  if (!marketplace.interface) {
    marketplace.interface = { displayName: "Meta Flow Marketplace" };
  }
  if (!Array.isArray(marketplace.plugins)) {
    marketplace.plugins = [];
  }
  const index = marketplace.plugins.findIndex((plugin) => plugin?.name === entry.name);
  if (index >= 0) {
    marketplace.plugins[index] = { ...marketplace.plugins[index], ...entry };
  } else {
    marketplace.plugins.push(entry);
  }
  return marketplace;
}

export function removeMarketplaceEntry(existing, name = "meta-flow") {
  const marketplace = existing && typeof existing === "object" ? structuredClone(existing) : {};
  if (!Array.isArray(marketplace.plugins)) {
    marketplace.plugins = [];
  }
  marketplace.plugins = marketplace.plugins.filter((plugin) => plugin?.name !== name);
  return marketplace;
}

export async function updateMarketplace(targets, options = {}) {
  const current = await readJsonOrDefault(targets.marketplaceTarget, {
    name: "meta-flow-marketplace",
    interface: { displayName: "Meta Flow Marketplace" },
    plugins: []
  });
  const next = mergeMarketplace(current, marketplaceEntry(targets));
  await writeJsonPretty(targets.marketplaceTarget, next, options);
}

export async function uninstallMarketplace(targets, options = {}) {
  const current = await readJsonOrDefault(targets.marketplaceTarget, {
    name: "meta-flow-marketplace",
    interface: { displayName: "Meta Flow Marketplace" },
    plugins: []
  });
  const next = removeMarketplaceEntry(current);
  await writeJsonPretty(targets.marketplaceTarget, next, options);
}

export function describeMarketplace(targets) {
  return path.resolve(targets.marketplaceTarget);
}
