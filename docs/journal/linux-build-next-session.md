# Handoff: building Telegram-iOS from Linux — state and remaining work

Written 2026-10-25 end of day for the next session; **updated 2026-10-26: Phase 0 complete
(the Xcode 27.2 .xip arrived, full-SDK bundle built and registered — §1a)**. Read together with
[`linux-build-research-plan.md`](linux-build-research-plan.md) (the plan, maturity levels L0–L4),
[`linux-build-2026-10-25.md`](linux-build-2026-10-25.md) (running log) and
[`receipts/`](../receipts/) (phase evidence). This file is the session-entry point: everything
needed to continue without re-deriving.

## 1. One-paragraph state

**Updated 2026-11-02 evening — black screen root-caused and fixed; the authorized chat
list renders again.** Two stacked causes, both from the 2026-11-01 session:

1. **The 10-28 `#if TGBUILD` runtime fixes were lost from the tree** in the working-tree
   churn around the 11-01 branch reorganization (the App Group fallback in `AppDelegate.swift`, the CloudKit stub in
   `CloudData.swift`, the Siri stubs in `AppDelegate.swift`, and the tgbuildLog
   breadcrumbs). Without the fallback the launch took the silent `guard let
   appGroupUrl … presentNative("Error 2"); return true` — alive, heartbeats, forever
   black. All restored 2026-11-02 (`tgbuildLog(_:)` helper + breadcrumbs along
   didFinishLaunching are part of the restoration — keep them; they are the only
   app-level diagnostic channel, read via `pymobiledevice3 apps afc
   XTL-…ph.telegra.Telegraph` → pull `/Documents/tgbuild-log.txt`).
2. **The ladder had been recompiled with swift.py's default `--min 17.0`** (the 11-01
   rebuild), which FOLDS every `#available(iOS 17)`/`(iOS 26)` gate into an
   unconditional call — on the iOS 16.7 device the first such path aborts
   (`-[Display.ScrollToTopView setAllowsKeyboardScrolling:]: unrecognized selector`,
   SIGABRT ~1 s after launch, no .ips produced). Proven by IRGen diff: at min 16.0 the
   `$s_stdlib_isOSVersionAtLeast` runtime check survives, at min 17.0 it is folded away
   — the swift.py help note claiming "at min < 17 the compiler STILL folds" is WRONG.
   The GradientBackground/TranslateUI "pins" of 31.10 products were the same symptom,
   not a separate bug. **Fixed by a full ladder rebuild with `--min 16.0`; this flag is
   now LOAD-BEARING — every swift.py invocation must carry it** (the min-16 cache is a
   separate cache-dir tree, so min-17 products can silently come back if the flag is
   omitted). The RecaptchaEnterprise stub swiftmodule had to be re-emitted at min 16
   into BOTH `build-input/swift/prebuilt-frameworks/RecaptchaEnterprise.framework/…`
   AND `…/RecaptchaEnterprise.xcframework/ios-arm64_arm64e/…` (the import resolves
   through the xcframework slice; `-target`-min mismatch fails TelegramUI's import).
   After the rebuild: relink, install, launch — the authorized chat list renders with
   live rows and live list-view transitions (`enqueueTransition: 9 del / 9 ins` in the
   breadcrumb log), no crash reports.

**Updated 2026-10-28 evening — the Linux build launches *as itself* and renders its
onboarding screen with the "Linux NUC" marker.** Correction of the earlier claim: the
2026-10-27 "renders a signed-in chat list" and the morning "black screen fixed" evidence
belonged to the **official App Store Telegram** still installed on the phone — launches
by the canonical bundle id hit it, because xtool provisions our build as
`XTL-[redacted-team-id].ph.telegra.Telegraph`. The first real launches of OUR build surfaced a
chain of failures, all fixed with evidence in
[`receipts/2026-10-28-black-screen-fixed.md`](../receipts/2026-10-28-black-screen-fixed.md):
dyld (app rpath + `Frameworks/` + weak swift/Translation loads + a hand-written
`swift_allocateMetadataPack` shim — the Linux toolchain has no
libswiftCompatibilityPacks.a), the free profile's missing App Group entitlement (silent
early return → black window; `#if TGBUILD` fallback to the local container), the missing
iCloud entitlement (CloudKit trap; stubbed emergency-data source), and the TL_OBJC_DIRECT
contract (swift.py forwards `TL_OBJC_DIRECT=1` to the clang importer; the reladdered
build parses the first `help.getConfig` response and renders). Proof it is our build: the
onboarding title, the icon label, and the app name all read **"Linux NUC"**
(`receipts/assets/2026-10-28-linux-nuc-*.png`), and the app runs under the XTL- id signed
by the free team. Never launch by `ph.telegra.Telegraph` for proof — that's the official
app. The API credentials are wired
(`variables.bzl`: api_id 611335 / the user-provided hash; re-extract + BuildConfig
rebuild; see receipt §7) — the phone-entry screen renders and accepts input; the
user then **logged in successfully** — the two post-login crashes (the Siri-entitlement
assert in INPreferences, and TCC's privacy violation over the missing
`NS*UsageDescription` keys) are fixed (receipt §8), and the last black screen after login
is gone too (receipt §9): the Linux actool's Assets.car is unreadable by iOS 16 CoreUI,
so link.py now exports all five asset catalogs as loose namespaced image files
(rasterizing 1244 svg/pdf vector imagesets via cairosvg/pdftoppm) — **the authorized chat
list renders with live messages, avatars and tab icons**
(`receipts/assets/2026-10-28-linux-nuc-chat-list.png`).

**Next session's plan is written: [`next-session-ui-walk.md`](ui-walk-method.md) —
a read-only walk through the app to catalog and iteratively fix the graphical gaps
(static asset-coverage audit first, then screen-by-screen with the user driving the
touch screen). Then the six extensions, the real td/tde2e (stubs), the reference-core wasm
blob, and the remaining screen-local Metal bundles (same runtime-MSL pattern).

**Update 2026-10-28 ~23:40 — the walk's static half is done** (see
[`ui-gaps.md`](ui-gaps.md) and receipt §10): the audit tool
(`tools/tgbuild/audit_images.py`) found three link.py export bugs (shared catalog
namespaces wiping each other, raster imagesets exported under content filenames,
`//Telegram:Lib`'s app-root resource closure missing) and all 23 graph resource bundles
are now assembled into TelegramUI.framework. Post-fix audit: **0 force-unwrap lookups
missing**; the app was relinked, installed, relaunched — the chat list renders complete.

**Update 2026-10-29 — the walk is underway** (receipt §11): the user's first drive
opened the channel preview (ChatController not-a-member mode) — custom-emoji reactions,
inline GIF playback, link previews all render. The glass-buttons-as-white-squares gap
was root-caused (every component Metal loader's `makeDefaultLibrary` needs a compiled
metallib the Linux bundles can't carry) and fixed with a TGBUILD runtime source-compile
fallback in all 16 loaders (`tools/tgbuild/patch_metal_loaders.py`, idempotent);
rebuilt, installed 13:25, no crashes. Open: the preview's message column insets ~122 pt
from the right (root cause unknown), header blur backdrop, a "Video" preview white
square. The interactive walk (that doc's §3) continues: the user drives the touch
screen, the agent screenshots and fills the ledger.

## 1a. Full-SDK mode — what exists now (2026-10-26)

- `Xcode_27.2_Release_Candidate.xip` (2.0 GB, Xcode 27.2 / build 27B48 — the Xcode that
  matches Swift 6.4) was verified via `tools/xip_version.py`, then built with
  `xtool sdk build` into
  **`~/dev/omarchy-apple-dev/sdk-free/sdk-cache/darwin-iPhoneOS27.2.xtoolsdk`**
  (contains iPhoneOS27.2.sdk + iPhoneSimulator + MacOSX27.2.sdk) and registered
  (`xtool sdk install`; `swift sdk list` shows `darwin`).
- **The real iPhoneOS27.2.sdk has 318 frameworks** (sdk-free had 13).
- Smoke test: `MTAes.m` and `MTEncryption.m` — two of the 10 MtProtoKit files that failed
  on Security/CommonCrypto — compile to Mach-O arm64 with **zero errors** against the real
  SDK:
  ```sh
  export PATH=/usr/local/usr/bin:$PATH
  SR=~/dev/omarchy-apple-dev/sdk-free/sdk-cache/darwin-iPhoneOS27.2.xtoolsdk/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS27.2.sdk
  TC=$(dirname $(dirname $(readlink -f $(command -v swiftc))))
  $TC/bin/clang -target arm64-apple-ios16.0 -isysroot $SR -c -fmodules -fno-autolink \
    -I submodules/MtProtoKit/PublicHeaders -I submodules/MtProtoKit/Sources \
    -I submodules/EncryptionProvider/PublicHeaders \
    -fmodule-map-file=build-input/objc/EncryptionProvider/module.modulemap \
    -fmodules-cache-path=/tmp/fullsdk-mc  submodules/MtProtoKit/Sources/MTEncryption.m -o /tmp/x.o
  ```

## 1b. Full-SDK driver mode — DONE (2026-10-27)

Implemented exactly along the plan, with these deltas discovered on the way (recipes and
evidence in [`receipts/2026-10-27-fullsdk-switch.md`](../receipts/2026-10-27-fullsdk-switch.md)):

- **objc.py**: `TGBUILD_SYSROOT` / `TGBUILD_SDKFREE` env switching; stubs ignored entirely in
  full mode; SDK libc++ (`usr/include/c++/v1`) per C++ file only; sysroot in the object hash;
  one shared clang module cache for all invocations (per-invocation temp caches made C++ TUs
  rebuild Foundation/libc++ for minutes each).
- **cc.sh** (machine-local): clang resource include BEFORE the SDK's usr/include (the SDK's
  `float.h` is canary-wrapped — `_c_standard_library_obsolete` fires otherwise); `-iframework`
  for SubFrameworks (+PrivateFrameworks; the SDK has no PrivateFrameworks — the private
  headers live in **SubFrameworks**, which xtool's bundle dropped; restored from the .xip via
  `~/dev/omarchy-apple-dev/tools/xip_extract.py --no-clobber`, 4573 files).
- **swift.py**: synthesized resource dir (`build-input/swift/full-res`, symlinks to the
  toolchain's `lib/swift/{clang,shims}`) — the toolchain resource dir itself cannot be passed
  (its `os/` shims shadow the SDK's); `-I …/prebuilt-modules/27.2` — the device modules are
  **arm64e-only and import fine for arm64**; `-nostdinc` unnecessary; the hand-written
  `os`/`Network` Swift shims are dropped (the SDK has the real ones).
- **SDK cache**: exact-case symlinks `endian.h`→`Endian.h`, `CommonCrypto/CommonHMac.h`→
  `CommonHMAC.h` (APFS case-insensitivity the repo sources rely on).
- **WebProxyWebViewCarrier.swift**: real-SDK availability annotations (`@available(iOS 27.0)`
  / `(iOS 18.4)`) on the two WKUIDelegate methods — valid in both modes.
- Ladder result: 12/13 closure modules ok; TelegramCore open on §4.1.

## 1c. What remains user-gated: NOTHING for now

Apple ID ✅, phone ✅, Xcode .xip ✅. The next phases (full-mode switch, Display, the rest
of the graph, link/package, device install) are all autonomous.

## 2. Iteration loops (the commands that matter)

```sh
cd $HOME/dev/Telegram-iOS
export PATH=/usr/local/usr/bin:$HOME/.local/bin:$PATH   # Swift 6.4 toolchain

# Swift module driver (the main loop):
python3 tools/tgbuild/swift.py //submodules/TelegramCore:TelegramCore --force
#   └ per-module -emit-module + -c in dependency order, content-hash cache

# Full stderr for ONE Swift module (driver prints only the first error):
python3 tools/tgbuild/probe.py //submodules/TelegramCore:TelegramCore

# ObjC backend (modulemaps for all 78 objc_library targets already generated):
python3 tools/tgbuild/objc.py //submodules/MtProtoKit:MtProtoKit --force

# Link + package + install + launch (the end-to-end loop, ~5 min; see
# receipts/2026-10-28-black-screen-fixed.md):
python3 tools/tgbuild/link.py --app                # frameworks + binary + resources
cd build-input/link && rm -rf Payload Telegram.ipa && mkdir Payload && \
  cp -a Telegram.app Payload/ && zip -qry Telegram.ipa Payload && cd -
xtool install --usb build-input/link/Telegram.ipa
~/pymobiledevice3/bin/pymobiledevice3 developer dvt launch ph.telegra.Telegraph --kill-existing
idevicescreenshot /tmp/shot.png && idevicecrashreport -e /tmp/crashes | grep -i telegram

# After editing ANY sdkm/darwin header — the clang module cache is stale otherwise:
rm -rf build-input/swift/clang-cache

# After editing tools/tgbuild/overlay/*.swift (Foundation overlay + os/Network shims):
./tools/tgbuild/rebuild-foundation.sh

# Graph re-extract (after git pull / BUILD changes):
python3 tools/tgbuild/extract.py -o build-input/graph/modules.json

# Codegen (TelegramApi + FlatSerialization sources; outputs are untracked):
./build-system/SwiftTL/.build/out/Products/Release-linux-x86_64/SwiftTL \
  submodules/TelegramApi/swift_scheme.tl /tmp/gen/Generated --swift-file-count=44 \
  --objc-output=/tmp/gen/Generated --fixtures-output=/tmp/gen/Generated/Tests/SchemaFixtures.swift
#   then copy Api*.swift → submodules/TelegramApi/Generated/
/tmp/flatbuffers-24.12.23/build/flatc --require-explicit-ids --swift -o /tmp/fbsgen \
  submodules/TelegramCore/FlatSerialization/Models/*.fbs
#   then copy *_generated.swift → submodules/TelegramCore/FlatSerialization/
```

SwiftTL and flatc are host-built; rebuild recipes are in the Phase 3 receipt if `.build` or
`/tmp` were cleaned.

## 3. Machine-local state — the snapshot (IMPORTANT)

Half the toolchain is **outside this repo** (`~/.local/share/omarchy-apple-dev/sdk-free/…`)
and is not tracked by any git. **`docs/tgbuild-sdkfree-snapshot/`** is a faithful copy of
every file modified or created there (31 files, 392 KB):

- `darwin-usr-include/` — module.modulemap (added: `uuid`, `clock_shim`, `os_lock`,
  `os_base`, libkern `OSAtomic` submodules; Darwin→os cycle fix), `objc-NSObject.h`
  (`_Nonnull init` — THE root fix for Optional-init imports), `sys-fcntl.h`
  (overloadable non-variadic `open`), `sys__types__s_ifmt.h` (mode-typed S_* macros),
  `_time.h` (CLOCK_UPTIME_RAW added), `clock_shim.h`, `libkern-OSAtomic.h`.
- `sdkm-foundation-headers/Foundation.h` — the heavily extended hand-written Foundation
  (URL loading, JSONSerialization with typed options, NSKeyedArchiver/Unarchiver,
  NSRegularExpression, NSUbiquitousKeyValueStore, NSDecimalNumber*, NSOperationQueue,
  block observers, CFStringTokenizer subset, NSIndexSet family, NSStream/NSOutputStream,
  NSLock/NSRecursiveLock, NSThread, NSScanner, NSCharacterSet, NSUUID, NS_ROOT_CLASS,
  NS_CLOSED_ENUM with real `enum_extensibility`, `NS_ASSUME_NONNULL`-cleanup, clock ids
  as `static const clockid_t` after `#undef`).
- `sdkm-frameworks/` — twelve authored framework modules: WebKit, Security, CoreTelephony,
  Photos, LinkPresentation, CoreServices, CommonCrypto, SystemConfiguration, CloudKit,
  CoreText, AVFoundation (each `Headers/*.h` + `Modules/module.modulemap`).
- `host-zlib/module.modulemap` — for the host SwiftTL build.

**Restore after a machine reset** (or to diff drift):
`cp -r docs/tgbuild-sdkfree-snapshot/darwin-usr-include/<file> ~/.local/share/omarchy-apple-dev/sdk-free/swift/darwin/usr/include/<same-relative-path>` and likewise for `sdkm-frameworks/<fw>/{Headers,Modules}` → `.../sdkm/Frameworks/<fw>.framework/`. The Foundation overlay
Swift sources are already in-repo (`tools/tgbuild/overlay/`), so `rebuild-foundation.sh`
recreates `swift/ovl/*.swiftmodule` from them.

Repo-side uncommitted changes that MUST NOT be reverted: `tools/tgbuild/*` (the drivers),
`submodules/MtProtoKit/PublicHeaders/MtProtoKit/MTKeychain.h` (`#if TGBUILD` id-form),
`MTOutputStream.h`/`MTRequest.h` (nullability), `submodules/TelegramCore/Sources/Network/
Network.swift` (`#if TGBUILD` Keychain witness), `submodules/WebProxyTransport/Sources/
WebProxyDiagnostics.swift` (`#if canImport(os.log)`), `docs/`. Untracked generated sources
live in `submodules/TelegramApi/Generated/` and `submodules/TelegramCore/FlatSerialization/
*_generated.swift`.

## 4. Remaining phases, in order

### Phase 3 tail — TelegramCore (718 files)

The 2026-10-25 tail list is **gone** in full-SDK mode (items 2–6: `[Any]→Int`,
OSAtomicIncrement32, URLResourceKey family, Log.swift time-outs, NW shim — all resolved by
the real Foundation/Darwin/libdispatch modules; item 1 remains):

1. `EncryptionProvider` type invisible in the whole-module compile of TelegramCore
   (`ProcessSecretChatIncomingDecryptedOperations.swift:73`, the plain ObjC-protocol
   name) — **RESOLVED 2026-10-27 evening, as a driver workaround**. Root behavior: this
   compiler's ClangImporter is **source-order sensitive in whole-module compiles** — the
   exact same 718-file compile with the importing file placed first in the source list
   compiles cleanly (2/2 runs), driver order fails deterministically (2/2). swift.py now
   retries a failed pass once with the file named in the first "cannot find type" error
   moved to the front (source order carries no Swift semantics; a NOTE is printed when it
   fires). Investigation trail (import order, direct-header modulemaps — worse, reverted;
   the debug-probe masking; the false "stale cache fixes it") is in the receipt.
2. **Display** (153 files) fails the same way (`ASDisplayNode` invisible whole-module,
   single-file compiles fine) but is NOT healed by the rotation retry (the reporter-first
   order still fails) nor by clang-cache warming. Next steps: find Display's healer file
   by bisect (the TelegramCore healer was "the file importing the module first", here 87
   files import AsyncDisplayKit and the first of them is not sufficient), or reproduce
   the importer state bug upstream against this SDK.

### §4 continuation (unchanged in intent, updated numbers)

Then the ladder continues (each step = "next module compiles"):

- **Display (153 files)** — in full-SDK mode UIKit is Apple's real one; expect source-level
  availability/API drift only, not the overlay-authoring effort the sdk-free plan assumed.
  AsyncDisplayKit sits behind it.
- **The rest of the ~738 swift_library modules** toward TelegramUI (213 files + 523 deps).
  With the real SDK the remaining families are genuine availability/API drift and the
  odd `#if TGBUILD` patch.
- **111 objc/cc modules**: the full-SDK sweep runs with `--no-stubs` over the 57 roots in
  `/tmp/objc-roots.txt` (regenerate: any objc/cc target not depended on by another objc/cc
  target). Failures classify through objc.py's taxonomy.
- Acceptance for L0: every `swift_library`/`objc_library`/`cc_library` in
  `deps(//Telegram:Telegram)` has a cached build product (`meta.modules` count in
  modules.json = the checklist; rust modules are excluded — see Phase 6).

### Phase 4 — link and package (3–5 days est.)

- Link the main binary + TelegramUIFramework with `$SDKFREE_HOME/toolset/ld64.lld`,
  sysroot `$SDKFREE_HOME/iPhoneOS.sdk`; **InContext2 shim** (`/tmp/tgi/swiftshim.c` from the
  night session — recreate if /tmp was wiped; the C source is quoted in the baseline doc) and
  keep the shim list an explicit ABI contract with iOS 16.7.
- Inputs: `build-input/swift/objects/*.o` (Swift), `build-input/objc-cache/*/*.o` (ObjC),
  host `bazel-bin` archives for cc_libraries, prebuilt `td`/`ffmpeg` archives in-repo.
- Resources: `actool`/`ibtool` exist in `~/dev/omarchy-apple-dev/sdk-free/bin` (Linux
  builds); `.metal` → no Linux compiler: precompile once on a Mac/VM or ship `.metallib`
  (plan §5 lists the alternatives). Strings/codegen outputs already generate on Linux.
- Info.plist merge (values from `build-input/configuration-repository/variables.bzl`),
  entitlements, `.app` tree, ad-hoc sign with `rcodesign`, offline validation.
- Acceptance L1: `nm -u` clean against the SDK stub set; L2: `.app` passes `rcodesign`
  validation.

### Phase 5 — device loop (1–2 days, user present once)

`xtool auth` is DONE (`xtool auth status`: [redacted-apple-id], Team ID [redacted-team-id], token
to 2027-10). The iPhone X is connected and visible (`xtool devices`; if "Operation not
permitted" — `sudo systemctl restart usbmuxd`, that was the fix once already). Then:
`xtool install <App.ipa>` (free-ID signing happens on install), `xtool launch`, syslog via
`pymobiledevice3 syslog live`, screenshot for the receipt. Acceptance L3: process alive
10 s, first screen renders.

### Phase 6 — completeness (parallelizable)

- The 6 extensions (each = a small Phase 4: own binary/plist/profile).
- Incremental-cache correctness: hash inputs are srcs+flags+modulemap today; add the SDK
  hash. `tgbuild --check` diffing module lists against `bazel query` after pulls.
- rust modules (159 of them: mtproto-engine, wallet-engine, tlottie) have NO Linux backend
  and are the one structural gap in L0 — `Cargo.Bazel.lock` has zero linux triples; fixing
  needs rustup + lockfile regen behind a flag (touches a Mac-shared lockfile — the plan says
  do it on a branch).
- TelegramCore unit tests where host-runnable.

### Phase 7 — native Bazel backend (optional, explicitly last)

Turn the drivers into a real `swift_toolchain` + crosstool registered from `build-system/`
so plain `bazel build` works. Engineering polish, not a milestone.

### User-gated (the single item)

**Xcode .xip** (~15 GB): switches sdk-free to full mode — real headers for every framework.
When it lands: `objc.py --no-stubs`, delete the authored framework modules one by one,
re-run the closures; any file that then fails marks a stub that lied. Until then everything
above proceeds without it.

## 5. Traps the next session should not re-derive

- **cquery cannot run on Linux** (analysis needs the Apple toolchain). Use `bazel query`.
- **`-nostdinc`** in the Swift driver is load-bearing: without it the host glibc leaks in
  (`open` imports variadic-unavailable). The clang resource dir
  (`/usr/local/usr/lib/clang/21/include`) must be re-added explicitly.
- **clang module cache** (`build-input/swift/clang-cache/`) goes stale after every sdkm/
  darwin header edit — `rm -rf` it in the same command as the driver run.
- **apinotes are dead** in this compiler (3 locations tried); type-shaping happens via
  `swift_name` attributes in the headers. `ByteCountFormatter` was the negative control.
- **De-genericizing NSDictionary** breaks every init with an NSDictionary parameter
  (importer stops recognizing them). Reverted once; do not retry. The Keychain
  NSDictionary-requirement is solved by the `#if TGBUILD` id-form instead.
- **Unannotated ObjC inits import as Optional** on this compiler — fixed at the root
  (`_Nonnull init` in objc/NSObject.h, snapshot). New hand-authored headers should wrap in
  `NS_ASSUME_NONNULL` or annotate.
- **Variadic C functions are uncallable from Swift** and `swift_name` is ignored on them —
  hence non-variadic `open`/`fcntl` helpers and the Foundation-overlay `fcntl` wrappers.
- **The os module collision**: a swiftmodule named `os` on the overlay search path cycles
  the module graph; the shims live in `build-input/swift/shims/` instead.
- **Two TGBUILD defines** in swift.py: `-DTGBUILD` (Swift `#if`) AND `-Xcc -DTGBUILD`
  (clang `#if` in headers). Both are load-bearing.
- This shell's `grep` is ugrep: `grep -A`/pattern quirks differ; prefer `python3` for
  file surgery on headers (a `sed`-style bulk edit once corrupted Foundation.h — the
  fix was re-derivable from the duplicated-block structure, but avoid the class of bug).
- The iPhone's usbmuxd can wedge (`Operation not permitted` everywhere): restart the
  service before blaming the cable.

New traps from the 2026-10-27 full-SDK switch:

- **The SDK's stdc headers are canary-wrapped**: the clang resource include must precede
  `-isystem $SR/usr/include`, or `<float.h>` resolves into the SDK and
  `_c_standard_library_obsolete` fires (`found_incompatible_headers__check_search_paths`).
- **libc++ on every file's path breaks .m files**: `-isystem $SR/usr/include/c++/v1` lets
  libc++'s C++-only `stdatomic.h` shadow the compiler's in module builds →
  `unknown type name 'atomic_bool'`. Per-C++-file only.
- **The toolchain's own resource dir cannot be `-resource-dir` in full mode**: the driver
  puts it on the clang include path ahead of the SDK; its `os/object.h` shim breaks the
  SDK's `os_workgroup` module (Dispatch fails to build). Use the synthesized
  `build-input/swift/full-res`.
- **Apple's prebuilt device swiftmodules are arm64e-only** and import cleanly for arm64.
- **The iPhoneOS SDK has no PrivateFrameworks** — the private headers public frameworks
  import live in `System/Library/SubFrameworks`; the xtoolsdk bundle omits that dir;
  restore from the .xip with `xip_extract.py --no-clobber` (the .xip carries NULLcanary
  placeholders for files the cache has real content for).
- **APFS case-insensitivity shows on Linux**: repo sources include `<endian.h>` and
  `<CommonCrypto/CommonHMac.h>`; the SDK ships `Endian.h`/`CommonHMAC.h`. Exact-case
  symlinks in the SDK cache fix it without source edits.
- **Duplicate `-Xcc -fmodules-cache-path`**: the FIRST wins. Probe scripts that append a
  second one write nothing — check the first path's contents.
- **Per-invocation temp module caches are unusable at scale**: one tgcalls C++ TU took
  minutes rebuilding libc++; objc.py shares `build-input/objc-cache/clang-modules`
  (clang's per-module lock files make it concurrency-safe).

New traps from the 2026-10-28 session (details and evidence in
[`receipts/2026-10-28-black-screen-fixed.md`](../receipts/2026-10-28-black-screen-fixed.md)):

- **swift.py's cache key hashes source PATHS, not contents** — an edited module stays
  "cached"; `--force` recompiles the whole ~520-module closure (hours). The driver now
  also marks a module stale by source-mtime-vs-manifest. To force one module the old
  way: `rm -rf build-input/swift-cache/<hash dir of its .swiftmodule>`.
- **TaskStop on a driver's Bash task kills only the wrapper** — the `python3 swift.py`
  child survives (an orphaned --force run kept compiling for an hour). Follow up with
  `pkill -9 -f swift-frontend`.
- **ibtool arg order**: global flags must precede `--compile OUT IN` — everything after
  `--compile` is consumed as its arguments.
- **DefaultAppIcon.xcassets is broken everywhere** (`AppIconLLC.appiconset` declares a
  76×76 size with no source; the Linux actool *crashes* on it) — the default icon ships
  as loose `IconDefault*.png` + `CFBundleIconFiles`, as link.py now does.
- **The Linux actool works** for plain image sets (`--compile DIR
  --output-partial-info-plist … --platform iphoneos --minimum-deployment-target 16.0 …`).
- **`idevicedebug run` always "fails"** (30 s FBS timeout — free accounts can't attach a
  debugger) but the process starts; the clean launcher is
  `pymobiledevice3 developer dvt launch <bundle-id> --kill-existing`.
- **`~/pymobiledevice3` venv is gone** after some cleanup — recreate with
  `python3 -m venv ~/pymobiledevice3 && ~/pymobiledevice3/bin/pip install pymobiledevice3`.
- **idevicesyslog does not carry the app's NSLog** on this setup — don't plan
  app-level diagnostics around it (the `[tgbuild]` breadcrumbs are in main.m/AppDelegate
  but invisible); rely on rendering + crash reports so far.

## 6. Artifact map

| Path | What |
|---|---|
| `build-input/graph/modules.json` | the 1009-module graph (Phase 1) |
| `build-input/objc*/`, `build-input/swift*/` | Phase 2/3 products and caches |
| `build-input/configuration-repository/` | fixed `variables.bzl` + provisioning |
| `docs/tgbuild-sdkfree-snapshot/` | machine-local header snapshot (§3) |
| `docs/receipts/` | Phase 1/2/3 evidence (commands + verbatim output) |
| `submodules/TelegramApi/Generated/`, `…/FlatSerialization/*_generated.swift` | codegen outputs (untracked) |
| `~/.local/share/omarchy-apple-dev/sdk-free/` | sysroot, toolset, swift overlays (machine-local; snapshot covers the edits) |
| `~/pymobiledevice3` venv, `~/.local/bin/xtool` | device tooling (authed) |
