# Receipt: Display unblocked; ObjC residue green; Rust backend live; linker proven

Date: 2026-10-27 (second session of the day). Entry point was
[`linux-build-next-session.md`](../journal/linux-build-next-session.md) §4.1 (Display). Everything
below is evidence-backed; commands runnable from `$HOME/dev/Telegram-iOS` with
`export PATH=/usr/local/usr/bin:$HOME/.local/bin:$PATH`.

## 1. Display: root cause found and fixed (was §4.1's open item)

The whole-module failure ("cannot find type 'ASDisplayNode'") reduced to a **two-file
repro** via ddmin over the module's 153 files (harness: run the exact driver flags on a
file subset, poisoned = the ASDisplayNode error; reporter `ASTransformLayerNode.swift`
pinned):

- a.swift: `import UIKit; import AsyncDisplayKit; class _R: ASDisplayNode {}`
- b.swift: `import UIKitRuntimeUtils` (one line)

→ error, order-independent, fresh clang caches included. ddmin over b.swift's lines →
the single line `import UIKitRuntimeUtils`; over UIKitRuntimeUtils's umbrella headers →
**`UIBarButtonItem+Proxy.h` alone**. That header had `#import
<AsyncDisplayKit/ASDisplayNode.h>` — a public header pulling another objc module's header.
The UIKitRuntimeUtils PCM then shadows ASDisplayNode's declarations, and when both modules
load in one compile the ClangImporter hides the real AsyncDisplayKit decls
(minimal-repro evidence in this session's bisect scripts, `/tmp/display_*.py`, 2026-10-27).

**Fix (repo):** `UIBarButtonItem+Proxy.h` now uses `@class ASDisplayNode;` (pointer use
only; comment in the header explains why the import must not come back). A repo-wide scan
(objc public headers `#import <RepoModule/…>` cross-imports) found **zero** other
instances — this was the only one. Display compiles 153/153 at `--min 16.0` (driver run
`ok`).

Rotation workaround stays in swift.py (harmless; TelegramCore still needs it — its
trigger was among `import MtProtoKit` files per the 2026-10-27 night entry, mechanism
possibly related but not re-investigated).

## 2. objc.py driver fixes — the ObjC campaign went 946/3070 → ~3000/3070

Each fix below flipped a distinct failure family in the sweep:

1. **libc++ before the clang resource dir for C++ TUs.** cc.sh grew `NOSDK_CXX_V1`
   (objc.py sets it per C++ file): `-isystem $SR/usr/include/c++/v1` now precedes the
   resource dir — the order Apple's own driver uses. Without it libc++'s `<cstddef>`/
   `<cctype>`/`<cstring>` fail: their `#include <stddef.h>` must resolve to libc++'s own
   wrapper (`_LIBCPP_STDDEF_H`), not the compiler's. ~500 objects (absl 145,
   TgVoipWebrtc, LegacyComponents 23, RLottieBinding 26, CompanionRenderer 29, crc32c,
   libprisma, subcodec, ImageDCT…).
2. **No `-fmodules` for C++ TUs** (.mm/.cpp/.cc): under modules the SDK's math.h hides
   the `isnan/isnormal/isfinite` macro family from C++ (`#if
   !__has_feature(modules)` guard) → AsyncDisplayKit 29 misses. No repo .mm uses
   `@import`. AsyncDisplayKit now 58/58.
3. **x86-only copts dropped**: `-msse2` family (webrtc: "unsupported option for target
   arm64-apple-ios") and MSVC-style `/std:c11` (BoringSSL's 360 .S files: clang parsed
   it as a file name). crypto 360/360, ssl 37/37 after.
4. **Linux-branch select() leakage**: the graph extraction flattens selects to the union
   of branches on a linux host, so glibc feature defines arrived: `-D_XOPEN_SOURCE=700`
   (BoringSSL copts+select) hides `u_char` behind `_POSIX_C_SOURCE` gating in
   sys/types.h → ssl 0/37 until dropped. Driver now strips
   `_XOPEN_SOURCE/_POSIX_C_SOURCE/_GNU_SOURCE/_DEFAULT_SOURCE` from copts and defines.
5. **Arch/platform define unions**: webrtc carried BOTH `-DWEBRTC_ARCH_X86_FAMILY`
   (SSE paths + emmintrin: "module _Builtin_intrinsics.intel.sse2 requires feature
   x86") and `-DWEBRTC_ARCH_ARM64`; both `-DWEBRTC_LINUX`(+`_ENABLE_LINUX_ALSA`) and
   `-DWEBRTC_IOS`; wamr carried `BUILD_TARGET_X86_64`+`BH_PLATFORM_LINUX` next to their
   arm64/darwin twins. Driver drops the x86/linux twin when the arm64/darwin one is
   present.
6. **Source-list unions**: query flattens srcs selects too — x86 implementation files
   (`*_sse2.cc`, `*_avx2.cc`, …) and linux platform files (`/linux/`, `*_alsa_linux.cc`)
   are skipped with `skipped:*` statuses; `ReferenceCoreEmbedded.cpp` (Mac-local,
   not in git) is skipped as `skipped:missing-source`.
7. **Shell-escaped copts**: Bazel runs actions through a shell, so
   `-DAPP_CONFIG_API_HASH=\"…\"` reaches a subprocess argv with the backslashes intact
   ("expected expression", BuildConfig). Driver unescapes `\"` → `"`.
8. **EXTRA_INCLUDE_DIRS / EXTRA_COPTS** tables (objc.py, keyed by label) for inputs the
   label graph does not carry: ffmpeg Public headers (bazel-bin, built 2026-10-25),
   opus/vpx/dav1d Public headers + webrtc's generated field_trials header (k8 tree —
   see §4 for the bazel-bin symlink repoint trap), td SharedHeaders, mozjpeg Public,
   webp src tree, EncryptionProvider/SSignalKit/h264bitstream/RichTextInputDecObjC
   include dirs, the rust FFI headers (mtproto_engine.h is checked in;
   wallet_engineFFI.h generated — §3). libsrtp gets `-include stdint.h` (its vendored
   config.h is intentionally blank; srtp.h uses uint32_t without including stdint).
9. `probe.py` had a syntax error (line 27 unindented) — fixed.
10. objects.json now written from the 5-tuple jobs (was a 4-tuple unpack crash after
    the per-job env change).

Result after the residue passes: **every objc/cc module is green except webrtc (28
header-path misses at last count, rebuild with final flags running) and TgVoipWebrtc (8,
same)**. webrtc_objc 87/87, AsyncDisplayKit 58/58, LegacyComponents 413/413 (was
390/413), wamr 45/45, libsrtp 17/17, all *Binding modules green.

## 3. Rust backend — the "one structural gap" is closed

`cargo build/rustc --target aarch64-apple-ios` works on this Linux box:

- Toolchain: rustup 1.96.1 (`rust-toolchain.toml` pin) + stable 1.99.1, both with the
  `aarch64-apple-ios` target installed.
- Env: `CC_aarch64_apple_ios=/tmp/ios-clang.sh` (wrapper: `/usr/local/usr/bin/clang
  -target arm64-apple-ios16.0 -isysroot $SDK -fno-objc-arc`), `SDKROOT=$SDK` (cc-rs
  wants xcrun otherwise), `AR_aarch64_apple_ios=llvm-ar`. Recreate the wrapper after a
  /tmp wipe (3 lines; SDK path in §4a of the handoff).
- **libmtproto_engine_ffi.a** (`cargo build --release --target aarch64-apple-ios -p
  mtproto-ffi`, 54 s, 533 defined symbols), **libwallet_engine.a** (`cargo rustc
  --release --target aarch64-apple-ios -p wallet-engine --crate-type staticlib`),
  **libtlottie.a** (same in `submodules/tlottie/tlottie`, needs the target on the
  default toolchain too).
- **WalletEngineFFI bindings generated on Linux**: host builds of
  `wallet-engine/bindgen/apple` (uniffi bindgen, 7 min) and the postprocess tool
  (scratch cargo project wrapping `Sources/SwiftBindingsPostprocess.rs`, which needs
  its `#[path]`ed module — build as the bin path directly, depends on anyhow 1);
  cdylib of `wallet-engine` for metadata (`cargo rustc --crate-type cdylib`); then the
  bindgen (`--swift-sources --headers --modulemap --metadata-no-deps --module-name
  wallet_engineFFI …`, needs cargo on PATH — it shells out to `cargo metadata`) and
  postprocess wrote `third-party/wallet-engine/Generated/{WalletEngineFFI.swift,
  wallet_engineFFI.h}` (17k lines Swift). MTProtoEngineFFI's `mtproto_engine.h` is
  checked in; both bridges now compile (0/0 = archive/headers-only modules).

## 4. Third-party archives for the link — bazel-bin is a trap, genrule libs need manual builds

- **Every `.a` under `bazel-out/k8-fastbuild` is ELF x86-64** (host-config builds):
  libwebrtc, libcrypto/ssl, ffmpeg libav*.a, libopus, libVPX, libdav1d, openh264, ogg,
  subcodec, tgcalls_core — none usable for the device link. The arm64 objects for every
  module WITH sources are objc.py's per-file .o files under `build-input/objc-cache/`.
- **`bazel build … --cpu=ios_arm64` REPOINTS the `bazel-bin` symlink** (k8-fastbuild →
  ios_arm64-fastbuild). Address archives through the versioned
  `bazel-out/<config>/bin/...` paths, never through `bazel-bin`.
- **mozjpeg arm64 built by hand** (genrule dies on Ubuntu's `sh`=dash: "Syntax error"):
  cmake with `CMAKE_SYSTEM_NAME=Darwin`, our clang `-target arm64-apple-ios16.0 -isysroot
  $SDK`, **`CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`** (the executable link check
  would fail), `-fuse-ld=$TS`; outputs copied to
  `bazel-bin/third-party/mozjpeg/Public/mozjpeg/{headers,jconfig.h,lib/libjpeg.a,lib/libturbojpeg.a}`.
  MozjpegBinding 1/1.
- **ffmpeg arm64**: `/tmp/build-ffmpeg-linux.sh` (copy of `build-ffmpeg-bazel.sh` with
  `-arch arm64`/`xcrun -sdk … clang` replaced by `-isysroot $SDK --target=…` / our clang
  with `-fuse-ld=$TS -mlinker-version=1114`). Staging the genrule does in its execroot:
  `Sources/FFMpeg/lib{opus,dav1d,vpx}/` populated from
  `bazel-out/k8-fastbuild/bin/third-party/{opus,dav1d,libvpx}/Public/...` (headers +
  .a; **not gitignored** — machine-local, restorable). configure also needs llvm
  binutils as `nm`/`ar`/`ranlib` on PATH (`/tmp/llvm-bin` symlinks) — the host nm can't
  read Mach-O test objects.
- Still to build for the link: ogg, openh264, webp, td, VPX, dav1d (only if ffmpeg's
  bundled static linking doesn't cover the deps), boost_regex (check whether libprisma
  actually references its symbols).

## 5. Phase 4 linker — proven

`ld64.lld` from the Swift toolchain **refuses platform iOS** and cannot read the SDK's
.tbd files. The **xtoolsdk's own toolset linker works**:
`~/dev/omarchy-apple-dev/sdk-free/sdk-cache/darwin-iPhoneOS27.2.xtoolsdk/toolset/bin/ld64.lld`
(`orig/` beside it is the unpatched one; FINDINGS.md line ~165 documents the toolset.json
wiring). Invocation:

```sh
clang++ -target arm64-apple-ios16.0 -isysroot $SDK -mlinker-version=1114 \
  -fuse-ld=$TS -dynamiclib -install_name @rpath/MtProtoKit.framework/MtProtoKit \
  -framework Foundation -framework Security -framework CFNetwork \
  -framework SystemConfiguration -framework UIKit -lSystem -lobjc -lc++ -lz \
  @objs.txt -o MtProtoKit
```

`-mlinker-version=1114` is required or clang omits `-platform_version`. **MtProtoKit
dylib linked end to end**: 1.5 MB Mach-O arm64, NOUNDEFS (93 objects, /tmp/mpk-objs.txt).
Framework partition from the graph (for the link driver): MtProtoKit 2, SwiftSignalKit 1,
Postbox 9, TelegramCore 12, TelegramUI 821 modules.

## 6. Swift ladder state

- Pass 1 finished: 91 ok + 14 cached / 632 failed — the failures are the Display
  deployment-target cascade (pass 1 ran while Display's stable swiftmodule was still the
  17.0 one) plus the MTProtoEngineFFI umbrella header, both fixed during the pass.
- **Pass 2 running** with `--min 16.0` over all 738 labels (log: /tmp/swift-pass2.log).
- The `--min` default is 17.0 — always pass `--min 16.0` (the device is iOS 16.7);
  17.0 cache entries for the TelegramCore closure exist and are harmless.

## 7. Small notes

- The `swift.py`/`objc.py` stdout is block-buffered under redirection: pass
  `PYTHONUNBUFFERED=1` or read `build-input/*-cache` manifests to monitor.
- `WalletTransactionItemComponent`-era failures in pass-1's tail are all "no such
  module" cascades, not source errors.
- All three rust target dirs and /tmp recipes are machine-local; the archives they
  produce should be copied into `build-input/link/` once the link driver lands.

## 8. Passes 2–3 and the source-level fixes they surfaced (late 2026-10-27)

- **Pass 2** finished 560 green / 177 failed; the failures were cascades behind two
  real ones, both fixed in source; **pass 3** then ran with zero new failures while
  re-verifying the earlier region.
- **`_Translation_SwiftUI`**: SwiftUI's `View.translationPresentation` lives in the
  underscore-prefixed framework; `import Translation` does not re-export it in this
  toolchain (verified with a minimal typecheck: adding `import _Translation_SwiftUI`
  flips "no member" to clean). Fixed in
  `DocumentCanvasView+EditMenuActions.swift` and `TranslateScreen.swift`.
- **The clang-claiming bug, second appearance**: TabBarComponent (single file,
  `import UIKit/Display/SearchBarNode`) could not see `ASDisplayNode`; ddmin over the
  file's import lines reduced it to `import SearchBarNode` — a SWIFT module whose
  interface references AsyncDisplayKit types claims the clang decls on import and
  shadows them, same family as the `UIBarButtonItem+Proxy.h` poison. Rebuilding
  SearchBarNode does not help and import order does not matter. **Fix: a direct
  `import AsyncDisplayKit` in the consuming file** (verified: direct import → clean
  compile). Applied to `TabBarComponent.swift`; the same one-line fix is the playbook
  for any future "cannot find type 'AS…'" in a module that imports another
  swift module exposing ADK types.
- **Single-file swift modules compile in script mode** (top-level code): CloudData,
  Emoji, Reachability each emitted `T _main` and collided at the link. swift.py now
  passes `-parse-as-library` for single-source modules only (scoping keeps other cache
  keys stable).
- **libvpx arm64**: the `*-darwin*` configure branches are xcrun-tangled (they
  overwrite CC from `xcrun --sdk iphoneos --find clang`, probe `-Werror` rejects
  `-fuse-ld`, the link check drives the host ld). Built with `--target=generic-gnu`
  (C-only, no NEON) + `/tmp/ios-clang.sh` as CC, whose wrapper adds `-fuse-ld` only
  for non-`-c` invocations. Fine for a first ship; revisit for NEON later.
- **ffmpeg arm64 built** (libavcodec/format/util/swresample, `/tmp/build-ffmpeg-linux.sh`
  + staged libopus/libdav1d/libvpx from the k8 Public trees + llvm binutils as `nm`).
  The pkg-config shim's version dance passes once the staged `libdav1d.a` is actually
  arm64 (the first staging silently kept the k8 x86 archive — `chmod u+w` first, the
  genrule writes read-only files).
- **libwebp arm64**: same cmake recipe as mozjpeg
  (`CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`). libogg needs no archive (ogg has
  sources, objc.py compiles them).
- All arm64 genrule archives now live in **`build-input/link/libs/`** (av*4, dav1d,
  opus, vpx, webp×3, mozjpeg via bazel-bin) — link.py's GENRULE_LIBS points there.
  Still missing at link time, if anything references them: td, boost_regex,
  openh264-encoder.
- webrtc at 1195/1198: the `<third_party/ffmpeg/...>` alias tree
  (`build-input/link/webrtc-include`) must point at the **k8** ffmpeg Public (the
  bazel-bin symlink had been repointed to the ios config, whose Public is pruned).

## 9. END STATE: the app builds and runs on the iPhone X (2026-10-27, 23:56)

- **TelegramUI.o**: 31.8 MB Mach-O arm64 (738/738 swift modules; the last one needed the
  `RecaptchaEnterprise` canImport stub — its xcframework ships interface-only Swift
  modules this toolchain cannot load — and a hand-built `GeneratedSources` module
  (`tools/tgbuild/stubs/GeneratedSources.swift` + `make-generated-sources.sh`) standing
  in for Apple's intent codegen).
- **`tools/tgbuild/link.py --app`** assembles the app: the five frameworks (MtProtoKit
  1.5 MB, SwiftSignalKit 0.8, Postbox 10.2, TelegramCore 61.9, TelegramUI ~370 MB) and a
  minimal Telegram binary + bundle (Info.plist via plistlib, frameworks embedded,
  PresentationStrings.data). 448 MB uncompressed, 135 MB ipa.
- **`xtool install --usb build-input/link/Telegram.ipa`** → provisioned, signed,
  "Successfully installed!" on [redacted-device] (iOS 16.7). The Developer Disk Image
  was mounted with `pymobiledevice3 mounter auto-mount` (needed only for launching via
  a debugger).
- **Launched**: `idevicedebug run ph.telegra.Telegraph` (task attach is denied on a free
  account but the process starts); `pymobiledevice3 processes ps` shows
  `"ProcessName": "Telegram"` alive minutes later, in the foreground
  (`idevicescreenshot` → black screen: no LaunchScreen.storyboard/Assets.car/.metallib
  in the bundle yet — the app window renders nothing without them).
- Link fixes this phase, in order: framework dylibs linked by path (not -framework);
  swift tbds dir on -L; the objects.json **basename collision** (two
  `audio_encoder_opus.cc`) silently dropped objects — keys are source labels now;
  `-parse-as-library` must be part of the cache key; rust archives carry duplicate
  runtimes — tlottie was rebuilt `panic=abort`, mtproto/wallet keep their std cgu with
  `_rust_eh_personality` **weakened** (llvm-objcopy -W; localizing or dropping the member
  breaks `__rustc::__rdl_alloc`); libvpx.a needed re-indexing (GNU SYMDEF that lld
  rejects); `libsharpyuv.a` joins the webp set; Combine's symbols live in
  Combine.framework (no libswiftCombine.tbd); `libclang_rt.ios` from the toolchain clang
  dir supplies `__isPlatformVersionAtLeast`; the third-party/ogg and
  third-party/opusfile modules are excluded from the link (OpusBinding vendors both);
  the desktop ADM (`audio_device_impl.cc`) and the stdlib task-queue factory are
  skipped (the iOS build uses tgcalls's vendored copies — audio_device_impl.cc's
  `webrtc::ios_adm::AudioDeviceIOS` reference is link-stubbed in
  `build-input/link/webrtc-ios-adm-stub.cpp`); gcd_helpers.m is excluded from
  webrtc_objc (webrtc_platform_helpers carries it).
