# Contributing

Contributions should preserve the core meta-flow role boundaries:

- Reviewers do not route.
- Adjudicator does not write code.
- Executor handles one concrete task.
- Result verifier verifies one concrete task and does not fix code.
- Direction evaluator decides whether the goal or plan still holds.

Before opening a pull request, run:

```bash
npm test
npm run verify
npm pack --dry-run
```

Do not add dependencies unless the benefit is clear and the security impact is documented.
