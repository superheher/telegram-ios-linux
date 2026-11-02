# NOTICE

## Upstream

The build target of this repository is [TelegramMessenger/Telegram-iOS](https://github.com/TelegramMessenger/Telegram-iOS),
base commit `fb0e62ba8a` (recorded in `patches/base-commit`). That repository
and every source file the patch series touches are licensed by their upstream
terms; the patch series (`patches/`) is a derivative work of GPL-licensed code
and is licensed GPL-3.0 with the rest of this repository (see `LICENSE`).

`tools/generated/` contains code generated from schemas that are part of the
upstream repository; the same upstream license applies to them.

## Third-party vendored scripts

`tools/host/` — `install-toolchain.sh`, `cc.sh`, `xip_extract.py`,
`xip_version.py` — are vendored from the `omarchy-apple-dev` toolkit,
Copyright (c) 2026 Joshua Warren, MIT License. They are unmodified except for
being placed here; the MIT license text governs those files.

## What this repository is

Tools (`tools/tgbuild/`), source patches (`patches/`), and documentation
(`docs/`) for compiling Telegram-iOS on an x86_64 Linux host. It is an
independent build-infrastructure project, not an application fork: it carries
no application features beyond the compile-time and runtime fallbacks the
Linux build needs.

## Trademarks

This project is unofficial. It is not affiliated with, endorsed by, or
connected to Telegram Messenger Inc. in any way. The name "Telegram", the
Telegram logo, and the paper-plane-in-a-blue-circle logo are trademarks or
registered trademarks of Telegram Messenger Inc.; this documentation uses the
name only to identify the software it builds. Do not use those marks for your
own builds of the app, and make sure your users understand that anything built
with this pipeline is an unofficial build.

## Credentials in the sources

The patch series leaves the app's `api_id`/`api_hash` pair untouched. The pair
it carries (`611335` / `d524b414d21f4d37f08684c1df41ac9c`) is the public
test-credentials pair that Telegram's own open-source clients (Telegram
Desktop among them) ship in their public sources; it is not a secret specific
to this project. Obtain your own `api_id` if you build and distribute your own
client.
