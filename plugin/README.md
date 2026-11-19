# PlayTeam Check

**Is your Android app ready for Google Play?** PlayTeam Check reviews your project against the 12 things that most
often block a release (target API level, 16 KB memory pages, privacy policy, Data safety and the SDKs you ship, account
deletion, photo and video permissions, restricted permissions and foreground services, app name, Google branding,
payments, closed test, content rating) and tells you what to fix, with the official Google page for each point.

Works with native Android (Kotlin / Java), Flutter, React Native and Expo projects. Open your project and type
`/playteam-check:check`, or ask "is my app ready for Google Play?".

## What it does and doesn't do

- It is **read-only**: Claude only reads your project files. Nothing is written, built, installed or sent anywhere,
  and the plugin contains no code, hooks or servers, only instructions.
- Each point is 🟢 nothing found, 🟠 to check, 🔴 likely rejection, or ⚪ only Play Console can tell.
- It is a quick static review, not a full audit, and a green point is not a guarantee of approval.

## Privacy

PlayTeam Check collects no data and makes no network request.

The paid PlayTeam pack (https://playteamdev.gumroad.com) runs a full audit team before each release and fixes what
can be fixed. PlayTeam is an independent product by Delarroc Technologies, not affiliated with or endorsed by Google.
Google Play and Android are trademarks of Google LLC.

MIT licence — see [LICENSE](LICENSE).
