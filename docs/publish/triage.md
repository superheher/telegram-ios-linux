# Patch triage: source state → Linux build series

The publication source tree carries two entangled change sets on top of the
upstream base `fb0e62ba8a`: application-feature work (belongs to a fork, never
published here) and the Linux build adaptation (published as `patches/`). They
cannot be separated by branch arithmetic — the build adaptation was never
committed; it lived in the working tree and inside a stash that a later rebase
left dangling in the source repository.

Sources used for the triage:

- The dangling stash `cffaf28090` ("tgbuild-infra-1031", 2026-10-31) — 101
  files, recovered from the source repository's object database. It is the
  Linux build adaptation as of 2026-10-31, diffed against the base + one
  unrelated feature commit.
- The source tree's current working state (2026-11-02) — the post-rebase
  restoration of the runtime fixes, newer than the stash for three files.
- The build journals (`linux-build-2026-10-25.md`, `linux-build-next-session.md`)
  and the phase receipts, which list the expected build changes and their
  reasons.

## Series composition (8 patches)

| Patch | Files | Source |
|---|---|---|
| 0001 Bazel host builds | `MODULE.bazel` (wasi-sdk pin arm64→x86_64-linux), `third-party/webrtc/BUILD` (x86_64 arch cflags/sources, ALSA, V4L2, missing static-lib TUs), `third-party/webrtc/absl/BUILD` (curated list → `glob()`), `third-party/webrtc/crc32c/BUILD` (SSE4.2 branch) | stash |
| 0002 third-party codecs | `third-party/wamr/BUILD` (x86_64 native invoke), `third-party/openh264/BUILD` (NEON guarded), `third-party/subcodec/src/mbs_mux_common.{h,cpp}` (NEON guards, out-of-line inline), `third-party/libjxl/libjxl/BUILD.bazel` → `BUILD.bazel.upstream` (subpackage shadowed the outer glob) | stash (+ the `.upstream` half of the rename from the source tree's untracked file) |
| 0003 MtProtoKit headers | ~50 `PublicHeaders/MtProtoKit/*.h`: nullability annotations, generic-dictionary removal where the Linux importer cannot bridge | stash |
| 0004 compile hooks | `TLObjectSupport.swift` (responds-to guard for `tl_constructorInfo`), `Network.swift` (keychain @objc id-form under `#if TGBUILD`), `WebProxyTransport` diagnostics + availability, `TabBarComponent.swift` (direct AsyncDisplayKit import), `UIBarButtonItem+Proxy.h` (`@class` instead of the cross-module import), `DocumentCanvasView+EditMenuActions.swift` + `TranslateScreen.swift` (`_Translation_SwiftUI` import) | stash |
| 0005 breadcrumbs | `main.m` (`tglog` + heartbeat), `ChatListNode.swift`, `ChatControllerNode.swift`, `ApplicationContext.swift` — all diagnostic output to `Documents/tgbuild-log.txt` behind `#if TGBUILD` | stash |
| 0006 runtime fallbacks | `AppDelegate.swift` (tgbuildLog helper + breadcrumbs, App Group container fallback, Siri authorization stubs), `CloudData.swift` (CloudKit stub → async error) | current working tree (2026-11-02 restoration, newer than the stash) |
| 0007 Metal runtime compile | `MetalEngine.swift` + 16 component Metal loaders: `makeDefaultLibrary` fallback that inlines the bundle's `#include "…"` and compiles MSL at runtime (the Linux package ships `.metal` sources without a compiled metallib) | MetalEngine from the current tree (richer than the stash's), 16 loaders from the stash (the output of `tools/tgbuild/patch_metal_loaders.py`) |
| 0008 TgVoipWebrtc submodule | `tgcalls/group/GroupInstanceReferenceImpl.cpp` (`#include <mutex>`), `macos/PublicHeaders/TgVoipWebrtc/OngoingCallThreadLocalContext.h` (ungeneric dictionary) — applied inside the submodule checkout | submodule working tree |

## Decisions on overlapping files

Six files carry both feature and build changes in the source tree. Each of
their hunks was classified:

| File | Decision |
|---|---|
| `AppDelegate.swift` | Build hunks only, from the current tree (the 2026-11-02 restoration). The stash's version has the same fixes plus extra session breadcrumbs (`dl ~NNN`) and unguarded `tgbuildLog` calls that would not compile upstream — not taken. Its `#if canImport(RecaptchaEnterprise)` hunks are superseded by the stub-module approach in `tools/tgbuild` (the import resolves against a generated stub), so they are not taken either. |
| `CloudData.swift` | Current tree version: timer-based async error emission, refined from the stash's plain async. |
| `MetalEngine.swift` | Current tree version: directory scan with `#include` inlining and logging; the stash held an earlier single-file variant. |
| `TabBarComponent.swift` | Stash version (direct `import AsyncDisplayKit` + the comment explaining the ClangImporter shadowing); the current tree has the same import without the comment. |
| `UIBarButtonItem+Proxy.h` | Stash version (`@class ASDisplayNode` + the comment); same code as the current tree. |
| `ApplicationContext.swift` | Only the stash's `#if TGBUILD` diagnostic hunks; the current tree's other hunks there are the sync-contacts feature — excluded. |

## Excluded (feature work, not published)

All remaining files of the source tree's diff against the base: the 11 feature
commits (hidden accounts, QR login, camera memory, sync-contacts default,
share button, fast forward, passkey crash fix, list-view loop, test server
switch, add-to-emoji-set, album caption edit) plus the uncommitted tail files
`BotPaymentsUI/BotCheckoutControllerNode.swift`, `FaceScanScreen/AgeNet*.swift`,
`TabBarComponent` feature hunks, feature docs and asset changes.

The `submodules/TgVoipWebrtc/tgcalls` submodule shows as dirty in the source
tree; only its two build hunks above are published (patch 0008). Its pointer
is unchanged.

## Completeness control

- `git diff --name-only fb0e62ba8a` over the series == the stash's 101 files
  (with `BUILD.bazel` deleted and `BUILD.bazel.upstream` added) + the three
  files taken at their current-tree version — no file missed, no file extra.
- For the 98 files taken from the stash, the series' blob hashes equal the
  stash's (byte-identical).
- Series diffs contain none of the forbidden identifiers (gate greps clean).
- Acceptance build: a fresh worktree at the base with the series applied must
  pass `extract.py`, the `swift.py //submodules/TelegramUI:TelegramUI --min 16.0`
  ladder and `link.py --app` (journal records the run).
