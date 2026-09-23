#!/usr/bin/env python3
"""
joomscan.py — Joomla security scanner
Tests the most important Joomla security checks with no external dependencies.
Inspired by JoomScan (OWASP), rewritten in pure Python.
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
    "1.5": "EOL - multiple RCE (CVE-2015-8562, CVE-2013-3242)",
    "2.5": "EOL - SQL Injection, XSS (CVE-2015-8769, CVE-2013-1453)",
    "3.0": "EOL - multiple critical CVEs",
    "3.1": "EOL - object injection (CVE-2015-8566)",
    "3.2": "EOL - SQL injection (CVE-2014-7228)",
    "3.3": "EOL - XSS, CSRF",
    "3.4": "EOL - RCE (CVE-2015-8562 variant)",
    "3.5": "EOL",
    "3.6": "EOL - privilege escalation (CVE-2016-9838)",
    "3.7": "Critical SQL Injection (CVE-2017-8917)",
    "3.8": "multiple XSS",
    "3.9": "open redirect, XSS",
    "4.0": "information disclosure (CVE-2021-23132)",
    "4.1": "SSTI/RCE (CVE-2023-23752) — unauthenticated API leak",
    "4.2": "CVE-2023-23752 — sensitive data exposure via /api/",
    "5.0": "check recent security bulletins",
}

# ─── SENSITIVE PATHS ──────────────────────────────────────────────────────────
SENSITIVE_PATHS = [
    # Admin
    ("/administrator/", "Admin panel exposed"),
    ("/administrator/index.php", "Admin login"),
    # Config backups
    ("/configuration.php.bak", "PHP configuration backup"),
    ("/configuration.php~", "PHP configuration backup (tilde)"),
    ("/configuration.php.old", "PHP configuration backup (.old)"),
    ("/config.php.bak", "Alternate config backup"),
    # Info files
    ("/README.txt", "README exposed (reveals version)"),
    ("/CHANGELOG.txt", "Changelog exposed (reveals version)"),
    ("/htaccess.txt", "htaccess.txt exposed"),
    ("/web.config.txt", "web.config.txt exposed"),
    ("/joomla.xml", "joomla.xml exposed"),
    # Installation
    ("/installation/", "Installation directory exposed — CRITICAL"),
    ("/installation/index.php", "Installation script accessible — CRITICAL"),
    # Log / backup
    ("/administrator/logs/", "Admin logs exposed"),
    ("/logs/", "Logs directory exposed"),
    ("/cache/", "Cache directory exposed"),
    ("/tmp/", "Tmp directory exposed"),
    # Upload
    ("/images/stories/", "Legacy upload directory"),
    ("/media/", "Media directory"),
    # Database
    ("/administrator/manifests/files/joomla.xml", "Manifest XML (reveals exact version)"),
    # phpinfo / debug
    ("/phpinfo.php", "phpinfo exposed"),
    ("/test.php", "test.php exposed"),
    # API (CVE-2023-23752)
    ("/api/index.php/v1/config/application?public=true", "API config leak (CVE-2023-23752)"),
    ("/api/index.php/v1/users?public=true", "User enumeration via API"),
]

# ─── VULNERABLE EXTENSIONS ────────────────────────────────────────────────────
VULNERABLE_EXTENSIONS = [
    ("/components/com_users/", "com_users — historic SQL injection"),
    ("/components/com_contact/", "com_contact — multiple XSS"),
    ("/components/com_content/", "com_content — open redirect"),
    ("/components/com_search/", "com_search — XSS"),
    ("/components/com_weblinks/", "com_weblinks — legacy SQL injection"),
    ("/components/com_virtuemart/", "VirtueMart — SQL injection (CVE-2016-10033)"),
    ("/components/com_akeeba/", "Akeeba Backup — historic file disclosure"),
    ("/components/com_jce/", "JCE Editor — RCE (CVE-2012-1563, multiple)"),
    ("/components/com_jdownloads/", "JDownloads — historic LFI"),
    ("/components/com_k2/", "K2 — SQL injection, XSS"),
    ("/components/com_rsform/", "RSForm — SQL injection"),
    ("/components/com_foxcontact/", "FoxContact — SQL injection"),
    ("/plugins/system/debug/", "Debug plugin exposed"),
    ("/plugins/authentication/ldap/", "LDAP auth plugin (injection risk)"),
]


def fetch(url, timeout=TIMEOUT):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as resp:
            body = resp.read(8192).decode("utf-8", errors="replace")
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

def check_is_joomla(base):
    indicators = ["/administrator/", "/components/", "/modules/"]
    hits = 0
    for path in indicators:
        code, _, body = fetch(base + path)
        if code in (200, 301, 302, 403):
            hits += 1
        if "joomla" in body.lower():
            hits += 2
    return hits >= 2


def detect_version(base):
    sources = [
        (base + "/administrator/manifests/files/joomla.xml", r"<version>([^<]+)</version>"),
        (base + "/language/en-GB/en-GB.xml", r"<version>([^<]+)</version>"),
        (base + "/CHANGELOG.txt", r"Joomla!\s+([\d.]+)"),
        (base + "/README.txt", r"Joomla!\s+([\d.]+)"),
        (base + "/", r'content="Joomla!\s*([\d.]+)'),
    ]
    for url, pattern in sources:
        code, _, body = fetch(url)
        if code == 200 and body:
            m = re.search(pattern, body, re.IGNORECASE)
            if m:
                return m.group(1).strip(), url
    return None, None


def check_debug_mode(base):
    code, _, body = fetch(base + "/")
    if "joomla-version" in body.lower() or "Joomla! Debug Console" in body:
        return True
    if re.search(r"(Call Stack|Stack trace|jdebug)", body):
        return True
    return False


def check_security_headers(base):
    code, headers, _ = fetch(base + "/")
    missing = []
    wanted = [
        ("X-Content-Type-Options", "nosniff"),
        ("X-Frame-Options", None),
        ("X-XSS-Protection", None),
        ("Content-Security-Policy", None),
        ("Strict-Transport-Security", None),
        ("Referrer-Policy", None),
    ]
    headers_lower = {k.lower(): v for k, v in headers.items()}
    for header, _ in wanted:
        if header.lower() not in headers_lower:
            missing.append(header)
    return missing


def check_user_enum_api(base):
    users_found = []
    urls_to_try = [
        base + "/api/index.php/v1/users?public=true",
        base + "/api/users",
    ]
    for url in urls_to_try:
        code, _, body = fetch(url)
        if code == 200 and ("username" in body or "email" in body):
            try:
                data = json.loads(body)
                items = data.get("data", [])
                for item in items[:10]:
                    attrs = item.get("attributes", {})
                    user = attrs.get("username") or attrs.get("name", "")
                    email = attrs.get("email", "")
                    if user:
                        users_found.append({"username": user, "email": email})
            except Exception:
                users_found.append({"raw": body[:200]})
            break
    return users_found


def check_api_config_leak(base):
    url = base + "/api/index.php/v1/config/application?public=true"
    code, _, body = fetch(url)
    if code == 200 and len(body) > 50:
        leaked = {}
        try:
            data = json.loads(body)
            attrs = (data.get("data") or [{}])
            if isinstance(attrs, list) and attrs:
                leaked = attrs[0].get("attributes", {})
            elif isinstance(attrs, dict):
                leaked = attrs.get("attributes", {})
        except Exception:
            pass
        sensitive_keys = ["password", "db", "host", "user", "secret", "key", "mail"]
        found = {k: v for k, v in leaked.items()
                 if any(s in k.lower() for s in sensitive_keys)}
        return True, found if found else {"response_size": len(body)}
    return False, {}


def check_sensitive_paths(base):
    findings = []

    def probe(path_desc):
        path, desc = path_desc
        url = base + path
        code, _, body = fetch(url)
        if code == 200:
            return {"url": url, "status": code, "description": desc, "severity": "high"}
        elif code in (301, 302):
            return {"url": url, "status": code, "description": desc + " (redirect)", "severity": "info"}
        elif code == 403:
            return {"url": url, "status": code, "description": desc + " (exists but forbidden)", "severity": "medium"}
        return None

    with ThreadPoolExecutor(max_workers=15) as ex:
        futures = {ex.submit(probe, pd): pd for pd in SENSITIVE_PATHS}
        for f in as_completed(futures):
            result = f.result()
            if result:
                findings.append(result)

    return sorted(findings, key=lambda x: {"high": 0, "medium": 1, "info": 2}[x["severity"]])


def check_extensions(base):
    findings = []

    def probe(path_desc):
        path, desc = path_desc
        url = base + path
        code, _, _ = fetch(url)
        if code in (200, 403):
            return {"url": url, "status": code, "description": desc}
        return None

    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(probe, pd): pd for pd in VULNERABLE_EXTENSIONS}
        for f in as_completed(futures):
            result = f.result()
            if result:
                findings.append(result)

    return findings


def check_registration_open(base):
    code, _, body = fetch(base + "/index.php?option=com_users&view=registration")
    if code == 200 and ("registration" in body.lower() or "register" in body.lower()):
        return True
    return False


def check_admin_bruteforce_protection(base):
    code, headers, body = fetch(base + "/administrator/index.php")
    has_captcha = "captcha" in body.lower() or "recaptcha" in body.lower()
    has_2fa_mention = "two-factor" in body.lower() or "2fa" in body.lower()
    return {
        "login_accessible": code == 200,
        "captcha_present": has_captcha,
        "2fa_mention": has_2fa_mention,
    }


# ─── REPORT ───────────────────────────────────────────────────────────────────

def print_banner(target):
    print("=" * 60)
    print(f"  joomscan.py — Joomla Security Scanner")
    print(f"  Target : {target}")
    print(f"  Date   : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)


def severity_label(sev):
    labels = {"critical": "[CRITICAL]", "high": "[HIGH]   ", "medium": "[MEDIUM] ", "low": "[LOW]    ", "info": "[INFO]   "}
    return labels.get(sev, "[INFO]   ")


def run_scan(target, output_path=None):
    base = normalize_url(target)
    report = {
        "target": base,
        "scan_date": datetime.now().isoformat(),
        "is_joomla": False,
        "version": None,
        "version_source": None,
        "vulnerable_version": None,
        "debug_mode": False,
        "security_headers_missing": [],
        "sensitive_paths": [],
        "vulnerable_extensions": [],
        "api_config_leak": False,
        "api_config_data": {},
        "users_via_api": [],
        "registration_open": False,
        "admin_protection": {},
        "findings_summary": [],
    }

    print_banner(base)

    # 1. Verify Joomla
    print("\n[*] Checking if target is Joomla...")
    report["is_joomla"] = check_is_joomla(base)
    if not report["is_joomla"]:
        print("[-] Does not appear to be a Joomla site. Continuing anyway...")
    else:
        print("[+] Joomla detected!")

    # 2. Version
    print("\n[*] Detecting version...")
    version, vsource = detect_version(base)
    report["version"] = version
    report["version_source"] = vsource
    if version:
        print(f"[+] Version detected: {version} (via {vsource})")
        for vprefix, vuln_desc in VULNERABLE_VERSIONS.items():
            if version.startswith(vprefix):
                report["vulnerable_version"] = vuln_desc
                print(f"  {severity_label('critical')} Version {version} is VULNERABLE: {vuln_desc}")
                report["findings_summary"].append({
                    "severity": "critical",
                    "title": f"Joomla {version} vulnerable",
                    "detail": vuln_desc,
                })
                break
    else:
        print("[-] Version not detected automatically")

    # 3. Debug mode
    print("\n[*] Checking debug mode...")
    report["debug_mode"] = check_debug_mode(base)
    if report["debug_mode"]:
        print(f"  {severity_label('high')} Debug mode ACTIVE — exposes internal information")
        report["findings_summary"].append({"severity": "high", "title": "Debug mode active", "detail": "Exposes stack traces and internal data"})
    else:
        print("[+] Debug mode not detected")

    # 4. CVE-2023-23752 — API config leak
    print("\n[*] Testing CVE-2023-23752 (API config leak)...")
    leaked, leak_data = check_api_config_leak(base)
    report["api_config_leak"] = leaked
    report["api_config_data"] = leak_data
    if leaked:
        print(f"  {severity_label('critical')} CVE-2023-23752 CONFIRMED — configuration data exposed via API!")
        if leak_data:
            print(f"    Leaked keys: {list(leak_data.keys())}")
        report["findings_summary"].append({
            "severity": "critical",
            "title": "CVE-2023-23752 — API config leak",
            "detail": f"Exposed config: {leak_data}",
        })
    else:
        print("[+] API config leak not detected")

    # 5. User enumeration via API
    print("\n[*] Attempting user enumeration via API...")
    users = check_user_enum_api(base)
    report["users_via_api"] = users
    if users:
        print(f"  {severity_label('high')} {len(users)} user(s) enumerated via API!")
        for u in users[:5]:
            print(f"    → {u}")
        report["findings_summary"].append({
            "severity": "high",
            "title": f"User enumeration via API ({len(users)} users)",
            "detail": str(users[:5]),
        })
    else:
        print("[+] No users found via API")

    # 6. Sensitive paths
    print("\n[*] Checking sensitive paths...")
    sensitive = check_sensitive_paths(base)
    report["sensitive_paths"] = sensitive
    if sensitive:
        print(f"  Found {len(sensitive)} sensitive paths:")
        for p in sensitive:
            print(f"  {severity_label(p['severity'])} [{p['status']}] {p['url']} — {p['description']}")
            if p["severity"] in ("high", "critical"):
                report["findings_summary"].append({
                    "severity": p["severity"],
                    "title": p["description"],
                    "detail": p["url"],
                })
    else:
        print("[+] No sensitive paths found")

    # 7. Vulnerable extensions
    print("\n[*] Checking vulnerable extensions...")
    ext_findings = check_extensions(base)
    report["vulnerable_extensions"] = ext_findings
    if ext_findings:
        print(f"  Extensions present ({len(ext_findings)}):")
        for e in ext_findings:
            print(f"  {severity_label('medium')} [{e['status']}] {e['url']} — {e['description']}")
    else:
        print("[+] No common vulnerable extensions detected")

    # 8. Open registration
    print("\n[*] Checking user registration...")
    report["registration_open"] = check_registration_open(base)
    if report["registration_open"]:
        print(f"  {severity_label('medium')} User registration OPEN — possible account takeover or spam")
        report["findings_summary"].append({"severity": "medium", "title": "Open user registration", "detail": "Self-registration enabled"})
    else:
        print("[+] Registration closed or not detected")

    # 9. Admin protection
    print("\n[*] Analyzing admin panel protection...")
    admin_info = check_admin_bruteforce_protection(base)
    report["admin_protection"] = admin_info
    if admin_info.get("login_accessible"):
        print(f"  {severity_label('medium')} Admin login accessible")
        if not admin_info.get("captcha_present"):
            print(f"  {severity_label('medium')} No CAPTCHA detected — possible brute force")
        if admin_info.get("2fa_mention"):
            print(f"  {severity_label('info')} 2FA mentioned on page")

    # 10. Security headers
    print("\n[*] Checking security headers...")
    missing_headers = check_security_headers(base)
    report["security_headers_missing"] = missing_headers
    if missing_headers:
        print(f"  {severity_label('low')} Missing headers: {', '.join(missing_headers)}")
    else:
        print("[+] Security headers present")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  FINDINGS SUMMARY")
    print("=" * 60)
    by_sev = {}
    for f in report["findings_summary"]:
        by_sev.setdefault(f["severity"], []).append(f)

    for sev in ("critical", "high", "medium", "low"):
        if sev in by_sev:
            for f in by_sev[sev]:
                print(f"  {severity_label(sev)} {f['title']}")
                print(f"             {f['detail']}")

    total = len(report["findings_summary"])
    print(f"\n  Total findings: {total}")
    print("=" * 60)

    if output_path:
        with open(output_path, "w") as fh:
            json.dump(report, fh, indent=2, ensure_ascii=False)
        print(f"\n[+] JSON report saved to: {output_path}")

    return report


def main():
    parser = argparse.ArgumentParser(
        description="joomscan.py — Joomla security scanner (Python, no external dependencies)"
    )
    parser.add_argument("--url", "-u", required=True, help="Target URL (e.g. https://site.com)")
    parser.add_argument("--output", "-o", help="Save report as JSON")
    parser.add_argument("--timeout", "-t", type=int, default=10, help="HTTP timeout (seconds)")
    args = parser.parse_args()

    global TIMEOUT
    TIMEOUT = args.timeout

    run_scan(args.url, args.output)


if __name__ == "__main__":
    main()
