# Build guide: Telegram-iOS from Linux, end to end

This guide takes a clean Ubuntu 24.04 x86_64 host to an installed, running
build of Telegram-iOS on an arm64 iPhone. Everything it uses is in this
repository (`tools/`, `patches/`) plus public downloads (Swift toolchain,
Xcode `.xip`, pinned flatbuffers). Written from the sessions this repo
documents — see `docs/journal/` and `docs/receipts/` for the evidence trails.

## 0. What you need

| Requirement | Notes |
|---|---|
| Ubuntu 24.04 x86_64, ~120 GB free | the SDK cache alone is ~3.4 GB; build caches reach tens of GB; the Xcode `.xip` is 2 GB |
| 4+ cores, 16 GB RAM | 4 cores/15 GB does the whole build; it is slow (whole-ladder rebuilds run hours) |
| An arm64 iPhone with a cable | the verified device ran iOS 16.7.16; a free Apple ID works |
| Apple ID + a one-time `xtool auth` | free personal provisioning; the profile is valid 7 days per install |
| Xcode 27.2 `.xip` | must match the Swift version (Swift 6.4 ↔ Xcode 27.x); the `.xip` is a public download, not copied into this repo |
| `usbmuxd` running | `sudo systemctl restart usbmuxd` clears most wedges before blaming the cable |

## 1. Toolchain

`tools/host/install-toolchain.sh` (vendored, MIT — see NOTICE) installs, in
user paths, the pieces the drivers need; re-runs skip what exists:

- Swift 6.4 toolchain (clang, swiftc, ld64.lld land under `/usr/local/usr/bin`
  or the toolchain's bin dir — keep it first on `PATH`);
- xtool, built from source (`xtool auth` logs the Apple ID in once; the token
  lives in `~/.config/xtool/`, machine-local, never committed);
- the SDK out of the Xcode `.xip`: `xtool sdk build <Xcode.xip>` produces the
  `darwin-iPhoneOS27.2.xtoolsdk` bundle and registers it (`swift sdk list`);
- pymobiledevice3 (device install/launch/screenshot over USB);
- host Bazel 9.2.0 (only for the graph query — see `docs/architecture.md`).

Then restore what `xtool sdk build` drops from the bundle — the SDK has no
`PrivateFrameworks`, and public framework headers import private frameworks
unguarded:

```sh
python3 tools/host/xip_extract.py <Xcode.xip> <xtoolsdk-root> --no-clobber
```

The drivers find the SDK by path (default
`~/dev/omarchy-apple-dev/sdk-free/sdk-cache/darwin-iPhoneOS27.2.xtoolsdk`,
override with `TGBUILD_XTOOLSDK`; clang with `TGBUILD_CC`/`TGBUILD_CLANG`).

## 2. Repository

```sh
git clone https://github.com/TelegramMessenger/Telegram-iOS telegram-ios
cd telegram-ios
git checkout fb0e62ba8a        # the base this series is cut against
<path-to-this-repo>/patches/apply-patches.sh .   # applies patches/0001–0008
```

Patch 0008 lands inside the `submodules/TgVoipWebrtc/tgcalls` submodule — keep
that submodule checked out before applying (`git submodule update --init
submodules/TgVoipWebrtc/tgcalls`; the script does it if missing).

Then materialize the generated sources (they are not in the upstream tree):

```sh
cp -a <this-repo>/tools/generated/TelegramApi/.       submodules/TelegramApi/Generated/
cp -a <this-repo>/tools/generated/FlatSerialization/. submodules/TelegramCore/FlatSerialization/
mkdir -p third-party/wallet-engine/Generated
cp -a <this-repo>/tools/generated/wallet-engine/.     third-party/wallet-engine/Generated/
touch Telegram/empty.swift    # the //Telegram:_LocalDebugOptions placeholder
```

(Or regenerate from the schemas — recipes in `tools/generated/README.md`.)
Build these once, outside git: they stay untracked exactly like on the Mac
flow. Also create the Siri-intents stand-in after the first cache setup:
`tools/tgbuild/make-generated-sources.sh`.

## 3. Build inputs and caches

The drivers keep all state under `build-input/` (git-ignored; regenerable):

| Path | What | Regenerate |
|---|---|---|
| `build-input/graph/` | module graph from `bazel query` | `python3 tools/tgbuild/extract.py` (~1 min) |
| `build-input/swift-cache/`, `objc-cache/` | content-addressed module products | automatic |
| `build-input/swift/` | prebuilt SDK swiftmodules dir, synthesized resource dir (`full-res`), clang-cache, `GeneratedSources.o` | extract + first runs |
| `build-input/objc/` | modulemaps for the 78 objc_library targets | extract |
| `build-input/link/` | prebuilt third-party archives (ffmpeg, webrtc, tgcalls, …), pack shim, packaged app | link step |

The third-party archives (`build-input/link/libs/`) come from the one-time
Bazel phase: the patch series fixes the repo's Bazel files for x86_64 hosts
(patches 0001/0002), and `bazel build //third-party/...`-era targets produce
the static libs the app links. Rebuilding all of third-party from scratch is a
multi-hour Bazel run; the journals record which targets matter.

## 4. Compile

```sh
export PATH=/usr/local/usr/bin:$HOME/.local/bin:$PATH   # toolchain first

python3 tools/tgbuild/extract.py                        # graph (after BUILD-file changes)

# the ladder: compile every Swift module //Telegram:Telegram needs, in
# dependency order, content-hash cached. --min 16.0 IS LOAD-BEARING (see traps):
python3 tools/tgbuild/swift.py //submodules/TelegramUI:TelegramUI --min 16.0 --jobs 3

# ObjC/C modules (MtProtoKit, LegacyComponents, …):
python3 tools/tgbuild/objc.py //submodules/MtProtoKit:MtProtoKit --min 16.0
```

`swift.py` walks the whole dependency closure itself — one command covers the
~740 Swift modules. objc.py handles the ObjC side per target. After editing
ANY SDK/header material (`tools/snapshot` targets, sdkm headers):
`rm -rf build-input/swift/clang-cache` in the same command, or stale clang
module state reports ghosts.

## 5. Link, package, install

```sh
python3 tools/tgbuild/link.py --app          # frameworks + Telegram binary + resources
cd build-input/link && rm -rf Payload Telegram.ipa && mkdir Payload && \
  cp -a Telegram.app Payload/ && zip -qry Telegram.ipa Payload && cd -

xtool install --usb build-input/link/Telegram.ipa
~/pymobiledevice3/bin/pymobiledevice3 developer dvt launch \
  "XTL-<team-id>.ph.telegra.Telegraph" --kill-existing
idevicescreenshot /tmp/shot.png
idevicecrashreport -e /tmp/crashes | grep -i telegram
```

Free provisioning suffixes the bundle id with your team id (`XTL-<team-id>.…`)
— launch the suffixed id, not the canonical one (launching the canonical id
foregrounds the App Store Telegram; receipt 2026-10-28 §0).

App-level diagnostics: the binary writes `Documents/tgbuild-log.txt`
(startup breadcrumbs + heartbeats, see patches 0005/0006). Pull it with
`pymobiledevice3 apps afc <bundle-id>`; `idevicesyslog` does NOT carry the
app's NSLog output on this setup.

## 6. Iteration loops

- One Swift module: `python3 tools/tgbuild/swift.py //submodules/X:X --min 16.0`
  — cached closure, only that module recompiles (~15 min for TelegramUI, ~1 min
  for typical modules), then `link.py --app` (~4 min) + re-zip + install.
- Full stderr for one failing module: `tools/tgbuild/probe.py //submodules/X:X`.
- Assets only: `link.py --app` alone re-exports resources (~1 min).
- After editing any overlay (`tools/tgbuild/overlay/*.swift`): rerun
  `tools/tgbuild/rebuild-foundation.sh` (sdk-free mode) and reset the clang cache.
- After editing headers inside the SDK cache: reset `build-input/swift/clang-cache`.

## 7. Machine-local recovery (sdk-free mode only)

If you rebuild the no-Xcode sysroot (`tools/snapshot/` targets), restore the
snapshot: copy `tools/snapshot/` over `~/.local/share/omarchy-apple-dev/sdk-free/`
per its README (five Apple-licensed headers are not shipped — the README lists
what to take from apple-oss and what to change), then run
`tools/tgbuild/rebuild-foundation.sh` and reset the clang cache.

## 8. Known limits (see docs/status.md for the full picture)

Free-signed builds expire after 7 days (re-install to refresh). The six app
extensions and the watch app are not built. Rust-backed engines are stubbed at
link time. arm64e and iOS > 16.7 are untested.
