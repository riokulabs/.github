# CLA setup: one-time manual steps

The CLA text (`CLA.md`, `CLA-ENTITY.md`) and the workflow (`templates/common/.github/workflows/cla.yml`) are in this repo. Everything runs in GitHub Actions; there is no server to deploy. These steps are done by hand, by the org owner, on github.com. Do them in this order. Until step 5 is done, do not push a repo that contains the synced `cla.yml`: the job would fail on every pull request.

1. **Tag.** `CLA.md` and `CLA-ENTITY.md` are final (no legal review, the maintainer's decision 2026-10-20). The commit is tagged `cla-v1.0` locally; push the tag with the `.github` repo. The workflow and CONTRIBUTING link to `blob/cla-v1.0/CLA.md`, so the text people sign stays fixed.

2. **Fork the action.** Done 2026-10-20: `riokulabs/cla-action` forked from `iainmcgin/cla-github-action` (default branch at `786020d9a25a88bcbf0cf12dc6b260e61d736355` = v3.2.0 `0d27e5a1` + a README-only commit). Hardening done 2026-10-20 (`docs/cla-action-review.md`): the allowlist patch is applied and tagged `v3.2.0-rioku.1` (`0b62b0cd03d96b423726bebff3bfaf7bdd078881`); an allowlist entry now only exempts commits linked to a GitHub account, and wildcards match the whole login. Tests passed and `dist/` was rebuilt from a clean `npm ci` with no diff. The allowlist still holds no human login.

3. **Create the signatures repo.** Create `riokulabs/cla-signatures`, **private**, default branch `main`, with only a README. Do not create `signatures/v1/cla.json`; the action creates it on the first run. Add a ruleset on `main`: block deletion and force pushes. If you also require pull requests there, add the CLA App (step 4) as a bypass actor, or the bot cannot write. Clone it into the workspace backups so the signatures have a second copy.

4. **Create the GitHub App.** Org settings > Developer settings > GitHub Apps > New GitHub App, for example `riokulabs-cla-bot`. Homepage URL: `https://rioku.dev`. Turn the webhook off. Repository permissions: **Contents: Read and write**, nothing else (Metadata: read is added automatically). "Only on this account". Create it, note the **App ID**, and generate a **private key** (a `.pem` file; never commit it). Install the App on the org with **Only select repositories: `cla-signatures`**.

5. **Org variable and secret.** Org settings > Secrets and variables > Actions:
   - Variable `CLA_APP_ID` = the App ID.
   - Secret `CLA_APP_PRIVATE_KEY` = the whole contents of the `.pem` file. Then delete the local `.pem` or keep it in your password manager only.
   - Repository access for both: "Selected repositories", the repos that have `cla.yml` (`se2-data-center`, `se2publish`, `se2diag`, `riokulabs-site`).
   - Note: `actions/create-github-app-token` now prefers `client-id` over `app-id`. `app-id` still works and only logs a deprecation notice. To switch later, add a variable `CLA_APP_CLIENT_ID` with the App's Client ID and change `app-id:` to `client-id:` in the template.

6. **Sync.** `cla.yml` is pinned to `0b62b0cd…` (`v3.2.0-rioku.1`) and `codeowner` is `derrickmehaffy` (done 2026-10-20). Run `tools/sync-github-structure.py --all` (dry run), check the diff, then `--apply`, and commit in each repo.

7. **Test from a second account.** With a second GitHub account that is not on the allowlist, fork one public repo, push a signed-off commit, and open a pull request. Check that:
   - the `CLA Assistant` check fails and the bot comments with the sign phrase and the CLA link;
   - commenting `I have read the Rioku Labs CLA and I hereby sign it` makes the check pass (the bot re-runs the failed run);
   - `signatures/v1/cla.json` appears in `riokulabs/cla-signatures` with the test account's login and numeric ID;
   - commenting `recheck` re-runs the check;
   - after you merge (or close and reopen) the PR, the conversation is locked only on merge.
   Remove the test account's entry from `cla.json` afterwards if you do not want it kept.

8. **Make the check required.** In each repo's `main` ruleset, add the status check **`CLA Assistant`** next to `guard`, `data`, `lint` and `Conventional Commits, no AI attribution`. It only appears in the list after it has run once (step 7).

9. **Keep DCO sign-off.** Leave the org setting "Require contributors to sign off on web-based commits" on. The CLA (once per person) and the DCO sign-off (each commit) do different jobs.

## Later

- **Guardians.** When a guardian posts the guardian comment from `CLA.md` section 8.2, record it by hand in `cla-signatures` (`guardians/<login>.md`: both logins, numeric IDs, the PR and the comment link). If a minor contributes without a guardian, merge only if you accept that code staying GPL-only; label the PR `cla:minor-gpl-only`.
- **Entity CLAs.** Store the signed PDF and Schedule A in `cla-signatures/entities/<organisation>/`. Designated Contributors still post the normal signing comment.
- **A new CLA version** that changes rights: new `CLA.md` version and tag (`cla-v2.0`), new `path-to-signatures` (`signatures/v2/cla.json`), update `path-to-document`, sync.
- **The `.github` repo itself** does not get `cla.yml` (`repos/.github.toml` excludes `.github/workflows/*`). PRs to it are not CLA-checked; review them by hand, or add a copy of the workflow there.
