#!/usr/bin/env python3
"""
Synthetic WAT record generator for Tracera ML pipeline testing.

This generates realistic WAT-like records that mimic Common Crawl WAT format,
allowing the ML pipeline to be tested without requiring AWS credentials
or downloading large Common Crawl datasets.

Usage:
    python generate_synthetic_wat.py --output-dir ml/data/pilot/raw --num-records 5000
"""

import json
import gzip
import random
import argparse
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List
from urllib.parse import urlparse
import uuid


# Realistic data for generating synthetic records
DOMAINS = [
    "example.com", "github.io", "herokuapp.com", "azurewebsites.net",
    "blogspot.com", "wordpress.com", "wixsite.com", "netlify.app",
    "vercel.app", "pages.dev", "cloudflare.com", "fastly.net",
    "amazonaws.com", "googleusercontent.com", "firebaseapp.com",
    "netlify.com", "surge.sh", "render.com", "fly.dev", "railway.app",
    "shopify.com", "bigcommerce.com", "squarespace.com", "weebly.com",
]

SUBDOMAINS = [
    "www", "api", "blog", "app", "cdn", "assets", "static", "media",
    "images", "docs", "help", "support", "admin", "dashboard", "shop",
    "store", "news", "events", "community", "forum", "wiki", "dev",
    "staging", "test", "beta", "preview", "demo", "sandbox", "dev",
]

TLD_COUNTRY = [
    "co.uk", "com.au", "co.nz", "co.za", "co.jp", "co.kr", "co.in",
    "com.br", "com.mx", "com.ar", "com.tr", "com.sg", "com.hk",
    "org.uk", "org.au", "gov.uk", "gov.au", "edu.au", "ac.uk",
]

PATHS = [
    "", "/", "/index.html", "/home", "/about", "/contact", "/products",
    "/services", "/blog", "/news", "/api/v1/users", "/api/v2/data",
    "/dashboard", "/settings", "/profile", "/login", "/register",
    "/search", "/category/tech", "/category/business", "/tag/python",
    "/page/1", "/page/2", "/archives/2024", "/archives/2023",
]

USER_AGENTS = [
    "Mozilla/5.0 (compatible; CCBot/2.0; +https://commoncrawl.org/faq/)",
    "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
    "Mozilla/5.0 (compatible; Bingbot/2.0; +http://www.bing.com/bingbot.htm)",
    "Mozilla/5.0 (compatible; YandexBot/3.0; +http://yandex.com/bots)",
]

SERVER_HEADERS = [
    "nginx", "nginx/1.18.0", "nginx/1.24.0", "Apache/2.4.41",
    "Apache/2.4.52", "Apache/2.4.57", "Microsoft-IIS/10.0",
    "cloudflare", "Google Frontend", "AWS", "Vercel", "Netlify",
    "Envoy", "ATS/9.1.1", "ATS/9.2.0", "openresty/1.21.4.1",
]

POWERED_BY = [
    "Express", "Express/4.18.2", "Next.js", "PHP/8.1.0", "PHP/8.2.0",
    "ASP.NET Core", "Django/4.2", "Rails/7.1", "Laravel/10",
    "Spring Boot/3.1", "FastAPI/0.100", "Gin/1.9", "Actix-web/4.3",
]

CONTENT_TYPES = [
    "text/html; charset=utf-8",
    "text/html; charset=iso-8859-1",
    "application/json",
    "application/xml",
    "text/plain",
    "text/css",
    "application/javascript",
]

SECURITY_HEADERS_PRESENCE = {
    "strict-transport-security": 0.35,
    "content-security-policy": 0.25,
    "x-content-type-options": 0.55,
    "x-frame-options": 0.60,
    "referrer-policy": 0.40,
    "permissions-policy": 0.20,
}

COOKIE_PATTERNS = [
    # Secure, HttpOnly, SameSite=Strict
    "session=abc123; Secure; HttpOnly; SameSite=Strict",
    "auth_token=xyz789; Secure; HttpOnly; SameSite=Lax",
    # Secure, HttpOnly, no SameSite
    "sessionid=def456; Secure; HttpOnly",
    # No security flags
    "tracking_id=ghi789; path=/",
    "preferences=dark_mode; path=/; expires=Fri, 31 Dec 2025 23:59:59 GMT",
    # SameSite=None with Secure (cross-site)
    "cross_site=abc; Secure; SameSite=None",
    # Multiple cookies
    "session=aaa; Secure; HttpOnly; SameSite=Strict, csrf=bbb; Secure; SameSite=Lax, pref=ccc; path=/",
]


def random_domain() -> str:
    """Generate a realistic domain name."""
    domain_type = random.random()
    if domain_type < 0.6:
        # Standard .com/.org/.net
        base = random.choice(DOMAINS)
        subdomain = random.choice(SUBDOMAINS) if random.random() < 0.4 else ""
        if subdomain:
            return f"{subdomain}.{base}"
        return base
    elif domain_type < 0.85:
        # Country TLDs
        base = random.choice(DOMAINS).split('.')[0]
        tld = random.choice(TLD_COUNTRY)
        subdomain = random.choice(SUBDOMAINS) if random.random() < 0.3 else ""
        if subdomain:
            return f"{subdomain}.{base}.{tld}"
        return f"{base}.{tld}"
    else:
        # Platform domains (github.io, herokuapp.com, etc.)
        platform = random.choice(["github.io", "herokuapp.com", "azurewebsites.net",
                                   "blogspot.com", "netlify.app", "vercel.app",
                                   "pages.dev", "firebaseapp.com", "wixsite.com"])
        if platform in ["github.io", "netlify.app", "vercel.app", "pages.dev"]:
            name = f"{random.choice(['user', 'myapp', 'blog', 'docs', 'api', 'app', 'dev', 'staging'])}{random.randint(1, 999)}"
        else:
            name = f"{random.choice(['myapp', 'app', 'blog', 'shop', 'api', 'admin', 'dashboard'])}{random.randint(1, 9999)}"
        return f"{name}.{platform}"


def generate_cookies() -> str:
    """Generate realistic Set-Cookie header."""
    num_cookies = random.choices([0, 1, 2, 3, 4], weights=[0.3, 0.25, 0.2, 0.15, 0.1])[0]
    if num_cookies == 0:
        return ""
    return ", ".join(random.sample(COOKIE_PATTERNS, min(num_cookies, len(COOKIE_PATTERNS))))


def generate_security_headers() -> Dict[str, str]:
    """Generate realistic security headers."""
    headers = {}
    for header, prob in SECURITY_HEADERS_PRESENCE.items():
        if random.random() < prob:
            if header == "strict-transport-security":
                headers[header] = f"max-age={random.choice([31536000, 15768000, 63072000])}"
            elif header == "content-security-policy":
                policies = [
                    "default-src 'self'",
                    "default-src 'self'; script-src 'self' 'unsafe-inline'",
                    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'",
                    "default-src 'self'; img-src *; script-src 'self'",
                ]
                headers[header] = random.choice(policies)
            elif header == "x-content-type-options":
                headers[header] = "nosniff"
            elif header == "x-frame-options":
                headers[header] = random.choice(["DENY", "SAMEORIGIN", "ALLOW-FROM https://example.com"])
            elif header == "referrer-policy":
                headers[header] = random.choice([
                    "strict-origin-when-cross-origin", "no-referrer",
                    "origin", "strict-origin", "origin-when-cross-origin"
                ])
            elif header == "permissions-policy":
                headers[header] = random.choice([
                    "geolocation=(), camera=(), microphone=()",
                    "geolocation=(), camera=(), microphone=(), payment=()",
                    "accelerometer=(), gyroscope=(), magnetometer=()",
                ])
    return headers


def generate_wat_record(record_id: int, target_origins: int) -> Dict[str, Any]:
    """Generate a single synthetic WAT record."""
    domain = random_domain()
    scheme = "https" if random.random() < 0.75 else "http"
    path = random.choice(PATHS)
    url = f"{scheme}://{domain}{path}"
    
    parsed = urlparse(url)
    hostname = parsed.hostname or domain
    
    # Generate response
    status_code = random.choices(
        [200, 301, 302, 304, 403, 404, 500, 502, 503],
        weights=[0.7, 0.08, 0.07, 0.05, 0.03, 0.04, 0.01, 0.01, 0.01]
    )[0]
    
    content_type = random.choice(CONTENT_TYPES)
    is_html = content_type.startswith("text/html")
    
    # Generate security headers
    sec_headers = generate_security_headers()
    
    # Generate cookies
    cookies = generate_cookies()
    
    # Server and X-Powered-By
    server = random.choice(SERVER_HEADERS) if random.random() < 0.8 else None
    powered_by = random.choice(POWERED_BY) if random.random() < 0.3 else None
    
    # Content length
    if is_html:
        content_length = random.randint(500, 500000)
    else:
        content_length = random.randint(100, 50000)
    
    # Build headers dict
    headers = {"content-type": content_type}
    if cookies:
        headers["set-cookie"] = cookies
    if server:
        headers["server"] = server
    if powered_by:
        headers["x-powered-by"] = powered_by
    headers.update(sec_headers)
    
    # WAT metadata
    crawl_date = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    crawl_date_iso = datetime.now(timezone.utc).isoformat()
    
    # Simulate WARC record ID
    warc_record_id = f"<urn:uuid:{uuid.uuid4()}>"
    
    # Build WAT record (simplified WAT format)
    wat_record = {
        "Envelope": {
            "WARC-Header-Metadata": {
                "WARC-Type": "response",
                "WARC-Target-URI": url,
                "WARC-Date": crawl_date_iso,
                "WARC-Record-ID": warc_record_id,
                "WARC-Block-Digest": f"sha1:{uuid.uuid4().hex[:40]}",
                "WARC-Payload-Digest": f"sha1:{uuid.uuid4().hex[:40]}",
                "WARC-IP-Address": f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}",
                "WARC-Identified-Payload-Type": "text/html" if is_html else "application/octet-stream",
            },
            "Payload-Metadata": {
                "HTTP-Response-Metadata": {
                    "Headers": {
                        k: v if isinstance(v, list) else [v] for k, v in headers.items()
                    },
                    "Status": str(status_code),
                    "Status-Line": f"HTTP/1.1 {status_code} OK" if status_code == 200 else f"HTTP/1.1 {status_code}",
                }
            },
            "Container": {
                "GZIP-Length": str(content_length + random.randint(0, 1000)),
                "WARC-Identified-Payload-Type": "text/html" if is_html else "application/octet-stream",
            }
        },
        "Container": {
            "GZIP-Length": str(content_length + random.randint(0, 1000)),
        }
    }
    
    return wat_record


def write_wat_gz(records: List[Dict], output_path: Path) -> int:
    """Write WAT records to a gzipped JSONL file."""
    bytes_written = 0
    with gzip.open(output_path, 'wt', encoding='utf-8') as f:
        for record in records:
            line = json.dumps(record, separators=(',', ':'))
            f.write(line + '\n')
            bytes_written += len(line) + 1
    return bytes_written


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic WAT records for Tracera ML pipeline")
    parser.add_argument("--output-dir", default="ml/data/pilot/raw", help="Output directory")
    parser.add_argument("--num-records", type=int, default=5000, help="Number of records to generate")
    parser.add_argument("--segment-name", default="synthetic-segment-001", help="Segment name")
    parser.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    args = parser.parse_args()
    
    random.seed(args.seed)
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / f"{args.segment_name}.warc.wat.gz"
    
    print(f"Generating {args.num_records} synthetic WAT records...")
    print(f"Output: {output_file}")
    
    records = []
    for i in range(args.num_records):
        record = generate_wat_record(i, args.num_records)
        records.append(record)
        if (i + 1) % 1000 == 0:
            print(f"  Generated {i + 1} records...")
    
    bytes_written = write_wat_gz(records, output_file)
    print(f"Done! Wrote {len(records)} records, {bytes_written:,} bytes to {output_file}")
    print(f"File size: {output_file.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()