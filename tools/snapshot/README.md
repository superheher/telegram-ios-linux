# sdk-free snapshot — recovery point for the pre-Xcode sysroot

Faithful copy of every **authored** file that the sdk-free build mode needs
outside this repository. The original tree lives under
`~/.local/share/omarchy-apple-dev/sdk-free/` (see `tools/host/`), is not under
version control, and predates the full-SDK mode: with a real iPhoneOS27.2 SDK
built from the Xcode `.xip` (`xtool sdk build`), this whole tree is unused.
It is published as the recovery point for the sdk-free mode and as the
drift reference for the full-SDK setup.

Layout mirrors the destination paths relative to
`~/.local/share/omarchy-apple-dev/sdk-free/`:

| Here | Destination |
|---|---|
| `darwin-usr-include/module.modulemap` | `swift/darwin/usr/include/module.modulemap` |
| `darwin-usr-include/clock_shim.h` | `swift/darwin/usr/include/clock_shim.h` |
| `sdkm-foundation-headers/Foundation.h` | `swift/sdkm/Frameworks/Foundation.framework/Headers/Foundation.h` |
| `sdkm-frameworks/<Name>/…` | `swift/sdkm/Frameworks/<Name>.framework/{Headers,Modules}/…` |
| `host-zlib/module.modulemap` | also mirrored in-repo at `build-input/host-zlib/` (host SwiftTL build) |

The Swift-side overlay sources that consume these headers are in-repo at
`tools/tgbuild/overlay/`; `tools/tgbuild/rebuild-foundation.sh` applies them.

## Files not published here

Five files of the sdk-free tree carry Apple's license headers (APSL /
Apple OS Reference). They are not copied into this repository; if you rebuild
the sdk-free mode, create them yourself as follows:

| File (destination path) | Origin | What to do |
|---|---|---|
| `swift/darwin/usr/include/objc/NSObject.h` | Apple ObjC runtime header (apple-oss `objc4`) | Take the upstream `NSObject.h` unchanged; the sdk-free tree only shortens it to the declarations the importer needs. Any current objc4 revision works. |
| `swift/darwin/usr/include/libkern/OSAtomic.h` | Apple libkern header (apple-oss `xnu`) | Take upstream `libkern/OSAtomic.h` unchanged. |
| `swift/darwin/usr/include/_time.h` | Apple C library header (apple-oss) | Take upstream `_time.h`; the sdk-free copy carries small marked additions (clock ids consumed by `clock_shim.h`). |
| `swift/darwin/usr/include/sys/fcntl.h` | Apple C library header (apple-oss) | Take upstream `sys/fcntl.h`; one marked edit: `open` is declared non-variadic so the Swift importer exposes `open(_:_:_:)`. |
| `swift/darwin/usr/include/sys/_types/_s_ifmt.h` | Apple C library header (apple-oss) | Take upstream unchanged. |

The `module.modulemap` beside them **is** authored (this repository, this
directory) and declares the Darwin module over those headers.
