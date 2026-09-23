#!/usr/bin/env python3
"""
JS Secret Scanner — scan JavaScript files for exposed secrets and API endpoints.
Usage: python3 js_secret_scanner.py --urls-file urls.txt --output secrets.json
       python3 js_secret_scanner.py --url https://target.com --output secrets.json
"""

import argparse
import json
import re
import sys
import urllib.request
import urllib.error
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from html.parser import HTMLParser


UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

# ── Secret patterns ──────────────────────────────────────────────────────────
_TS = r'(?:[a-zA-Z<>\[\]|]+\s*=\s*)?'

SECRET_PATTERNS = {
    "AWS_Access_Key":    (r'AKIA[0-9A-Z]{16}',                                    "CRITICAL"),
    "AWS_Secret":        (rf'(?i)aws[_\-]?secret[_\-]?key\s*[=:]\s*{_TS}["\']([A-Za-z0-9+/]{{40}})["\']', "CRITICAL"),
    "JWT":               (r'eyJ[A-Za-z0-9\-_]+\.eyJ[A-Za-z0-9\-_]+\.[A-Za-z0-9\-_]+', "CRITICAL"),
    "Slack_Webhook":     (r'https://hooks\.slack\.com/services/[A-Z0-9]+/[A-Z0-9]+/[A-Za-z0-9]+', "CRITICAL"),
    "GitHub_Token":      (r'gh[pus]_[0-9a-zA-Z]{36,}',                           "CRITICAL"),
    "Stripe_Live":       (r'sk_live_[0-9a-zA-Z]{24,}',                           "CRITICAL"),
    "Private_Key":       (r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',   "CRITICAL"),
    "Firebase_URL":      (r'https://[a-z0-9\-]+\.firebaseio\.com',               "HIGH"),
    "Database_URL":      (r'(?:mongodb|postgres|mysql|redis|jdbc|mssql|sqlite)://[^\s\'"`,)]+', "HIGH"),
    "Internal_URL":      (r'https?://[a-z0-9.\-]+(\.internal|\.local|\.corp|\.intranet|\.cluster\.local)[^\s\'"`,)]*', "HIGH"),
    "GCP_Key_ID":        (r'"private_key_id"\s*:\s*"([a-f0-9]{40})"',           "HIGH"),
    "API_Key":           (rf'(?i)(?:api[_\-]?key|apikey|x-api-key)\s*[=:]\s*{_TS}["\']([A-Za-z0-9+/=_\-]{{16,}})["\']', "HIGH"),
    "Secret_Key":        (rf'(?i)(?:secret[_\-]?key|app[_\-]?secret)\s*[=:]\s*{_TS}["\']([A-Za-z0-9\-_+/=]{{16,}})["\']', "HIGH"),
    "Client_Secret":     (rf'(?i)client[_\-]?secret\s*[=:]\s*{_TS}["\']([^"\']{{16,}})["\']', "HIGH"),
    "OAuth_Secret":      (rf'(?i)oauth[_\-]?secret\s*[=:]\s*{_TS}["\']([^"\']{{8,}})["\']', "MEDIUM"),
    "Password":          (rf'(?i)(?:password|passwd|pwd)\s*[=:]\s*{_TS}["\']([^"\']{{6,}})["\']', "MEDIUM"),
    "Token":             (rf'(?i)(?:auth[_\-]?token|access[_\-]?token|bearer)\s*[=:]\s*{_TS}["\']([A-Za-z0-9\-_.+/=]{{16,}})["\']', "MEDIUM"),
    "Basic_Auth_URL":    (r'https?://[^:@\s]+:[^:@\s]+@[^\s\'"`,)]{8,}',        "MEDIUM"),
}

# ── API endpoint patterns ─────────────────────────────────────────────────────
ENDPOINT_PATTERNS = [
    r'(?:url|path|endpoint|route|baseUrl|baseURL)\s*[=:+]\s*[`"\']([/][a-zA-Z0-9/_\-{}.:?=&%]+)[`"\']',
    r'[`"\']([/](?:api|v\d|graphql|rest|ws|wss|rpc|internal)[/][^`"\'<>\s]{3,})[`"\']',
    r'(?:this\.[a-zA-Z]+|axios|fetch|http)\s*\.\s*(?:get|post|put|delete|patch)\s*\(\s*[`"\']([/][^`"\']+)[`"\']',
]


def fetch(url, timeout=12):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "*/*"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            ct = r.headers.get("Content-Type", "")
            if any(x in ct for x in ("image/", "video/", "font/", "application/octet")):
                return None
            return r.read().decode("utf-8", errors="ignore")
    except Exception:
        return None


class ScriptURLParser(HTMLParser):
    """Extract src from <script> tags."""
    def __init__(self, base_url):
        super().__init__()
        self.base = base_url
        self.scripts = []

    def handle_starttag(self, tag, attrs):
        if tag == "script":
            attrs_dict = dict(attrs)
            src = attrs_dict.get("src", "")
            if src and src.endswith(".js"):
                abs_src = urllib.parse.urljoin(self.base, src)
                if abs_src not in self.scripts:
                    self.scripts.append(abs_src)


def extract_js_urls(html, base_url):
    """Extract all JS URLs from the page (tags + string references)."""
    urls = set()

    parser = ScriptURLParser(base_url)
    try:
        parser.feed(html)
    except Exception:
        pass
    urls.update(parser.scripts)

    for m in re.finditer(r'["\']([^"\']*?\.js(?:\?[^"\']*)?)["\']', html):
        raw = m.group(1)
        if raw.startswith("//"):
            raw = "https:" + raw
        abs_url = urllib.parse.urljoin(base_url, raw)
        parsed = urllib.parse.urlparse(abs_url)
        base_parsed = urllib.parse.urlparse(base_url)
        if parsed.netloc == base_parsed.netloc:
            urls.add(abs_url)

    return list(urls)


def scan_text(text, source_url):
    findings = []
    seen = set()

    for name, (pattern, severity) in SECRET_PATTERNS.items():
        for m in re.finditer(pattern, text):
            full = m.group(0)
            val = m.group(1) if m.lastindex else full
            if len(val) < 6:
                continue
            if val in ("undefined", "null", "true", "false", "string", "number"):
                continue
            key = f"{name}:{val[:40]}"
            if key in seen:
                continue
            seen.add(key)
            findings.append({
                "type": name,
                "severity": severity,
                "value_preview": val[:20] + "..." + val[-8:] if len(val) > 28 else val,
                "full_value": val,
                "source": source_url,
            })

    return findings


def scan_endpoints(text, source_url):
    endpoints = set()
    for pattern in ENDPOINT_PATTERNS:
        for m in re.finditer(pattern, text):
            ep = m.group(1)
            if len(ep) > 3 and ep not in endpoints:
                endpoints.add(ep)
    return [{"endpoint": ep, "source": source_url} for ep in sorted(endpoints)]


def scan_url(base_url):
    result = {"url": base_url, "js_files": [], "secrets": [], "endpoints": []}

    html = fetch(base_url)
    if not html:
        return result

    js_urls = extract_js_urls(html, base_url)
    result["js_files"] = js_urls

    result["secrets"].extend(scan_text(html, base_url))
    result["endpoints"].extend(scan_endpoints(html, base_url))

    for js_url in js_urls[:30]:  # limit to 30 files per host
        content = fetch(js_url)
        if content:
            result["secrets"].extend(scan_text(content, js_url))
            result["endpoints"].extend(scan_endpoints(content, js_url))

    return result


def print_findings(results):
    COLORS = {"CRITICAL": "\033[91m", "HIGH": "\033[93m", "MEDIUM": "\033[96m"}
    RST = "\033[0m"
    BLD = "\033[1m"

    total_secrets = sum(len(r["secrets"]) for r in results)
    total_endpoints = sum(len(r["endpoints"]) for r in results)

    print(f"\n{BLD}{'='*60}{RST}")
    print(f"{BLD}JS SECRET SCANNER RESULTS{RST}")
    print(f"{'='*60}")
    print(f"Hosts scanned    : {len(results)}")
    print(f"Secrets found    : {total_secrets}")
    print(f"API endpoints    : {total_endpoints}")
    print(f"{'='*60}\n")

    for r in results:
        if not r["secrets"] and not r["endpoints"]:
            continue
        print(f"{BLD}[HOST] {r['url']}{RST}")
        print(f"  JS files: {len(r['js_files'])}")

        for severity in ("CRITICAL", "HIGH", "MEDIUM"):
            secs = [s for s in r["secrets"] if s["severity"] == severity]
            if secs:
                color = COLORS.get(severity, "")
                for s in secs:
                    print(f"  {color}[{severity}]{RST} {s['type']}: {s['value_preview']}")
                    print(f"           Source: {s['source']}")

        unique_eps = {e["endpoint"] for e in r["endpoints"]}
        if unique_eps:
            print(f"  [ENDPOINTS] {len(unique_eps)} found:")
            for ep in sorted(unique_eps)[:15]:
                print(f"    {ep}")
            if len(unique_eps) > 15:
                print(f"    ... +{len(unique_eps)-15} more in JSON output")
        print()


def main():
    parser = argparse.ArgumentParser(description="JS Secret Scanner for Pentest / Bug Bounty")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--url", help="Single URL to scan")
    group.add_argument("--urls-file", help="File with list of URLs (one per line)")
    parser.add_argument("--output", help="JSON output file", default="js_secrets.json")
    parser.add_argument("--threads", type=int, default=5, help="Parallel threads (default: 5)")
    parser.add_argument("--quiet", action="store_true", help="Silent mode (JSON only)")
    args = parser.parse_args()

    if args.url:
        urls = [args.url]
    else:
        try:
            with open(args.urls_file) as f:
                urls = [line.strip() for line in f if line.strip() and line.startswith("http")]
        except FileNotFoundError:
            print(f"[ERROR] File not found: {args.urls_file}", file=sys.stderr)
            sys.exit(1)

    if not args.quiet:
        print(f"[*] Scanning {len(urls)} URLs with {args.threads} threads...")

    results = []
    with ThreadPoolExecutor(max_workers=args.threads) as executor:
        futures = {executor.submit(scan_url, url): url for url in urls}
        for future in as_completed(futures):
            try:
                results.append(future.result())
                if not args.quiet:
                    url = futures[future]
                    secs = len(results[-1]["secrets"])
                    if secs > 0:
                        print(f"  [+] {url} — {secs} secrets found")
            except Exception as e:
                if not args.quiet:
                    print(f"  [!] Error on {futures[future]}: {e}", file=sys.stderr)

    results.sort(key=lambda x: len(x["secrets"]), reverse=True)

    if not args.quiet:
        print_findings(results)

    with open(args.output, "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)

    if not args.quiet:
        print(f"[*] Results saved to: {args.output}")

    criticals = sum(
        1 for r in results
        for s in r["secrets"]
        if s["severity"] == "CRITICAL"
    )
    sys.exit(1 if criticals > 0 else 0)


if __name__ == "__main__":
    main()
