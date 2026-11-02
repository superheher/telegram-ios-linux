# Receipt: the first real launches of the Linux build, and what they took

Date: 2026-10-28. Started as "make the launch non-black" (per
[`linux-build-next-session.md`](../linux-build-next-session.md) §1) and ended as the
first launches of the Linux-built app **as itself** — with a correction of yesterday's
central claim recorded in §1. Everything below is evidence-backed.

## 0. CORRECTION of the 2026-10-27/28 claims: which app was actually launched

Until 11:00 today, every launch used bundle id `ph.telegra.Telegraph`. `pymobiledevice3
apps list` shows **two** apps on the phone:

- `ph.telegra.Telegraph` — the **official App Store Telegram** (signer "Apple iPhone OS
  Application Signing", team C67CF9S4VU, container EC310818…), still installed;
- `XTL-[redacted-team-id].ph.telegra.Telegraph` — **our build** (signer "Apple Development:
  [redacted-apple-id]", get-task-allow, our own minimal Info.plist verbatim).

xtool suffixed the bundle id at provisioning. Every launch by the canonical id therefore
foregrounded the **official** app: the 2026-10-27 "process alive, black screenshot", this
morning's identical observation, and — the big one — the 10:02 screenshot of a
**rendered, signed-in chat list**, which was the official Telegram, not our build. The
chat-list "milestone" of this morning was invalid and is retracted. The logged-in account
the user saw belongs to the phone's own official Telegram; our installs never touched its
data container.

The honest first launch of our build happened at 11:15 today (by the XTL- id), and it
crashed in dyld — the chain below is what it took to get past that, and §5 is where it
currently stands.

## 1. What proves a build is ours

- The home-screen icon label reads **"Linux NUC"** (`CFBundleDisplayName` in link.py),
  visible in screenshots (`docs/receipts/assets/2026-10-28-linux-nuc-icon.png`).
- The phone-entry screen's large title (`Login.PhoneTitle`) and the in-app app name
  (`Application.Name`) are rewritten to "Linux NUC" at package time (link.py
  `assemble_resources`, with an assert that the strings exist).
- The installed app answers to `XTL-[redacted-team-id].ph.telegra.Telegraph`, signed by the
  free team, `MinimumOSVersion 16.0`, portrait-only, `CFBundleIcons` exactly as link.py
  writes them.
- The `[tgbuild]` breadcrumb file it writes into its own container
  (`Documents/tgbuild-log.txt`, pulled with `pymobiledevice3 apps pull`) is the same
  instrumentation compiled into `main.m`/AppDelegate.

## 2. The dyld launch chain (crashes fixed in order, all evidence = .ips files)

1. `dyld4::PrebuiltLoader::serialize` assertion — ld64 auto-adds the app rpath and marks
   swift overlays weak; the xtoolsdk lld does neither. Fixed in link.py:
   `-rpath @executable_path/Frameworks -rpath /usr/lib/swift` on every link, and a
   post-link pass flipping `/usr/lib/swift/*` and the 17+-only Translation frameworks'
   loads to `LC_LOAD_WEAK_DYLIB` (25 loads in TelegramUI, 2 in the binary).
2. `unknown library ordinal 20 … binding '_pthread_create'` — self-inflicted: the first
   flip patch wrote `0x18` where `LC_LOAD_DYLIB` is `0x0C`, corrupting 15 load commands.
   Fixed; note `LC_RPATH` is `0x1C | 0x80000000` (the req bit), which cost a debug round.
3. Same serialize assertion again — the frameworks were at the bundle root; the
   `@executable_path/Frameworks` rpath needs `Telegram.app/Frameworks/` (link.py now
   puts them there and removes stale root copies).
4. `Symbol not found: _swift_allocateMetadataPack` — the Swift 6.4 compiler emits
   metadata-pack calls that only exist in the runtime from iOS 17; Apple toolchains
   statically link `libswiftCompatibilityPacks.a` for targets ≤ 16.4, and the Linux
   toolchain ships no such archive. `build-input/link/swift-pack-shim.c` implements
   `swift_allocateMetadataPack`/`swift_allocateWitnessTablePack` from the upstream
   semantics (LSB-tagged heap pointer, count at elements[-1], content-uniqued); linked
   into all five frameworks + the binary via link.py `PACK_SHIM_O`.

## 3. The startup chain after dyld (evidence = the in-app breadcrumb file)

`main.m` (tglog) and AppDelegate (tgbuildLog) append `Documents/tgbuild-log.txt`;
`pymobiledevice3 apps pull <XTL-id> Documents/tgbuild-log.txt` reads it. This is the
only working app-level diagnostic channel — the device syslog does NOT carry the app's
NSLog output, and debugserver attach is denied on the free account.

- `classes Application=found AppDelegate=found` — the `//Telegram:Lib` link fix
  (yesterday's) verified.
- `didFinishLaunching: MetalEngine.shared ok` — the runtime MSL compile works on device
  (MetalEngineShaders.metal → `device.makeLibrary(source:)`, ~1 s on the iPhone X).
- The hang found by dense breadcrumbs: `guard let appGroupUrl = maybeAppGroupUrl` —
  the free-provisioned profile carries **no App Group entitlement**, `containerURL…`
  returns nil, and the app took a silent `presentNative(UIAlertController("Error 2"));
  return true` — no window, no crash, forever black. Fixed with a `#if TGBUILD` fallback
  to the app's own Documents container (the group is only shared with extensions, which
  this build has none of).
- `CloudKit` EXC_BREAKPOINT in `fetchRawData` — `CKContainer.default()` traps without
  the iCloud entitlement. `#if TGBUILD` stub in CloudData.swift returning an async
  `.generic` error (async because the upstream `|> restart` chain re-enters
  synchronously — the first synchronous version stack-overflowed).
- `-[TLObject tl_typeIndex]: unrecognized selector` (twice: MTLog's description path and
  the response parse path) — **the TL_OBJC_DIRECT contract**: TelegramApiObjC's
  TLObject.h declares its accessors `direct` under `TL_OBJC_DIRECT=1`, which the ObjC
  side receives (objc.py passes dep defines), and direct methods are *removed from the
  runtime method list*. swift.py only passed a module's OWN defines, never its objc
  deps', so Swift called `tl_typeIndex` via objc_msgSend — into a table that no longer
  has it. Fixed by having swift.py pass `TL_OBJC_DIRECT=1` as `-Xcc -D` for every module
  with TelegramApiObjC among its transitive objc deps (Bazel semantics: the define
  reaches the clang importer). MTLog's description path additionally degrades to
  "unknown" under TGBUILD when a payload is not an NSObject.

## 4. Where it stands (end of this session)

**The Linux build renders its first screen.** After the TL_OBJC_DIRECT ladder rebuild
(574 modules), relink and install, the app launched by `XTL-[redacted-team-id].ph.telegra.Telegraph`
and rendered the full onboarding screen — the large title reads **"Linux NUC"**
(Tour.Title1), the tagline, the page dots and the Start Messaging button; the process
stays alive (pid evidence in `processes ps`, both apps side by side). Screenshots:
`docs/receipts/assets/2026-10-28-linux-nuc-onboarding.png` (the onboarding screen),
`…-linux-nuc-icon.png` (the "Linux NUC" icon on the home screen),
`…-onboarding-before-marker.png` (the same screen before the Tour.Title1 marker, saying
"Telegram"). The network path works end to end: the app's `help.getConfig` round trip
completed and parsed — the previous run's parse crash is gone with the direct-define
rebuild.

The breadcrumb instrumentation (main.m tglog + AppDelegate tgbuildLog +
Documents/tgbuild-log.txt) stays in the tree under `#if TGBUILD` — it is the only working
app-level diagnostic channel found so far.

## 5. The iteration recipe as it stands (all commands work)

```sh
export PATH=/usr/local/usr/bin:$HOME/.local/bin:$PATH PYTHONUNBUFFERED=1
python3 tools/tgbuild/swift.py //submodules/<mod>:<mod> --min 16.0   # stale-by-mtime
python3 tools/tgbuild/link.py --app                                  # ~1 min
cd build-input/link && rm -rf Payload Telegram.ipa && mkdir Payload && \
  cp -a Telegram.app Payload/ && zip -qry Telegram.ipa Payload
# kill any running instance first — a live old install wedges xtool at 100%:
~/pymobiledevice3/bin/pymobiledevice3 developer dvt kill <pid>
xtool install --usb Telegram.ipa
~/pymobiledevice3/bin/pymobiledevice3 developer dvt launch XTL-[redacted-team-id].ph.telegra.Telegraph
idevicescreenshot /tmp/shot.png
~/pymobiledevice3/bin/pymobiledevice3 apps pull XTL-[redacted-team-id].ph.telegra.Telegraph \
  Documents/tgbuild-log.txt /tmp/log.txt
idevicecrashreport -e /tmp/crashes
```

## 6. Traps added to the collection

- **`grep` here is ugrep and silently skips binaries** — "not found" results on .o/.a
  files are meaningless; scan with python.
- **`pkill -f "xtool install"` kills your own shell** (the pattern matches the shell's
  own command line). Use `pkill -x xtool`.
- **xtool install wedges at 100%** while an old instance of the app is running — kill
  the app (`developer dvt kill <pid>`) and the install completes on its own.
- **Two Telegrams live on the device**; launching by `ph.telegra.Telegraph` launches the
  official one. Ours is `XTL-[redacted-team-id].ph.telegra.Telegraph`.
- **idevicesyslog carries NSExceptions** ("Terminating app due to uncaught exception…")
  even though it does not carry NSLog — the reason line names the exact selector.
- **`LC_LOAD_DYLIB` is 0x0C, `LC_LOAD_WEAK_DYLIB` is 0x18|0x80000000, `LC_RPATH` is
  0x1C|0x80000000** — for hand-patched Mach-O headers.


## 7. API credentials wired (2026-10-28 evening)

The placeholder credentials from `build-input/configuration-repository/variables.bzl`
(api_id 8 — the tdesktop development pair, restricted by the server) are replaced with
the user-provided pair (`telegram_api_id = "611335"`,
`telegram_api_hash = "d524b414d21f4d37f08684c1df41ac9c"`). The values reach
`BuildConfig.m` through the graph's expanded copts
(`-DAPP_CONFIG_API_ID=… / -DAPP_CONFIG_API_HASH=\\\"…\\\"`), so re-running
`tools/tgbuild/extract.py` re-expanded them, `objc.py //submodules/BuildConfig:BuildConfig
--force` rebuilt the module (the hash string is verifiable in the .o), and the relinked
app was installed and launched. `//submodules/BuildConfig:BuildConfig` is the only graph
target carrying APP_CONFIG defines. Evidence: the phone-entry screen renders with the
"Linux NUC" title, country selector, phone field and Continue
(`docs/receipts/assets/2026-10-28-linux-nuc-phone-entry.png`), process stable. The
interactive login itself is the user's step (entering the phone number and the received
code on the device) — **and it succeeded**: the user logged in with their phone number.

## 8. Post-login crashes: Siri entitlement and TCC usage descriptions

Two crashes fired right after a successful login, both entitlement/privacy-shaped:

1. `+[INPreferences siriAuthorizationStatus]` asserts the process holds
   `com.apple.developer.siri`; the authorized context checks device permissions
   (AppDelegate's `siriAuthorization` closure) and the assert aborted the app. Both Siri
   closures (`requestSiriAuthorization`, `siriAuthorization`) are stubbed under
   `#if TGBUILD` — Siri shortcuts are non-functional without the entitlement.
2. `TCC __TCC_CRASHING_DUE_TO_PRIVACY_VIOLATION__` — the minimal Info.plist carried no
   `NS*UsageDescription` keys, and the post-login flow touches Contacts. link.py now
   merges every `*UsageDescription` key from the real `Telegram/Telegram-iOS/Info.plist`
   into the packaged plist (10 keys). Verified: the contacts permission dialog now
   appears instead of the crash
   (`docs/receipts/assets/2026-10-28-linux-nuc-contacts-prompt.png`), with the session
   surviving relaunches (the login persisted in the local Postbox database).

The push-notification entitlement (`aps-environment`) is likewise absent from the free
profile — notification registration just never yields a token, which Telegram treats as
"no push"; nothing to fix for local use.

## 9. THE CHAT LIST RENDERS (2026-10-28, 22:13)

After the login, the authorized root controller stayed uninstalled and the screen black —
no crash. Breadcrumb chain: the authorized context arrived, the chat list controller's
`ready` fired (51 entries from the Postbox view), but the combined gate never completed.
The gate waits for `TabBarController.ready`, which waits until **every tab's
UITabBarItem.image is set** — and the icons are `UIImage(bundleImageName:
"Chat List/Tabs/IconChats")`-style lookups into the app bundle's **Assets.car**. Two
missing pieces, both fixed in link.py's `assemble_resources`:

1. **Assets.car from the Linux actool is rejected by the device's CoreUI**
   (`BOMFatalException` in `_BOMTreeOpen` when the chat list first opened the bundle's
   asset manager — the app aborted at startup). The car is gone entirely.
2. **Loose files instead**: every imageset from the five app catalogs (Icons,
   TelegramUI Images, LegacyImages, PasswordSetupUI, CallScreen) is exported into the
   bundle at its namespaced path (`Chat List/Tabs/IconChats@3x.png` …), which
   `UIImage(named:inBundle:)` resolves without a catalog. Vector imagesets (1244 of
   them — .svg and .pdf, both of which the Linux actool also cannot compile) are
   rasterized to 1x/2x/3x PNGs: SVG via cairosvg (pymobiledevice3 venv), PDF via
   pdftoppm at 72·scale dpi. Rasterized files are named after the IMAGESET (what
   imageNamed looks up), not the content file.

Result: the app renders the full authorized chat list — account folders, real chats with
network-loaded photo avatars, unread badges, live incoming messages (22:06 timestamps
while writing this), the Contacts/Calls/Chats/Settings tab bar with icons. Evidence:
`docs/receipts/assets/2026-10-28-linux-nuc-chat-list.png`; process stable. Known cosmetic
gaps: a few assets whose lookups remain unresolved render as white placeholders (e.g.
video-message preview icons); missing entries degrade to nil images rather than crashes
except where sources force-unwrap a lookup — those spots will surface one by one as
screens get exercised.

## 10. The static asset audit and the three export bugs it exposed (23:00–23:40)

The UI walk's §1 audit (`tools/tgbuild/audit_images.py`, 906 unique lookup names scanned
against the packaged app) found the "white placeholder" classes were not missing assets
in the repo but three systematic bugs in link.py's export — all fixed there:

1. **Shared namespaces wiped across catalogs.** `Camera/` is owned by both
   TelegramUI Images.xcassets and LegacyImages.xcassets, `Call/` by TelegramUI Images
   and CallScreenAssets. Each catalog's export cleared its namespace dirs in the app,
   so the later catalog deleted the earlier one's files — every `Camera/*` and most
   `Call/*` lookups were nil. Fixed: namespaces cleared once, before any export.
2. **Raster imagesets exported under the content filename.** `UIImage(named:)` looks up
   the imageset name, but e.g. `IconMicrophone.imageset` carries
   `ModernConversationMicButton@2x.png` — exported under the wrong name (~90 common
   lookups nil: chat input icons, avatars, item-list buttons). Fixed: raster exports
   renamed to the imageset name per Contents.json scale, light variant preferred over
   dark.
3. **`//Telegram:Lib`'s `data` closure never exported.** That closure is the Bazel
   app-root resource manifest (94 .tgs animations, BlankVideo.m4v, PhoneCountries.txt,
   `LegacyComponentsResources.bundle/`, marker.png, currencies.json, …) —
   `TGComponentsImageNamed` (LegacyComponents) was nil everywhere and the animations
   were absent. Fixed: exported flattened the rules_apple way (basename at root,
   `.lproj/`/`.bundle/` dirs kept; 678 files).

Additionally, **all 23 `apple_resource_bundle` targets of the graph are now assembled**
into `Telegram.app/Frameworks/TelegramUI.framework/<Name>.bundle/` (owner resolved from
the graph's `data` edges — all owners link into TelegramUI.framework), each with a
minimal Info.plist: DrawingUI, PremiumUI, AnimationCompression, Camera/CameraNeo,
TelegramCallsUI, CallScreen, VoiceChatActionButton, CameraScreen, DustEffect,
LiquidGlassShapes, MediaEditor, PremiumDiamond, QrStudio, StoryPeerList, Wallet×2,
HlsBundle, WallpaperBackgroundNode, Libprisma, RichTextEditorUIKitResources,
MetalEngine, CompanionResources. `LegacyComponentsResources.bundle` lands at the app
root (its loader looks in the main bundle path).

Post-fix audit: **0 force-unwrap lookups missing** (the pre-fix crash-class list —
Camera/CloseIcon+FlipIcon+Placeholder, Chat/Message/ImpressionCount, Media Editor text
tools, Peer Info/MediaGridShadow — all resolve now); the 14 remaining missing names are
guarded nil-safe lookups for assets that exist nowhere in the repo (seasonal holiday
tab icons, media-type badges, Siri/Widget extension assets, dead TGToolbarButton code).
The relinked app was installed and relaunched: the chat list renders complete (header
buttons, archive row, avatars, badges — `docs/receipts/assets/ui-walk/
2026-10-28-relaunch-after-resource-fix.png`), no new crash reports, breadcrumb
heartbeats steady. The ledger with the full tables lives in
[`docs/ui-gaps.md`](../ui-gaps.md); the screen-by-screen walk continues there.

## 11. The walk's first drive and the Metal-loader fix (2026-10-29 morning)

The user's first walk drive opened the un-joined "Pavel Durov" channel preview
(ChatController in its not-a-member mode) and scrolled it — most of the screen renders
(custom-emoji reactions, inline GIF playback, link preview with logo, date headers,
view counts, the Join bar). Two gaps found; the big one fixed the same day:

- **Glass buttons drew white squares** for their backdrops. Root cause: all 16
  component Metal loaders (LiquidGlassShapes, DrawingUI, PremiumUI, DustEffect,
  MediaEditor, CameraLegacy/Neo/CameraScreen, TelegramCallsUI, CallScreen, QrStudio,
  StoryPeerList, PremiumDiamond, Wallet×2, AnimationCompression) call
  `device.makeDefaultLibrary(bundle:)`, which requires a **compiled default.metallib**;
  the Linux bundles ship the MSL **source** (no Linux metal compiler), so every one of
  those pipelines was nil. Fix: `tools/tgbuild/patch_metal_loaders.py` patched each
  loader with a `#if TGBUILD` fallback that inlines the bundle's `#include "…"` lines
  and compiles the sources at runtime via `device.makeLibrary(source:)` — the pattern
  MetalEngine already uses (receipt §3). CompanionRenderer needed nothing (it already
  compiles its `.metal.txt` sources at runtime); WallpaperBackgroundNode and
  VoiceChatActionButton have no loader at all. All 16 modules rebuilt, app relinked,
  reinstalled, relaunched (13:25) — no crashes (`2026-10-29-metal-fix-relaunch.png`).
  Patch idempotent; re-run `patch_metal_loaders.py` safely after pulls.
- **Open:** the message column is inset ~122 pt from the right with a brighter
  wallpaper strip (measured 253 pt of 375 pt; NOT NavigationSplitContainer — its
  split-master math gives 187.5 pt; safeInsets should be symmetric on iPhone X).
- **Open (cosmetic):** message text shows through behind the header pill (no blur
  backdrop); a white placeholder square in the chat list's "Video" message preview.

New trap for the collection: **`device.makeDefaultLibrary(bundle:)` needs a compiled
metallib — on this build every bundle only carries MSL source, so any loader without
the TGBUILD source-compile fallback silently yields nil** (the feature degrades; the
white square is the tell).
