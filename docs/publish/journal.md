# Publication journal

Working log of the publication of this repository. One entry per stage:
what was done, what verified it, deviations from `docs/publish/plan.md`.

| Stage | Scope | Status | Evidence |
|---|---|---|---|
| 0 | Scaffold: plan, journal, .gitignore | done | commit history, commit-style checker |
| 1 | Source inventory frozen | done | `docs/publish/inventory/`, grep gate |
| 2 | Linux build patch series + verification build | done | `patches/`, `docs/publish/triage.md`, verification run (below) |
| 3 | Tools: tgbuild, host, snapshot | done | `tools/`, vendored extract run |
| 4 | Generated sources | done | `tools/generated/` |
| 5 | Scrub and documentation | done | `tools/scrub.py`, `docs/journal/`, `docs/receipts/`, the four docs |
| 6 | License and notice | done | `LICENSE`, `NOTICE.md` |
| 7 | README | done | `README.md` |
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

## Stage 2 — Patch series (2026-11-02/03)

The build adaptation was recovered from a dangling stash in the source
repository (`cffaf28090`, "tgbuild-infra-1031", 2026-10-31, 101 files — the
uncommitted Linux build adaptation a branch reorganization had swept out of
the working tree). Hunk-level triage against the current source state and the
journals produced the 8-patch series; full details and per-file decisions in
[`triage.md`](triage.md).

- Series committed in a scratch worktree at the base, exported with
  `git format-patch`, imported as `patches/0001–0008` + `series` +
  `apply-patches.sh` + `base-commit`.
- Patch 0008 is the TgVoipWebrtc submodule's two build hunks, applied inside
  the submodule checkout by `apply-patches.sh`.
- **Dry run**: fresh shared clone at `fb0e62ba8a` + `apply-patches.sh` → 7
  commits land, resulting tree hash identical to the series worktree's
  (`9b95b528e0e0…`), author/committer `superheher` on every commit.
- Completeness: series file set == stash set (with the libjxl rename
  completed); 98 files byte-identical to the stash; 3 files taken at the
  newer current-tree version; series diffs grep-clean of forbidden words.
- **Verification build** (fresh worktree of the base + series + generated
  sources + copied caches with preserved mtimes):
  - `extract.py`: green — 1495 targets, 1009 modules, ~53 s;
  - `swift.py //submodules/TelegramUI:TelegramUI --min 16.0 --jobs 3`: green —
    the whole ladder including TelegramCore (718 files, the known
    clang-importer source-order retry) and TelegramUI; mostly cache hits, the
    modules containing patched sources recompiled;
  - `link.py --app`: recorded below with the run's output.

Deviation from plan: the plan expected the series to come from
"base + 11 feature commits − features"; in reality the build adaptation was
never part of any commit — the stash is where it lived. Also the wasi/Bazel
host fixes, MtProtoKit nullability and the 15 Metal loader patches were no
longer in the working tree at freeze time; the stash restored them.

## Stage 3 — Tools (2026-11-03)

- `tools/tgbuild/` vendored from the frozen inventory list (no
  `__pycache__`), with four parameterization edits, all documented:
  `patch_metal_loaders.py` derives REPO from its own location instead of the
  hard-coded host path; `link.py` takes the sdk-cache root from
  `TGBUILD_XTOOLSDK` and clang from `TGBUILD_CLANG` (the two `-L` clang
  runtime paths follow the root); `objc.py` takes the cc.sh path from
  `TGBUILD_CC`; `swift.py` lost two debug prints, its `--min` default is 16.0
  and its help text now states the min-17 fold behavior correctly (the old
  note claimed the compiler folds availability checks at min < 17 — the
  2026-11-02 IRGen diff proved the opposite).
- `tools/host/` vendored from omarchy-apple-dev (MIT): cc.sh,
  xip_extract.py, xip_version.py, install-toolchain.sh + a README mapping
  each file to its consumer.
- `tools/snapshot/`: authored files published as-is (Foundation.h, the 12
  sdkm framework modules, host-zlib modulemap, the authored darwin-usr-include
  files); the five Apple-licensed headers (objc-NSObject.h, libkern-OSAtomic.h,
  _time.h, sys-fcntl.h, sys/_types/_s_ifmt.h) are NOT published —
  `tools/snapshot/README.md` lists each with its origin and the one marked
  edit to reproduce.
- Acceptance: the vendored `extract.py` ran against the verification worktree
  and wrote `/tmp/graph.json` (1495 targets / 1009 modules); `grep -rn
  "/home/h" tools/` → 0 (remaining defaults are `~/…` + env overrides).

## Stage 4 — Generated sources (2026-11-03)

`tools/generated/` = TelegramApi (44 Api*.swift + TLApiSchemaData.m +
fixtures, Tests kept) and FlatSerialization (34 *_generated.swift), copied
verbatim from the frozen tree, with a README describing provenance (generated
from the upstream repo's GPL schemas), the SwiftTL host-build recipe and the
flatc v24.12.23 recipe. (The Siri-intents stand-in is in
`tools/tgbuild/stubs/` and compiled by `make-generated-sources.sh`.)

## Stage 5 — Scrub and documentation (2026-11-03)

- `tools/scrub.py` encodes the replacement table (§5 of the plan; public
  Telegram Desktop credentials kept, noted in NOTICE).
- 6 phase receipts imported into `docs/receipts/` (scrubbed: 5 files had
  host paths, one the Apple ID and team id ×6, one a device name), plus the
  3 impersonal screenshots with the full triage table in
  `docs/receipts/assets/README.md` (everything with chats/phone-entry/ui-walk
  withheld, reasons per file).
- Journals imported into `docs/journal/`: the three build journals (scrubbed;
  "rebase war" rephrased), `ui-gaps.md` (sections A/B/C/E whole; the walk
  section reduced to the build-relevant findings — Metal loaders, resource
  fixes, the open inset bug) and the walk methodology as `ui-walk-method.md`
  (audit, bundles, gap classes, fix-install cycle — the account walk not
  imported).
- New summaries written fresh: `docs/build-guide.md`,
  `docs/architecture.md`, `docs/status.md`, `docs/traps.md`.
- Acceptance: forbidden-word gate → 0; every markdown link in the repo
  resolves (script-checked); the guides read as build documents and do not
  reference "the next session".

## Stage 6 — License and notice (2026-11-03)

GPL-3.0 `LICENSE` (upstream's license; the patches and generated files are
derivatives). `NOTICE.md`: upstream base and license, the MIT vendored
scripts, the unofficial/trademark position in original words, the public
api_id/api_hash pair note.

## Stage 7 — README (2026-11-03)

`README.md`: what the pipeline does, what is verified (device/OS/arch),
pointer map, quick start (3 commands), status/scope, legal pointers.
