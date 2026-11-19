#!/usr/bin/env python3
"""PlayTeam Check — a read-only Google Play pre-release check for Android projects.

Run from the root of an Android project (the folder that holds settings.gradle or settings.gradle.kts):
    python3 check.py [--root <folder>] [--json]
    (Windows: py -3 check.py)

It reads the Gradle files, the manifests, the string resources and the Kotlin/Java/Dart/JS sources, and reports the
12 points of the "12 things to check before you publish on Google Play" checklist. It never writes, builds, installs
or sends anything: no file is changed and no network call is made.

Each point is green (nothing found), orange (to check), red (likely rejection) or "manual" (only Play Console can tell).
Python 3.9+, standard library only. MIT licence, (c) 2026 Delarroc Technologies.
"""
import argparse, json, os, re, sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.dont_write_bytecode = True
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

VERSION = "1.0.0"
REQUIRED_TARGET = 36          # Google Play, new apps and updates since August 31, 2026
SKIP = {"build", ".gradle", ".git", ".idea", "node_modules", ".dart_tool", "Pods", ".cxx", "intermediates"}
A = "{http://schemas.android.com/apk/res/android}"
PACK = "https://playteamdev.gumroad.com"

SRC = {
    1: "https://support.google.com/googleplay/android-developer/answer/14151465",
    2: "https://support.google.com/googleplay/android-developer/answer/11926878",
    3: "https://developer.android.com/guide/practices/page-sizes",
    4: "https://support.google.com/googleplay/android-developer/answer/10144311",
    5: "https://support.google.com/googleplay/android-developer/answer/10787469",
    6: "https://support.google.com/googleplay/android-developer/answer/13327111",
    7: "https://support.google.com/googleplay/android-developer/answer/14115180",
    8: "https://support.google.com/googleplay/android-developer/answer/9888170",
    9: "https://support.google.com/googleplay/android-developer/answer/9898842",
    10: "https://developer.android.com/distribute/marketing-tools/brand-guidelines",
    11: "https://play.google.com/about/monetization-ads/payments",
    12: "https://support.google.com/googleplay/android-developer/answer/9898843",
}
TITLES = {
    1: "Closed test (new personal accounts)", 2: "Target API level", 3: "16 KB memory pages",
    4: "Privacy policy", 5: "Data safety vs the SDKs you ship", 6: "Account deletion",
    7: "Photo and video permissions", 8: "Restricted permissions and foreground services",
    9: "App name", 10: "Google / Android branding", 11: "Payments", 12: "Content rating and target audience",
}

# SDKs that collect or share user data (Data safety must declare them). Pattern on Gradle / pubspec / package.json.
DATA_SDKS = [
    (r"firebase-analytics|firebase_analytics|@react-native-firebase/analytics", "Firebase Analytics"),
    (r"firebase-crashlytics|firebase_crashlytics|@react-native-firebase/crashlytics", "Firebase Crashlytics"),
    (r"firebase-messaging|firebase_messaging|@react-native-firebase/messaging", "Firebase Cloud Messaging"),
    (r"firebase-auth|firebase_auth|@react-native-firebase/auth", "Firebase Authentication"),
    (r"play-services-ads|google_mobile_ads|react-native-google-mobile-ads", "Google Mobile Ads"),
    (r"facebook-android-sdk|facebook-core|flutter_facebook|react-native-fbsdk", "Meta (Facebook) SDK"),
    (r"io\.sentry|sentry_flutter|@sentry/react-native", "Sentry"),
    (r"onesignal", "OneSignal"),
    (r"revenuecat|purchases_flutter|react-native-purchases", "RevenueCat"),
    (r"com\.mapbox|mapbox_maps|@rnmapbox", "Mapbox"),
    (r"appsflyer", "AppsFlyer"), (r"com\.adjust|adjust_sdk", "Adjust"), (r"amplitude", "Amplitude"),
    (r"mixpanel", "Mixpanel"), (r"applovin", "AppLovin"), (r"unity3d\.ads|unity-ads", "Unity Ads"),
    (r"com\.google\.ai\.client|generativeai|firebase-vertexai|firebase-ai|google_generative_ai", "Google Gemini / Firebase AI"),
    (r"com\.openai|openai-java|dart_openai|\"openai\"", "OpenAI"), (r"anthropic", "Anthropic API"),
]
RESTRICTED = {
    "ACCESS_BACKGROUND_LOCATION": "background location", "MANAGE_EXTERNAL_STORAGE": "all files access",
    "QUERY_ALL_PACKAGES": "all package visibility", "READ_SMS": "SMS", "SEND_SMS": "SMS", "RECEIVE_SMS": "SMS",
    "READ_CALL_LOG": "call log", "WRITE_CALL_LOG": "call log", "PROCESS_OUTGOING_CALLS": "call log",
    "USE_EXACT_ALARM": "exact alarms", "USE_FULL_SCREEN_INTENT": "full-screen intents",
    "REQUEST_INSTALL_PACKAGES": "installing packages", "BIND_ACCESSIBILITY_SERVICE": "accessibility service",
}


def walk(root, exts):
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP and not x.startswith(".")]
        for f in files:
            if f.endswith(exts):
                yield Path(d) / f


def read(p):
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def find_root(start):
    p = Path(start).resolve()
    for c in [p, *p.parents]:
        if any((c / n).exists() for n in ("settings.gradle", "settings.gradle.kts", "pubspec.yaml")):
            return c
        if (c / "package.json").exists() and (c / "android").is_dir():
            return c
    return None


class Report:
    def __init__(self):
        self.items = {}

    def set(self, n, status, text, todo=""):
        rank = {"green": 0, "manual": 1, "orange": 2, "red": 3}
        cur = self.items.get(n)
        if cur is None or rank[status] > rank[cur["status"]]:
            self.items[n] = dict(point=n, title=TITLES[n], status=status, finding=text, todo=todo, source=SRC[n])


def target_sdk(gradle_text, props):
    """targetSdk values of the app (literal, gradle.properties, version catalog or a Kotlin constant)."""
    vals = []
    for m in re.finditer(r"(?<![\w.])((?:defaultConfig\.)?targetSdk(?:Version)?)\s*[=(]?\s*([^\s)\n]+)", gradle_text):
        v = m.group(2).strip("\"'")
        v = re.sub(r"\.(get|toInt|toInteger)\b\(?\)?", "", v).rstrip("(")
        if v.isdigit():
            vals.append(int(v))
            continue
        cat = re.match(r"(?:project\.)?libs\.versions\.([\w.]+)", v)
        keys = [cat.group(1).replace(".", "-").lower()] if cat else []
        keys.append(v.split(".")[-1])
        got = next((props[k] for k in keys if str(props.get(k, "")).isdigit()), None)
        if got is None:
            c = re.search(rf"\b{re.escape(v.split('.')[-1])}\s*(?::\s*Int)?\s*=\s*(\d{{2}})\b", gradle_text)
            got = c.group(1) if c else None
        if got is not None:
            vals.append(int(got))
    return vals


def main():
    ap = argparse.ArgumentParser(description="PlayTeam Check: read-only Google Play pre-release check.")
    ap.add_argument("--root", default=".", help="project folder (default: current folder or its parents)")
    ap.add_argument("--json", action="store_true", help="print the results as JSON")
    a = ap.parse_args()
    root = find_root(a.root)
    if root is None:
        print("No Android project found here (no settings.gradle, pubspec.yaml or React Native android/ folder). "
              "Run from the project folder, or pass --root <folder>.")
        return 2

    gradle_files = [p for p in walk(root, (".gradle", ".gradle.kts", ".toml"))]
    gradle_files += [p for p in walk(root, (".kt",))
                     if re.search(r"/(build-logic|buildSrc|build-plugin|gradle-plugins?)/", p.as_posix())]
    gradle = "\n".join(read(p) for p in gradle_files)
    for extra in ("pubspec.yaml", "package.json", "app.json"):
        if (root / extra).exists():
            gradle += "\n" + read(root / extra)
    props = {}
    for p in walk(root, (".properties", ".toml")):
        for m in re.finditer(r"^\s*([\w.-]+)\s*=\s*\"?([^\s\"#]+)", read(p), re.M):
            props[m.group(1).lower()] = m.group(2)
            props[m.group(1).split(".")[-1]] = m.group(2)
    manifests = [p for p in walk(root, ("AndroidManifest.xml",)) if "/test" not in p.as_posix().lower()]
    code = [p for p in walk(root, (".kt", ".java", ".dart", ".js", ".jsx", ".ts", ".tsx"))
            if not re.search(r"/(test|androidTest|__tests__)/", p.as_posix())]
    code_text = "\n".join(read(p) for p in code)
    strings = {}
    names = []  # (priority, app_name): the app module's main resources first
    for p in walk(root, (".xml",)):
        pp = p.as_posix()
        if re.search(r"/res/values/[^/]+\.xml$", pp):
            for m in re.finditer(r'<string name="([^"]+)"[^>]*>(.*?)</string>', read(p), re.S):
                strings.setdefault(m.group(1), m.group(2).strip())
                if m.group(1) == "app_name":
                    rel = p.relative_to(root).as_posix()
                    prio = (0 if re.match(r"(app[\w-]*|android/app)/src/main/", rel) else 1 if "/src/main/" in rel else 2, len(rel))
                    names.append((prio, m.group(2).strip()))
    if names:
        strings["app_name"] = min(names)[1]
    for m in re.finditer(r"resValue\s*\(?\s*[\"']string[\"']\s*,\s*[\"'](\w+)[\"']\s*,\s*[\"']\\?\"?([^\"'\\]+)", gradle):
        strings.setdefault(m.group(1), m.group(2).strip())
    texts = code_text + "\n" + "\n".join(strings.values())
    perms = {}
    services = []
    for mf in manifests:
        try:
            t = ET.parse(mf).getroot()
        except ET.ParseError:
            continue
        for e in t.iter():
            if e.tag in ("uses-permission", "uses-permission-sdk-23"):
                n = (e.get(A + "name") or "").split(".")[-1]
                if n and e.get("{http://schemas.android.com/tools}node") != "remove":
                    perms.setdefault(n, mf.relative_to(root).as_posix())
            if e.tag == "service" and e.get(A + "foregroundServiceType"):
                services.append((e.get(A + "name"), e.get(A + "foregroundServiceType")))
    r = Report()

    # 1. Closed test: only Play Console knows the account type and date.
    r.set(1, "manual", "Can't be read from the code: it depends on your developer account.",
          "Personal account created after November 13, 2023? Run a closed test with 12+ testers opted in for 14 days in a row "
          "before applying for production.")

    # 2. Target API.
    ts = target_sdk(gradle, props)
    if not ts:
        r.set(2, "orange", "targetSdk not found in the Gradle files (set by a plugin or a variable?).",
              f"Check that the release build targets API {REQUIRED_TARGET} or higher.")
    elif min(ts) < REQUIRED_TARGET:
        r.set(2, "red", f"targetSdk {min(ts)} found; Google Play requires {REQUIRED_TARGET} for new apps and updates.",
              f"Set targetSdk = {REQUIRED_TARGET}, then test the app: Android 16 behaviour changes apply.")
    else:
        r.set(2, "green", f"targetSdk {max(ts)}.")

    # 3. 16 KB pages: only native code is concerned.
    so = [p for p in walk(root, (".so",))]
    native = so or re.search(r"externalNativeBuild|ndkVersion|cmake\s*\{", gradle)
    if native:
        r.set(3, "orange", "Native code found" + (f" ({len(so)} .so file(s))" if so else " (NDK / CMake build)") + ".",
              "Check Play Console › App bundle explorer for a \"16 KB\" warning, or build with NDK r28+ / AGP 8.5.1+.")
    else:
        r.set(3, "green", "No native code in the project (an SDK can still bring some: check App bundle explorer).")

    # 4. Privacy policy link in the app.
    pp = re.search(r"https?://[^\s\"'<>)]*(privacy|confidential|datenschutz|privacidad)[^\s\"'<>)]*", texts, re.I)
    if pp:
        r.set(4, "green", f"Privacy policy link found in the app: {pp.group(0)[:90]}")
    else:
        r.set(4, "red", "No privacy policy link found in the app's code or strings.",
              "Publish a public privacy policy page, link it in Play Console and inside the app (Settings or About).")

    # 5. Data safety: SDKs that collect data.
    sdks = sorted({name for pat, name in DATA_SDKS if re.search(pat, gradle, re.I)})
    net = re.search(r"\b(Retrofit|OkHttp|HttpURLConnection|Ktor|Volley|http\.get|fetch\(|axios|Dio\()", code_text)
    if sdks:
        r.set(5, "orange", "SDKs that collect or share data: " + ", ".join(sdks) + ".",
              "Declare what each of them collects in Play Console › App content › Data safety, and name them in your privacy policy.")
    elif net:
        r.set(5, "orange", "No known tracking SDK, but the app makes network calls.",
              "Check what data those calls send and declare it in Data safety (\"No data collected\" only if nothing leaves the device).")
    else:
        r.set(5, "green", "No data-collecting SDK and no obvious network call found.")

    # 6. Account creation without deletion.
    strong = re.search(r"createUserWithEmail|auth\.signUp|\.signUp\(|registerUser|createUserAccount|"
                       r"supabase\.auth\.sign_?[uU]p|Auth0.*signup", texts)
    signup = strong or re.search(r"signIn|sign_in|login|createAccount|create_account|FirebaseAuth|GoogleSignIn|"
                                 r"credentials\.Credential|supabase\.auth|Auth0", texts)
    delete = re.search(r"delete[_ ]?(my[_ ]?)?account|deleteAccount|delete_account|"
                       r"currentUser\??\.delete|deleteUser", texts, re.I)
    if strong and not delete:
        r.set(6, "red", f"Account creation code found ({strong.group(0)}) but no account deletion flow.",
              "Add \"Delete my account\" in the app and a web deletion page declared in Data safety.")
    elif signup and not delete:
        r.set(6, "orange", f"Sign-in code found ({signup.group(0)}), no account deletion flow.",
              "Required only if users can create an account in the app (not when they sign in to an account made elsewhere).")
    elif signup:
        r.set(6, "green", "Accounts and an account deletion flow both found.")
    else:
        r.set(6, "green", "No account creation found.")

    # 7. Photo and video permissions.
    media = [p for p in ("READ_MEDIA_IMAGES", "READ_MEDIA_VIDEO") if p in perms]
    if media:
        picker = re.search(r"PickVisualMedia|ACTION_PICK|GetContent|image_picker", code_text)
        r.set(7, "red" if picker else "orange", ", ".join(media) + " declared" + (" while the app also uses a picker" if picker else "") + ".",
              "Only galleries and editors may keep them: use the Android photo picker for a one-off choice, "
              "or fill in the declaration in Play Console. Check the merged manifest: SDKs can add them.")
    else:
        r.set(7, "green", "No broad photo or video permission in the project's manifests.")

    # 8. Restricted permissions and foreground services.
    found = sorted({f"{p} ({RESTRICTED[p]})" for p in perms if p in RESTRICTED})
    fgs = [f"{n.split('.')[-1] if n else '?'}: {t}" for n, t in services]
    if found:
        r.set(8, "orange", "Restricted permissions: " + ", ".join(found) + ".",
              "Each needs a declaration in Play Console and a core feature that uses it; remove the ones you don't need.")
    if fgs:
        r.set(8, "orange", "Foreground services: " + ", ".join(fgs[:5]) + ".",
              "Declare each foreground service type in App content, with a video showing how the user starts it.")
    if not found and not fgs:
        r.set(8, "green", "No restricted permission or foreground service in the project's manifests.")

    # 9 and 10. App name.
    name = strings.get("app_name") or ""
    lst = list(walk(root, ("title.txt",)))
    store = read(lst[0]).strip() if lst and "fastlane" in lst[0].as_posix() else ""
    shown = store or name
    if not shown:
        r.set(9, "manual", "App name not found (no app_name string, no fastlane title).",
              "Keep the store title under 30 characters, with no ranking, price, promotion or emoji.")
        r.set(10, "manual", "App name not found.", "Don't put \"Android\" or \"Google\" in the name; write \"for Android\".")
    else:
        issues = []
        if len(shown) > 30:
            issues.append(f"{len(shown)} characters (max 30)")
        if re.search(r"#1|\bbest\b|\bfree\b|\bnew\b|\bsale\b|% off|\btop\b", shown, re.I):
            issues.append("ranking, promotion or price word")
        if re.search(r"[\U0001F300-\U0001FAFF☀-➿]", shown):
            issues.append("emoji")
        if len(shown) > 4 and shown.isupper():
            issues.append("ALL CAPS (fine only if it is your brand)")
        if issues:
            r.set(9, "orange", f"\"{shown}\": " + ", ".join(issues) + ".", "Shorten it and keep it descriptive.")
        else:
            r.set(9, "green", f"\"{shown}\".")
        if re.search(r"\b(android|google|play store)\b", shown, re.I) and not re.search(r"\bfor android\b", shown, re.I):
            r.set(10, "orange", f"\"{shown}\" uses a Google brand in the name.", "Write \"for Android\" after your own name, or remove the brand.")
        else:
            r.set(10, "green", "No Google brand at the start of the app name.")

    # 11. Payments.
    billing = re.search(r"billingclient|billing-ktx|in_app_purchase|react-native-iap|revenuecat|purchases_flutter", gradle, re.I)
    other = re.search(r"stripe|paypal|braintree|adyen|mollie", gradle, re.I)
    if other:
        r.set(11, "orange", f"Payment SDK found: {other.group(0)}" + (" (with Google Play Billing too)." if billing else "."),
              "Digital content and subscriptions must go through Google Play Billing (or an enrolled program); "
              "other payment SDKs are fine only for physical goods and off-app services.")
    elif billing:
        r.set(11, "green", "Google Play Billing used for in-app purchases.")
    else:
        r.set(11, "green", "No in-app payment found.")

    # 12. Content rating and target audience.
    kids = re.search(r"\b(kids?|children|toddler|preschool|coloring|alphabet)\b", " ".join(strings.values()) + " " + shown, re.I)
    r.set(12, "manual", "Answered in Play Console only." + (f" Child-directed words found (\"{kids.group(0)}\"): the Families rules may apply." if kids else ""),
          "Fill in the content rating questionnaire and Target audience and content honestly.")

    items = [r.items[n] for n in sorted(r.items)]
    if a.json:
        print(json.dumps(dict(version=VERSION, project=str(root), points=items), indent=2, ensure_ascii=False))
        return 0
    icon = {"green": "🟢", "orange": "🟠", "red": "🔴", "manual": "⚪"}
    print(f"PlayTeam Check {VERSION} — {root.name}  (read-only: nothing was changed)\n")
    for i in items:
        print(f"{icon[i['status']]} {i['point']:>2}. {i['title']}: {i['finding']}")
        if i["todo"] and i["status"] != "green":
            print(f"       → {i['todo']}")
    c = {s: sum(1 for i in items if i["status"] == s) for s in icon}
    print(f"\nScore: {c['green']} green · {c['orange']} to check · {c['red']} likely rejection · {c['manual']} to confirm in Play Console")
    print("Sources: the official Google page for each point is in the JSON output (--json).")
    print(f"\nThis is a quick scan of 12 points. The full PlayTeam pack audits and fixes everything before each release "
          f"(security, Google Play rules, legal, UI, translations, quality, store listing, release): {PACK}")
    return 1 if c["red"] else 0


if __name__ == "__main__":
    sys.exit(main())
