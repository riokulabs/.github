---
name: prepare-release
description: Prepare a release of @@name@@ - version, changelog section, tag command. Use when asked to cut, prepare or draft a release. Prepares only; never tags, pushes or publishes.
---

# Prepare a release of @@name@@

Do these in order and stop before anything leaves the machine.

1. Working tree clean, on `main`, `scripts/test.sh` passes.
2. Pick the version (Semantic Versioning) from the commits since the last tag: `git log --oneline $(git describe --tags --abbrev=0)..HEAD`.
3. Draft the changelog section: `scripts/changelog.sh <version>`. Edit the wording for users, then add it under the right heading in `CHANGELOG.md` (format: `## [x.y.z] - YYYY-MM-DD`, Keep a Changelog groups).
@@release_steps|raw@@
4. Commit as `chore(release): <version>`.
@@tag_step|raw@@

Never push, tag or publish yourself.
