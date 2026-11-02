# Source inventory, frozen 2026-11-02

The publication inputs were frozen on 2026-11-02 so later changes to the
upstream working tree cannot invalidate what was imported, and so every
imported file can be identified by checksum.

| File | Contents |
|---|---|
| `worktree-2026-11-02.diff` | Uncommitted tail of the source working tree at freeze time (`git diff`). |
| `status-2026-11-02.txt` | `git status --short` of the source tree at freeze time. |
| `untracked-2026-11-02.txt` | Untracked files with byte sizes, largest first. The 2 GB Xcode `.xip` tops the list; it is machine-local and never published. |
| `commits-since-base.txt` | The 11 commits between upstream base `fb0e62ba8a` and the source branch tip. Input for the patch triage (stage 2). |
| `checksums-2026-11-02.sha256` | sha256 of every file imported or considered for import, grouped by source directory. |

Notes:

- Base commit: `fb0e62ba8a` ("Bump version", upstream `TelegramMessenger/Telegram-iOS` master).
- Paths in `checksums-2026-11-02.sha256` are relative to the base directory
  stated in each section header (`$HOME/dev/Telegram-iOS`,
  `$HOME/dev/omarchy-apple-dev`), so the file carries no absolute host paths.
- Excluded from checksumming and from publication (machine-local,
  regenerable or private): `omarchy-apple-dev/.git`, `omarchy-apple-dev/sdk-free/sdk-cache/`
  (3.4 GB SDK cache), `omarchy-apple-dev/tools/darwin-tools/` (304 MB of
  host binaries; only build recipes for them are published).
- Identifiers pointing at private context (branch names, author handles)
  in these frozen records are replaced with `[redacted]`; commit hashes
  and subjects are kept verbatim.
