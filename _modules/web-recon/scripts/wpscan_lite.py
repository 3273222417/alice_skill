#!/usr/bin/env python3
"""
wpscan_lite.py — WordPress security scanner (fallback when wpscan is not installed)
Tests essential WordPress security checks with no external dependencies.
"""

import argparse
import json
import re
import sys
import urllib.request
import urllib.error
import urllib.parse
import ssl
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

SSL_CTX = ssl.create_default_context()
SSL_CTX.check_hostname = False
SSL_CTX.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

TIMEOUT = 10

# ─── VULNERABLE VERSIONS ──────────────────────────────────────────────────────
VULNERABLE_VERSIONS = {
    "3.": "EOL — multiple RCE, SQLi, XSS",
    "4.0": "EOL — persistent XSS (CVE-2015-3440)",
    "4.1": "EOL — XSS, CSRF",
    "4.2": "EOL — persistent XSS (CVE-2015-3440)",
    "4.3": "EOL — privilege escalation",
    "4.4": "EOL — SSRF, XSS",
    "4.5": "EOL — SSRF (CVE-2016-6896)",
    "4.6": "EOL — RCE via PHPMailer (CVE-2016-10033)",
    "4.7": "EOL — REST API privilege escalation (CVE-2017-1001000) — CRITICAL",
    "4.8": "EOL — SQLi, XSS",
    "4.9": "EOL — multiple XSS",
    "5.0": "EOL — file manager RCE if Crop Image exposed",
    "5.1": "EOL — CSRF to RCE",
    "5.2": "EOL — XSS in Customizer",
    "5.3": "EOL — stored XSS",
    "5.4": "EOL — object injection",
    "5.5": "EOL — DoS, XSS",
    "5.6": "EOL — XXE via ID3 tags",
    "5.7": "EOL — XSS",
    "5.8": "EOL — SQL injection via WP_Query (CVE-2022-21661)",
    "5.9": "EOL — stored XSS",
    "6.0": "Check security bulletins — multiple security patches",
    "6.1": "Check security bulletins",
    "6.2": "Check security bulletins",
    "6.3": "Check security bulletins — SQLi in WP_Query (CVE-2023-22622)",
    "6.4": "Check security bulletins",
}

# ─── SENSITIVE PATHS ──────────────────────────────────────────────────────────
SENSITIVE_PATHS = [
    # Admin and login
    ("/wp-login.php", "high", "Login page exposed"),
    ("/wp-admin/", "medium", "Admin panel (redirects to login)"),
    ("/wp-admin/admin-ajax.php", "info", "admin-ajax.php accessible"),
    # Version / info
    ("/readme.html", "high", "readme.html exposed — reveals WP version"),
    ("/license.txt", "low", "license.txt exposed"),
    ("/wp-includes/version.php", "medium", "version.php accessible"),
    # XML-RPC
    ("/xmlrpc.php", "high", "xmlrpc.php exposed — brute force and SSRF vector"),
    # wp-config backups
    ("/wp-config.php.bak", "critical", "wp-config backup exposed — DB credentials"),
    ("/wp-config.php~", "critical", "wp-config backup (tilde) — DB credentials"),
    ("/wp-config.php.old", "critical", "wp-config backup (.old) — DB credentials"),
    ("/wp-config.bak", "critical", "wp-config backup (.bak) — DB credentials"),
    ("/wp-config-backup.php", "critical", "wp-config-backup exposed"),
    ("/.wp-config.php.swp", "critical", "vim swap file for wp-config"),
    # Debug / logs
    ("/wp-content/debug.log", "high", "debug.log exposed — stack traces and internal data"),
    ("/debug.log", "high", "debug.log in root"),
    ("/wp-content/uploads/", "medium", "uploads directory listing"),
    # Installation
    ("/wp-admin/install.php", "critical", "Installation script accessible — CRITICAL"),
    ("/wp-admin/setup-config.php", "high", "Setup config accessible"),
    # Exports / backups
    ("/wp-content/backup-db/", "critical", "Database backup exposed"),
    ("/wp-content/backups/", "high", "Backups directory exposed"),
    ("/wp-content/uploads/backup/", "high", "Backup in uploads directory"),
    # Plugins info
    ("/wp-content/plugins/", "medium", "Plugins directory listing"),
    # phpinfo
    ("/phpinfo.php", "high", "phpinfo exposed"),
    ("/wp-admin/phpinfo.php", "high", "phpinfo in admin"),
]

# ─── VULNERABLE PLUGINS ───────────────────────────────────────────────────────
VULNERABLE_PLUGINS = [
    ("contact-form-7", "Contact Form 7 — historic XSS, file upload bypass"),
    ("woocommerce", "WooCommerce — multiple SQLi/XSS by version"),
    ("yoast-seo", "Yoast SEO — stored XSS (CVE-2021-25118)"),
    ("elementor", "Elementor — RCE/file upload (CVE-2022-1329)"),
    ("wordfence", "Wordfence — presence confirmation"),
    ("wp-super-cache", "WP Super Cache — historic RCE (CVE-2021-24209)"),
    ("w3-total-cache", "W3 Total Cache — SSRF, info disclosure"),
    ("duplicator", "Duplicator — path traversal (CVE-2020-11738) — CRITICAL"),
    ("ninja-forms", "Ninja Forms — SQLi, email injection"),
    ("gravityforms", "Gravity Forms — file upload bypass"),
    ("wp-file-manager", "WP File Manager — unauthenticated RCE (CVE-2020-25213) — CRITICAL"),
    ("ultimate-member", "Ultimate Member — privilege escalation (CVE-2023-3460)"),
    ("advanced-custom-fields", "ACF — stored XSS (CVE-2023-30777)"),
    ("all-in-one-seo-pack", "All in One SEO — privilege escalation (CVE-2021-25036)"),
    ("akismet", "Akismet — presence confirmation"),
    ("jetpack", "Jetpack — multiple XSS/SQLi by version"),
    ("wpforms-lite", "WPForms — info disclosure"),
    ("mailpoet", "MailPoet — historic RCE (CVE-2014-5460)"),
    ("revslider", "Revolution Slider — LFI/RCE (CVE-2014-9734) — CRITICAL"),
    ("wp-symposium", "WP Symposium — historic critical SQLi"),
    ("timthumb", "TimThumb — classic RCE (CVE-2011-4106)"),
]


def fetch(url, method="GET", timeout=TIMEOUT):
    try:
        req = urllib.request.Request(url, headers=HEADERS, method=method)
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            body = resp.read(16384).decode("utf-8", errors="replace")
            return resp.status, dict(resp.headers), body
    except urllib.error.HTTPError as e:
        return e.code, {}, ""
    except Exception:
        return 0, {}, ""


def normalize_url(url):
    url = url.strip().rstrip("/")
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


# ─── CHECKS ───────────────────────────────────────────────────────────────────

def check_is_wordpress(base):
    code, _, body = fetch(base + "/")
    indicators = ["wp-content", "wp-includes", "wordpress", "/wp-json/", "wp-emoji"]
    hits = sum(1 for i in indicators if i in body.lower())
    if hits >= 2:
        return True
    code2, _, _ = fetch(base + "/wp-login.php")
    return code2 == 200


def detect_version(base):
    sources = [
        (base + "/", r'<meta name="generator" content="WordPress ([\d.]+)"'),
        (base + "/readme.html", r'<br />\s*([\d.]+)\s*</h1>|Version ([\d.]+)'),
        (base + "/?feed=rss2", r'<generator>https?://wordpress\.org/\?v=([\d.]+)</generator>'),
        (base + "/wp-includes/version.php", r"\$wp_version\s*=\s*'([\d.]+)'"),
        (base + "/wp-json/", r'"version":"([\d.]+)"'),
        (base + "/wp-sitemap.xml", r'WordPress/([\d.]+)'),
    ]
    for url, pattern in sources:
        code, _, body = fetch(url)
        if body:
            m = re.search(pattern, body, re.IGNORECASE)
            if m:
                version = next((g for g in m.groups() if g), None)
                if version:
                    return version.strip(), url
    return None, None


def check_xmlrpc(base):
    url = base + "/xmlrpc.php"
    code_get, _, body_get = fetch(url)
    if code_get == 405 or "XML-RPC server accepts POST requests only" in body_get:
        return True, "Active (responds to POST requests)"
    if code_get == 200 and "xmlrpc" in body_get.lower():
        return True, "Active"
    if code_get == 200:
        return True, "HTTP 200 — verify manually"
    return False, None


def check_user_enum_rest(base):
    users = []
    urls = [
        base + "/wp-json/wp/v2/users",
        base + "/wp-json/wp/v2/users?per_page=100",
        base + "/?rest_route=/wp/v2/users",
    ]
    for url in urls:
        code, _, body = fetch(url)
        if code == 200 and '"slug"' in body:
            try:
                data = json.loads(body)
                for u in data[:10]:
                    users.append({
                        "id": u.get("id"),
                        "slug": u.get("slug"),
                        "name": u.get("name"),
                        "link": u.get("link"),
                    })
                return users, url
            except Exception:
                pass
    return [], None


def check_user_enum_author(base):
    users = []
    for i in range(1, 6):
        url = base + f"/?author={i}"
        code, headers, _ = fetch(url)
        location = headers.get("Location", "") or headers.get("location", "")
        if code in (301, 302) and "/author/" in location:
            m = re.search(r"/author/([^/]+)", location)
            if m:
                users.append({"id": i, "username": m.group(1)})
    return users


def check_debug_mode(base):
    code, _, body = fetch(base + "/wp-content/debug.log")
    if code == 200 and len(body) > 10:
        return True, "debug.log exposed at /wp-content/debug.log"
    _, _, home_body = fetch(base + "/")
    if re.search(r"(PHP (Warning|Notice|Fatal error|Deprecated)|WP_DEBUG)", home_body):
        return True, "PHP errors visible on homepage (WP_DEBUG likely active)"
    return False, None


def check_registration(base):
    code, _, body = fetch(base + "/wp-login.php?action=register")
    if code == 200 and ("register" in body.lower() or "registration" in body.lower()):
        if "Registration is not allowed" not in body and "disabled" not in body.lower():
            return True
    return False


def check_sensitive_paths(base):
    findings = []

    def probe(item):
        path, severity, desc = item
        url = base + path
        code, _, body = fetch(url)
        if code == 200:
            return {"url": url, "status": 200, "severity": severity, "description": desc, "body_size": len(body)}
        elif code == 403:
            return {"url": url, "status": 403, "severity": "info", "description": desc + " (exists, 403)"}
        elif code in (301, 302):
            return {"url": url, "status": code, "severity": "info", "description": desc + " (redirect)"}
        return None

    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = {ex.submit(probe, item): item for item in SENSITIVE_PATHS}
        for f in as_completed(futures):
            r = f.result()
            if r:
                findings.append(r)

    return sorted(findings, key=lambda x: {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}.get(x["severity"], 5))


def check_plugins(base):
    found = []

    def probe(item):
        slug, desc = item
        url = base + f"/wp-content/plugins/{slug}/"
        code, _, _ = fetch(url)
        if code in (200, 403):
            _, _, readme = fetch(base + f"/wp-content/plugins/{slug}/readme.txt")
            version = None
            m = re.search(r"Stable tag:\s*([\d.]+)", readme, re.IGNORECASE)
            if m:
                version = m.group(1)
            return {"slug": slug, "status": code, "version": version, "description": desc}
        return None

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(probe, item): item for item in VULNERABLE_PLUGINS}
        for f in as_completed(futures):
            r = f.result()
            if r:
                found.append(r)

    return found


def check_themes(base):
    _, _, body = fetch(base + "/")
    m = re.search(r'/wp-content/themes/([^/]+)/', body)
    if m:
        theme_slug = m.group(1)
        _, _, css = fetch(base + f"/wp-content/themes/{theme_slug}/style.css")
        version = None
        vm = re.search(r"Version:\s*([\d.]+)", css)
        if vm:
            version = vm.group(1)
        return theme_slug, version
    return None, None


def check_security_headers(base):
    _, headers, _ = fetch(base + "/")
    headers_lower = {k.lower(): v for k, v in headers.items()}
    missing = []
    for h in ["x-content-type-options", "x-frame-options", "content-security-policy",
              "strict-transport-security", "referrer-policy", "permissions-policy"]:
        if h not in headers_lower:
            missing.append(h)
    return missing


def check_rest_api(base):
    code, _, body = fetch(base + "/wp-json/")
    if code == 200 and "routes" in body:
        return True, "REST API fully accessible — exposes endpoints and namespaces"
    code2, _, body2 = fetch(base + "/?rest_route=/")
    if code2 == 200 and "routes" in body2:
        return True, "REST API exposed via ?rest_route="
    return False, None


def check_wp_cron(base):
    code, _, body = fetch(base + "/wp-cron.php")
    return code == 200


def check_wlwmanifest(base):
    code, _, _ = fetch(base + "/wlwmanifest.xml")
    return code == 200


# ─── REPORT ───────────────────────────────────────────────────────────────────

SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
SEV_LABEL = {
    "critical": "[CRITICAL]",
    "high":     "[HIGH]    ",
    "medium":   "[MEDIUM]  ",
    "low":      "[LOW]     ",
    "info":     "[INFO]    ",
}


def run_scan(target, output_path=None):
    base = normalize_url(target)
    report = {
        "target": base,
        "scan_date": datetime.now().isoformat(),
        "scanner": "wpscan_lite.py",
        "is_wordpress": False,
        "version": None,
        "version_source": None,
        "vulnerable_version": None,
        "debug_mode": False,
        "debug_detail": None,
        "xmlrpc": False,
        "xmlrpc_detail": None,
        "rest_api_exposed": False,
        "rest_api_detail": None,
        "users_rest": [],
        "users_author": [],
        "registration_open": False,
        "wp_cron_public": False,
        "active_theme": None,
        "theme_version": None,
        "sensitive_paths": [],
        "plugins_found": [],
        "security_headers_missing": [],
        "findings_summary": [],
    }

    print("=" * 62)
    print("  wpscan_lite.py — WordPress Security Scanner (fallback)")
    print(f"  Target : {base}")
    print(f"  Date   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 62)

    def add_finding(severity, title, detail=""):
        report["findings_summary"].append({"severity": severity, "title": title, "detail": detail})

    # 1. Confirm WordPress
    print("\n[*] Checking if target is WordPress...")
    report["is_wordpress"] = check_is_wordpress(base)
    if not report["is_wordpress"]:
        print("[-] Does not appear to be WordPress. Continuing anyway...")
    else:
        print("[+] WordPress detected!")

    # 2. Version
    print("\n[*] Detecting version...")
    version, vsource = detect_version(base)
    report["version"] = version
    report["version_source"] = vsource
    if version:
        print(f"[+] Version: {version}  (via {vsource})")
        for prefix, vuln in VULNERABLE_VERSIONS.items():
            if version.startswith(prefix):
                report["vulnerable_version"] = vuln
                print(f"  {SEV_LABEL['critical']} WordPress {version} VULNERABLE: {vuln}")
                add_finding("critical", f"WordPress {version} vulnerable", vuln)
                break
        if not report["vulnerable_version"]:
            print(f"  {SEV_LABEL['info']} Version {version} — check if latest minor")
    else:
        print("[-] Version not detected")

    # 3. XML-RPC
    print("\n[*] Testing xmlrpc.php...")
    xmlrpc, xmlrpc_detail = check_xmlrpc(base)
    report["xmlrpc"] = xmlrpc
    report["xmlrpc_detail"] = xmlrpc_detail
    if xmlrpc:
        print(f"  {SEV_LABEL['high']} xmlrpc.php EXPOSED: {xmlrpc_detail}")
        print(f"    → Allows amplified brute force and potential SSRF")
        add_finding("high", "xmlrpc.php exposed", xmlrpc_detail)
    else:
        print("[+] xmlrpc.php not accessible")

    # 4. REST API
    print("\n[*] Checking REST API...")
    rest_exposed, rest_detail = check_rest_api(base)
    report["rest_api_exposed"] = rest_exposed
    report["rest_api_detail"] = rest_detail
    if rest_exposed:
        print(f"  {SEV_LABEL['medium']} {rest_detail}")
        add_finding("medium", "REST API exposed", rest_detail)

    # 5. User enumeration
    print("\n[*] Enumerating users (REST API + ?author=)...")
    users_rest, rest_url = check_user_enum_rest(base)
    report["users_rest"] = users_rest
    if users_rest:
        print(f"  {SEV_LABEL['high']} {len(users_rest)} user(s) via REST API ({rest_url}):")
        for u in users_rest[:5]:
            print(f"    → ID {u['id']}: {u['slug']} / {u['name']}")
        add_finding("high", f"User enumeration via REST API ({len(users_rest)} users)", str([u['slug'] for u in users_rest[:5]]))

    users_author = check_user_enum_author(base)
    report["users_author"] = users_author
    if users_author and not users_rest:
        print(f"  {SEV_LABEL['medium']} {len(users_author)} user(s) via ?author=N:")
        for u in users_author:
            print(f"    → ID {u['id']}: {u['username']}")
        add_finding("medium", f"User enumeration via ?author= ({len(users_author)} users)", str([u['username'] for u in users_author]))

    if not users_rest and not users_author:
        print("[+] No users enumerated")

    # 6. Debug mode
    print("\n[*] Checking debug mode...")
    debug, debug_detail = check_debug_mode(base)
    report["debug_mode"] = debug
    report["debug_detail"] = debug_detail
    if debug:
        print(f"  {SEV_LABEL['high']} Debug mode active: {debug_detail}")
        add_finding("high", "WP_DEBUG active", debug_detail)
    else:
        print("[+] Debug mode not detected")

    # 7. Sensitive paths
    print("\n[*] Checking sensitive paths...")
    sensitive = check_sensitive_paths(base)
    report["sensitive_paths"] = sensitive
    high_paths = [p for p in sensitive if p["severity"] in ("critical", "high")]
    if sensitive:
        print(f"  Found {len(sensitive)} paths ({len(high_paths)} critical/high):")
        for p in sensitive:
            if p["severity"] in ("critical", "high", "medium"):
                print(f"  {SEV_LABEL.get(p['severity'], '[INFO]    ')} [{p['status']}] {p['url']}")
                print(f"    → {p['description']}")
                if p["severity"] in ("critical", "high"):
                    add_finding(p["severity"], p["description"], p["url"])
    else:
        print("[+] No sensitive paths found")

    # 8. Plugins
    print("\n[*] Detecting installed plugins...")
    plugins = check_plugins(base)
    report["plugins_found"] = plugins
    if plugins:
        print(f"  {len(plugins)} plugin(s) detected:")
        for p in plugins:
            version_str = f" v{p['version']}" if p.get("version") else ""
            print(f"  {SEV_LABEL['medium']} {p['slug']}{version_str} — {p['description']}")
        add_finding("medium", f"{len(plugins)} known vulnerable plugins detected", str([p["slug"] for p in plugins]))
    else:
        print("[+] No common vulnerable plugins detected")

    # 9. Active theme
    print("\n[*] Detecting active theme...")
    theme, theme_ver = check_themes(base)
    report["active_theme"] = theme
    report["theme_version"] = theme_ver
    if theme:
        print(f"  {SEV_LABEL['info']} Theme: {theme}" + (f" v{theme_ver}" if theme_ver else ""))

    # 10. Open registration
    print("\n[*] Checking user registration...")
    report["registration_open"] = check_registration(base)
    if report["registration_open"]:
        print(f"  {SEV_LABEL['medium']} Registration OPEN — possible account creation")
        add_finding("medium", "Open user registration", "/wp-login.php?action=register")
    else:
        print("[+] Registration closed or not detected")

    # 11. wp-cron public
    print("\n[*] Checking wp-cron.php...")
    report["wp_cron_public"] = check_wp_cron(base)
    if report["wp_cron_public"]:
        print(f"  {SEV_LABEL['low']} wp-cron.php publicly accessible (potential DoS via repeated requests)")
        add_finding("low", "wp-cron.php public", "Potential DoS via repeated calls")

    # 12. wlwmanifest
    wlw = check_wlwmanifest(base)
    if wlw:
        print(f"\n  {SEV_LABEL['info']} wlwmanifest.xml exposed (confirms WordPress)")

    # 13. Security headers
    print("\n[*] Checking security headers...")
    missing_h = check_security_headers(base)
    report["security_headers_missing"] = missing_h
    if missing_h:
        print(f"  {SEV_LABEL['low']} Missing headers: {', '.join(missing_h)}")
    else:
        print("[+] Security headers present")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 62)
    print("  FINDINGS SUMMARY")
    print("=" * 62)
    findings_sorted = sorted(report["findings_summary"], key=lambda x: SEV_ORDER.get(x["severity"], 9))
    for f in findings_sorted:
        print(f"  {SEV_LABEL.get(f['severity'], '[INFO]    ')} {f['title']}")
        if f["detail"]:
            print(f"              {f['detail'][:100]}")
    print(f"\n  Total: {len(findings_sorted)} finding(s)")
    print("=" * 62)

    if output_path:
        with open(output_path, "w") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
        print(f"\n[+] JSON report saved to: {output_path}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="wpscan_lite.py — WordPress scanner with no external dependencies"
    )
    parser.add_argument("--url", "-u", required=True, help="Target URL")
    parser.add_argument("--output", "-o", help="Save JSON report")
    parser.add_argument("--timeout", "-t", type=int, default=10, help="HTTP timeout (seconds)")
    args = parser.parse_args()

    global TIMEOUT
    TIMEOUT = args.timeout

    run_scan(args.url, args.output)


if __name__ == "__main__":
    main()
