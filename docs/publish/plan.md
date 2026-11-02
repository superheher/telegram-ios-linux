# План публикации: репозиторий `telegram-ios-linux`

План для агента-исполнителя. Создан 2026-11-02, исходное состояние зафиксировано на
вечер 2026-11-02 (сборка зелёная, чат-лист на устройстве рендерится —
`docs/linux-build-next-session.md` §1, обновление 2026-11-02).

**Ценность репозитория**: воспроизводимая сборка Telegram-iOS на Linux без macOS —
инструменты (`tgbuild`), патчи к исходникам, документация и дневник того, как это было
сделано. Это проект про **сборку**, а не форк приложения: никаких фич форка, никаких
упоминаний других веток/аккаунтов.

---

## 1. Параметры (все изменения вносятся только здесь)

| Параметр | Значение |
|---|---|
| Имя автора в коммитах | `superheher` (если нужно буквально `gh superheher` — поменять здесь) |
| Почта автора | `[redacted-author-email]` |
| GitHub-аккаунт | `superheher` (активный в `gh auth status`; второй аккаунт **не использовать**) |
| Имя репозитория | `telegram-ios-linux` |
| Локальный путь нового репо | `~/dev/telegram-ios-linux` |
| Базовый коммит апстрима | `fb0e62ba8a` (`Bump version`, master `TelegramMessenger/Telegram-iOS`) |
| Источник данных | `$HOME/dev/Telegram-iOS`, ветка `[redacted]` + рабочее дерево — **только чтение** |
| Локальный каталог хост-скриптов | `~/dev/omarchy-apple-dev` (только чтение, скрипты вендрятся копированием) |

## 2. Жёсткие правила

1. **Авторство**: каждый коммит нового репо — `GIT_AUTHOR_NAME`/`GIT_COMMITTER_NAME` =
   параметр из §1. Настроить `git config` в новом репо сразу после init и проверять
   `git log --format='%an <%ae> | %cn <%ce>'` в конце каждого этапа.
2. **Темы коммитов** — по правилам kit (первое слово из списка: Reverted, Replaced,
   Removed, Documented, Updated, Moved, Renamed, Migrated, Split, Extended, Added,
   Fixed, Improved; единственная квалифицированная форма — `Slightly improved`;
   документы — `Documented <what> in <place>.`). Перед каждым коммитом:
   `python3 ~/kit/commit-style/check_commit_msg.py --string "<subject>"`. Никогда
   не использовать `--no-verify`.
3. **Запрещённые слова в новом репо**: `[redacted]`, `[redacted]`, а также `[redacted-device]`,
   `[redacted-apple-id]`, UDID `[redacted-udid]`, имя устройства. Гейт каждого этапа:
   `grep -rin "[redacted]\|[redacted]\|[redacted-apple-id]\|[redacted-udid]" --exclude-dir=.git .` → 0 совпадений.
   (Подстановка `[redacted]` допустима, просто отсутствие — лучше.)
4. **Никогда не включать в репо**: `Xcode_27.2_Release_Candidate.xip` (2 ГБ, лежит в
   корне исходного репо), кэш `darwin-iPhoneOS27.2.xtoolsdk` (~11 ГБ,
   `~/dev/omarchy-apple-dev/sdk-free/sdk-cache/`), содержимое `build-input/`
   (кэши объектов, граф-кэши можно как сгенерированные заново), токены
   `~/.config/xtool/`, скриншоты с реальными чатами/аккаунтом (триаж — этап 5).
5. **Исходный репозиторий не изменяется**: ни ветка `[redacted]`, ни рабочее дерево,
   ни кэши `build-input/`. Все изменения — только в новом репо и его временных
   worktree. Чтение исходников, `git show`, `git diff` — сколько нужно.
6. **Пошаговое документирование**: каждый этап завершается обновлением
   `docs/publish/journal.md` в новом репо (что сделано, чем проверено, отклонения)
   и коммитом(ами). Этап считается закрытым только после зелёного критерия приёмки.
7. **Load-bearing знание** (из дневника, не переоткрывать): флаг `--min 16.0` в
   каждом вызове `swift.py` обязателен (при min 17 компилятор сворачивает
   `#available`-гейты → SIGABRT на iOS 16.7); после правки любых заголовков —
   `rm -rf build-input/swift/clang-cache`; usbmuxd клинит — `sudo systemctl restart usbmuxd`.

## 3. Целевая структура репозитория

```
telegram-ios-linux/
├── README.md                  — что это, статус, ограничения, быстрый старт
├── LICENSE                    — GPLv3
├── NOTICE.md                  — база апстрима, происхождение, товарные знаки Telegram
├── .gitignore                 — build-input/, кэши, .xip, .o, __pycache__, машинно-локальное
├── docs/
│   ├── build-guide.md         — ГЛАВНЫЙ документ: сборка с нуля на чистой Ubuntu 24.04
│   ├── architecture.md        — как устроен tgbuild: граф 1009 модулей, драйверы, кэши, SDK
│   ├── status.md              — что работает/не работает (уровни L0–L4 + текущие дыры)
│   ├── traps.md               — свод ловушек (из §5 handoff + все последующие)
│   ├── journal/               — дневники сессий (вычищенные): linux-build-2026-10-25.md и др.
│   ├── receipts/              — приёмочные акты (вычищенные) + отобранные ассеты
│   └── publish/               — план (копия этого файла), journal.md, inventory/
├── patches/
│   ├── base-commit            — fb0e62ba8a + URL апстрима (однострочный файл)
│   ├── series                 — порядок применения
│   ├── 0001-*.patch …         — серия по подсистемам (метод — §6)
│   └── apply-patches.sh       — накат серии на свежий worktree базового коммита
├── tools/
│   ├── tgbuild/               — extract.py, swift.py, objc.py, link.py, probe.py,
│   │                            audit_images.py, patch_metal_loaders.py,
│   │                            make-generated-sources.sh, rebuild-foundation.sh,
│   │                            overlay/, stubs/   (без __pycache__)
│   ├── host/                  — вендренные из ~/dev/omarchy-apple-dev: cc.sh,
│   │                            xip_extract.py, рецепты xtool/actool/ibtool
│   ├── snapshot/              — копия docs/tgbuild-sdkfree-snapshot/ (sdk-free режим)
│   └── generated/             — сгенерированные исходники (этап 4)
└── (больше ничего)
```

## 4. Этапы

### Этап 0 — Каркас
`git init ~/dev/telegram-ios-linux`; repo-local `git config` идентичности; скопировать
этот план в `docs/publish/plan.md`; создать пустой `docs/publish/journal.md` (таблица
этапов); `.gitignore` по §3.
- Коммит: `Documented the publication plan in docs/publish/.`
- Приёмка: `git log` показывает один коммит с правильным автором; чекер доволен темой.

### Этап 1 — Заморозка входных данных
Источник данных меняется под ногами (параллельно идёт работа над форком). До всего
остального зафиксировать в `docs/publish/inventory/`:
- `git -C $HOME/dev/Telegram-iOS diff > inventory/worktree-2026-11-02.diff`
  (незакоммиченный хвост);
- `git status --short`, список untracked с размерами;
- `git log --format='%H %an %s' fb0e62ba8a..[redacted]` (11 хэшей фичевых коммитов —
  вход для триажа §6);
- контрольные суммы всех импортируемых каталогов (`tools/tgbuild`, набор `docs/*`,
  `docs/receipts/`, `docs/tgbuild-sdkfree-snapshot/`, `~/dev/omarchy-apple-dev`
  — список файлов + sha256).
- Коммит: `Documented the source inventory in docs/publish/inventory/.`
- Приёмка: по inventory можно восстановить, ЧТО импортировано, даже если источник
  изменится; дифф рабочегого дерева снят (дальнейшие изменения источника не влияют).

### Этап 2 — Патч-серия (самый трудоёмкий этап)
Задача: из исходного дерева выделить ТОЛЬКО сборочные изменения относительно
`fb0e62ba8a` и оформить серией патчей. Метод — §6.
1. Worktree: `git -C $HOME/dev/Telegram-iOS worktree add /tmp/tgi-base fb0e62ba8a`
   (или копия). В нём по триаж-таблице применить сборочные хунки.
2. Оформить серией коммитов по подсистемам (см. §6, порядок в `patches/series`),
   автор — из §1, темы — по правилам (примеры: `Updated the WebRTC build for x86_64
   hosts.`, `Added TGBUILD compile hooks to Swift sources.`, `Fixed MtProtoKit header
   nullability for the Linux importer.`).
3. `git format-patch fb0e62ba8a -o patches/` → перенести в новый репо, написать
   `patches/apply-patches.sh` (clone base → apply series).
4. **Приёмка (обязательная)**: в свежем worktree базового коммита применить серию,
   затем на этой машине прогнать конвейер: `extract.py` (граф собирается),
   лестница `swift.py //submodules/TelegramUI:TelegramUI --min 16.0` зелёная,
   `link.py --app` собирает `.ipa`. Опционально (пользователь рядом): установка
   на iPhone X и запуск. Внимание: у второго worktree свои кэши `build-input/` —
   проверить свободное место (`df -h`), кэши сотни МБ…единицы ГБ.
- Коммиты: `Added the Linux build patch series for Telegram-iOS fb0e62ba8a.` (патчи +
  скрипт) и `Documented the patch triage in docs/publish/.` (таблица триажа).
- Приёмка-документ: в journal — вывод apply + сборки, размеры, время.

### Этап 3 — Инструменты
1. `tools/tgbuild/` — скопировать из inventory-списка (без `__pycache__`), это ядро:
   драйверы, оверлеи Foundation, стабы. Проверить: ни один файл не содержит
   абсолютных путей `$HOME/...` (если содержит — параметризовать через env
   `TGBUILD_HOME`/`$HOME` и записать в build-guide).
2. `tools/host/` — вендрить из `~/dev/omarchy-apple-dev`: `cc.sh` (обёртка clang),
   `tools/xip_extract.py`, рецепты сборки xtool/actool/ibtool (если это скрипты —
   сами скрипты; если бинарники — только рецепты сборки). С пометкой происхождения
   в NOTICE.
3. `tools/snapshot/` — копия `docs/tgbuild-sdkfree-snapshot/` (31 файл, sdk-free
   режим). Триаж: файлы, являющиеся переработанными заголовками Apple
   (например `darwin-usr-include/objc-NSObject.h`), публиковать нельзя — заменить
   на инструкцию «что и как поменять в своём экземпляре» (дифф-описание в
   `tools/snapshot/README.md`); целиком авторские файлы (Foundation.h, 12
   framework-модулей sdkm) публикуются как есть.
- Коммиты: `Added the tgbuild Linux build drivers.`, `Added host toolchain scripts
  to tgbuild.`, `Added the sdk-free header snapshot with provenance notes.`
- Приёмка: `python3 tools/tgbuild/extract.py -o /tmp/graph.json` отрабатывает на
  патченном worktree этапа 2; grep на абсолютные пути — 0.

### Этап 4 — Сгенерированные исходники
`submodules/TelegramApi/Generated/` (44 файла) и
`submodules/TelegramCore/FlatSerialization/*_generated.swift` (34 файла) нужны каждой
сборке. По умолчанию — скопировать в `tools/generated/` с README «откуда и как
регенерируются» (рецепт: SwiftTL host-сборка + flatc 24.12.23, команды в
`tools/tgbuild/make-generated-sources.sh` и receipts фазы 3). Они порождаются из
схем GPL-репо — публикация легальна. Альтернатива (если захочется чистоты) — не
публиковать, только рецепт; решение поменять можно здесь.
- Коммит: `Added generated TelegramApi and FlatSerialization sources.`
- Приёмка: свежая генерация по рецепту воспроизводит файлы побайтно (или
  документированные отличия).

### Этап 5 — Скраб и документация
1. Скрипт `tools/scrub.py` (живёт в новом репо) с явным списком замен (таблица в §5)
   — прогнать по всем импортируемым текстам.
2. Импорт дневников в `docs/journal/`: `linux-build-2026-10-25.md`,
   `linux-build-research-plan.md`, `linux-build-next-session.md` (после скраба —
   убрать ссылки на ветку форка и фичевые работы, оставить сборочную линию),
   `next-session-ui-walk.md` + `ui-gaps.md` (только сборочные части: аудит ассетов,
   бандлы, Metal-лоадеры; ходьбу по фичам UI — не импортировать).
3. Импорт `docs/receipts/` (6 актов, вычищенных) в `docs/receipts/`.
4. **Скриншоты (18 МиБ, триаж обязательный)**: публиковать только безличные —
   `2026-10-28-linux-nuc-icon.png`, `2026-10-28-linux-nuc-onboarding.png`,
   `2026-10-28-onboarding-before-marker.png`. НЕ публиковать всё с чатами
   (`*-chat-list*`, `ui-walk/*`) и `*-phone-entry*` (вводился номер телефона).
   В `docs/receipts/assets/README.md` — таблица триажа (каждый файл → публиковать/
   нет → почему). При желании позже — переснять на тестовом аккаунте.
5. Новые сводные документы (пишутся заново, на основе дневников, без их мусора):
   - `docs/build-guide.md` — чистая Ubuntu 24.04 → работающая сборка: Swift 6.4,
     xtool (сборка из исходников + `xtool auth` + `xtool sdk build` из .xip,
     восстановление SubFrameworks через xip_extract.py), pymobiledevice3, Bazel
     (host-часть), кодген, драйверы, `--min 16.0`, линк, подпись, установка,
     цикл итерации, восстановление машинно-локального из snapshot.
   - `docs/architecture.md` — граф 1009 модулей, objc/swift/link драйверы, кэши,
     clang-модули, оверлеи, отличия от Bazel/rules_apple-пути.
   - `docs/status.md` — L0–L4 (определения из research-plan), что зелёное, дыры:
     Rust-движки (159 модулей, заглушки), 6 расширений, watch, arm64e/iOS>16.7
     непроверены, free-подпись 7 дней.
   - `docs/traps.md` — весь §5 handoff + ноябрьские находки (--min 16.0 и др.).
- Коммиты: по группам, `Documented the Linux build guide in docs/build-guide.md.`,
  `Documented the session journals in docs/journal/.`, `Documented the phase receipts
  in docs/receipts/.` и т.п.
- Приёмка: гейт запрещённых слов (правило 3 §2) — 0; каждая ссылка в docs
  разрешается внутри репо; build-guide читается подряд и не ссылается на
  «следующую сессию».

### Этап 6 — Лицензия и NOTICE
`LICENSE` (GPL-3.0), `NOTICE.md`: база — `TelegramMessenger/Telegram-iOS`
@ `fb0e62ba8a`, лицензия апстрима; этот репозиторий — инструменты и документация для
сборки, патчи производны от GPL-кода; товарные знаки: неофициальный статус, имя
Telegram и логотип принадлежат Telegram (руководство из README апстрима —
переписать своими словами, не копируя); происхождение host-скриптов
(omarchy-apple-dev) и снапшота.
- Коммит: `Added GPLv3 license and upstream notice.`

### Этап 7 — README
Честно и без пафоса: что это (полный конвейер сборки Telegram-iOS на Linux x86_64
без macOS: компиляция 1009 модулей, линковка, ресурсы, подпись, установка на
устройство), что проверено (iPhone X, iOS 16.7.16, arm64), ограничения (см. status),
быстрый старт (3 команды → build-guide), карта репо. Скриншот-иконку onboarding —
по желанию.
- Коммит: `Documented the repository overview in README.md.`

### Этап 8 — Гигиена перед пушем
1. Секреты: `grep -rin` по маркерам (token, password, api_hash собственный, BEGIN
   PRIVATE KEY) по всему дереву + по патчам; `api_id 611335` — публичные креды
   Telegram Desktop, остаются с комментарием.
2. Бинарный аудит: `git ls-files | xargs file` — нет Mach-O/бинарников кроме
   ожидаемых ассетов; размер репо разумный (<100 МБ).
3. Авторство: все коммиты — из §1 (`%an|%cn`); чекер тем по всей истории:
   `git log --format=%s | while read s; do python3 ~/kit/commit-style/check_commit_msg.py --string "$s" || echo "BAD: $s"; done`.
4. Гейт запрещённых слов ещё раз, включая `git log --all --format=%s`.
5. Сухой прогон: свежий `git clone` нового репо в /tmp → `apply-patches.sh` →
   `extract.py` (без полной сборки; полная уже доказана этапом 2).
- Коммит: `Documented the pre-publication audit in docs/publish/journal.md.`

### Этап 9 — Публикация
1. `gh repo create superheher/telegram-ios-linux --private --source . --push`
   (сначала приватный, пуш ~сотни МБ).
2. Ревью на github.com глазами пользователя: README, build-guide, триаж скриншотов.
3. Публичность — только по явному подтверждению пользователя:
   `gh repo edit superheher/telegram-ios-linux --visibility public`.
4. Постпроверка: свежий клон в /tmp, полный гейт §8.3–8.4 на клоне.
5. Опционально (отдельная работа, не блокирует): тег `v0.1` на первую публичную
   точку; апстримные PR хост-фиксов (x86_64-селекты webrtc/wamr/openh264, libjxl
   BUILD) в TelegramMessenger/Telegram-iOS.
- Коммит: `Documented the publication in docs/publish/journal.md.`

## 5. Список замен скраба (применять ко всем текстам нового репо)

| Найти | Заменить |
|---|---|
| `[redacted-apple-id]` (Apple ID) | `[redacted-apple-id]` |
| `[redacted-author-email]` | не должен встречаться в текстах (только git-авторство) |
| `[redacted-team-id]` (Team ID) | `[redacted-team-id]` |
| `[redacted-udid]` (UDID-префикс) | `[redacted-udid]` |
| `[redacted-device]'s iPhone` / `[redacted-device]` | `[redacted-device]` |
| `[redacted]`, `[redacted]`, `[redacted]` | убрать контекст или `[redacted]` |
| `[redacted]` (аккаунт/автор) | `[redacted]` |
| имя бандла `XTL-[redacted-team-id].ph.telegra.Telegraph` | `XTL-<team-id>.ph.telegra.Telegraph` |
| `611335` / `d524b414d21f4d37f08684c1df41ac9c` | оставить (публичные креды Telegram Desktop) с пометкой в NOTICE |
| пути `$HOME/...` | `$HOME/...` или `~/...` |

Отдельно: в импортируемых дневниках встречаются формулировки вида «наша фича»,
«ветка [redacted]», «rebase war» — такие абзацы вырезать целиком, сохраняя
сборочные факты вокруг них; правки вносить бережно (дневник — исторический
документ, но публикуется как документ сборки).

## 6. Метод триажа патчей (этап 2)

Исходное состояние: ветка `[redacted]` = `fb0e62ba8a` + 11 фичевых коммитов, в
которые **вшита** сборочная адаптация (autosquash), + 9 файлов незакоммиченного
хвоста. Значит, простое «взять дифф ветки» не работает, и «вычесть фичевые коммиты»
тоже: адаптация сидит внутри них.

Порядок:
1. Составить полный список изменённых файлов: `git diff --name-only fb0e62ba8a` в
   исходном репо (на [redacted], включая рабочее дерево) — ориентир ~160 файлов.
2. Список ожидаемых сборочных изменений собрать из дневников — они перечислены
   явно: таблица в `linux-build-2026-10-25.md` («What was patched»), §1b/§3
   `linux-build-next-session.md` (MtProtoKit nullability + `#if TGBUILD` id-form,
   Network.swift, WebProxyDiagnostics.swift, WebProxyWebViewCarrier.swift,
   availability-аннотации), patch_metal_loaders.py (16 Metal-лоадеров), main.m
   breadcrumbs, AppDelegate runtime-фиксы (`tgbuildLog`, App Group fallback, Siri
   stub), CloudData (CloudKit stub), TLObjectSupport.swift. Фингерпринт сборочных
   хунков: `#if TGBUILD`, `-DTGBUILD`, `TGBUILD_SDKFREE`, `TGBUILD_SYSROOT`,
   упоминания tgbuild/link.py.
3. Фичевые коммиты (исключить целиком их замысел, хунки проверять): `d9c068b984`
   (hidden accounts), `5e7e41f321` (QR login), `7e344fc0a8` (camera memory),
   `f545e568aa` (sync contacts), `cd94638937` (share button), `e150f9e76e` (fast
   forward), `c918b0888a` (passkey crash), `63b8174209` (list view loop),
   `94cda84b60` (test server switch), `d530d31d23` (add-to-emoji-set),
   `ff23781124` (album caption edit). Файлы, тронутые только ими, и не
   упомянутые в п.2 — в серию не попадают.
4. Смешанные файлы (например AppDelegate.swift, MetalEngine.swift, TabBarComponent.swift)
   — разбирать по-хунково: сборочный хунк → патч, фичевый → нет. Каждый спорный
   хунк записывать в триаж-таблицу (`docs/publish/triage.md`): файл, хунк,
   классификация, обоснование.
5. Итог серии — 8–12 патчей по подсистемам:
   1) host-фиксы Bazel (MODULE.bazel wasi x86_64, wamr/openh264/webrtc/crc32c
   arch-селекты, absl glob, libjxl BUILD rename, subcodec NEON-гарды, tgcalls
   `#include <mutex>`); 2) MtProtoKit/заголовочные nullability + id-form;
   3) `#if TGBUILD` compile-хуки Swift/ObjC; 4) app runtime (main.m, AppDelegate,
   CloudData, Siri/App Group/CloudKit fallback); 5) Metal-лоадеры runtime-компиляция;
   6) прочее из триажа. Каждый патч — внятное тело с «почему».
6. Контроль полноты: после сборки верификационного worktree сравнить поведение —
   лестница зелёная, app запускается. Контроль чистоты: в серии не должно быть
   хунков с фичевой семантикой (проверка глазами по триаж-таблице; ревью таблицы
   пользователем перед этапом 9).
7. Подмодуль `submodules/TgVoipWebrtc/tgcalls` показывается изменённым при dirty
   submodule — в серию не включать; приёмку делать при чистом состоянии
   (`git submodule status`).

## 7. Финальный чек-лист публикации

- [ ] все коммиты authored+committed `superheher <[redacted-author-email]>`, темы чекер
      принимает
- [ ] `grep -rin "[redacted]\|[redacted]\|[redacted-apple-id]\|[redacted-udid]\|[redacted-device]"` → 0 (файлы, патчи,
      истории коммитов)
- [ ] серия патчей применяется к чистому `fb0e62ba8a` и собирается до `.ipa`
- [ ] `tools/tgbuild` работает без абсолютных путей
- [ ] нет `.xip`, SDK-кэшей, `build-input/`, скриншотов с реальными чатами
- [ ] LICENSE + NOTICE + README на месте
- [ ] приватный пуш → ревью пользователем → публичность по его подтверждению
