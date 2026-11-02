# Generated sources

Codegen outputs every build of the app needs; on the Mac flow Bazel generates
them under `bazel-out/`, on the Linux flow they are materialized into the
source tree (untracked) where the graph's srcs paths expect them.

| Directory | Content | Lands at |
|---|---|---|
| `TelegramApi/` | 44 `Api*.swift` + `TLApiSchemaData.m` + `Tests/` (fixtures, accessor probes) | `submodules/TelegramApi/Generated/` |
| `FlatSerialization/` | 34 `*_generated.swift` | `submodules/TelegramCore/FlatSerialization/` |

Copied verbatim from a working 2026-11-02 tree built from the base commit's
schemas. They derive from schemas that are part of the upstream GPL
repository, so publishing them carries the upstream license.

## Regenerating

**TelegramApi** — the generator is SwiftTL (`build-system/SwiftTL`), a
`swift_binary` the Bazel graph declares. rules_swift's Linux auto-config has
no toolchain, so build it with the host swiftc instead:

```sh
# zlib modulemap for the host build lives at build-input/host-zlib/ after
# tools/snapshot is installed (or write a two-line one for the system zlib)
cd build-system/SwiftTL
swift build -c release -Xswiftc -I -Xswiftc build-input/host-zlib -Xlinker -lz
```

Run the resulting binary with the repo's schema inputs the way the
`TelegramApi` BUILD's genrule wires them (see that genrule for the exact
argument list); it writes `Api0..43.swift`, `TLApiSchemaData.m` and the
fixtures into `submodules/TelegramApi/Generated/`.

**FlatSerialization** — the repo's genrule invokes a macOS cmake tarball and
`sysctl`, so build the pinned flatbuffers v24.12.23 (sha256-verify the release
tarball) with host cmake and run `flatc --swift` over the `.fbs` models in
`submodules/TelegramCore/FlatSerialization/Models/`, writing
`*_generated.swift` beside them.

`tools/tgbuild/make-generated-sources.sh` covers the third, smaller codegen:
the `GeneratedSources` stand-in for the Siri-intents library (Apple's intent
codegen runs only on macOS); compile it with the tgbuild driver flags and
install its products under `build-input/swift/`.
