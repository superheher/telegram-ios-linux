# Status: what works, what does not

Maturity levels are the research plan's L0–L4. Verified on the reference
device: iPhone X (iPhone10,6), iOS 16.7.16, arm64, free-provisioned profile.

| Level | Meaning | Status |
|---|---|---|
| L0 | everything compiles to arm64 iOS objects on Linux | **green** — the whole `deps(//Telegram:Telegram)` Swift+ObjC closure compiles (1009 modules; the ladder to `//submodules/TelegramUI:TelegramUI` and beyond) |
| L1 | links | **green** — 5 frameworks + app binary link with `ld64.lld`; no unexpected undefineds |
| L2 | packages | **green** — `.app`/`.ipa` assembled (resources, catalogs, bundles, plists), free-provisioned |
| L3 | runs | **green** — installs over USB, launches, the authorized chat list renders with live updates and list-view transitions |
| L4 | usable dev loop | **partial** — one-module rebuild ~1 min (TelegramUI ~15 min) + relink ~4 min + install; login/messaging work; not yet a daily-driver loop |

## Green, with evidence

- Graph extraction, ladder, link: `docs/receipts/2026-10-25-*.md`,
  `2026-10-27-*.md`.
- First real launches, black-screen root cause, bundle-id suffix trap:
  `docs/receipts/2026-10-28-black-screen-fixed.md`.
- Chat list rendering with live rows/updates: session journals
  (`docs/journal/linux-build-next-session.md` §1, 2026-11-02 update) and the
  published screenshots in `docs/receipts/assets/`.

## Holes and known limits

| Area | State |
|---|---|
| Rust engines (159 modules: `mtproto-engine`, wallet FFI, …) | linked as stubs. `Cargo.Bazel.lock` carries zero Linux triples; regenerating needs `cargo bazel` + a Rust toolchain and churns a lockfile shared with the Mac flow, for an iOS FFI archive — analysis in `docs/journal/linux-build-2026-10-25.md`. Features behind them (some network paths, wallet) degrade |
| 6 app extensions (share, notification service/content, intents, widget, broadcast upload) | not built; the app launches without them |
| Watch app | not built (prebuilt target upstream, skipped here) |
| arm64e / iOS > 16.7 | untested (the reference device is arm64 iOS 16.7.16; the weak-load surgery targets that exact gap) |
| Free signing | profile valid 7 days; re-install refreshes. Push (aps-environment), App Group, Siri, iCloud entitlements absent — the source patches degrade those features safely (`#if TGBUILD`) |
| Dark-mode catalog variants | loose-file export cannot carry `~dark` car variants — light artwork shows in dark mode (cosmetic, accepted; ledger C) |
| Siri/Recaptcha/CloudKit/push | stubbed at the source level (patches 0006/0007 + stub modules) with documented reasons in the code |
| Chat-screen message-column inset | an open cosmetic layout bug recorded in the ledger (§D) |

## Verification status of this repository's own claims

The patch series was applied to a fresh checkout of the base commit and the
conveyor (`extract.py` → `swift.py --min 16.0` ladder → `link.py --app`) was
run on it — see `docs/publish/journal.md` for the recorded run.
