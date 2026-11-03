# Traps: the list you re-derive at your own cost

Every entry cost a session somewhere. The load-bearing ones first.

## Load-bearing

- **`--min 16.0` on every `swift.py` invocation.** At `min >= 17` the compiler
  folds every `#available(iOS 17)`/`(iOS 26)` gate into an unconditional call;
  on an iOS 16.x device the first such path aborts (SIGABRT ~1 s after launch,
  no .ips). Proven by IRGen diff (2026-11-02): at min 16.0 the
  `$s_stdlib_isOSVersionAtLeast` runtime check survives, at min 17.0 it is
  folded away. The min-16 cache is a separate cache-dir tree — min-17 products
  silently come back if the flag is omitted. `swift.py`'s default is 16.0 for
  this reason.
- **After editing ANY SDK/header material: `rm -rf build-input/swift/clang-cache`**
  in the same command as the driver run — stale clang module state reports ghosts.
- **usbmuxd wedges** (`Operation not permitted` everywhere): `sudo systemctl
  restart usbmuxd` before blaming the cable.

## Graph and cache

- **`cquery` cannot run on Linux** (analysis needs the Apple toolchain). Use `bazel query`.
- **`bazel query` flattens `select()` to the union of branches on a Linux host** —
  glibc feature defines leak in from the linux_config branch; objc.py counters
  with explicit defines (`-D_XOPEN_SOURCE=700` handling).
- **swift.py's cache key hashes source PATHS, not contents** — an edited module
  stays "cached"; staleness is source-mtime-vs-manifest. A `--force` recompiles
  the whole ~520-module closure (hours). To force one module:
  `rm -rf build-input/swift-cache/<hash dir of its .swiftmodule>`.
- **Switching `--min` orphans the entire cache** (the value is in the key).
- **Duplicate `-Xcc -fmodules-cache-path`: the FIRST wins.** Probe scripts that
  append a second one write nothing.
- **An interrupted driver leaves a stale shared clang module cache** whose
  ghost PCM state fails unrelated modules (a "missing required module 'X'"
  cascade across modules that never touched X). `rm -rf
  build-input/swift/clang-cache` and rerun — the swift-cache products are
  fine, only the clang cache poisons.
- **Never run two driver passes against the same `build-input/` at once** —
  they race on the shared clang cache and the swift-cache directories; a
  killed pass is exactly how the stale-PCM state above is produced.
- **Per-invocation temp module caches are unusable at scale** — one tgcalls C++
  TU took minutes rebuilding libc++; objc.py shares one clang module cache
  (per-module lock files make it concurrency-safe).

## Compiler / SDK

- **`-nostdinc` in the Swift driver is load-bearing**: without it host glibc
  leaks in (`open` imports variadic-unavailable). The clang resource dir must
  be re-added explicitly.
- **The SDK's stdc headers are canary-wrapped**: the clang resource include
  must precede `-isystem $SR/usr/include`, or `<float.h>` resolves into the SDK
  and `_c_standard_library_obsolete` fires.
- **libc++ on every file's path breaks .m files** (`stdatomic.h` shadows the
  compiler builtin in module builds) — per-C++-file only.
- **The toolchain's own resource dir cannot be `-resource-dir` in full mode**
  (its `os/object.h` shim breaks the SDK's Dispatch module) — use the
  synthesized `build-input/swift/full-res`.
- **Apple's prebuilt device swiftmodules are arm64e-only** and import cleanly
  for arm64.
- **The iPhoneOS SDK has no PrivateFrameworks** — the private headers public
  frameworks import live in `System/Library/SubFrameworks`; `xtool sdk build`
  omits that dir; restore from the `.xip` with `xip_extract.py --no-clobber`
  (the `.xip` carries NULLcanary placeholders where the cache has real content).
- **APFS case-insensitivity shows on Linux**: repo sources include `<endian.h>`
  and `<CommonCrypto/CommonHMac.h>`; the SDK ships `Endian.h`/`CommonHMAC.h` —
  exact-case symlinks in the SDK cache fix it without source edits.
- **apinotes are dead** in this compiler (3 locations tried); type-shaping goes
  through `swift_name` attributes in the headers.
- **De-genericizing NSDictionary breaks every init with an NSDictionary
  parameter** (the importer stops recognizing them). Reverted once; do not
  retry. The Keychain NSDictionary-requirement is solved by the `#if TGBUILD`
  id-form instead (patch 0004).
- **Unannotated ObjC inits import as Optional** — fixed at the root
  (`_Nonnull init` annotations); hand-authored headers should wrap in
  `NS_ASSUME_NONNULL`.
- **Variadic C functions are uncallable from Swift** and `swift_name` is
  ignored on them — hence non-variadic `open`/`fcntl` helpers and the
  Foundation-overlay wrappers.
- **The `os` module collision**: a swiftmodule named `os` on the overlay search
  path cycles the module graph; shims live in `build-input/swift/shims/`.
- **Two TGBUILD defines**, both load-bearing: `-DTGBUILD` (Swift `#if`) and
  `-Xcc -DTGBUILD` (clang `#if` in headers).
- **A swiftmodule min-target mismatch fails the import** — the
  RecaptchaEnterprise stub swiftmodule must be re-emitted at the ladder's min
  into BOTH `build-input/swift/prebuilt-frameworks/RecaptchaEnterprise.framework`
  AND its `xcframework/ios-arm64_arm64e` slice (the import resolves through the
  xcframework slice).

## Tooling and host

- **TaskStop on a driver's shell task kills only the wrapper** — the
  `python3 swift.py` child survives; follow up with `pkill -9 -f swift-frontend`.
- **ibtool arg order**: global flags must precede `--compile OUT IN`.
- **DefaultAppIcon.xcassets is broken upstream** (`AppIconLLC.appiconset`
  declares a 76×76 size with no source; the Linux actool *crashes* on it) —
  the default icon ships as loose `IconDefault*.png` + `CFBundleIconFiles`.
- **The Linux actool works** for plain image sets; **`pdftoppm` bakes a white
  background** into PDF-vector rasterizations (no alpha support in the build
  installed here) — `pdftocairo -png -transp` matches actool's output.
- **This shell's `grep` may be ugrep** (`-A`/pattern quirks differ); prefer
  python3 for header surgery — a sed-style bulk edit once corrupted a
  hand-authored header past recovery.

## Device

- **`idevicedebug run` always "fails"** (30 s FBS timeout — free accounts
  cannot attach a debugger) but the process starts; the clean launcher is
  `pymobiledevice3 developer dvt launch <bundle-id> --kill-existing`.
- **idevicesyslog does not carry the app's NSLog** on this setup — the
  app-level diagnostic channel is `Documents/tgbuild-log.txt` (breadcrumbs from
  patches 0005/0006), pulled via `pymobiledevice3 apps afc`.
- **`xtool install` wedges at 100% if the app is running** — kill it first
  (`dvt process-id-for-bundle-id` + `dvt kill`; `apps kill` does not exist in
  this pymobiledevice3).
- **Launching the canonical bundle id foregrounds the App Store Telegram** —
  free provisioning suffixes the id (`XTL-<team-id>.…`); launch that one.
