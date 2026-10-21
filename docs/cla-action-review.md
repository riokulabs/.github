# Review: `iainmcgin/cla-github-action` v3.2.0 (to fork as `riokulabs/cla-action`)

Reviewed 2026-10-20, read-only, from the public repository at commit `0d27e5a16278d4adb6b0c4b92f08ad27b0a21dc8` (tag `v3.2.0`, "Cut v3.2.0", 2026-06-17, commit signature verified by GitHub). Files read: `action.yml`, `CHANGELOG.md`, `README.md`, `package.json`, `LICENSE`, and every file under `src/`. `dist/index.js` (1.25 MB, the code that actually runs) was scanned, not read line by line. Nothing was built or run.

**Verdict: fit to fork and use, with one small patch recommended before tagging `v3.2.0-rioku.1`** (allowlist on unlinked authors, below). Nothing found that sends data anywhere but the GitHub API, runs pull request code, or needs more access than listed.

## Patch applied (2026-10-20)

The allowlist patch from risk 2 is in `riokulabs/cla-action` as tag `v3.2.0-rioku.1`, commit `0b62b0cd03d96b423726bebff3bfaf7bdd078881` (upstream `v3.2.0` plus a README commit and the patch). `checkAllowList` now exempts a committer only when it has a non-zero GitHub user ID, matched on the login; unlinked committers, and email entries, are never exempted, and they still fail as unlinked. Wildcards are anchored (`^…$`), and regex metacharacters other than `*` stay literal. Unit and integration tests cover a spoofed unlinked `dependabot[bot]`, the linked `dependabot[bot]`, and `*[bot]` against `evil[bot]x`. `npm test` passed (143 passed, 1 skipped), and `dist/` rebuilt from a clean `npm ci` (Node 24.18.0) matched the committed file byte for byte. `cla.yml` is pinned to that SHA.

## What it does

A Node 24 JavaScript action (`runs.using: node24`, `main: dist/index.js`), Apache-2.0, forked from SAP's archived CLA Assistant Lite (`contributor-assistant/github-action`). On each pull request event and on PR comments it:

1. Lists the PR's commits through the GraphQL API (paginated), collecting each commit's author (or committer) as a GitHub login and numeric ID, plus anyone named in `Co-authored-by:` trailers. The PR opener is always added. The `github-actions[bot]` ID is dropped.
2. Removes allowlisted names.
3. Reads the signatures JSON from the remote repo (`remote-organization-name`/`remote-repository-name`, `path-to-signatures` on `branch`) with the `PERSONAL_ACCESS_TOKEN` env token. If the file is missing (404) it creates `{"signedContributors": []}`.
4. Reads all PR comments (paginated). A comment signs when the sign phrase is on its own line (case-insensitive, trailing `.`/`!` ignored, not inside a `>` quote) and the rest of the comment is short. Only comments from people in the "not signed" set count; comments by `github-actions[bot]` never count.
5. Appends new signers to the JSON (one commit per signing event) and posts or updates its PR comment listing who still has to sign.
6. Fails the job (`core.setFailed`) until everyone has signed. The check is the job's own check run, so the required check is the job name, `CLA Assistant`.
7. After a signing comment, re-runs the latest failed `pull_request_target` run of this workflow on the PR's head branch, so the PR's check turns green.
8. On `closed` with `merged`, locks the PR conversation so signing comments cannot be edited. On `reopened`, removes a stale lock.

Stored per signer (`src/interfaces.ts`): login (`name`), numeric `id`, `comment_id`, `created_at`, `repoId`, `pullRequestNo`. The comment body is stripped before saving. No name or email of linked users is stored.

## Inputs we use

| Input | Our value | Note |
|---|---|---|
| `path-to-document` | `https://github.com/riokulabs/.github/blob/cla-v1.0/CLA.md` | Link only, shown in the bot comment. Tag `cla-v1.0` must exist. |
| `remote-organization-name` / `remote-repository-name` | `riokulabs` / `cla-signatures` | Switches storage to the remote repo and to `PERSONAL_ACCESS_TOKEN`. |
| `branch` | `main` | Default in the action is `master`. |
| `path-to-signatures` | `signatures/v1/cla.json` | One file for the org. |
| `custom-pr-sign-comment` | `I have read the Rioku Labs CLA and I hereby sign it` | Same phrase the bot asks for and accepts. |
| `allowlist` | owner login, `dependabot[bot]`, `github-actions[bot]` | Exact names, no wildcards (see risks). |
| `signed-commit-message`, `create-file-commit-message` | Conventional-Commit style | Cosmetic, in the signatures repo. |
| `lock-pullrequest-aftermerge` | `true` | Default. |
| `require-opener-as-author` | `true` | Default; fails if the PR opener authored none of the commits. |

Not used: `use-dco-flag` (we keep the DCO as a sign-off, not as this bot's mode), `custom-notsigned-prcomment`, `custom-allsigned-prcomment`, `suggest-recheck`.

Env: `GITHUB_TOKEN` (required; PR comments, GraphQL, workflow re-run, lock) and `PERSONAL_ACCESS_TOKEN` (required for remote storage). We pass a GitHub App installation token in `PERSONAL_ACCESS_TOKEN`; the code only needs a token with contents read/write on the signatures repo.

## Permissions

- Workflow `GITHUB_TOKEN`: `actions: write` (list workflows and runs, re-run), `pull-requests: write` (comments via the issues API, GraphQL PR commits, lock/unlock), `contents: read`. **`statuses: write`, which the README lists, is not needed:** nothing in `src/` creates commit statuses (`createCommitStatus` appears in `dist/` only inside Octokit's endpoint table). Dropped in our workflow.
- App token: `contents: write` on `riokulabs/cla-signatures` only (`permission-contents: write` narrows it even if the App is later given more).

## Risks and notes

1. **`pull_request_target`.** The workflow runs with secrets on fork PRs. The action never checks out the PR and reads only API data, so this is safe as long as nobody adds `actions/checkout` or a `run:` step that uses PR content. The workflow and `AGENTS.md` say so. The comment body appears only in the job `if:`, never in a shell.
2. **Allowlist matches unauthenticated names (recommended patch).** For a commit whose email is not linked to a GitHub account, the committer "name" is the raw git author name, which anyone can set. `checkAllowList` matches that name (and the email) against the allowlist, so an unlinked commit authored as `dependabot[bot]` or as the owner's login is treated as allowlisted. Wildcard patterns are also unanchored regexes (`bot*` matches `robotics`). Impact is limited: the PR opener must still sign, and must have authored at least one commit (`require-opener-as-author`). Mitigation now: exact logins only, no wildcards (done). Patch for the fork: in `src/checkAllowList.ts`, apply the allowlist only when `committer.id` is non-zero, and anchor the wildcard regex (`^...$`). Add a unit test, rebuild `dist/`.
3. **`Co-authored-by` trailers** add people to the set that must sign; they cannot make an unsigned person pass. Noreply-form trailers are trusted for login and ID, which only ever adds requirements.
4. **`dist/index.js` is a bundled build** and is what runs. A scan found only GitHub API hosts (`api.github.com`, `uploads.github.com`) as live endpoints; the other URLs are spec links in bundled libraries. `child_process` appears only in `@actions/exec` (bundled, not called by `src/`); no `eval`. Before tagging the fork, rebuild from source (`npm ci && npm run build`) on a clean machine and check the result matches the committed `dist/`, or commit your own build.
5. **Signatures branch protection.** The action writes straight to `branch`. Its message says the branch must not be protected. Use a ruleset on `cla-signatures` `main` that blocks deletion and force pushes, and give the CLA App a bypass for "require pull request", rather than classic protection that blocks the App.
6. **Re-run lookup by workflow name.** `reRunLastWorkFlowIfRequired` finds this workflow by its `name:` (`cla`). Do not give another workflow in the same repo the same name.
7. **Maintenance.** The upstream fork says it is maintained "for internal use only". Treat `riokulabs/cla-action` as ours: watch upstream for fixes, and turn on Dependabot for its npm dependencies (`@actions/core`, `@actions/github`, `@octokit/plugin-retry`).
8. **Licence.** Apache-2.0. Keep `LICENSE` in the fork; there is no `NOTICE` file. Mark our changes in `CHANGELOG.md`.

## Fork checklist

1. Fork at `0d27e5a16278d4adb6b0c4b92f08ad27b0a21dc8` into `riokulabs/cla-action`.
2. Apply the allowlist patch (risk 2), run `npm ci && npm test && npm run build`, commit `src/` and `dist/` together.
3. Tag `v3.2.0-rioku.1`, copy the full commit SHA into `templates/common/.github/workflows/cla.yml`, sync.
