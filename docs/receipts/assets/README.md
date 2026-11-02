# Screenshot assets — publication triage

The build sessions captured device screenshots as evidence. Only impersonal
ones are published here; the full set stays in the private working tree. The
receipts' text mentions some withheld files by name (they document what was
captured); those references point at files that are deliberately not in this
repository.

| File | Verdict | Why |
|---|---|---|
| `2026-10-28-linux-nuc-icon.png` | publish | Home-screen icon of the Linux-built app; no user content. |
| `2026-10-28-linux-nuc-onboarding.png` | publish | Onboarding screen of a fresh install; no account content. |
| `2026-10-28-onboarding-before-marker.png` | publish | Onboarding screen before the launch-marker probe; no account content. |
| `2026-10-28-linux-nuc-chat-list.png` | withhold | Authorized chat list with real conversations. |
| `2026-10-28-chat-list-first-render.png` | withhold | Authorized chat list with real conversations. |
| `2026-10-28-chat-list-rendering.png` | withhold | Authorized chat list with real conversations. |
| `2026-10-28-linux-nuc-contacts-prompt.png` | withhold | Permission dialog over a populated environment; not needed. |
| `2026-10-28-linux-nuc-phone-entry.png` | withhold | Phone-entry screen (a real number was entered during the session). |
| `ui-walk/*` | withhold | Interactive UI walk over an authorized account (real chats throughout). |

Re-shooting the withheld evidence on a test account is possible later; the
receipts' claims do not depend on the withheld images (their numbers come from
logs and crash reports).
