import test from "node:test";
import assert from "node:assert/strict";
import { mergeMarketplace, removeMarketplaceEntry } from "../../src/cli/lib/marketplace.js";

test("mergeMarketplace preserves other plugins and updates meta-flow entry", () => {
  const existing = {
    plugins: [
      { name: "other", source: { path: "./plugins/other" } },
      { name: "meta-flow", source: { path: "old" } }
    ]
  };
  const merged = mergeMarketplace(existing, { name: "meta-flow", source: { path: "new" } });
  assert.equal(merged.plugins.length, 2);
  assert.equal(merged.plugins.find((plugin) => plugin.name === "other").source.path, "./plugins/other");
  assert.equal(merged.plugins.find((plugin) => plugin.name === "meta-flow").source.path, "new");
});

test("removeMarketplaceEntry removes only meta-flow", () => {
  const next = removeMarketplaceEntry({
    plugins: [
      { name: "other" },
      { name: "meta-flow" }
    ]
  });
  assert.deepEqual(next.plugins.map((plugin) => plugin.name), ["other"]);
});
