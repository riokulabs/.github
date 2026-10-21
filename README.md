# riokulabs/.github

The one place the shared GitHub setup for every Rioku Labs repository is edited. GitHub also uses this repository's community health files (CODE_OF_CONDUCT, CONTRIBUTING, SECURITY, SUPPORT, issue forms, PR template) as defaults for org repos that have no copy of their own, and shows `profile/README.md` on the org page.

Each repository still carries its own full copy so it works when cloned alone. The copies are generated from `templates/` by `tools/sync-github-structure.py`. Do not edit the copies; edit the templates and sync.

```
templates/common/      files every repo gets
templates/<kind>/      replaces the common file of the same path (kinds: mod, tool, website, org)
repos/_defaults.toml   variables for all repos
repos/<name>.toml      per-repo variables: target path, kind, test commands, PR checks, keep/exclude lists
tools/sync-github-structure.py   render and copy (dry run by default)
tools/check-issue-forms.py       validate issue forms and YAML
profile/README.md      org profile (shown on github.com/riokulabs)
CLA.md, CLA-ENTITY.md  the Contributor Licence Agreement (individual and entity); linked by every repo's CONTRIBUTING
docs/cla-setup.md      one-time manual steps for the CLA bot (fork, signatures repo, GitHub App, required check)
docs/cla-action-review.md  review of the CLA action we fork
```

See `../GITHUB-SETUP.md` for the workflow and the manual GitHub steps.
