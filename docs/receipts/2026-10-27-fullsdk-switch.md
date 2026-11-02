# Receipt: full-SDK mode — drivers switched, ladder to TelegramApi green, MtProtoKit 93/93

Date: 2026-10-27. Machine state this depends on: `~/dev/omarchy-apple-dev/sdk-free/sdk-cache/
darwin-iPhoneOS27.2.xtoolsdk` (built 2026-10-26, see `linux-build-next-session.md` §1a),
Swift 6.4 toolchain at `/usr/local/usr`, `Xcode_27.2_Release_Candidate.xip` in the repo root.

## 1. Driver changes (repo-tracked)

- `tools/tgbuild/objc.py`: sysroot resolution `TGBUILD_SYSROOT` > xtoolsdk default, with
  `TGBUILD_SDKFREE=1` restoring the sdk-free tree; full mode drops the stub include path
  entirely, uses the SDK's `usr/include/c++/v1` **per C++ file only** (module-level placement
  shadows `<stdatomic.h>` for .m files: `unknown type name 'atomic_bool'` reproduced and fixed),
  folds the sysroot into the object hash, and shares one clang module cache
  (`build-input/objc-cache/clang-modules`). cc.sh is fed `NOSDK_SYSROOT=$SYSROOT`,
  `NOSDK_MIN=16.0`.
- `tools/tgbuild/swift.py`: full mode = `-sdk <real SDK>`, synthesized resource dir
  (`build-input/swift/full-res` — symlinks to the toolchain's `lib/swift/{clang,shims}`;
  the toolchain resource dir itself puts `os/` shim headers ahead of the SDK and Dispatch's
  module stops building), `-I <xtoolsdk>/…/swift/iphoneos/prebuilt-modules/27.2`, toolchain
  shims modulemap, repo module dir. Dropped: overlay dir, sdkm framework maps, apinotes,
  `-nostdinc`, the swift `os`/`Network` shim modules (the SDK carries real ones).
  `--emit-only` no longer copies a nonexistent .o.
- `~/dev/omarchy-apple-dev/sdk-free/cc.sh` (machine-local repo, uncommitted): clang
  resource dir BEFORE `-isystem $SR/usr/include`; `-iframework` for PrivateFrameworks and
  SubFrameworks.

## 2. SDK cache repair (machine-local, restorable from the .xip)

```
ln -sfn Endian.h $SR/usr/include/endian.h
ln -sfn CommonHMAC.h $SR/usr/include/CommonCrypto/CommonHMac.h
python3 ~/dev/omarchy-apple-dev/tools/xip_extract.py Xcode_27.2_Release_Candidate.xip "$SR" \
  --prefix "Xcode.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS.sdk/System/Library/" \
  --no-clobber     # 4573 files: SubFrameworks (16 frameworks incl. UIUtilities), nested frameworks
```

Facts discovered: the .xip's SDK dir is `iPhoneOS.sdk` (unversioned; `AppleTVOS27.2.sdk`
style names exist as extra symlink-ish members); the iPhoneOS SDK ships **no
PrivateFrameworks** — the private headers UIKit imports live under `SubFrameworks`;
several members are `NULLcanary`-padded placeholders in the .xip (e.g. UIKit's UIView.h)
whose real content only exists in the cache — hence `--no-clobber`. Extracted files scan
clean (0 NULLcanary hits).

## 3. Evidence

```
$ python3 tools/tgbuild/objc.py //submodules/MtProtoKit:MtProtoKit --no-stubs --force
EncryptionProvider              0/0    ok
MtProtoKit                     93/93   ok

$ python3 tools/tgbuild/swift.py //submodules/TelegramCore:TelegramCore --min 16.0
SwiftSignalKit  ManagedFile  RangeSet  Postbox  TelegramApi  MediaPreuploadRegistry
WebProxyTransport  CloudData  Reachability  Emoji  FlatBuffers  FlatSerialization  TelegramCore
summary: cached=12, ok=1        # TelegramCore ok incl. the -c object pass
$ file build-input/swift/objects/TelegramCore.o
build-input/swift/objects/TelegramCore.o: Mach-O 64-bit arm64 object
```

Mach-O proof (full SDK, real Foundation+UIKit):

```
$ swiftc -Onone -target arm64-apple-ios16.0 -sdk $SR -resource-dir build-input/swift/full-res \
    -I <prebuilt-modules> … -emit-object -c /tmp/tf.swift -o /tmp/tf.o   # imports Foundation, UIKit
$ file /tmp/tf.o
/tmp/tf.o: Mach-O 64-bit arm64 object
```

The source change: `WebProxyWebViewCarrier.swift` — `@available(iOS 27.0, *)` on
`requestGeolocationPermissionFor` and `@available(iOS 18.4, *)` on `runOpenPanelWith`
(the sdk-free header baseline had left them unannotated; the real SDK annotates).

## 4. Negative results worth keeping

- `arm64e-apple-ios.swiftmodule` (the only device slices Apple prebuilt) import cleanly
  for an arm64 target — no rebuild of overlays needed.
- The `EncryptionProvider` whole-module failure (see below) is **not** an artifact of the
  full-SDK switch: the same error blocked TelegramCore in sdk-free mode (§4.1 of the
  handoff, written 2026-10-25).
- Reordering `import EncryptionProvider` above `internal import TelegramApi` does not help.
- **Direct-header modulemaps** (`header "<abs path>"` instead of the generated umbrella)
  make the import fail in configurations that pass under the umbrella form — the generator
  was reverted the same day; an apparent "3/3 pass" for direct headers was a test harness
  bug (a `-Xcc -fmodule-map-file=…` flag glued into one argv, so swiftc died on an unknown
  argument and the absence of type errors read as success). Keep the umbrella form.
- **Debug-probe masking**: a temporary `EncryptionProviderProtocol`-typed probe function in
  the failing file makes every later run report the *suffixed* spelling first (line order),
  and the suffixed name fails strictly more often than the plain one. The probe was
  removed; the honest signal is the plain `EncryptionProvider` name.
- Clean statement after removing the probe: one file + the full TelegramCore clang flag
  set compiles the import; the 718-file whole-module compile in driver source order
  fails deterministically — **unless the importing file is placed first in the source
  list, in which case it compiles cleanly (2/2 runs each way)**. This compiler's
  ClangImporter is source-order sensitive in whole-module compiles. swift.py retries a
  failed pass once with the file named in the first "cannot find type" error rotated to
  the front; with that, TelegramCore compiles end to end.
- The objc sweep under the full SDK: 111 modules, 946/3070 objects. The misses
  concentrate in third-party C++ (webrtc 1217, absl 144, crypto 360, ssl 37,
  AsyncDisplayKit 39, LegacyComponents 23) — a separate campaign; repository ObjC
  modules are largely green (MtProtoKit 93/93, LegacyComponents 390/413, Stripe 27/27,
  ZipArchive 16/16, libphonenumber 13/13).
- **Display** (153 files) fails the same way (`ASDisplayNode` invisible whole-module,
  single-file fine) and is NOT healed by the rotation retry or clang-cache warming —
  open (§4.1 of the handoff).
- Earlier readings superseded by the above: "stale sdk-free-era clang cache passes"
  (that probe's exit status was swallowed by a pipe; likely a swiftc crash, not a pass),
  and "excluding the 196 `import MtProtoKit` files fixes it" (same masked-error hazard).
