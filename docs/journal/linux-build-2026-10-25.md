# Compiling Telegram-iOS on Linux (x86_64) — state after the 2026‑10‑24/25 session

What compiles on this Ubuntu 24.04 box today, with what evidence, what was
patched, and what is still missing. Host: 4 cores, 15 GiB RAM, Ubuntu 24.04,
Swift 6.4.0 at `/usr/local/usr/bin` (not on the default PATH — add it), xtool
built from source, pymobiledevice3 in `~/pymobile3-venv`.

## What works, with evidence

**1. The C++ core (WebRTC + tgcalls) builds natively on Linux through Bazel.**

```sh
./build-input/bazel-9.2.0-linux-x86_64 build //submodules/TgVoipWebrtc:tgcalls_core
# -> Build completed successfully, 1186 total actions
#    bazel-bin/submodules/TgVoipWebrtc/libtgcalls_core.a   (54 MB static)
#    bazel-bin/submodules/TgVoipWebrtc/libtgcalls_core.so  (20 MB shared)
```

All three host `cc_test`s of the repo pass on Linux:

```
//submodules/TgVoipWebrtc:streaming_audio_renderer_test   PASSED
//submodules/TgVoipWebrtc:mtproto_dtls_transport_test     PASSED
//submodules/TgVoipWebrtc:group_frame_transformer_test    PASSED
```

Third-party C libraries that build on Linux x86_64: `boringssl (crypto+ssl)`,
`opus`, `ogg`, `opusfile`, `libvpx:libvpx_lib`, `dav1d`, `mozjpeg:mozjpeg_lib`,
`libyuv`, `subcodec:subcodec`, `wamr`, `rnnoise` (all `bazel build` green).

**2. iOS-targeted compilation on Linux, without Xcode (sdk-free sysroot).**

The no-Xcode sysroot at `~/.local/share/omarchy-apple-dev/sdk-free/iPhoneOS.sdk`
had been cut earlier from **this machine's paired iPhone X (iOS 16.7.16,
build 20H392)** — `sdk-free/cache/device-info.json`. Objects compile:

```sh
export PATH=/usr/local/usr/bin:$HOME/.local/bin:$PATH
~/dev/omarchy-apple-dev/sdk-free/cc.sh -c -fmodules -fno-autolink \
  -I submodules/MurMurHash32/PublicHeaders \
  submodules/MurMurHash32/Sources/MurMurHash32.m -o x.o
# x.o: Mach-O 64-bit arm64 object
```

A 100-file survey over every submodule's C/ObjC sources (compile-only,
`-fmodules`, iOS 17 target): **95 of 733 files compile (13%)**, three modules
fully (`MurMurHash32`, `MimeTypes`, `EncryptionProvider`), `MtProtoKit` 39/93.
The rest fail mostly on sysroot gaps (no headers for Metal, AVFoundation,
WebKit, CoreText, … — the sdk-free framework list is short by design).

**3. Swift for iOS compiles AND links on Linux against the iPhone X runtime.**

Compiler Swift 6.4 emits `swift_getTypeByMangledNameInContext2`, a runtime
symbol iOS 16.7's libswiftCore (Swift 5.8) does not have, so linking failed.
In the Swift sources the `2` variant differs from the old one only by a
ptrauth sign of the context descriptor (`stdlib/public/runtime/MetadataLookup.cpp`);
iPhone X is arm64 (no PAC), so a forwarding shim is ABI-correct on it:

```c
// /tmp/tgi/swiftshim.c
void *swift_getTypeByMangledNameInContext(const char *, unsigned long, const void *, const void *const *);
void *swift_getTypeByMangledNameInContext2(const char *s, unsigned long n, const void *c, const void *const *a) {
    return swift_getTypeByMangledNameInContext(s, n, c, a);
}
```

With the shim injected into the link (`/tmp/tgi/swiftc-x.sh` = a copy of
`sdk-free/swiftc.sh` that adds it), real submodules build end to end:

- `AudioWaveform` (pure Swift, Foundation): `.swiftmodule` + arm64 iOS
  executable.
- `AppLockState` (Swift) importing `MonotonicTime` (ObjC clang module) — the
  full chain compiles and links into an arm64 iOS Mach-O executable
  (`/tmp/tgi/swiftobj/AppLockState.exe`). Needed a stub `bsm/audit.h`
  (`/tmp/tgi/darwin_extra`) because `sys/sysctl.h` in the overlay tree pulls it.

## What was patched in the repo (all in the spirit of the existing Linux support)

| File | Change |
|---|---|
| `MODULE.bazel` | `wasi_sdk_linux`: arm64-linux tarball → x86_64-linux (sha256 `0ba8b5bf…`) — the pinned arm64 binary gave "Exec format error" on this host |
| `third-party/wamr/BUILD` | `BUILD_TARGET_AARCH64` + `invokeNative_aarch64.s` → `select()` on cpu (x86_64 gets `invokeNative_em64.s` + `BUILD_TARGET_X86_64`) |
| `third-party/openh264/BUILD` | arch selects: `@platforms//cpu:aarch64` keeps NEON asm, default (x86_64) gets none |
| `third-party/webrtc/BUILD` | `arch_specific_cflags` split by cpu (x86_64 gets `-DWEBRTC_ARCH_X86_FAMILY -msse2 -mavx2 -mfma`, `-DWEBRTC_ENABLE_LINUX_ALSA`, `-DWEBRTC_INCLUDE_INTERNAL_AUDIO_DEVICE`); `arch_specific_sources` gains x86 branch: fir_filter sse/avx2, sinc_resampler sse/avx2, ooura_fft_sse2, complex_bit_reverse, filter_ar_fast_q12, ALSA audio device, aec3/rnn_vad AVX2 variants, V4L2 video capture; declared the headers those sources include; added `logging/rtc_event_log/encoder/bit_writer.cc`, `api/numerics/samples_stats_counter.cc`, `modules/rtp_rtcp/source/deprecated/deprecated_rtp_sender_egress.cc` (statically-linked iOS never missed them; the shared lib did) |
| `third-party/webrtc/absl/BUILD` | sources/hdrs switched from a hand-picked list to `glob()` over the vendored tree (minus tests/benchmarks/gtest-dependent files); the curated list predated everything cord/hash/status/sync/flags need |
| `third-party/webrtc/crc32c/BUILD` | x86_64 branch adds `crc32c_sse42.cc` and `-msse4.2` (select, so arm builds unchanged) |
| `submodules/TgVoipWebrtc/tgcalls/tgcalls/group/GroupInstanceReferenceImpl.cpp` | `#include <mutex>` (GCC strictness) |
| `third-party/subcodec/src/mbs_mux_common.{h,cpp}` | NEON paths guarded by `__ARM_NEON`; scalar fallbacks already existed; two out-of-line `always_inline` definitions became `inline` (GCC refuses to inline link-time-overwritable bodies) |

## What still does not compile on Linux

- **The app target `//Telegram:Telegram`** — see "Can the rest be built?" below;
  verified blockers listed there.
- **`//third-party/mtproto-engine` (Rust)** — three stacked causes, checked:
  1. `Cargo.Bazel.lock` contains **zero** linux triples (only apple ones) —
     regenerating it needs `cargo bazel` and a Rust toolchain, absent on this
     host; 2. `MODULE.bazel`'s `rust.toolchain(sha256s = …)` pins only
     darwin/ios archives; 3. `supported_platform_triples` lists only apple.
     Fixable in principle (rustup + add `x86_64-unknown-linux-gnu` + regen
     lock), but it churns a lockfile shared with the Mac flow, and the Linux
     value is nil: the engine is an iOS FFI archive consumed by the app.
- **Most Swift/ObjC submodules against the sdk-free sysroot** (13% of
  C/ObjC files): the no-Xcode sysroot only covers Foundation/UIKit/
  CoreGraphics/QuartzCore/CoreFoundation/UserNotifications. A full-Xcode SDK
  (mode `full`, `install-toolchain.sh`) would lift much of this, still not to
  the whole app.

## Can the rest be built on Linux? (routes checked 2026-10-25)

1. **Bazel itself building iOS targets on Linux — no.** The repo vendors
   `rules_apple`/`rules_swift`/`apple_support` (MODULE.bazel
   local_path_overrides) and registers `local_config_apple_cc` from
   apple_support's crosstool, which is an `xcrun`-driven macOS toolchain (the
   comment at MODULE.bazel:227 notes rules_swift rejects the generic local
   CC toolchain). No Linux→iOS crosstool/swift-toolchain exists in these
   rules or upstream; building one is a research project, not a config flip.
2. **The xtool/SwiftPM adapter route — dead for this app.**
   `tools/xcodeproj2xtool.py:1002`: "N ObjC/C source files are not supported
   and were [excluded]". Telegram is ObjC-heavy (LegacyComponents 413 files,
   MtProtoKit 93, …), so the converter cannot carry it.
3. **Hand-rolled pipeline (what this session proved in miniature: cc.sh +
   swiftc-x + ld64.lld + sdk-free/bin/actool + rcodesign) — possible in
   principle, not realistic as a whole-app build.** It means reimplementing
   the Bazel graph by hand: 277 submodules in dependency order, codegen
   genrules, 7 embedded extensions + watch app, entitlements. Hard external
   dependency either way: signing (fastlanematch password / Apple ID) and,
   for full SDK coverage, the Xcode .xip download — both need the user's
   credentials.
4. **macOS VM in QEMU/KVM — technically open.** `/dev/kvm` present, VT-x on
   (8 threads). The repo's own legacy `buildbox/` scripts ran exactly this
   (libvirt VM + Xcode). Costs: macOS + Xcode 27 images (~25 GB), Apple ID
   login, and on 4 cores/15 GB an hours-long build per iteration; macOS on
   non-Apple hardware is against Apple's EULA — user's call, not something to
   set up overnight autonomously.

Update 2026-10-25: **`//third-party/libjxl:jxl_lib` now builds on Linux.**
The vendored `third-party/libjxl/libjxl/BUILD.bazel` (upstream's own) made
`libjxl/` a Bazel subpackage, so the outer glob matched nothing; renamed to
`BUILD.bazel.upstream` (no other rule referenced it — only
`submodules/MozjpegBinding/BUILD` consumes libjxl, via the outer package).

## The iPhone

The iPhone X was **not visible on USB all night** (`lsusb` has no 05ac device;
usbmuxd is running and healthy). The pairing record from earlier is intact
(`/var/lib/lockdown/[redacted-udid]….plist`), so when the cable is re-plugged:
`idevice_id -l`, then `device-run.sh` / `pymobiledevice3` flows from
`~/dev/omarchy-apple-dev` install and launch what we build. Nothing was
deployable tonight anyway — the app target itself does not build on Linux
(see above); what this session can put on the phone later is a
swiftc-x-built demo or the survey's object-level results.

## Reproduce the demo chain

```sh
export PATH=/usr/local/usr/bin:$HOME/.local/bin:$PATH
cd $HOME/dev/Telegram-iOS
./build-input/bazel-9.2.0-linux-x86_64 build //submodules/TgVoipWebrtc:tgcalls_core
./build-input/bazel-9.2.0-linux-x86_64 test //submodules/TgVoipWebrtc:streaming_audio_renderer_test \
  //submodules/TgVoipWebrtc:mtproto_dtls_transport_test //submodules/TgVoipWebrtc:group_frame_transformer_test
```

Bazel 9.2.0 (linux-x86_64) lives at `build-input/bazel-9.2.0-linux-x86_64`
(downloaded from the official release; versions.json pins only the darwin
binary). meson/nasm/libasound2-dev were apt-installed for the genrules.
The build used `build-input/configuration-repository` with
`variables.bzl` generated from `build-system/appstore-configuration.json`
(codesigning data is unused by the C++ targets but the repo mapping requires
the package to exist).

## Update 2026-10-25 (day session): Phase 1 done — the app graph extracts on Linux

Following [`linux-build-research-plan.md`](linux-build-research-plan.md) Phase 1.
Receipt with full evidence:
[`receipts/2026-10-25-phase1-graph-extractor.md`](../receipts/2026-10-25-phase1-graph-extractor.md).

- **`build-input/configuration-repository` was broken and is fixed.** The
  night session's `variables.bzl` used unprefixed names, but BUILD files load
  `telegram_*` symbols, and there was no `provisioning/` package — loading
  `//Telegram` failed. Now matches `BuildConfiguration.write_to_variables_file`
  (15 symbols) + `example-configuration` layout with fake-codesigning profiles.
- **cquery is impossible on Linux, query is not.** `cquery` needs analysis;
  `objc_library` analysis fails without the Apple CC toolchain. Loading-phase
  `bazel query --output=xml` carries all attribute data (selects flatten to
  branch unions) and runs cleanly over the whole app graph.
- **`tools/tgbuild/extract.py` → `build-input/graph/modules.json`**: 1009
  compile modules (738 swift, 78 objc, 33 cc, 159 rust, 1 prebuilt
  xcframework), topologically ordered, all 6 extensions + 5 frameworks + watch
  app + app target included, 0 warnings, exit 0. Spot-verified against disk
  (TelegramUI 213 = exactly its `Sources/` tree; lottie 181; Display 153).
  Facts for later phases: 159 rust modules have no Linux backend yet;
  `//Telegram:GeneratedSources` is intent-codegen (recorded as `intent_srcs`).
- **Plan §7 quick win done**: every `cc_library` in the app graph is green on
  Linux host — 29 compile targets `bazel build` clean (boringssl, dav1d,
  libvpx, libyuv, mozjpeg, ogg, openh264, opus(+file), rnnoise, subcodec,
  wamr, webp, webrtc+absl+crc32c+libsrtp+pffft), and `td_lib`/`ffmpeg*`
  need no compilation at all: they wrap **prebuilt** in-repo archives
  (`third-party/td/Public/td/lib/lib*.a`, ffmpeg likewise) — Phase 2 can
  consume them as-is for the iOS arm64 link.

## Update 2026-10-25 (day session, cont.): Phase 2 ObjC backend

Receipt: [`receipts/2026-10-25-phase2-objc-backend.md`](../receipts/2026-10-25-phase2-objc-backend.md).

- **`tools/tgbuild/objc.py`**: per-module modulemaps (MonotonicTime pattern
  generalized), dependency-closure compile through sdk-free `cc.sh`, flags
  from modules.json, content-hash object cache, failure taxonomy.
- **Stub layer** (`build-input/objc-stubs/`, 33 headers + 2 forced includes):
  Darwin system headers (os/lock, pthreads, sockets, netdb, sysctl, zlib with
  canonical z_stream, …), dispatch sources (as ObjC class pointers — what
  OS_OBJECT_USE_OBJC means at runtime), and the Foundation/CF surface the
  rebuilt sysroot headers lack. All signatures mirror the real iOS SDK;
  `--no-stubs` flips it off when the full SDK lands.
- **Results**: SSignalKit 24/24, AppBundle 1/1, MtProtoKit **83/93**
  (baseline survey: 39/93 with `-Wno-everything`), LegacyComponents 43/413.
  338 Mach-O arm64 objects in the cache (verified: `_OBJC_CLASS_$_MTContext`,
  240 text symbols in MTContext.m.o).
- **The no-Xcode ceiling, quantified per file**: MtProtoKit's 10 remaining
  files need Security/CommonCrypto/CFNetwork/SystemConfiguration;
  LegacyComponents' 370 need OpenGLES (57), AVFoundation (47), Photos (9),
  QuartzCore headers (12), CoreVideo/CoreText/UTI (4), or the fuller UIKit
  surface (241 files; the sysroot UIKit is a 285-line skeleton). Every one of
  these is lifted at once by the Phase 0 Xcode .xip.

## Update 2026-10-25 (day session, cont.): Phase 3 Swift backend — milestones 1–2

Receipt: [`receipts/2026-10-25-phase3-swift-backend.md`](../receipts/2026-10-25-phase3-swift-backend.md).

- **`tools/tgbuild/swift.py`**: per-module `-emit-module` + `-c` in dependency order from
  modules.json; content-hash cache; transitive ObjC-dep clang modulemaps (direct-only broke
  on Postbox.swiftmodule's recorded Crc32/sqlcipher/StringTransliteration imports).
- **Foundation overlay rebuilt** (`rebuild-foundation.sh` + `overlay/Foundation+Tgbuild.swift`):
  the closed-source-bridge API the app uses (String.data/Range/enumerateSubstrings,
  Data.write/contentsOf, FileManager URL variants, IndexSet, CharacterSet, URL resource
  values, JSONEncoder/Decoder stubs, Date adopted from swift-5.3 sources, errno, fcntl).
- **Thin framework modules authored**: CommonCrypto, SystemConfiguration, CloudKit (with
  swift_name shaping), CoreText/AVFoundation umbrellas; `os`/`Network` Swift shims.
- **Codegen on Linux**: SwiftTL (TelegramApi, host swiftc build) and flatc (host cmake build
  of the pinned v24.12.23) generate TelegramApi's 44 files and the 34 FlatSerialization files.
- **Ladder**: SwiftSignalKit (26) ✓, Postbox (221) ✓, + TelegramApi/FlatBuffers/
  FlatSerialization/ManagedFile/RangeSet/MediaPreuploadRegistry/Reachability/Emoji/CloudData —
  **11 arm64 .swiftmodule + .o products** (Postbox 10.5 MB, TelegramApi 12.9 MB objects).
- **One wall left before TelegramCore**: WebProxyTransport needs a WebKit overlay (20 WK*
  types). Repo patch: `#if canImport(os.log)` in WebProxyDiagnostics.swift (Mac unchanged).
- Import-resolution facts recorded for posterity: dotted Swift imports never fall back to a
  Swift module; a dotted swiftmodule name doesn't resolve; `-module-alias` engages after
  resolution; C variadics are uncallable from Swift and `swift_name` is ignored on them.

### Correction 2026-10-25 13:20 — Phase 0 is nearly complete

- **`xtool auth` was already done on 2026-10-24 21:51–21:58** (before the
  night build session, unrecorded): Apple ID [redacted-apple-id], Team ID
  `[redacted-team-id]`, token expiry 2027-10-24 (`xtool auth status`; credentials in
  `~/.config/xtool/data/`). The plan's Phase 0 item 1 is not a gate.
- **The iPhone X is on USB right now.** It had been attached with a wedged
  usbmuxd (socket present, `OSError 107` / `Operation not permitted` on every
  client) and the host pairing record had vanished from /var/lib/lockdown.
  `sudo systemctl restart usbmuxd` brought it back:
  `xtool devices` → "[redacted-device]" [usb] [redacted-udid]…, iPhone10,6,
  iOS 16.7.16 (build 20H392) — the same device the sdk-free sysroot was cut
  from. `pymobiledevice3 lockdown info` responds (Activated).
- Remaining user item: only the **Xcode .xip** download. The device loop
  (Phase 5) is no longer credential-gated: once an .app/.ipa exists, `xtool
  install` can run immediately.

### 2026-10-25, вечер: WebKit-overlay итерация — WebProxyTransport ✓, TelegramCore в хвосте

- **Новые clang-модули в sdkm**: WebKit (20 WK*-типов, 3 делегата, WKContentWorld,
  `__callAsyncJavaScript` через NS_REFINED_FOR_SWIFT), Security (SecRandom),
  CoreTelephony, Photos/LinkPresentation/CoreServices (umbrella). Foundation-модуль:
  URL-loading (NSURLRequest/Response/HTTPURLResponse/Components/QueryItem/учётка auth),
  NSKeyedArchiver/Unarchiver, NSRegularExpression, NSUbiquitousKeyValueStore,
  NSDecimalNumberHandler, NSOperationQueue, block-observers, JSONSerialization (typed options).
- **Swift-шимы**: `Network` дополнен NWConnection/NWParameters/NWEndpoint (TCP-поверхность
  TelegramCore); `os` — как раньше.
- **Корневые фиксы darwin/objc**: `-[NSObject init]` → `_Nonnull` (Optional-иниты по всему
  графу ушли); MTRequest/MTOutputStream nullability (responseParser-блок nullable и др.);
  MTKeychain.h — `#if TGBUILD` id-форма метода dictionary (Swift 6.4 не бриджит
  NSDictionary-требования без apinotes; апиноты clang не читает — проверено 3 расположения).
- **Репо-патчи**: WebProxyDiagnostics.swift (`#if canImport(os.log)`), Network.swift
  (`#if TGBUILD`-ветка Keychain-свидетеля + non-IUO свидетели).
- **Состояние**: замыкание TelegramCore 12/13 ✓ (последний — сам TelegramCore, 718 файлов,
  остаток ~10 семейств API; список и итерационный контур — в конце receipt Phase 3).

### 2026-10-26: Phase 0 complete — the Xcode .xip arrived

The user placed `Xcode_27.2_Release_Candidate.xip` (2.0 GB; Xcode 27.2 / 27B48, verified
with `tools/xip_version.py` — the Xcode whose Swift matches our 6.4). `xtool sdk build`
extracted and bundled it into
`~/dev/omarchy-apple-dev/sdk-free/sdk-cache/darwin-iPhoneOS27.2.xtoolsdk`
(iPhoneOS27.2.sdk + Simulator + MacOSX27.2.sdk; ~11 GB unpacked), registered via
`xtool sdk install` (`swift sdk list` → darwin).

The real iPhoneOS27.2.sdk carries **318 frameworks** (sdk-free: 13). Smoke test against
it: `MTAes.m` and `MTEncryption.m` — two of the ten MtProtoKit files blocked on
Security/CommonCrypto — compile to Mach-O arm64 with **zero errors**. The no-Xcode
ceiling is formally lifted; next step is switching the tgbuild drivers to full-SDK mode
(documented in `docs/linux-build-next-session.md` §1b), after which `--no-stubs` runs
replace the stub-layer verification.

### 2026-10-27: full-SDK mode implemented; ladder green to TelegramApi; MtProtoKit 93/93 no-stubs

The drivers now default to the real iPhoneOS27.2.sdk (`TGBUILD_SDKFREE=1` restores the
sdk-free tree; `TGBUILD_SYSROOT` overrides both). Receipt:
[`receipts/2026-10-27-fullsdk-switch.md`](../receipts/2026-10-27-fullsdk-switch.md).

**Swift side.** The invocation that works: `-sdk` real SDK, `-resource-dir` a synthesized
dir (symlinks to the toolchain's `clang` + `shims`; the toolchain's own resource dir puts
its os/ shim headers ahead of the SDK's and Dispatch stops building), `-I` Apple's
prebuilt-modules dir — the xtoolsdk's device modules are arm64e-only and **are accepted
for an arm64 target**. `-nostdinc` is unnecessary in full mode (no glibc leaks). The
ladder compiles: SwiftSignalKit, ManagedFile, RangeSet, Postbox, TelegramApi,
MediaPreuploadRegistry, WebProxyTransport, CloudData, Reachability, Emoji, FlatBuffers,
FlatSerialization — the whole sdk-free §4 tail (EncryptionProvider probe, `[Any]→Int`,
OSAtomic, URLResourceKey, Log.swift, NW shim) evaporated, as §1b predicted. WebProxyTransport
needed real availability annotations (`@available(iOS 18.4/27)`, valid in both modes).

**ObjC side.** MtProtoKit compiles **93/93 with `--no-stubs`** against the real SDK.
Four fixes were needed:

1. **cc.sh include order**: the resource dir must come BEFORE `-isystem $SR/usr/include` —
   otherwise `<float.h>` from SDK `math.h` finds the SDK's canary-wrapped copy and
   `_c_standard_library_obsolete` fires (`requires feature
   'found_incompatible_headers__check_search_paths'`).
2. **libc++ per-C++-file only**: `-isystem $SR/usr/include/c++/v1` on every file shadows
   `<stdatomic.h>` in module builds (libc++'s stdatomic.h is a C++ shim), leaving
   `atomic_bool` unknown to .m files. objc.py now appends it per .mm/.cpp/.cc file.
3. **APFS case-insensitivity**: the SDK ships `Endian.h`/`CommonHMAC.h` while the repo
   sources `#import <endian.h>`/`<CommonCrypto/CommonHMac.h>` — resolved by exact-case
   symlinks inside the SDK cache (`usr/include/endian.h`, `usr/include/CommonCrypto/CommonHMac.h`).
4. **SubFrameworks**: UIKit imports `<UIUtilities/…>` unguarded; the frameworks live in the
   SDK's `System/Library/SubFrameworks/` (there is no PrivateFrameworks dir), which xtool's
   sdk-cache bundle dropped. Restored from the .xip with the new
   `~/dev/omarchy-apple-dev/tools/xip_extract.py` (same xar→pbzx→cpio streaming as
   xip_version.py, `--no-clobber` because the .xip carries NULLcanary placeholders for some
   files the cache already has real copies of — UIView.h among them). cc.sh grew
   `-iframework …/PrivateFrameworks` and `-iframework …/SubFrameworks`.

**Driver plumbing.** objc.py shares one clang module cache
(`build-input/objc-cache/clang-modules`): per-invocation temp caches made every TU rebuild
Foundation/libc++ — a tgcalls C++ file cost minutes (the first sweep sat at ~0 objects for
17 minutes). swift.py copies only the products a pass produced (`--emit-only` crashed on
the missing .o).

**Open.** TelegramCore's `EncryptionProvider` lookup still fails in the whole-module
compile (the type is the ObjC protocol; neither spelling resolves; the clang PCM builds
fine and is hash-identical to the working mini-repro's). A file-level bisect over the
module is running; excluding all 196 `import MtProtoKit` files makes the import resolve,
so the trigger is among them. sdk-free-era clang module caches (/tmp/tg-mcache) make the
compile PASS — stale-PCM luck, not a fix.

### 2026-10-27 (evening): the EncryptionProvider hunt, narrowed to scale

The whole-module-only failure survived three false leads, each worth recording:

- **Import order** (`import EncryptionProvider` above/below `internal import TelegramApi`):
  no effect.
- **Direct-header modulemaps** (replacing the generated umbrella with explicit `header`
  entries): made things *worse* — configurations that import fine under the umbrella form
  come up empty under direct headers. The generator was reverted; keep the umbrella form.
- **The debugger's own probe line**: a temporary `EncryptionProviderProtocol`-typed function
  planted in the failing file masked every later whole-module run — the suffixed spelling
  fails *more* readily than the plain one, and the driver prints the first error only.
  Removed; the real signal is the plain name at :73.

Clean statement after removal: one file + the full TelegramCore clang-flag set +
`import EncryptionProvider` compiles; the 718-file whole-module compile of the same module
does not see the type (plain name; deterministic across runs). An exponential file-count
bisect over the module is running to find the smallest poisoning file set.

Under the umbrella format the ta-set/tc-set matrix reads: plain name resolves on both sets
at one-file scale; only whole-module scale fails.

### 2026-10-27 (night): TelegramCore green — the importer bug is source-order sensitive

The `EncryptionProvider` failure is a **ClangImporter source-order sensitivity in
whole-module compiles**. Proof, 2/2 runs each way on identical flags and file sets:
driver source order (the importing file mid-list) fails deterministically; the same list
with `ProcessSecretChatIncomingDecryptedOperations.swift` moved to the front compiles
cleanly (exit 0). Source order has no Swift semantics, so `swift.py` now retries a failed
pass once with the file named in the first "cannot find type" error rotated to the front
(and prints a NOTE when it does). Result: **TelegramCore compiles — the full 13-module
closure is green in full-SDK mode**, `build-input/swift/objects/TelegramCore.o` is a
Mach-O arm64 object, and the result is cached/stable across reruns.

The same bug family blocks Display (`ASDisplayNode` invisible whole-module while a
single-file compile sees it); there the rotation retry does not heal it (the reporter
first still fails) nor does clang-cache warming — 87 files import AsyncDisplayKit and the
"importer first" heuristic that fixes TelegramCore is insufficient. That is the next
session's first item (§4.1 of the handoff).

Hunt hygiene worth remembering: a debug probe typed with the *suffixed* protocol name
planted in the failing file masks the real diagnostic (line order + the suffix fails more
readily), and a test harness that glues `-Xcc -fmodule-map-file=…` into a single argv
produces instant unknown-argument failures that read as passes if you only grep for type
errors. Both burned real time today.
