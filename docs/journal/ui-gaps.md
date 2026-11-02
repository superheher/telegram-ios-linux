# UI gap ledger — the read-only walk

Working ledger companion to [`ui-walk-method.md`](ui-walk-method.md): every graphical
gap found on the Linux build (statically before the walk, then screen by screen), with
root cause, fix, and status. Walk screenshots are withheld from this repository
(see `../receipts/assets/README.md`).

Started 2026-10-28 late evening. Tool: `python3 tools/tgbuild/audit_images.py` re-runs
the static audit against `build-input/link/Telegram.app` at any time.

## A. Static asset-coverage audit (§1 of the plan) — done before walking

Scanned every tracked `.swift`/`.m` source for `UIImage(bundleImageName:)`,
`UIImage(named:)` and ObjC `imageNamed:` lookups: **906 unique names**, 162 dynamic
(interpolated — unchecked by definition). Checked against the loose files in the
packaged app. The audit found three systematic export bugs that together explained
every "white icon" class; all three are fixed in `tools/tgbuild/link.py`:

| # | Root cause | Effect | Fix (link.py) | Status |
|---|---|---|---|---|
| A1 | Shared namespaces across catalogs: `Camera/` is owned by **both** TelegramUI Images.xcassets and LegacyImages.xcassets, `Call/` by TelegramUI Images and CallScreenAssets; each catalog's export cleared its namespace dirs, so the later catalog **wiped** the earlier one's exports | every `Camera/*` and most `Call/*` lookups nil (camera screen, call UI) | clear each owned namespace once, before any export | FIXED — `Camera/CloseIcon`, `Call/*` verified in the app |
| A2 | Raster imagesets whose content files are named differently from the imageset (`IconMicrophone.imageset` carries `ModernConversationMicButton@2x.png`) were exported under the **content** name; `UIImage(named:)` looks up the **imageset** name | ~90 common lookups nil (chat input icons, avatars, item-list buttons) | rename raster exports to imageset name per Contents.json scale, preferring light over dark variants (vector imagesets already did this) | FIXED — `Chat/Input/Text/IconMicrophone@2x.png`, `Avatar/ArchiveAvatarIcon*` verified |
| A3 | `//Telegram:Lib`'s `data` closure (the Bazel app-root resource manifest — 94 .tgs animations, BlankVideo.m4v, PhoneCountries.txt, `LegacyComponentsResources.bundle/`, marker.png, currencies.json, anim_*.json, InfoPlist.strings …) was never exported; only 5 catalogs and 2 hand-picked files were | features silently degrade: TGComponentsImageNamed (LegacyComponents) nil everywhere, wallpaper/dice/reactions animations missing | export the closure flattened the rules_apple way: basename at root, `.lproj/`/`.bundle/` dirs kept | FIXED — 679 files exported |
| A4 | **PDF-vector imagesets rasterized onto an opaque white background.** `pdftoppm` (the poppler-24.02 build installed here — it has no `-transp` option at all) draws the page onto white and drops alpha, so every PDF-rasterized icon shipped with a baked white square behind the glyph. 1182 of the 1577 catalog imagesets are PDF-only (73 SVG go through cairosvg — transparent; 322 raster PNGs are copied verbatim — alpha preserved), which is why "practically all" icons showed it | white square behind almost every icon on the device | `pdftocairo -png -transp` in link.py (`export_imageset`) — same pixel dimensions at the same `-r`, straight-alpha PNG, matching what actool renders | FIXED 2026-10-30 — found on-device, NOT by this audit (it checks presence, not pixels). Resources-only re-export: 3732 rasterizations, 0 failed; 3983/4183 bundle PNGs now RGBA (the 16 RGB leftovers are opaque by design: the app icon set, the cube faces, Wallet gradients; 184 more are palette PNGs copied verbatim). Corner of `Components/CommunityShadow` went (255,255,255) → (0,0,0,0); verified on the iPhone X chat list (screenshot withheld, see the assets triage) |

After the fixes the force-unwrap class (the plan's §1.3 crash risk) is resolved at the
source of the problem — the lookups resolve — rather than by stubbing call sites:

- **Force-unwrapped lookups missing pre-fix (27 sites, would crash):**
  `Camera/CloseIcon` + `Camera/FlipIcon` (CameraScreen, CaptureControls,
  FlipButtonContentComponent), `Camera/Placeholder`, `Camera/SelfiePlaceholder`
  (CallControllerNode, OngoingCallContext), `Camera/VideoMessageFlash/Flip`,
  `Chat/Message/ImpressionCount` (PresentationThemeEssentialGraphics),
  `Media Editor/Fill|Flip|Stroke` (DrawingScreen), `Media Editor/TextDefault|TextFilled|
  TextSemi|TextStroke` (TextSettingsComponent), `Peer Info/MediaGridShadow` (7 sites).
  All exported after A1/A2; the post-fix audit reports **0 force-unwrap lookups
  missing**.
- The three the plan named from last session — `Chat/Message/ReplyQuoteIcon`
  (TextNode), `Item List/PremiumIcon` (TextAlertController), `Components/AppBadge`
  (WindowContent) — already exported (vector rasterization did them right); verified
  present.
- Remaining audit residue (benign, nil-degrading, no force-unwraps; 14 names):
  - `Chat List/Tabs/Holiday/Icon*` — seasonal tab icons; the imagesets exist nowhere in
    the repo catalogs and the lookup is guarded (`useSpecialTabBarIcons()` falls back to
    the regular icons).
  - `Media Editor/MediaVideo|MediaSlomo|MediaTimelapse` — media-picker grid video-type
    badges; the imagesets don't exist in any catalog (nil on every build, optional
    lookup).
  - `Intents/SavedMessages`, `Widget/SavedMessages`, `Settings/Permissions/Siri` —
    Siri/Widget-extension and Siri-permission assets; this build has no extensions and
    Siri is `#if TGBUILD`-stubbed.
  - `BackButton*.png`/`HeaderButton*.png`/`NavigationBackArrow.png` — TGToolbarButton /
    TGModernBackToolbarButton main-bundle lookups for assets that don't exist anywhere
    in the repo (pre-catalog dead code; those controls aren't instantiated by the
    modern UI).
  - `Chat/Context Menu/FormatHeading\(level + 1)`, `\(imageNamePrefix)*`,
    `test` (Tests/CallUITest) — dynamic or test-target names.
  - 162 dynamic lookups total (interpolated names) — unverifiable statically; they
    surface during the walk instead.

## B. Resource bundles (§2 of the plan) — assembled 2026-10-28

The graph lists 23 `apple_resource_bundle` targets; only MetalEngine's was assembled
before. link.py now assembles **all 23** into `Telegram.app/Frameworks/TelegramUI.framework/<Name>.bundle/`
(every owner module links into TelegramUI.framework in this build; owners are resolved
from the graph's `data` edges + the framework closures, so the location follows the
linking automatically), each with a minimal Info.plist so `NSBundle(bundleWithPath:)`
loads. Loaders verified in source: `Bundle(for:).path(forResource:)` per module —
DrawingUI (drawing screen silently no-ops without it), PremiumUI DataRain,
AnimationCompression DCT, Camera/CameraNeo, TelegramCallsUI video shaders, CallScreen,
VoiceChatActionButton, CameraScreen, DustEffect, LiquidGlassShapes, MediaEditor,
PremiumDiamond, QrStudio, StoryPeerList, Wallet×2, HlsBundle (HLS JS player),
WallpaperBackgroundNode, Libprisma (Syntaxer.mm), RichTextEditorUIKitResources
(TextSpeckle, exported imageset-named inside the bundle), MetalEngine.
`LegacyComponentsResources.bundle` lands at the app **root** (its loader looks in the
main bundle path). Status: all 23 present in the packaged app; each runtime-MSL screen
still needs its first open to prove the shader compile (walk items below).

## C. Known gaps accepted for now

| Screen | Symptom | Root cause | Fix | Status |
|---|---|---|---|---|
| any (dark mode) | dark-variant artwork shows the light asset | loose-file export can't carry catalog appearance variants (`~dark` is car-only) | none acceptable until a car path exists | ACCEPTED (cosmetic) |
| watch/siri/widget | n/a | extensions not built | out of scope this build | OUT OF SCOPE |
| push | no push token | free profile lacks aps-environment | none (receipt §8) | ACCEPTED |

## D. On-device verification findings (build-relevant subset)

The full screen-by-screen walk stays in the private working tree (it was driven
over an authorized account; its screenshots are withheld, see
`receipts/assets/README.md`). What matters for the build line:

| # | Finding | Status |
|---|---|---|
| 0 | Relaunch after the resource fixes: the chat list renders complete — header buttons, archive row, avatars, mute/pin badges, tab bar with badges; no new crash reports; breadcrumb heartbeats steady. Pre-fix vs post-fix: the archive-row icon (A2), the Contacts/Settings tab icons (A2) and the story-indicator chip stopped being blank. | DONE |
| 1 | All 16 component Metal loaders needed the TGBUILD runtime source-compile fallback (glass-button backdrops drew white squares — `makeDefaultLibrary(bundle:)` needs a compiled metallib the Linux bundles cannot carry). `tools/tgbuild/patch_metal_loaders.py` adds the fallback to all 16 loaders; rebuilt, installed, relaunched, no crashes. | FIXED (installed) |
| 2 | Open layout question carried out of the walk: the chat-screen message column inset (~122 pt from the right on a 375 pt screen) — not NavigationSplitContainer math, safeInsets should be symmetric on the device used; root cause still open. | OPEN (cosmetic) |

## E. Verification recipe

```sh
python3 tools/tgbuild/audit_images.py            # static audit vs the packaged app
python3 tools/tgbuild/link.py --app              # relink + re-assemble (~4 min)
cd build-input/link && rm -rf Payload Telegram.ipa && mkdir Payload && \
  cp -a Telegram.app Payload/ && zip -qry Telegram.ipa Payload && cd -
# kill a running instance first — xtool install wedges at 100% otherwise:
U=$(~/pymobiledevice3/bin/pymobiledevice3 developer dvt process-id-for-bundle-id \
      XTL-[redacted-team-id].ph.telegra.Telegraph)
~/pymobiledevice3/bin/pymobiledevice3 developer dvt kill $U
xtool install --usb build-input/link/Telegram.ipa
~/pymobiledevice3/bin/pymobiledevice3 developer dvt launch XTL-[redacted-team-id].ph.telegra.Telegraph
idevicescreenshot /tmp/shot.png
idevicecrashreport -e /tmp/crashes | grep -i telegram
```
(`apps kill` does not exist in this pymobiledevice3; `dvt fps` streams forever —
`process-id-for-bundle-id` + `dvt kill` is the working pair.)
