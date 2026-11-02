# Publication journal

Working log of the publication of this repository. One entry per stage:
what was done, what verified it, deviations from `docs/publish/plan.md`.

| Stage | Scope | Status | Evidence |
|---|---|---|---|
| 0 | Scaffold: plan, journal, .gitignore | done | commit history, commit-style checker |
| 1 | Source inventory frozen | done | `docs/publish/inventory/`, grep gate |
| 2 | Linux build patch series + verification build | pending | |
| 3 | Tools: tgbuild, host, snapshot | pending | |
| 4 | Generated sources | pending | |
| 5 | Scrub and documentation | pending | |
| 6 | License and notice | pending | |
| 7 | README | pending | |
| 8 | Pre-publication hygiene | pending | |
| 9 | Publication | pending | |

## Stage 0 — Scaffold (2026-11-02)

- `git init` (branch `master`), repo-local identity:
  `user.name=superheher`, `user.email=[redacted-author-email]` (the value
  itself is in the git metadata of every commit, by design).
- `docs/publish/plan.md` — copy of the publication plan;
  `docs/publish/journal.md` — this journal; `.gitignore` — `build-input/`,
  `*.xip`, `*.o`, `__pycache__/`, `*.pyc`, editor droppings.
- Commit subject validated with `~/kit/commit-style/check_commit_msg.py`;
  the global commit-msg hook ran on commit.

Deviation from plan: the plan's example subject
"Documented **the** publication plan…" is rejected by the checker (no
articles allowed). Subjects here and below are reworded to satisfy the
checker; the plan file's examples are left as-is.

Deviation from plan (same stage): the verbatim copy of the plan carried
the literal private identifiers the plan itself says must never be
published (Apple ID, UDID prefix, team ID, private branch and account
names). Because the repository will become public and its early history
would carry those values, the plan copy was scrubbed with the §5
replacement table **before** the first commit, and the whole history was
recreated so no blob in any commit ever contained them. The plan copy
therefore reads `[redacted-*]` where the original had the literals.

## Stage 1 — Source inventory (2026-11-02)

Frozen into `docs/publish/inventory/` (see its README):

- `worktree-2026-11-02.diff` — the uncommitted tail of the source working
  tree (351 lines; checked for forbidden words before import: none).
- `status-2026-11-02.txt` — `git status --short` at freeze time.
- `untracked-2026-11-02.txt` — 206 untracked files with byte sizes,
  largest first (the 2 GB `.xip` tops it; never published).
- `commits-since-base.txt` — the 11 commits between base `fb0e62ba8a`
  and the source branch tip; author handles scrubbed to `[redacted]`,
  hashes and subjects verbatim.
- `checksums-2026-11-02.sha256` — 598 files checksummed across
  `tools/tgbuild`, the imported docs, `docs/receipts/`,
  `docs/tgbuild-sdkfree-snapshot/` and `$HOME/dev/omarchy-apple-dev`
  (minus `.git`, `sdk-free/sdk-cache/`, `tools/darwin-tools/`).

Gate: the forbidden-word grep of `docs/publish/plan.md` §2 rule 3
(the pattern itself names the words, so it is not quoted here) over the
whole tree → 0 matches.
