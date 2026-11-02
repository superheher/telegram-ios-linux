# Host toolchain scripts

Vendored from the `omarchy-apple-dev` toolkit (MIT, see NOTICE.md), with no
functional changes. They build and drive the toolchain that the `tools/tgbuild`
drivers expect on the host; the drivers' defaults point at the layout these
scripts produce.

| File | Role |
|---|---|
| `install-toolchain.sh` | Installs the iOS-on-Linux toolchain: Swift 6.4 toolchain, xtool (built from source), the iOS SDK out of an Xcode `.xip` (`xtool sdk build`), pymobiledevice3, and the host-side Bazel. Re-runnable; pieces already in place are skipped. |
| `cc.sh` | The clang wrapper `tools/tgbuild/objc.py` invokes for every C/ObjC file (resource-include ordering, `-iframework` for SubFrameworks, per-TU libc++ handling via `NOSDK_CXX_V1`). `TGBUILD_CC` in objc.py overrides the path. |
| `xip_extract.py` | Streams private-framework headers and module maps out of the Xcode `.xip` without unpacking Xcode: `xtool sdk build` drops them from the sdk-cache bundle, and public framework headers import private frameworks unguarded. |
| `xip_version.py` | Reads the Xcode build version out of a `.xip` before committing to the multi-GB `xtool sdk build`. |

Toolchain layout these produce (and the drivers' defaults assume):

- SDK cache: `~/dev/omarchy-apple-dev/sdk-free/sdk-cache/darwin-iPhoneOS27.2.xtoolsdk`
  (override with `TGBUILD_XTOOLSDK`; the SDK inside must be iPhoneOS27.2 for a
  Swift 6.4 toolchain).
- sdk-free tree: `~/.local/share/omarchy-apple-dev/sdk-free` (override with
  `SDKFREE_HOME`) — the pre-Xcode sysroot mode and `cc.sh` live here.
- clang/ld64.lld: `/usr/local/usr/bin` (Swift toolchain bin dir first on PATH;
  `TGBUILD_CLANG` overrides the clang++ path).

`install-toolchain.sh` is written for Arch-based hosts and mentions Omarchy in
places; the steps are portable, the package manager calls are not.
