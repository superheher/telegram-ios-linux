# UI-walk methodology — cataloging and fixing graphical gaps

Companion to [`ui-gaps.md`](ui-gaps.md) (the gap ledger). The walk itself was
driven on a device over an authorized account and stays private; this file
keeps the reusable build methodology: the static asset audit, the resource
bundle checklist, the gap classes and their fixes, and the fix-install cycle.

## The fix-install cycle

One screen per iteration: screenshot → classify gaps → fix → `link.py --app`
(assets only, ~1 min) or + module rebuild (Swift, ~15 min for TelegramUI) →
re-zip → `xtool install` (kill the running instance first — see
[`../receipts/2026-10-28-black-screen-fixed.md`](../receipts/2026-10-28-black-screen-fixed.md) §6)
→ relaunch → re-screenshot. Every gap lands in the ledger: screen, symptom,
root cause, fix, status.

## Static asset-coverage audit (do this first, before walking)

Most gaps are missing asset lookups; they can be enumerated statically instead
of stumbling on them:

1. Scan the Swift sources for every lookup name:
   `git grep -oE 'bundleImageName: "[^"]+"' -- '*.swift' | sort -u` and the same for
   `UIImage(named: "…")`, `imageNamed:` (LegacyComponents uses its own ObjC path —
   `UIImageObjectName`/`UIResources` — extend there too).
2. For each collected name, check the exported loose file exists in
   `build-input/link/Telegram.app/<name>.png` (+@2x/@3x). Names that also have a
   `.pdf`/`.svg`-only source were rasterized — verify the rasterizer did not skip any
   (receipt §9 printed failures).
3. Separately list the **force-unwrap lookups** (`bundleImageName: …)!` and
   `UIImage(named:)!`) — each missing name there is a future crash, not a hole. Export
   those assets (or stub the call site under `#if TGBUILD`) before walking into the
   screen that uses them.
4. Write the missing-names report into the ledger as the walk's checklist.
   `tools/tgbuild/audit_images.py` automates the whole audit.

## Resource bundles (the other systematic gap)

Several modules load their own `.bundle` at runtime and return nil/degrade when it is
absent (the MetalEngine pattern from receipt §3). Enumerate from the graph
(`apple_resource_bundle` targets in `build-input/graph/modules.json`) and assemble the
missing ones into the owning framework (`Frameworks/<Fw>.framework/<Name>.bundle/`) the
way `MetalEngineMetalSourcesBundle.bundle` is done in link.py. Known consumers:

- DrawingUI (`DrawingUIBundle` — metal + marker/json resources; the drawing screen
  silently no-ops without it),
- PremiumUI (`PremiumUIBundle` — DataRain textures),
- AnimationCompression (`AnimationCompressionBundle` — DCT metal),
- Camera / CameraNeo, TelegramCallsUI, WallpaperBackgroundNode (their metal sets —
  same runtime-MSL pattern as MetalEngine's `#if TGBUILD` loader, receipt §9 links),
- TelegramUI's own animation/lottie bundles if the graph lists them.

## Gap classes and their fixes

| Class | Symptom | Fix |
|---|---|---|
| missing loose asset | white/blank icon | add catalog/asset to the export in link.py |
| pdf-vector imageset rasterized by `pdftoppm` | white square behind the icon (alpha lost, baked white) | `pdftocairo -png -transp` in link.py (ledger A4) |
| svg/pdf vector set | missing + actool trap | already rasterized; verify the name spelling |
| resource bundle absent | feature silently no-ops | assemble the bundle (see above) |
| `force-unwrap` lookup | crash on screen open | export asset or `#if TGBUILD` stub |
| entitlement assert | abort at feature use | `#if TGBUILD` degrade (Siri pattern, receipt §8) |
| TCC privacy | `__TCC_CRASHING_DUE_TO_PRIVACY_VIOLATION__` | add the `NS*UsageDescription` (link.py merges them from the real plist) |
| perf: first-frame stalls | UI hangs seconds | prewarm path, out of scope unless egregious |

## Exit criteria

- The ledger covers every screen visited with no unfixed crash-class gap.
- The static audit reports zero force-unwrap lookups missing from the bundle.
- The receipt and the handoff are updated with the ledger and the before/after
  evidence (logs and crash reports; screenshots only if impersonal).
