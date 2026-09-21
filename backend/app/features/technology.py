import re

from app.collector.collector import CollectorResponse
from app.features.schema import TechnologyFeatures

FRAMEWORK_PATTERNS = {
    "express": [r"express", r"x-powered-by.*express"],
    "django": [r"django", r"csrftoken"],
    "rails": [r"rails", r"_session_id"],
    "laravel": [r"laravel", r"laravel_session"],
    "spring": [r"spring", r"jsessionid"],
    "asp.net": [r"asp\.net", r"__requestverificationtoken"],
    "nginx": [r"nginx"],
    "apache": [r"apache"],
    "cloudflare": [r"cloudflare", r"cf-ray"],
    "vercel": [r"vercel", r"x-vercel"],
    "netlify": [r"netlify"],
    "next.js": [r"next\.js", r"_next"],
    "nuxt": [r"nuxt"],
    "vite": [r"vite"],
    "webpack": [r"webpack"],
    "php": [r"php"],
    "python": [r"python"],
    "node.js": [r"node\.js"],
    "go": [r"go"],
    "java": [r"java"],
}


def extract_technology_features(response: CollectorResponse) -> TechnologyFeatures:
    headers = {k.lower(): v for k, v in response.headers.items()}
    content = response.content.decode("utf-8", errors="ignore").lower()

    server_header = headers.get("server", "")
    x_powered_by = headers.get("x-powered-by", "")

    server_header_present = bool(server_header)
    x_powered_by_present = bool(x_powered_by)

    combined = f"{server_header} {x_powered_by} {content}"

    detected = []
    for framework, patterns in FRAMEWORK_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, combined, re.IGNORECASE):
                detected.append(framework)
                break

    return TechnologyFeatures(
        server_header_present=server_header_present,
        x_powered_by_present=x_powered_by_present,
        framework_indicators=detected,
    )
