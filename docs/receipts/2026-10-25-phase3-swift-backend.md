# Phase 3 receipt — Swift backend: driver, overlay rebuilds, ladder to TelegramCore's doorstep (2026-10-25)

**Goal (plan §4 Phase 3):** topological compile with `swiftc-x`: per module emit `.swiftmodule`
+ object, cache by content hash. **Ladder, measured**: milestone 1 (SwiftSignalKit) and
milestone 2 (Postbox) **compile**; TelegramApi, FlatBuffers, FlatSerialization, ManagedFile,
RangeSet, MediaPreuploadRegistry, Reachability, Emoji, CloudData compile — **11 modules of the
TelegramCore closure produce Mach-O arm64 .swiftmodules + .o objects**. TelegramCore itself is
one module away: it imports WebProxyTransport, which needs a **WebKit framework overlay**
(20 WK* types — next session's task, see "Open" below).

## Tools built (repo, versioned)

- **`tools/tgbuild/swift.py`** — the Swift driver. From `modules.json`, dependency order;
  per module two passes (`-wmo -emit-module`, then `-wmo -c`), flags reconstructed from the
  night session's proven invocation (Swift 6.4, `-swift-version 5`, sdk-free resource dir with
  the stdlib rebuilt from source, overlay dir, sdkm framework maps, apinotes, `-nostdinc` +
  explicit clang resource dir to keep host glibc out). ObjC dependencies ride along as clang
  modules: modulemaps + include paths for the **transitive** objc/cc dep closure (direct-only
  broke on Postbox.swiftmodule's recorded Crc32/sqlcipher/StringTransliteration imports).
  Products cached by content hash under `build-input/swift-cache/` with stable copies at
  `build-input/swift/modules/` (for dependents) and `build-input/swift/objects/` (for Phase 4).
  Failure taxonomy: `missing-module` vs `swift-error`. An explicit clang module cache
  (`build-input/swift/clang-cache/`) — stale .pcm after header edits was a repeated trap;
  `rm -rf` it when sdkm/darwin headers change.
- **`tools/tgbuild/rebuild-foundation.sh`** — rebuilds the Foundation Swift overlay from the
  sdk-free project's curated swift-5.3 sources + `tools/tgbuild/overlay/Foundation+Tgbuild.swift`
  (the closed-source-bridge API the app needs), and builds two Swift shim modules (`os`,
  `Network`) into `build-input/swift/shims/` — their own dir because a swiftmodule named `os`
  on the overlay search path collides with the Darwin clang module `os` and cycles the graph.
- **`tools/tgbuild/overlay/`** — `Foundation+Tgbuild.swift` (overlay additions, every body
  forwarding to the real clang Foundation), `os.swift` (no-op unified-logging shim),
  `Network.swift` (NWPathMonitor shim reporting unsatisfied).
- **`tools/tgbuild/probe.py`** — prints full swiftc stderr for one module (the driver shows
  only the first error); indispensable for the iteration loop.
- **`tools/tgbuild/objc.py`** (Phase 2) gained: transitive-dep modulemaps unchanged, clang
  resource `-isystem`, UIKit-conditional forced include, host C++ headers for .mm/.cpp.

## Codegen on Linux (genrules the Bazel graph declares, run by hand)

- **SwiftTL** (TelegramApi's generator, a `swift_binary` — rules_swift's Linux auto-config has
  no toolchain): built with the **host** swiftc (`swift build -c release` + a zlib modulemap
  at `build-input/host-zlib/` + `-lz`). Generates `TelegramApi/Generated/Api0..43.swift`
  (+ TLApiSchemaData.m + fixtures) into the source tree where the graph's srcs paths expect
  them (untracked; the Mac flow generates under bazel-out).
- **flatc**: the repo's genrule is Mac-only (macOS cmake tarball, `sysctl`); built the pinned
  flatbuffers v24.12.23 (sha256 verified) with host cmake, generated the 34
  `FlatSerialization/*_generated.swift`.

## Machine-local header work (sdk-free tree; the no-Xcode "thin overlays" pattern)

- **New framework modules in sdkm**: CommonCrypto (HMAC + digest constants — 4 symbols the
  app uses), SystemConfiguration (SCNetworkReachability: 6 functions + 9 flags), CloudKit
  (CKContainer/CKDatabase/CKRecord/CKRecordID/CKError subset with swift_name shaping —
  `CKRecord.ID` nesting, `fetch(withRecordID:)`, `.default()`, `errorDomain` property),
  CoreText + AVFoundation (import umbrellas; no symbols referenced by their importers).
- **sdkm Foundation.h extended** (each mirrors the real SDK): NSLock/NSRecursiveLock,
  NSThread (init/format priority), NSStream/NSOutputStream, NSIndexSet + NSMutableIndexSet
  (full public surface), NSDirectoryEnumerator, NSCharacterSet, NSScanner, NSFormatter-less
  NSDate extras (distantFuture/Past as class properties, initWithTimeIntervalSinceReferenceDate,
  NSCopying conformance), NSCoder numeric codecs, NSString (getCharacters:range:, data/
  initWithContentsOfFile/replacingOccurrences/format arguments), NSData dataWithContentsOfFile,
  CFStringTokenizer subset (typedef CF_BRIDGED_TYPE + CF_RETURNS_RETAINED), NS_ROOT_CLASS,
  NS_CLOSED_ENUM with real `enum_extensibility(closed)` (the hand-rolled macro lacked it —
  plain-enum imports broke `TLFieldKind.int32` member lookup), utime include + non-variadic
  fcntl helpers (`_tg_fcntl2/3/3p` static inline).
- **Darwin tree**: `os` module restructured (os_unfair_lock exposed through the Darwin module,
  breaking a Darwin→os→ObjectiveC cycle), `S_IRUSR`-family macros typed `mode_t` (Swift
  imports them as UInt16 — what app code expects), `open` non-variadic (variadic imports
  unavailable in Swift; the app calls the 2- and 3-arg forms), fcntl static-inline helpers.
- **Apinotes/Foundation.res**: rebuilt overlay carries `Date` (from the swift-5.3 sources,
  playground/formatter blocks dropped), `ComparisonResult` alias, and the +Tgbuild extensions.

## Results

| Module (TelegramCore closure order) | Files | Status |
|---|---|---|
| SwiftSignalKit | 26 | **ok** (ladder milestone 1) |
| ManagedFile / RangeSet | 3+1 | **ok** |
| Postbox | 221 | **ok** (ladder milestone 2) — 10.5 MB object |
| TelegramApi | 44 generated + 15 | **ok** — 12.9 MB object |
| MediaPreuploadRegistry / FlatBuffers / FlatSerialization | 1/6/34 generated | **ok** |
| Reachability / Emoji / CloudData | small | **ok** (Network/CloudKit shims) |
| WebProxyTransport | 10 | **blocked on a WebKit overlay** (20 WK* types, delegates) |
| TelegramCore | 718 | waits on WebProxyTransport's module |

Every `.o` verified `Mach-O 64-bit arm64`. All products exit-0 through the driver.

## Repo patch (select-guarded, Mac path unchanged)

- `submodules/WebProxyTransport/Sources/WebProxyDiagnostics.swift`: `#if canImport(os.log)`
  around the unified-logging calls, no-op `#else` branch (+21 lines). Analysis trail that led
  here: `import os.log` resolves **only** to a clang dotted module (Swift dotted imports never
  fall back to a Swift module named `os`; a dotted swiftmodule name doesn't resolve either;
  `-module-alias` engages post-resolution); a clang os.log can't carry `os_log` (C variadics
  are uncallable from Swift, `swift_name` is ignored on them). The full SDK's os Swift overlay
  resolves this; until then the canImport guard is the honest shape.

## Known shim gaps (L0 markers, each load-bearing later)

- `JSONEncoder`/`JSONDecoder` bodies `fatalError` (2 call sites in Postbox Coding.swift) —
  real Codable-walking implementations are the L3 gate for those paths.
- `Network` shim reports `.unsatisfied`; `os` shim no-ops; `fileResourceIdentifier` is a
  path-hash stand-in (Apple's is opaque); `IndexSet.RangeView` walks via public NSIndexSet API.
- WebKit overlay (WebProxyTransport) — the next user-independent task before TelegramCore.

## Commands

```sh
cd $HOME/dev/Telegram-iOS
python3 tools/tgbuild/swift.py //submodules/SSignalKit/SwiftSignalKit:SwiftSignalKit --force
python3 tools/tgbuild/swift.py //submodules/Postbox:Postbox --force
python3 tools/tgbuild/swift.py //submodules/TelegramCore:TelegramCore --force   # 11 ok / WebProxyTransport = WebKit
python3 tools/tgbuild/probe.py //submodules/TelegramCore:TelegramCore           # full stderr for one module
./tools/tgbuild/rebuild-foundation.sh                                           # after editing overlay/*.swift
```

## Artifacts

| Path | What |
|---|---|
| `build-input/swift/modules/*.swiftmodule` (11) | stable interface copies (2.3 MB Postbox, 10.3 MB TelegramApi) |
| `build-input/swift/objects/*.o` (11) | Mach-O arm64 objects for Phase 4's link |
| `build-input/swift/shims/` | `os`, `Network` Swift shim modules |
| `build-input/swift-cache/<hash>/` | content-hashed products |
| `submodules/TelegramApi/Generated/`, `submodules/TelegramCore/FlatSerialization/*_generated.swift` | codegen outputs (untracked) |

---

# Итерация 2 (продолжение, 2026-10-25): WebKit-overlay и TelegramCore

## Результат

- **WebProxyTransport (10 файлов) компилируется** — 12-й модуль замыкания TelegramCore.
- **TelegramCore (718 файлов) дошёл до хвоста**: BlockingModules исправлены, осталось ~10
  семейств API (NWConnection shim дописан, clock-константы добавлены в _time.h, MTKeychain
  решён через `#if TGBUILD id`-форму, JSONEncoder/Decoder стали классами, NSRegularExpression,
  NSUbiquitousKeyValueStore, NSKeyedArchiver/Unarchiver, NSURLComponents/QueryItem,
  NSDecimalNumberHandler, NSOperationQueue, block-based observers добавлены в clang-модуль
  Foundation; MTRequest/MTOutputStream получили nullability-обёртки; ключевой корневой фикс —
  `_Nonnull` на `-[NSObject init]` в darwin objc/NSObject.h, устраняющий Optional-иниты для
  всего графа; CoreTelephony/Photos/LinkPresentation/CoreServices/Security — новые фреймворк-
  модули).

## Опыты, которые НЕ сработали (зафиксировано, чтобы не повторять)

- **apinotes**: clang 21 + этот swiftc не читают module-adjacent apinotes ни в одном из
  трёх испробованных расположений (фреймворк-корень, Modules/, module.apinotes); SwiftBridge
  через них недоступен. Обход — `swift_name`-атрибуты прямо в заголовках.
- **Де-генеризация NSDictionary** ради бриджинга к `[AnyHashable: Any]` ломает ВСЕ init'ы
  с NSDictionary-параметрами (импортёр перестаёт их узнавать). Откат через git-checkout 45
  репозиторных заголовков + ручное восстановление в sdkm.
- **`#if TGBUILD` в MTKeychain.h** (репо-заголовок, `-Xcc -DTGBUILD` от драйвера): Linux
  видит требование `- (nullable id)dictionaryForKey:...` → Any?-свидетель; macOS — прежний
  NSDictionary-метод. Свидетели Keychain в Network.swift переведены с IUO (String!) на
  non-optional String под тем же флагом.

## Точная позиция TelegramCore (для следующего запуска)

Одиночный тип-чек `tools/tgbuild/probe.py //submodules/TelegramCore:TelegramCore` показывает
остаток: EncryptionProvider-тип внутри файла с `internal import TelegramApi`
(ProcessSecretChatIncomingDecryptedOperations.swift:73), NW shim доводка, `OSAtomicIncrement32`
(moдуль libkern/OSAtomic.h в darwin добавлен — проверить видимость), `[Any]→Int` (23 места —
`jsonObject(with:options:)` опции), `creationDateKey`-семейство URLResourceKey, 4 места
«unable to type-check in reasonable time» (Log.swift — может уйти само после остальных).
Итерационный контур: правка → `rm -rf build-input/swift/clang-cache` → `swift.py --force`.
