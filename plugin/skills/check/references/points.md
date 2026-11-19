# The 12 points

"Gradle files" means every `*.gradle`, `*.gradle.kts`, `gradle.properties` and `gradle/*.toml` file, plus the `.kt`
files of convention plugins (`build-logic/`, `buildSrc/`, `build-plugin/`). For Flutter and React Native, also read
`pubspec.yaml` or `package.json`. "Manifests" means every `AndroidManifest.xml` outside build folders. "Strings" means
the `res/values/*.xml` files. "Code" means the `.kt`, `.java`, `.dart`, `.js`, `.jsx`, `.ts` and `.tsx` files.

## 1. Closed test (new personal accounts) — ⚪

Can't be read from the code. Ask: "Is your developer account a personal account created after November 13, 2023?"
If yes, the app needs a closed test with at least 12 testers opted in for 14 days in a row before production access.
Source: https://support.google.com/googleplay/android-developer/answer/14151465

## 2. Target API level

Find the app's `targetSdk` / `targetSdkVersion`. It can be a literal, a `gradle.properties` value, a version catalog
entry (`libs.versions.a.b.c` → key `a-b-c` in `gradle/libs.versions.toml`) or a Kotlin constant in a convention plugin.
- 🔴 lower than 36: Google Play has required 36 for new apps and updates since August 31, 2026.
- 🟢 36 or higher.
- 🟠 not found (set by a plugin you can't read): ask the user to check it.
Next step if red: set `targetSdk = 36`, then test the app, because Android 16 behaviour changes apply.
Source: https://support.google.com/googleplay/android-developer/answer/11926878

## 3. 16 KB memory pages

Look for native code: `.so` files, `externalNativeBuild`, `ndkVersion`, `cmake {` in the Gradle files.
- 🟠 native code found: the libraries must be aligned for 16 KB pages (NDK r28+ or AGP 8.5.1+, check with
  App bundle explorer in Play Console).
- 🟢 none (an SDK can still bring native code: check App bundle explorer).
Source: https://developer.android.com/guide/practices/page-sizes

## 4. Privacy policy

Look in the code and strings for an `https://` link containing `privacy`, `confidential`, `datenschutz` or `privacidad`.
- 🟢 found (quote the link).
- 🔴 none: the app must link its privacy policy inside the app as well as in Play Console.
Source: https://support.google.com/googleplay/android-developer/answer/10144311

## 5. Data safety vs the SDKs you ship

Look in the Gradle files (or `pubspec.yaml`, `package.json`) for SDKs that collect or share data:
Firebase Analytics, Crashlytics, Cloud Messaging, Authentication; Google Mobile Ads; Meta (Facebook) SDK; Sentry;
OneSignal; RevenueCat; Mapbox; AppsFlyer; Adjust; Amplitude; Mixpanel; AppLovin; Unity Ads; Gemini / Firebase AI;
OpenAI; Anthropic API.
- 🟠 SDKs found: list them; each must be reflected in the Data safety form.
- 🟠 no SDK, but network calls in the code (Retrofit, OkHttp, HttpURLConnection, Ktor, Volley, `fetch(`, axios, Dio):
  check what data leaves the device.
- 🟢 neither.
Source: https://support.google.com/googleplay/android-developer/answer/10787469

## 6. Account deletion

- 🔴 account creation in the app (`createUserWithEmail`, `auth.signUp`, `.signUp(`, `registerUser`,
  `createUserAccount`, Supabase / Auth0 sign-up) and no deletion flow (`deleteAccount`, `delete_account`,
  "delete my account", `currentUser.delete`, `deleteUser`).
- 🟠 sign-in only (`signIn`, `login`, `FirebaseAuth`, `GoogleSignIn`, `createAccount` for an external service…) and no
  deletion flow: required only if users can create the account in the app.
- 🟢 no account, or accounts with a deletion flow.
Next step if red: add "Delete my account" in the app and a web deletion page declared in Data safety.
Source: https://support.google.com/googleplay/android-developer/answer/13327111

## 7. Photo and video permissions

Look in the manifests for `READ_MEDIA_IMAGES` and `READ_MEDIA_VIDEO`.
- 🔴 declared while the code also uses a picker (`PickVisualMedia`, `ACTION_PICK`, `GetContent`, `image_picker`):
  the picker is enough, remove the permission.
- 🟠 declared: allowed only when broad access is a core feature (declaration form in Play Console); otherwise use the
  photo picker.
- 🟢 not declared.
Source: https://support.google.com/googleplay/android-developer/answer/14115180

## 8. Restricted permissions and foreground services

Look in the manifests for: `ACCESS_BACKGROUND_LOCATION`, `MANAGE_EXTERNAL_STORAGE`, `QUERY_ALL_PACKAGES`,
`READ_SMS`, `SEND_SMS`, `RECEIVE_SMS`, `READ_CALL_LOG`, `WRITE_CALL_LOG`, `PROCESS_OUTGOING_CALLS`, `USE_EXACT_ALARM`,
`USE_FULL_SCREEN_INTENT`, `REQUEST_INSTALL_PACKAGES`, `BIND_ACCESSIBILITY_SERVICE`, and for
`android:foregroundServiceType` values.
- 🟠 any found: each needs a declaration in Play Console (and a short video for foreground services) that matches a
  real feature.
- 🟢 none.
Source: https://support.google.com/googleplay/android-developer/answer/9888170

## 9. App name

Take the name from the manifest `android:label` (resolve `@string/app_name`, preferring the app module's `src/main`)
or from `fastlane/metadata/android/*/title.txt`.
- 🟠 more than 30 characters, ranking or price words (#1, best, free, new, sale, % off, top), emoji, or ALL CAPS.
- 🟢 otherwise (quote the name).
- ⚪ name not found: ask for it.
Source: https://support.google.com/googleplay/android-developer/answer/9898842

## 10. Google / Android branding

- 🟠 the name contains "Android", "Google" or "Play Store" (other than "… for Android" after the app's own name).
- 🟢 otherwise.
Source: https://developer.android.com/distribute/marketing-tools/brand-guidelines

## 11. Payments

In the Gradle files / `pubspec.yaml` / `package.json`: Google Play Billing (`billingclient`, `billing-ktx`,
`in_app_purchase`, `react-native-iap`, RevenueCat) vs other payment SDKs (Stripe, PayPal, Braintree, Adyen, Mollie).
- 🟠 another payment SDK: digital goods and features sold in the app must use Google Play Billing; other payment
  SDKs are fine only for physical goods and services.
- 🟢 Google Play Billing only, or no payment.
Source: https://play.google.com/about/monetization-ads/payments

## 12. Content rating and target audience — ⚪

Answered in Play Console only. If the name or strings contain child-directed words (kid, kids, children, toddler,
preschool, coloring, alphabet), say that the Families rules may apply. Ask who the app is for.
Source: https://support.google.com/googleplay/android-developer/answer/9898843
