# Phase 1 receipt — graph extractor (2026-10-25)

**Goal:** `modules.json` — the whole compile graph of the app from Bazel, on Linux.
**Acceptance (plan §4 Phase 1):** graph of `//Telegram:Telegram` (plus each extension)
extracts cleanly; counts per kind printed; no module missing srcs.
**Result: met.** `python3 tools/tgbuild/extract.py -o build-input/graph/modules.json`
exits 0 with zero warnings.

## Deviation from the plan (recorded, deliberate)

The plan sketched `bazel cquery --output=starlark`. **cquery cannot run for apple targets on
Linux**: cquery requires target *analysis*, and analysis of `objc_library` fails with
"Compiling objc_library targets requires the Apple CC toolchain" (apple_support's toolchain is
xcrun-driven macOS-only — the baseline doc's finding). Loading-phase `bazel query --output=xml`
returns the same attribute data (srcs, hdrs, deps, copts, module_name, sdk_frameworks, …) with
no toolchain resolution; `tools/tgbuild/extract.py` runs that instead. Select() attributes are
flattened to the union of branches (query's behavior at loading phase) — the superset the
driver wants.

## Prerequisite fixed: build-input/configuration-repository was incomplete

The 2026-10-24/25 session's `variables.bzl` used unprefixed names (`bundle_id`, …) but BUILD
files load `telegram_*` symbols (`telegram_bundle_id`, …), and there was no `provisioning/`
package, so loading `//Telegram` failed ("does not contain symbol 'telegram_bundle_id'",
missing `@build_configuration//provisioning:*.mobileprovision` targets). Fixed to match
`build-system/Make/BuildConfiguration.py:write_to_variables_file` + `example-configuration`:

- `variables.bzl`: all 15 `telegram_*` symbols BUILD files load (verified by grep across
  `Tests/`, `Telegram/`, `submodules/`).
- `provisioning/`: fake profiles copied from `build-system/fake-codesigning/profiles/` +
  `Wildcard.mobileprovision` (copy of the Telegram one; referenced by `Tests/AnimationCacheTest`),
  `exports_files` matching `example-configuration/provisioning/BUILD`.

## Commands

```sh
cd $HOME/dev/Telegram-iOS
python3 tools/tgbuild/extract.py -o build-input/graph/modules.json
# runs: ./build-input/bazel-9.2.0-linux-x86_64 query 'deps(//Telegram:Telegram)' \
#         --output=xml --noimplicit_deps --notool_deps
```

Exit 0, no warnings. (Iterating with `--xml <file>` reuses a saved query result.)

## Output (stdout, verbatim summary)

```
loaded 1495 rules, 73525 source files, 388 generated files
per-kind counts:
   738  swift_library
   156  rust_library
   151  cargo_toml_env_vars
    78  objc_library
    70  alias
    63  filegroup
    41  plist_fragment
    36  genrule
    33  cc_library
    27  cargo_build_script
    27  cargo_build_script_runfiles
    23  apple_resource_bundle
    18  config_setting
     8  constraint_value
     6  ios_extension
     5  ios_framework
     3  bool_flag
     3  rust_static_library
     3  constraint_setting
     2  framework_exported_symbols
     1  apple_intent_library
     1  ios_application
     1  apple_prebuilt_watchos_application
     1  apple_static_xcframework_import
modules (compile units): 1009, prebuilt: 1
topological order covers 1009 modules
extension in graph: //Telegram:BroadcastUploadExtension
extension in graph: //Telegram:IntentsExtension
extension in graph: //Telegram:NotificationContentExtension
extension in graph: //Telegram:NotificationServiceExtensionv1
extension in graph: //Telegram:ShareExtension
extension in graph: //Telegram:WidgetExtension
wrote build-input/graph/modules.json (22.0 MiB)
```

## Verification performed

- **Extensions**: all 6 `ios_extension`s, the 5 `ios_framework`s, `ios_application`, the
  prebuilt watch app and the Recaptcha xcframework import are in the graph (listed above).
- **No missing sources** (exit gate): the only srcs-less candidates were examined by hand and
  are legitimate — header-only/dep-only wrappers (`EncryptionProvider`, `boost_regex`,
  `mozjpeg`, `td`, `webp`, `wallet_engine`, `wallet_engine_ffi`, `MTProtoEngineFFI`), the
  prebuilt `RecaptchaEnterprise`, and `//Telegram:GeneratedSources`, whose srcs are an
  `apple_intent_library` (`swift_intent_library` macro; the `.intentdefinition` is in `data`) —
  recorded as `intent_srcs`, a Phase 3 special case (Apple intent codegen).
- **File counts vs disk** (graph is ground truth for what Mac builds):
  `TelegramUI` 213 (its `Sources/` holds exactly 213 .swift; plan's "1 835" was the whole
  `submodules/TelegramUI/` tree — the rest are separate Component libraries, hence
  TelegramUI's 523 module deps), `TelegramCore` 718, `Postbox` 221, `Display` 153 ✓,
  `SwiftSignalKit` 26 (its `Source/` tree), `lottie-ios:Lottie` 181 ✓ (matches plan),
  `MtProtoKit` 130, `LegacyComponents` 577, `rlottie` 106.
- **Topological order**: 0 violations (every module's module_deps earlier in `order`);
  `order[0]` = `//submodules/Crc32:Crc32`, `order[1]` = SwiftSignalKit (leaf-level),
  `//submodules/TelegramUI:TelegramUI` at position 845 of 1009.
- Every dep referenced from a module exists in the graph (checked; only cargo build-script
  noise was excluded, matching `--notool_deps`).

## Artifacts

| Path | sha256 (first 16) |
|---|---|
| `build-input/graph/modules.json` (22.0 MiB) | `a58f798de48fa0ef` |
| `build-input/graph/modules.json.query.xml` (47 MB) | `e81b41bebc7ffe4b` |

Both gitignored (`build-input/`). `modules.json` layout: `meta` (counts, warnings, query),
`order` (1009 module labels, deps-first), `targets` (per-rule: kind, attrs verbatim,
`srcs_files`/`hdrs_files`/`data_files`… resolved through filegroup/alias closure,
`module_deps` canonicalized through aliases), `files` (388 generated files → producing rule,
all but the empty-language touch-files from `Telegram/BUILD` genrules).

## Notable facts for later phases

- 1009 compile modules: 738 swift + 78 objc + 33 cc + 159 rust + 1 xcframework import.
  The 159 rust modules (mtproto-engine, tlottie, wallet-engine) have **no Linux backend**
  (baseline doc) — Phase 2/3 work ignores them; they are `module: true` in the JSON so the
  driver can see what links against them (`MTProtoEngineFFI`, `wallet_engine*`, `tlottie`).
- `swift_intent_library` (`//Telegram:GeneratedSources`) generates code from
  `Telegram/SiriIntents/en.lproj/Intents.intentdefinition` at analysis time — needs a Linux
  substitute or pre-generated artifacts in Phase 3.
- 36 genrules (codegen: `GenerateStrings`, empty-language `.strings` touch files, …) are in
  the graph with `cmd`/`outs`; they can run under Linux bazel as the plan expects.
- `module_deps` were canonicalized through 70 aliases (e.g. `//submodules/PasscodeCore` →
  the real library), so the topological order is over real modules.
