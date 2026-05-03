# Branch Workflow

This repo uses `develop` as the normal working branch.

## Rules

- Do day-to-day work on `develop`.
- Do not commit on `main`.
- Do not push directly to `main`.
- Pushes from branches other than `develop` are blocked locally by default.
- Merge to `main` through a `develop -> main` pull request.
- `main` is the production deployment branch.
- After a merge to `main`, GitHub Actions syncs `main` back into `develop` automatically.

## Local guardrails

`core.hooksPath` is configured to `.githooks`.

Active hooks:

- `.githooks/pre-commit`
  - blocks commits on `main`
- `.githooks/pre-push`
  - blocks pushes unless the current branch is `develop`
  - blocks direct pushes to `main`


## Normal flow

```bash
git checkout develop
# work
git add <files>
git commit -m "Your change"
git push <remote> develop
# then open a PR: develop -> main
# after merge, main is synced back into develop automatically
```

## Temporary overrides

Use these only when you intentionally need to bypass the defaults:

- `GAHYEONBOT_ALLOW_MAIN_COMMIT=1`
- `GAHYEONBOT_ALLOW_NON_DEVELOP_PUSH=1`

Examples:

```bash
GAHYEONBOT_ALLOW_MAIN_COMMIT=1 git commit -m "Emergency hotfix"
GAHYEONBOT_ALLOW_NON_DEVELOP_PUSH=1 git push <remote> main
```
