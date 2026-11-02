# Phase 2 receipt — ObjC backend: driver, modulemaps, stub layer (2026-10-25)

**Goal (plan §4 Phase 2):** auto-generate a `module.modulemap` per `objc_library`, iterate the
survey driver over modules in dependency order, fix what is fixable without the full SDK.
**Acceptance (full):** MtProtoKit and LegacyComponents fully compile — **not met, and the gap is
now precisely the user-gated part**: every remaining failure is either a framework the sdk-free
sysroot does not ship at all, or UIKit API breadth (the sysroot's UIKit is a 285-line skeleton).
Both are lifted wholesale by the Phase 0 Xcode .xip (full-SDK mode). Everything below that line
compiles.

## Tools built

- **`tools/tgbuild/objc.py`** — the ObjC/C compile driver. Per module, from
  `build-input/graph/modules.json`: resolves the compile closure (`--list` prints it
  deps-first), generates `module.modulemap` + umbrella header (the night session's hand-built
  MonotonicTime pattern, generalized; headers stay in the repo), compiles every compilable src
  (`.m .c .mm .cpp .cc .S`; `srcs` may list private headers — skipped) with flags from the
  Bazel graph (includes, copts minus `-Werror` unless `--strict`, defines, `non_arc_srcs` →
  `-fno-objc-arc`), dep modulemaps via `-fmodule-map-file`, content-hash object cache under
  `build-input/objc-cache/` (src + flags + modulemap hashed; `--force` rebuilds), and a failure
  taxonomy: `sdk-header-missing` (sysroot ceiling) vs `local-header-missing` vs `code-error`.
  Per-module `results.tsv` + `objects.json`. The stub layer is forced in via `-include`
  (`--no-stubs` disables it once the full SDK lands). PATH to the Swift 6.4 clang is set
  internally (`/usr/local/usr/bin` — cc.sh finds clang through `swift`).
- **`build-input/objc-stubs/`** — the no-Xcode shim layer (the plan's sanctioned "stay no-Xcode
  and add stubs" path, at sysroot level instead of per module):
  - Darwin system headers: `os/lock.h`, `pthread/pthread.h` + flat `pthread.h`, `sys/socket.h`,
    `netinet/in.h`, `netinet/tcp.h`, `arpa/inet.h`, `netdb.h`, `net/if.h`, `ifaddrs.h`,
    `sys/mman.h`, `sys/sysctl.h`, `sys/stat.h`, `fcntl.h`, `strings.h`, `endian.h`,
    `libkern/OSByteOrder.h`, `libkern/OSAtomic.h`, `mach/mach_time.h`, `zlib.h` (canonical
    z_stream layout), `features.h`, `bsm/audit.h` (from the night session).
  - `darwin-extras.h` (forced into every TU): CF time types the rebuilt CoreFoundation.h omits
    (CFAbsoluteTime, kCFAbsoluteTimeIntervalSince1970, CFBridging*), dispatch sources
    (dispatch_source_t as an ObjC class pointer — that is what OS_OBJECT_USE_OBJC means at
    runtime and what makes `@property (nonatomic, strong) dispatch_source_t` legal under ARC),
    Foundation classes/selectors the rebuilt set lacks (NSURLSession family, NSKeyedUnarchiver,
    NSMutableURLRequest, NSException, NSHTTPURLResponse, NSScanner, NSIndexSet/NSMutableIndexSet,
    NSOutputStream, NSCoder numeric codecs, NSData/NSString/NSBundle/NSURL/NSThread/NSSet/NSArray
    categories, NSComparator, NSRegularExpressionSearch, bzero/open/read/lseek).
  - `darwin-uikit-extras.h` (forced only for modules with UIKit in sdk_frameworks — splitting
    it out kept Foundation-only modules UIKit-free): UIImage +imageNamed:inBundle:.
  - UIKit/QuartzCore/CoreGraphics **subheader** stubs (the frameworks exist but as one
    consolidated header): UIKit/UIGeometry.h etc., CoreGraphics/CGAffineTransform.h.
- **Driver C++ stopgap**: the sysroot ships no C++ headers and uses `-nostdinc`; `.mm`/`.cpp`
  TUs get the host's libstdc++ headers as `-isystem` (compile-only; link/runtime ABI against
  real libc++ is Phase 4's concern).

## Commands

```sh
cd $HOME/dev/Telegram-iOS
python3 tools/tgbuild/objc.py //submodules/MtProtoKit:MtProtoKit --force
python3 tools/tgbuild/objc.py //submodules/LegacyComponents:LegacyComponents --force   # closure: AppBundle, SSignalKit first
```

## Results (per module, after iterating the stub layer to its user-independent limit)

| Module | Compilable srcs | OK | Remaining | Nature of the remainder |
|---|---|---|---|---|
| EncryptionProvider | 0 (header-only; modulemap generated) | — | — | — |
| AppBundle | 1 | **1 (100 %)** | 0 | — |
| SSignalKit | 24 | **24 (100 %)** | 0 | — |
| MtProtoKit | 93 | **83 (89 %)** | 10 | all `sdk-header-missing`: Security/Security.h ×3, CommonCrypto ×4, CFNetwork ×2, SystemConfiguration ×1 — four frameworks absent from the sysroot |
| LegacyComponents | 413 | 43 (10 %) | 370 | 129 `sdk-header-missing` (OpenGLES ×57, AVFoundation ×47, Photos ×9, QuartzCore-headers ×12, CoreVideo ×2, CoreText ×1, UniformTypeIdentifiers ×1) + 241 `code-error`, dominated by the skeleton UIKit/Foundation surface: unknown `NSOperation` ×55, `UIEdgeInsets` ×11, `UIImageOrientation` ×10, `UIUserInterfaceSizeClass` ×6, … |

Night-session baseline for comparison: MtProtoKit 39/93 *with the `-Wno-everything` crutch*;
now 83/93 with honest flags (only `-Werror` dropped, as a dev build warrants).

## Evidence the objects are real

`build-input/objc-cache/` holds 338 content-hashed objects. `MTContext.m.o`: Mach-O 64-bit
arm64 (magic `0xfeedfacf`, cputype 16777228), 1251 symbols, 240 text, `_OBJC_CLASS_$_MTContext`
metadata present, cross-module undefineds (`_OBJC_CLASS_$_MTDatacenterAddressSet`, …) exactly
what Phase 4 links against the app's other objects and the real iOS dylibs.

## Notable facts

- The stub layer is **additive and mechanically checkable**: every declaration mirrors the
  real iOS SDK signature; it applies only in no-Xcode mode (`--no-stubs` flips it off when the
  Phase 0 SDK lands, after which the sysroot's own headers must cover everything — any file
  that then fails marks a stub that lied).
- `sdk-frameworks` in `LegacyComponents/BUILD` spells UIKit as `UIKIt`; the driver
  case-insensitively maps framework names when deciding the UIKit forced-include.
- The 10 remaining MtProtoKit files are the *core crypto/network* ones (MTEncryption, MTRsa,
  MTAes, GCDAsyncSocket, PingFoundation, MTNetworkAvailability, MTTcpConnection, …): the
  absent frameworks are exactly Security/CommonCrypto/CFNetwork/SystemConfiguration. So even
  "MtProtoKit links" waits on the .xip — unless one hand-grows those four frameworks' headers,
  which is possible (their used surface is ~30 symbols) but the plan's estimate stands: the
  .xip is the single lever.
- LegacyComponents' ceiling is qualitatively different: OpenGLES/AVFoundation/Photos are used
  for real GPU/video/photo code — those are not stubbable at any honest fidelity; only the
  real SDK headers close them.

## Artifacts

| Path | What |
|---|---|
| `tools/tgbuild/objc.py` | the driver (repo, versioned) |
| `build-input/objc-stubs/` | 33 stub headers: 21 system headers + 10 framework subheaders + 2 forced includes (machine-local, gitignored) |
| `build-input/objc/<Module>/` | `module.modulemap` + umbrella header for **all 78 objc_library modules** in the graph (generator pass; `results.tsv` + `objects.json` for the five driven closures) |
| `build-input/objc-cache/<hash>/` | 338 Mach-O arm64 objects, content-hashed |
