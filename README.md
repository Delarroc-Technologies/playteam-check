# PlayTeam Check

**Is your Android app ready for Google Play?** A free, read-only plugin for Claude that reviews
your project against the 12 things that most often block a release, and tells you what to fix, with the official Google
page for each point.

Works with native Android (Kotlin / Java), Flutter, React Native and Expo projects.

```
🔴  2. Target API level: targetSdk 34 found; Google Play requires 36 for new apps and updates.
       → Set targetSdk = 36, then test the app: Android 16 behaviour changes apply.
🔴  4. Privacy policy: No privacy policy link found in the app's code or strings.
🟠  5. Data safety vs the SDKs you ship: SDKs that collect or share data: Firebase Analytics, Firebase Crashlytics.
🟢  6. Account deletion: No account creation found.
...
Score: 7 green · 1 to check · 2 likely rejection · 2 to confirm in Play Console
```

## Install

In Claude Code:

```
/plugin marketplace add Delarroc-Technologies/playteam-check
/plugin install playteam-check@playteam
```

Then open your Android project and type `/playteam-check:check`, or just ask "is my app ready for Google Play?".

The plugin itself contains no code: it is a skill (in [`plugin/`](plugin)) that tells Claude what to look for, and
Claude reads your files with its own tools.

You can also run the same 12 checks without Claude, with the standalone scanner in this repository
(Python 3.9+, no dependency, read-only):

```
python3 scanner/check.py --root path/to/your/project        # add --json for machine-readable output
```

## The 12 points

| # | Point | How it's checked |
|---|---|---|
| 1 | Closed test (new personal accounts: 12 testers, 14 days) | Asked: it depends on your developer account |
| 2 | Target API level (36 since August 31, 2026) | Gradle files, version catalog, convention plugins |
| 3 | 16 KB memory pages | Native code (`.so`, NDK, CMake) in the project |
| 4 | Privacy policy | A privacy policy link in the app's code or strings |
| 5 | Data safety | Known SDKs that collect data (analytics, ads, crash, AI…) and network calls |
| 6 | Account deletion | Account creation without a deletion flow |
| 7 | Photo and video permissions | `READ_MEDIA_IMAGES` / `READ_MEDIA_VIDEO` in the manifests |
| 8 | Restricted permissions and foreground services | SMS, call log, all files, exact alarms… and foreground service types |
| 9 | App name | Length, ranking / price words, emoji, ALL CAPS |
| 10 | Google / Android branding | "Android" or "Google" in the app name |
| 11 | Payments | Other payment SDKs next to (or instead of) Google Play Billing |
| 12 | Content rating and target audience | Asked; flags child-directed words |

Each point is 🟢 nothing found, 🟠 to check, 🔴 likely rejection, or ⚪ only Play Console can tell.

## What it does not do

- It **never changes your project**: it only reads files; nothing is written, built, installed or sent over the network.
- It is a quick static scan, not a full audit: it doesn't see what the merged manifest of your SDKs adds, what data really
  leaves the device, or your translations, UI and security. A green point is not a guarantee of approval.
- Google's rules change. Requirements were checked against Google's official pages in November 2026; when a linked page
  says otherwise, the page wins.

## Privacy

PlayTeam Check collects no data. The plugin only asks Claude to read your project; the standalone scanner runs locally
and makes no network request.

## Want the fixes too?

The paid **PlayTeam** pack runs a full team of audit agents before each release (security, Google Play rules, legal,
UI and accessibility, translations, technical quality, store listing, release, closed test) and fixes what can be fixed:
<https://playteamdev.gumroad.com>

## Licence

MIT — © 2026 Delarroc Technologies. PlayTeam is an independent product, not affiliated with or endorsed by Google.
Google Play and Android are trademarks of Google LLC.
