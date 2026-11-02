# Research plan: building Telegram-iOS for an iPhone from Linux

Status: active (2026-10-25). Author: night session of 2026-10-24/25; baseline
facts in [`linux-build-2026-10-25.md`](linux-build-2026-10-25.md).
**Phase 1 is done** — receipt
[`receipts/2026-10-25-phase1-graph-extractor.md`](receipts/2026-10-25-phase1-graph-extractor.md).
**Session entry point: [`linux-build-next-session.md`](linux-build-next-session.md)** —
current position (Phase 3 tail), iteration loops, machine-local snapshot
([`tgbuild-sdkfree-snapshot/`](tgbuild-sdkfree-snapshot/)), and the remaining
phases with acceptance criteria.

## 0. Goal and maturity levels

**Goal:** from this Ubuntu 24.04 x86_64 box, produce an installable build of
the Telegram app (bundle `ph.telegra.Telegraph` or a dev bundle id) that runs
on the connected iPhone X (iOS 16.7), with an iteration loop fast enough to
develop against.

The honest framing: a Mac builds this app through Bazel + rules_apple +
Xcode. None of that toolchain exists for Linux. This project replaces the
*execution backend* of the build while keeping the *graph* (Bazel) and the
*sources* untouched.

| Level | Meaning | Verifiable criterion |
|---|---|---|
| L0 | Everything the app consists of compiles to arm64 iOS objects on Linux | every `swift_library`/`objc_library`/`cc_library` in `deps(//Telegram:Telegram)` has a cached build product |
| L1 | Links | main binary + `TelegramUIFramework` link with `ld64.lld`, `nm` shows no unexpected undefineds, Mach-O loads in `otool`-level checks |
| L2 | Packages | `.app`/`.ipa` assembled (resources, plists, entitlements), ad-hoc or dev-signed, passes `rcodesign` validation offline |
| L3 | Runs | installs on the iPhone X over USB, process stays alive 10 s, no crash in syslog, first screen renders |
| L4 | Usable loop | incremental rebuild of one Swift module ≤ 5 min on this 4-core box; login and basic messaging work |

Scoping decisions (proposed, each reversible):
- **Dev build only.** Debug-ish, no App Store validation path.
- **Extensions and watch app are Phase 6, not blockers.** The app launches
  without them; they can be omitted from early dev builds.
- No EULA-gray work without an explicit user decision (macOS VM — see §5).

## 1. Baseline: what is already proven (this machine)

- Bazel 9.2.0 linux runs the repo: `tgcalls_core` (WebRTC+tgcalls, 1186
  actions), 12 third-party libs, 3 host `cc_test`s pass.
- iOS arm64 compilation on Linux works: ObjC via `sdk-free/cc.sh`
  (MurMurHash32 → Mach-O object), Swift via `swiftc-x` (AudioWaveform;
  AppLockState→MonotonicTime Swift+ObjC chain links into an executable)
  against the sysroot cut from **this phone's** iOS 16.7 cache.
- The Swift 6.4-vs-iOS-16.7 runtime gap is bridged (`swift_getTypeByMangledNameInContext2`
  shim; ABI-correct on non-PAC arm64 — see baseline doc).
- `actool` (asset catalogs) and `ibtool` (storyboards) Linux builds exist in
  `~/dev/omarchy-apple-dev`; `rcodesign` and `pymobiledevice3` are installed.

## 2. Inventory of what a build consists of (measured)

| Piece | Size | Linux tool status |
|---|---|---|
| Swift sources (submodules) | 4 795 files; TelegramUI 1 835, TelegramCore 741, Postbox 222, lottie-ios 181, Display 153 | compile: proven per-module (swiftc-x); scale: unproven |
| ObjC/C/C++ (submodules) | 4 411 files (LegacyComponents 413, MtProtoKit 93, …) | 13 % compile against the no-Xcode sysroot (framework-header ceiling, NOT a toolchain ceiling) |
| App target `//Telegram:Telegram` | `ios_application` + 6 `ios_extension`s + prebuilt watch app | rule needs Apple toolchain — replaced by our packager |
| Codegen | 135 genrule mentions (GenerateStrings.py etc.) | run under Linux bazel already (proven by tgcalls build) |
| Asset catalogs | 68 `.xcassets` | `actool` from omarchy (Linux, built) |
| Storyboards/xibs | 53 | `ibtool` subset (proven for Flutter storyboards) — audit which ones the app actually uses (Telegram UI is code-drawn; most are likely extension/launch screens) |
| Metal shaders | 33 `.metal` | **no Linux Metal compiler — precompile on a Mac/VM once, commit `.metallib` or cache them** (shaders change rarely) |
| Strings | 31 `.strings` + generation script | Python genrule — fine |
| Provisioning | fastlanematch git repo (`TELEGRAM_CODESIGNING_GIT_PASSWORD`) | user credential; **bypass**: free-Apple-ID `xtool install` (7-day profiles) or user's dev cert via `rcodesign` |

## 3. Architecture: the chosen route

**Bazel stays the source of truth for the graph; we replace the execution
backend for Apple-target compilation.**

```
bazel query 'deps(//Telegram:Telegram)' --output=xml   (loading phase; runs on Linux —
        │                                               cquery needs analysis, which needs
        │                                               the Apple toolchain; query does not)
        │  → modules.json: every swift_library / objc_library / cc_library
        │     with srcs, hdrs, deps, copts, defines, module_name (selects = branch union)
        ▼
tgbuild.py  (tools/tgbuild/)  ── compile cache keyed on content hash
        ├─ ObjC/C backend:  cc.sh  + auto-generated module.modulemap per module
        ├─ Swift backend:   swiftc-x per module: -emit-module chain in topo order
        ├─ Resources:       actool / ibtool / precompiled .metallib / copy
        ├─ Link:            ld64.lld (main binary, TelegramUIFramework, extension binaries)
        ├─ Package:         .app tree, Info.plist merge, entitlements
        └─ Sign:            ad-hoc (rcodesign -p -) | dev profile | xtool install
```

Why this shape:
- Reimplementing rules_swift's Swift backend as a real Bazel crosstool is a
  deeper research project (Phase 7, optional) — the driver gets results while
  keeping that door open.
- Using Bazel's graph avoids hand-maintaining the 277-submodule dependency
  order and reuses the codegen genrules unchanged.
- Per-module content-hash cache gives the L4 iteration loop.

Rejected routes (evidence in the baseline doc): xtool/SwiftPM adapter
(converter drops ObjC sources outright); stock rules_apple on Linux (its
crosstool is `xcrun`-driven macOS-only).

## 4. Phases

### Phase 0 — external dependencies — **DONE 2026-10-26**
1. **Apple ID — DONE 2026-10-24**: `xtool auth` logged in ([redacted-apple-id],
   Team ID `[redacted-team-id]`, token valid to 2027-10-24).
2. **Xcode .xip — DONE 2026-10-26**: the user provided
   `Xcode_27.2_Release_Candidate.xip` (27B48, the Xcode matching Swift 6.4);
   `xtool sdk build` produced
   `~/dev/omarchy-apple-dev/sdk-free/sdk-cache/darwin-iPhoneOS27.2.xtoolsdk`
   (iPhoneOS27.2.sdk — 318 frameworks vs sdk-free's 13) and it is registered
   (`swift sdk list` → darwin). Smoke test: MTAes.m/MTEncryption.m — two of the
   10 files that failed on Security/CommonCrypto — compile with zero errors
   against the real SDK. Full-mode switch of the drivers is the next step
   (docs/linux-build-next-session.md §1b).
3. **iPhone X — CONNECTED 2026-10-25** (usbmuxd restart fixed a wedged daemon).
3. Optional: `TELEGRAM_CODESIGNING_GIT_PASSWORD` (fastlanematch) if a proper
   dev profile is wanted instead of free 7-day ones.
4. **iPhone X — CONNECTED 2026-10-25** (was absent the previous night). It
   was on USB all along with a wedged usbmuxd (`/var/run/usbmuxd` not
   accepting; pairing record missing from /var/lib/lockdown);
   `systemctl restart usbmuxd` fixed it — `xtool devices` now lists
   "[redacted-device]" ([redacted-udid]…, iPhone10,6, iOS 16.7.16).

### Phase 1 — graph extractor (1–2 days) — **DONE 2026-10-25** (receipt
[`receipts/2026-10-25-phase1-graph-extractor.md`](receipts/2026-10-25-phase1-graph-extractor.md))
- `tools/tgbuild/extract.py`: `bazel query --output=xml` →
  `build-input/graph/modules.json` (label, kind, srcs, deps, copts, module_name, sdk deps;
  filegroups/aliases resolved; topological `order` over module deps). cquery turned out
  impossible on Linux (analysis needs the Apple toolchain) — see receipt for the deviation.
- Prereq fixed first: `build-input/configuration-repository` was incomplete (unprefixed
  `variables.bzl` symbols, no `provisioning/` package) — now matches
  `BuildConfiguration.write_to_variables_file` + fake-codesigning profiles.
- Acceptance: **met** — graph of `//Telegram:Telegram` + all 6 extensions + 5 frameworks +
  watch app extracts cleanly; counts per kind printed (738 swift / 78 objc / 33 cc /
  159 rust / 1 prebuilt = 1009 compile modules, topological order, 0 violations);
  no module missing srcs (srcs-less modules verified to be header-only wrappers, the
  prebuilt xcframework, or the intent-codegen `GeneratedSources`, tracked as `intent_srcs`).
- Count correction for Phase 3 sizing: `TelegramUI` itself is 213 srcs (its `Sources/`
  tree); the plan's 1 835 was the whole `submodules/TelegramUI/` tree — the rest are
  separate Component libraries (TelegramUI has 523 module deps). `lottie-ios:Lottie` 181,
  `Display` 153, `TelegramCore` 718, `Postbox` 221, `LegacyComponents` 577,
  `MtProtoKit` 130.

### Phase 2 — ObjC/C backend (3–7 days with full SDK; open-ended without) — **in progress,
user-independent part done 2026-10-25** (receipt
[`receipts/2026-10-25-phase2-objc-backend.md`](receipts/2026-10-25-phase2-objc-backend.md))
- **Done**: `tools/tgbuild/objc.py` (per-module modulemap generation from modules.json — the
  MonotonicTime pattern generalized — dependency-closure compile via sdk-free `cc.sh`,
  content-hash object cache, failure taxonomy), and the no-Xcode stub layer
  (`build-input/objc-stubs/`: 33 headers — Darwin system headers, zlib, dispatch sources,
  the Foundation/CF surface the rebuilt sysroot headers lack; `--no-stubs` disables it once
  the full SDK lands).
- **Measured**: SSignalKit 24/24 ✓, AppBundle 1/1 ✓, MtProtoKit **83/93** (was 39/93 with
  the survey's `-Wno-everything` crutch), LegacyComponents 43/413.
- **Ceiling, precisely**: every remaining failure is either a framework the sdk-free sysroot
  does not ship (MtProtoKit: Security/CommonCrypto/CFNetwork/SystemConfiguration ×10;
  LegacyComponents: OpenGLES ×57, AVFoundation ×47, Photos ×9, QuartzCore ×12, …) or UIKit
  API breadth (the sysroot UIKit is a 285-line skeleton; 241 LegacyComponents files).
  Both classes are lifted wholesale by the Phase 0 Xcode .xip — with it, this phase's
  acceptance (both modules fully compiling) is re-run as `objc.py --no-stubs` plus the SDK.
- Remaining acceptance gate: **MtProtoKit 10/10 and LegacyComponents' remainder compile** —
  blocked on Phase 0 (user).

### Phase 3 — Swift backend (1–2 weeks) — **in progress, milestones 1–2 done 2026-10-25**
(receipt [`receipts/2026-10-25-phase3-swift-backend.md`](receipts/2026-10-25-phase3-swift-backend.md))
- **Done**: `tools/tgbuild/swift.py` (topological per-module `-emit-module` + `-c`, flags from
  the night session's proven invocation, content-hash cache, transitive ObjC-dep clang
  modulemaps); Foundation overlay rebuilt with the closed-source-bridge API
  (`rebuild-foundation.sh` + `overlay/Foundation+Tgbuild.swift`); `Date` adopted from the
  swift-5.3 overlay sources; thin framework modules authored (CommonCrypto,
  SystemConfiguration, CloudKit, CoreText/AVFoundation umbrellas); `os`/`Network` Swift shim
  modules; SwiftTL and flatc codegen running on the host (TelegramApi's 44 generated files +
  34 FlatSerialization files).
- **Ladder**: 1. SwiftSignalKit (26) **✓** → 2. Postbox (221) **✓** — plus TelegramApi,
  FlatBuffers, FlatSerialization, ManagedFile, RangeSet, MediaPreuploadRegistry, Reachability,
  Emoji, CloudData: **11 modules of TelegramCore's closure compile to arm64 .swiftmodule + .o**.
- **Next**: a WebKit framework overlay (20 WK* types for WebProxyTransport — the one module
  still failing); then TelegramCore (718) type-checks (`probe.py` already shows it clean
  behind that one import); then the Display UIKit-overlay question (Risk #1).
- Risk watch: whole-module optimization memory on 15 GB for TelegramUI —
     fall back to incremental (`-emit-module -incremental`) or split.
- Acceptance: every Swift module in the graph has a cached product (L0).

### Phase 4 — link and package (3–5 days)
- Link main binary + `TelegramUIFramework` with `ld64.lld` (+ the InContext2
  shim; keep the shim list explicit — it is an ABI contract with iOS 16.7).
- Resources: `actool` run per catalog; `ibtool` on the storyboards the app
  truly references; precompiled `.metallib` from Phase 0/VM; strings genrule
  output copied in.
- `Info.plist` merge (app + `variables.bzl` values), entitlements, bundle
  structure (`Frameworks/`, `PlugIns/` skipped in dev build).
- Ad-hoc sign (`rcodesign`), offline validation.
- Acceptance: L1 + L2 — `.app` whose structure and signatures check out,
  `nm -u` clean against the SDK stub set.

### Phase 5 — device loop (1–2 days + user present once)
- `xtool auth` (user taps in credentials), `xtool install` or
  `pymobiledevice3 apps install` of the ad-hoc-signed app — free-ID signing
  happens on install.
- Launch, `syslog live`, screenshot via `developer dvt`.
- Acceptance: L3 — process alive 10 s, first screen renders (screenshot in
  the report).

### Phase 6 — completeness and loop quality (1–2 weeks, parallelizable)
- Extensions one by one (each is a small Phase 4: own binary/plist/profile).
- Incremental cache correctness (hash inputs = srcs+deps+copts+SDK hash).
- Regressions: a `tgbuild --check` mode comparing module lists against
  `bazel cquery` after `git pull`.
- Stretch: TelegramCore unit tests compiled+run where host-runnable.

### Phase 7 — optional research: native Bazel backend
- Turn the driver's compile steps into a real `swift_toolchain` +
  crosstool registered from `build-system/`, so plain `bazel build` works on
  Linux. Only after L4: it is engineering polish, not a milestone.

## 5. Control route: macOS VM on KVM (oracle, user-gated)

`/dev/kvm` + VT-x are present. A macOS VM (OSX-KVM-class setup) would:
- provide the **reference build** to diff against (entitlements, plists,
  `.metallib` compilation, watch app zip) — the oracle for correctness bugs
  our pipeline will hit;
- cost ~25 GB of images, an Apple ID login, hours per build on 4 cores;
- **violates Apple's EULA on non-Apple hardware** — starting it is the
  user's explicit decision, and it stays a build oracle, not the product.

If declined: precompile the 33 `.metal` files and the watch app once on any
available Mac (a friend's, or CI), commit the artifacts; everything else in
the plan is VM-free.

## 6. Top risks and mitigations

| # | Risk | Mitigation |
|---|---|---|
| 1 | Full-mode SDK still misses modules Linux swiftc can't import (SwiftUI-style prebuilt .swiftmodule from Apple's toolchain) | sdk-free already rebuilds stdlib modules from source; extend the same build to needed overlays; worst case: write thin overlays per framework (proven pattern) |
| 2 | Swift version friction: 6.4 compiler vs code written for 5.x/6.x-Xcode | keep `-swift-version 5`; pin compiler upgrades deliberately |
| 3 | Runtime gaps like the InContext2 symbol on other APIs | shim list grown empirically; each entry documented with ABI reasoning; iPhone X = non-PAC arm64 keeps ptrauth-class shims legal |
| 4 | TelegramUI WMO OOM on 15 GB | non-WMO per-file or chunked WMO; accept slower builds |
| 5 | ld64.lld unresolved corner (order files, exported symbols list `framework_exported_symbols.bzl`) | the repo ships its export list — feed it; escalate to omarchy's pinned darwin-tools ld64 |
| 6 | Entitlements/profile mismatch blocks install (aps, associated domains) | dev bundle id without push entitlements first; add entitlements stepwise |
| 7 | Graph drift after upstream pulls | `tgbuild --check` diff vs `bazel cquery` |
| 8 | Storyboards that ibtool can't compile | audit usage; most are likely replaceable by empty/plist-driven launch screens for dev builds |
| 9 | Codesigning credential unavailable long-term | ad-hoc + free-ID loop keeps research unblocked; real profile only for L4 polish |
| 10 | Scope creep into "make bazel do it natively" | Phase 7 explicitly last |

## 7. Parallel quick wins (any idle hour)

- mtproto-engine host build: rustup + add `x86_64-unknown-linux-gnu` +
  regenerate `Cargo.Bazel.lock` (touches a Mac-shared lockfile — do behind a
  flag/branch).
- Re-run the file survey in **full mode** once the SDK lands → real coverage
  number replaces the 13 % no-Xcode figure.
- Finish `bazel build` of every host-buildable `cc_library` in the graph
  (cheap cache warmth for Phase 2).

## 8. Working discipline

- Every phase ends with a receipt file under `docs/receipts/` (command,
  output, artifacts, hashes) — same style as the omarchy repo.
- `docs/linux-build-*.md` stays the running log; this plan's checkboxes are
  updated in place.
- All repo patches keep the arm/Mac paths untouched (select-guarded), as the
  night session's patches already are.

## 9. Summary estimate

To L3 (app runs on the iPhone X): **3–5 weeks of focused work**, of which
the Swift backend over TelegramUI is the dominant term; 1–2 days of that is
gated on the user (Apple ID, Xcode .xip, re-plugging the phone).
To L4: +1–2 weeks. Phase 7 not estimated (optional).
