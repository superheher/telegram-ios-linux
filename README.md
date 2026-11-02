# telegram-ios-linux

A reproducible pipeline that compiles, links, packages, signs and installs
Telegram-iOS **on Linux** (x86_64 host, arm64 device) — no Mac involved at any
step: 1009 Swift/ObjC modules, five frameworks, the app binary, asset
catalogs, resource bundles, free provisioning, USB install and launch.

Verified end to end: iPhone X, iOS 16.7.16, arm64 — the app installs, runs,
and the authorized chat list renders with live updates. Limits and holes are
listed honestly in [docs/status.md](docs/status.md).

## What is here

| Path | Content |
|---|---|
| `patches/` | the source-level Linux-build series (8 patches) against upstream base `fb0e62ba8a`, plus `apply-patches.sh` |
| `tools/tgbuild/` | the build drivers: graph extraction, Swift/ObjC compilation, link + packaging |
| `tools/host/` | toolchain install and SDK extraction scripts (vendored, MIT) |
| `tools/generated/` | generated sources every build needs + regeneration recipes |
| `tools/snapshot/` | recovery point for the no-Xcode sysroot mode (authored files) |
| `tools/scrub.py` | the private-identifier scrub used to prepare this repo |
| `docs/build-guide.md` | **start here**: clean Ubuntu 24.04 → installed build |
| `docs/architecture.md` | how the pipeline works (graph, drivers, caches, SDK handling) |
| `docs/status.md` | what is verified and what is not (L0–L4) |
| `docs/traps.md` | every trap that cost a session |
| `docs/journal/`, `docs/receipts/` | the session journals and phase receipts behind all claims |

## Quick start

1. Install the toolchain — `tools/host/install-toolchain.sh` + `xtool sdk build`
   from an Xcode `.xip` ([docs/build-guide.md](docs/build-guide.md) §1).
2. `git clone` upstream at the base commit and apply the series — §2.
3. Compile, link, install — §4–5.

Three commands once the toolchain is in place:

```sh
python3 tools/tgbuild/extract.py
python3 tools/tgbuild/swift.py //submodules/TelegramUI:TelegramUI --min 16.0
python3 tools/tgbuild/link.py --app
```

…then package, sign and install (§5 of the guide). Full cold builds take
hours on a 4-core machine; incremental loops are minutes.

## Status and scope

This is build infrastructure, not an app fork: the patches are compile-time
hooks and runtime fallbacks (free-profile entitlements, missing metallibs,
importer quirks), documented per hunk in [docs/publish/triage.md](docs/publish/triage.md).
Not built: extensions, watch app, Rust-backed engines (stubbed). See
[docs/status.md](docs/status.md).

## Legal

GPL-3.0 (see [LICENSE](LICENSE)); the patched sources and the generated files
derive from the upstream GPL repository — read [NOTICE.md](NOTICE.md) for
upstream attribution, vendored-script licensing, and the trademark position.
Unofficial: not affiliated with or endorsed by Telegram Messenger Inc.
