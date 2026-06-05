# Meta Flow Codex

Meta Flow is a Codex-native workflow for turning vague requests into clarified goals, reviewed proposals, adjudicated plans, concrete tasks, verified results, and direction-aware iteration.

## Install

Repo scope:

```bash
npx @bx-h/meta-flow@latest install --scope repo
```

User scope:

```bash
npx @bx-h/meta-flow@latest install --scope user
```

Global CLI:

```bash
npm i -g @bx-h/meta-flow
meta-flow install --scope repo
```

Pinned version:

```bash
npx @bx-h/meta-flow@0.1.0 install --scope repo
```

## Quick Start

1. Install with repo or user scope.
2. Restart Codex.
3. In Codex, say:

```text
Use $meta-flow for this request: "I want to improve our backend observability but I'm not sure where to start."
```

You can check installation state with:

```bash
meta-flow doctor --scope repo
```

## When To Use It

- Vague requests.
- Multi-stage tasks.
- High-reliability implementation.
- Work that needs a proposal before execution.
- Work that needs task-level verification.
- Work where execution may reveal facts that require goal adjustment.

## When Not To Use It

- Questions answerable in one response.
- Tiny code edits.
- Tasks without definable acceptance criteria.
- Pure discussion with no observable artifact.

## Workflow

Proposal phase:

```mermaid
flowchart LR
  A["INTAKE"] --> B["QUESTIONING"]
  B --> C["GOAL_CONTRACT_DRAFTED"]
  C --> D["RESEARCH_AND_PROPOSAL"]
  D --> E["PROPOSAL_REVIEW"]
  E --> F["ADJUDICATION"]
  F -->|revise| G["PROPOSAL_REWORK"]
  G --> E
  F -->|accept| H["PROPOSAL_SUMMARY"]
  H --> I["USER_PROPOSAL_CONFIRMATION"]
```

Execution phase:

```mermaid
flowchart LR
  A["PLANNING"] --> B["USER_PLAN_CONFIRMATION"]
  B --> C["MILESTONE_SELECTED"]
  C --> D["TASK_DECOMPOSITION"]
  D --> E["TASK_EXECUTION"]
  E --> F["TASK_VERIFICATION"]
  F -->|repair| G["TASK_REPAIR"]
  G --> E
  F -->|pass| H["MILESTONE_COMPLETED"]
  H --> I["DIRECTION_EVALUATION"]
  I -->|continue| C
  I -->|replan| A
  I -->|adjust goal| J["GOAL_ADJUSTMENT_REQUIRED"]
  I -->|done| K["FINAL_SUMMARY"]
  K --> L["USER_FINAL_CONFIRMATION"]
```

## Roles

- `questioner`: clarifies ambiguity and drafts the goal contract.
- `researcher-proposer`: researches and writes the proposal.
- `reviewers`: product, technical, risk, and verification reviewers.
- `adjudicator`: resolves reviewer/user/direction feedback and routes the workflow.
- `proposal-summarizer`: writes the user confirmation summary.
- `planner`: creates milestone checkpoints.
- `direction-evaluator`: decides whether the goal and plan still hold.
- `task-decomposer`: creates concrete tasks for a milestone.
- `executor`: executes exactly one concrete task.
- `result-verifier`: verifies exactly one concrete task.
- `final-summarizer`: writes completion evidence, gaps, and residual risk.

## File Write Scope

Repo scope writes under the target repo:

- `<repo>/plugins/meta-flow`
- `<repo>/.agents/plugins/marketplace.json`
- `<repo>/.codex/agents/*.toml`
- `<repo>/.codex/config.toml`

User scope writes under the current user home:

- `~/.codex/plugins/meta-flow`
- `~/.agents/plugins/marketplace.json`
- `~/.codex/agents/*.toml`
- `~/.codex/config.toml`

Task data under `.meta-flow/tasks` is not removed by uninstall.

## Uninstall

```bash
meta-flow uninstall --scope repo --yes
meta-flow uninstall --scope user --yes
```

Run a preview first:

```bash
meta-flow uninstall --scope repo --dry-run
```

## Safety

- No `postinstall` script modifies your system.
- The installer writes files only after explicit `meta-flow install`.
- No telemetry is collected.
- User code, config, and task content are not uploaded.
- Use `--dry-run` before installing.
- Existing unmanaged files are not overwritten unless `--force` is used.
- Overwrites support backups.
- Prefer pinned versions for reproducible installs.

## Codex Marketplace

You can also distribute the plugin through a Codex marketplace entry:

```bash
codex plugin marketplace add bx-h/meta-flow --ref v0.1.0
```

The npm installer still matters because it also materializes custom agent TOML files and validation scripts.

## Developer Docs

- [Architecture](docs/architecture.md)
- [Installation](docs/installation.md)
- [Publishing](docs/publishing.md)
- [Security](docs/security.md)
