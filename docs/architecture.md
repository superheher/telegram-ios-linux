# Architecture: how tgbuild builds Telegram-iOS on Linux

A Mac builds this app through Bazel + rules_apple + Xcode. None of that runs
on Linux: `rules_apple`'s crosstool is an `xcrun`-driven macOS toolchain, and
no Linux→iOS crosstool exists in these rules. tgbuild keeps the **graph**
(Bazel) and the **sources** untouched, and replaces the **execution backend**:
its drivers read the same BUILD files, execute the same compilation units with
the Linux-hosted Swift toolchain, and reimplement the packaging rules_apple
would do. The app-level patches the graph's sources need live in `patches/`
(one-time, source-level); everything else is tooling.

## The graph

`tools/tgbuild/extract.py` runs `bazel query 'deps(//Telegram:Telegram)'
--output=xml --noimplicit_deps --notool_deps'` and flattens the XML into
`build-input/graph/modules.json`:

- 1495 targets → **1009 compilable modules** (739 `swift_library`, 78
  `objc_library`, 33 `cc_library`, plus prebuilt/alias/filegroup entries),
- dependency order (topological), module deps split from target deps,
- per-module srcs resolved through filegroup/alias closure (the query
  flattens `select()` to the union of branches on a Linux host — see traps),
- the six `ios_extension`s and the watch app are listed but not compiled.

Bazel never executes a build action here; the query is the only use (analysis
phase — `cquery` — cannot run on Linux: it needs the Apple toolchain).

## Drivers

| Driver | Role |
|---|---|
| `extract.py` | graph extraction (above) + modulemap generation for all objc targets |
| `swift.py` | compiles the Swift closure: per-module `-emit-module` + `-c` in dependency order, wave-scheduled (`--jobs`), content-hash cached |
| `objc.py` | compiles `objc_library`/`cc_library` targets via `cc.sh`, shared clang module cache, per-C++-TU libc++ handling |
| `link.py` | links the 5 frameworks + the app binary with `ld64.lld`, assembles `Telegram.app` (resources, asset catalogs via actool, storyboards, plists, entitlements), the 23 resource bundles |
| `probe.py` | full stderr for one module (the drivers print only the first error) |
| `audit_images.py` | static asset-lookup audit against the packaged app |

Two `TGBUILD` defines are passed everywhere and both are load-bearing:
`-DTGBUILD` for Swift `#if`, `-Xcc -DTGBUILD` for clang `#if` in headers
(the source patches gate Linux-only fallbacks on it).

## Caches

- **swift-cache**: key = `label + srcs paths + flags` (NOT contents — the
  staleness check is source-mtime-vs-ok-manifest; edits without mtime changes
  go unnoticed, `--force` recompiles the whole closure in hours). One directory
  per module per min-version: switching `--min` orphans the cache.
- **objc-cache**: same idea; clang's shared module cache lives in
  `build-input/objc-cache/clang-modules` (per-module lock files make it
  concurrency-safe). Per-invocation temp caches are unusable at scale — one
  tgcalls C++ TU took minutes rebuilding libc++ in its own cache.
- **clang-cache** (`build-input/swift/clang-cache/`): goes stale after every
  SDK/header edit; reset it in the same command as the driver run.
- Cache keys are label-relative, so a relocated checkout can seed its caches
  from a previous tree if file mtimes are preserved.

## SDK handling (full-SDK mode)

The default mode uses the real iPhoneOS27.2 SDK from the Xcode `.xip` (via
`xtool sdk build`, restored private-framework headers via `xip_extract.py`).
Search-path order is where the bugs live (see traps):

1. clang resource include **before** the SDK's `usr/include` (the SDK's
   stdc headers are canary-wrapped),
2. libc++ (`usr/include/c++/v1`) per C++ file only — on every file it breaks
   `.m` module builds (`stdatomic.h` shadows the compiler builtin),
3. the toolchain's own resource dir cannot be passed via `-resource-dir` (its
   `os/object.h` shim breaks the SDK's Dispatch module) — the driver
   synthesizes `build-input/swift/full-res` instead,
4. Apple's prebuilt device swiftmodules are arm64e-only and import fine for
   arm64 (`-I .../prebuilt-modules/27.2`).

The pre-Xcode **sdk-free mode** (`TGBUILD_SDKFREE=1`) uses the hand-built
sysroot (`tools/snapshot/` + `cc.sh`) — historically first, kept as the
recovery mode; the full-SDK mode superseded it for the app itself.

## Link and packaging

`link.py --app`:

1. links 5 frameworks (TelegramUI, TelegramCore, LegacyComponents, …) with
   `ld64.lld`; weak-links `Foundation`/`UIKit` + a known set so iOS-17+ APIs
   bind nil on iOS 16 instead of halting dyld; lld misses the rpath ld64 adds,
   so `@executable_path/Frameworks` is set explicitly;
2. links the app binary from `//Telegram:Main`'s objects (the `@objc(Application)`
   principal class `main.m` names) + the pack shim + stub objects
   (`GeneratedSources`, `RecaptchaEnterprise-stub`, WebRTC ADM stub);
3. assembles `Telegram.app`: Info.plist (merged `NS*UsageDescription` from the
   real one), entitlements, loose icon PNGs (the repo's default icon catalog is
   broken upstream and crashes the Linux actool), strings `.data`, 68 asset
   catalogs via the Linux actool (PDF-vector imagesets rasterized with
   `pdftocairo -png -transp` — `pdftoppm` bakes a white background), 53
   storyboards/xibs where used, and the 23 `apple_resource_bundle`s into their
   owning frameworks;
4. patches the binary's Mach-O loads (`strengthen_swift_weak_loads`,
   `weaken_absent_api_refs`) for the iOS 16.7 device.

## Differences from the Bazel/rules_apple path

- No sandbox, no remote execution, no hermetic toolchains — the host toolchain
  is used directly, versions pinned by the install script.
- Codegen that Bazel would run as genrules runs by hand (SwiftTL, flatc,
  make-generated-sources.sh — see `tools/generated/README.md`).
- `ios_extension`/watch targets are not built (the app runs without them).
- Rust-backed engines (`mtproto-engine`, wallet, …) are linked as stubs: the
  vendored `Cargo.Bazel.lock` carries no Linux triples and the value of
  regenerating it for an iOS FFI archive was nil (status doc has the analysis).
- Mach-O binary surgery replaces what code signing/loading would handle on the
  Mac flow (weak-load flipping for iOS 16 compatibility).
