import random
import string

from app.dataset.schema import (
    Dataset,
    DatasetSample,
    DatasetVersion,
    LabelSource,
    RiskTier,
    SampleMetadata,
)
from app.features.schema import (
    CookieFeatures,
    FeatureSchemaVersion,
    FeatureVector,
    HTMLFeatures,
    HTTPFeatures,
    SecurityHeaderFeatures,
    TechnologyFeatures,
    TLSFeatures,
)

SECURITY_HEADERS = [
    "hsts",
    "csp",
    "x_content_type_options",
    "x_frame_options",
    "referrer_policy",
    "permissions_policy",
    "cross_origin_embedder_policy",
    "cross_origin_opener_policy",
    "cross_origin_resource_policy",
]

FRAMEWORKS = [
    "nginx",
    "apache",
    "express",
    "django",
    "rails",
    "laravel",
    "spring",
    "asp.net",
    "cloudflare",
    "vercel",
    "netlify",
    "next.js",
    "nuxt",
    "vite",
    "webpack",
    "php",
    "python",
    "node.js",
    "go",
    "java",
]


def random_domain() -> str:
    tlds = ["com", "org", "net", "io", "dev", "app", "co"]
    name = "".join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(5, 15)))
    return f"{name}.{random.choice(tlds)}"


def random_ip() -> str:
    return ".".join(str(random.randint(1, 254)) for _ in range(4))


def generate_http_features(risk_tier: RiskTier) -> HTTPFeatures:
    tier_config = {
        RiskTier.LOW: {"status_codes": [200], "https_prob": 0.95, "redirects": (0, 1)},
        RiskTier.MEDIUM: {"status_codes": [200, 301, 302], "https_prob": 0.8, "redirects": (0, 2)},
        RiskTier.HIGH: {
            "status_codes": [200, 301, 302, 403, 404],
            "https_prob": 0.5,
            "redirects": (0, 3),
        },
        RiskTier.CRITICAL: {
            "status_codes": [200, 301, 302, 400, 403, 500],
            "https_prob": 0.3,
            "redirects": (1, 5),
        },
    }
    cfg = tier_config[risk_tier]
    https = random.random() < cfg["https_prob"]

    return HTTPFeatures(
        status_code=random.choice(cfg["status_codes"]),
        response_size_bytes=random.randint(1000, 5_000_000),
        response_time_ms=random.uniform(50, 3000),
        content_type=random.choice(["text/html", "application/json", "text/plain"]),
        redirect_count=random.randint(*cfg["redirects"]),
        https_enabled=https,
        server_header=random.choice([None, "nginx", "Apache", "nginx/1.20.1", "Apache/2.4.41"]),
        x_powered_by=random.choice([None, "Express", "PHP/8.1", "ASP.NET", "Next.js"]),
    )


def generate_security_headers(risk_tier: RiskTier) -> SecurityHeaderFeatures:
    tier_present_prob = {
        RiskTier.LOW: 0.9,
        RiskTier.MEDIUM: 0.6,
        RiskTier.HIGH: 0.3,
        RiskTier.CRITICAL: 0.1,
    }
    prob = tier_present_prob[risk_tier]

    headers = {}
    for header in SECURITY_HEADERS:
        if random.random() < prob:
            headers[header] = generate_header_value(header)
        else:
            headers[header] = None

    return SecurityHeaderFeatures(**headers)


def generate_header_value(header: str) -> str:
    values = {
        "hsts": [
            "max-age=31536000",
            "max-age=31536000; includeSubDomains",
            "max-age=31536000; includeSubDomains; preload",
        ],
        "csp": [
            "default-src 'self'",
            "default-src 'self'; script-src 'self' 'unsafe-inline'",
            "default-src 'none'",
        ],
        "x_content_type_options": ["nosniff"],
        "x_frame_options": ["DENY", "SAMEORIGIN"],
        "referrer_policy": ["strict-origin-when-cross-origin", "no-referrer", "same-origin"],
        "permissions_policy": ["geolocation=()", "camera=(); microphone=()", "fullscreen=*"],
        "cross_origin_embedder_policy": ["require-corp"],
        "cross_origin_opener_policy": ["same-origin", "same-origin-allow-popups"],
        "cross_origin_resource_policy": ["same-origin", "cross-origin"],
    }
    return random.choice(values.get(header, ["present"]))


def generate_cookie_features(risk_tier: RiskTier) -> CookieFeatures:
    tier_config = {
        RiskTier.LOW: {
            "total": (0, 3),
            "secure_prob": 0.9,
            "httponly_prob": 0.8,
            "samesite_prob": 0.8,
        },
        RiskTier.MEDIUM: {
            "total": (1, 5),
            "secure_prob": 0.6,
            "httponly_prob": 0.5,
            "samesite_prob": 0.5,
        },
        RiskTier.HIGH: {
            "total": (2, 8),
            "secure_prob": 0.3,
            "httponly_prob": 0.2,
            "samesite_prob": 0.2,
        },
        RiskTier.CRITICAL: {
            "total": (3, 12),
            "secure_prob": 0.1,
            "httponly_prob": 0.1,
            "samesite_prob": 0.1,
        },
    }
    cfg = tier_config[risk_tier]
    total = random.randint(*cfg["total"])

    secure = sum(1 for _ in range(total) if random.random() < cfg["secure_prob"])
    httponly = sum(1 for _ in range(total) if random.random() < cfg["httponly_prob"])
    samesite = sum(1 for _ in range(total) if random.random() < cfg["samesite_prob"])

    return CookieFeatures(
        total_cookies=total,
        secure_cookies=secure,
        httponly_cookies=httponly,
        samesite_cookies=samesite,
        session_cookies=random.randint(0, total),
        persistent_cookies=random.randint(0, total),
        third_party_indicators=random.randint(0, total // 2),
    )


def generate_tls_features(risk_tier: RiskTier) -> TLSFeatures:
    tier_config = {
        RiskTier.LOW: {"expired_prob": 0.01, "expiry_days": (30, 365)},
        RiskTier.MEDIUM: {"expired_prob": 0.05, "expiry_days": (7, 365)},
        RiskTier.HIGH: {"expired_prob": 0.15, "expiry_days": (0, 180)},
        RiskTier.CRITICAL: {"expired_prob": 0.4, "expiry_days": (-30, 90)},
    }
    cfg = tier_config[risk_tier]
    expired = random.random() < cfg["expired_prob"]

    if expired:
        expiry_days = random.randint(-90, -1)
    else:
        expiry_days = random.randint(*cfg["expiry_days"])

    tls_versions = ["TLSv1.3", "TLSv1.2", "TLSv1.1", "TLSv1.0"]
    ciphers = [
        "TLS_AES_256_GCM_SHA384",
        "TLS_CHACHA20_POLY1305_SHA256",
        "ECDHE-RSA-AES256-GCM-SHA384",
        "ECDHE-RSA-AES128-GCM-SHA256",
        "AES256-SHA",
        "AES128-SHA",
    ]

    return TLSFeatures(
        cert_expiry_days=expiry_days,
        cert_expired=expired,
        tls_version=random.choice(tls_versions) if not expired else None,
        cipher_suite=random.choice(ciphers) if not expired else None,
        cert_subject=f"CN={random_domain()}",
        cert_issuer=random.choice(
            ["Let's Encrypt", "DigiCert", "GlobalSign", "Sectigo", "Self-Signed"]
        ),
        san_count=random.randint(1, 5),
    )


def generate_html_features(risk_tier: RiskTier) -> HTMLFeatures:
    tier_config = {
        RiskTier.LOW: {"scripts": (0, 5), "mixed_prob": 0.02},
        RiskTier.MEDIUM: {"scripts": (3, 15), "mixed_prob": 0.1},
        RiskTier.HIGH: {"scripts": (10, 30), "mixed_prob": 0.25},
        RiskTier.CRITICAL: {"scripts": (20, 60), "mixed_prob": 0.5},
    }
    cfg = tier_config[risk_tier]

    return HTMLFeatures(
        html_size_bytes=random.randint(5000, 500_000),
        script_count=random.randint(*cfg["scripts"]),
        stylesheet_count=random.randint(1, 10),
        image_count=random.randint(5, 50),
        iframe_count=random.randint(0, 5),
        form_count=random.randint(0, 5),
        external_domain_count=random.randint(0, 10),
        mixed_content_count=sum(
            1 for _ in range(random.randint(*cfg["scripts"])) if random.random() < cfg["mixed_prob"]
        ),
        has_password_field=random.random() < 0.3,
        has_file_upload=random.random() < 0.15,
    )


def generate_technology_features(risk_tier: RiskTier) -> TechnologyFeatures:
    tier_config = {
        RiskTier.LOW: {"disclose_prob": 0.3},
        RiskTier.MEDIUM: {"disclose_prob": 0.5},
        RiskTier.HIGH: {"disclose_prob": 0.7},
        RiskTier.CRITICAL: {"disclose_prob": 0.9},
    }
    prob = tier_config[risk_tier]["disclose_prob"]

    server_present = random.random() < prob
    x_powered_present = random.random() < prob

    frameworks = []
    if server_present:
        frameworks.append(random.choice(["nginx", "Apache", "cloudflare"]))
    if x_powered_present:
        frameworks.append(random.choice(["Express", "PHP", "ASP.NET", "Next.js"]))
    if random.random() < prob:
        frameworks.append(random.choice(FRAMEWORKS))

    return TechnologyFeatures(
        server_header_present=server_present,
        x_powered_by_present=x_powered_present,
        framework_indicators=list(set(frameworks)),
    )


def generate_feature_vector(risk_tier: RiskTier) -> FeatureVector:
    return FeatureVector(
        feature_schema_version=FeatureSchemaVersion.V1,
        http=generate_http_features(risk_tier),
        security_headers=generate_security_headers(risk_tier),
        cookies=generate_cookie_features(risk_tier),
        tls=generate_tls_features(risk_tier),
        html=generate_html_features(risk_tier),
        technology=generate_technology_features(risk_tier),
    )


def calculate_fixed_risk_score(features: FeatureVector) -> int:
    from app.rules import registry
    from app.scoring.risk import calculate_risk_score

    rule_results = registry.run_all(features)
    findings = []
    for result in rule_results:
        if result.triggered:
            findings.extend(result.findings)
    return calculate_risk_score(findings)


def generate_sample(risk_tier: RiskTier | None = None, family: str | None = None) -> DatasetSample:
    if risk_tier is None:
        risk_tier = random.choices(
            list(RiskTier),
            weights=[0.4, 0.3, 0.2, 0.1],
        )[0]

    features = generate_feature_vector(risk_tier)
    risk_score = calculate_fixed_risk_score(features)

    final_tier = risk_tier
    if risk_score >= 75:
        final_tier = RiskTier.CRITICAL
    elif risk_score >= 50:
        final_tier = RiskTier.HIGH
    elif risk_score >= 25:
        final_tier = RiskTier.MEDIUM
    else:
        final_tier = RiskTier.LOW

    domain = random_domain()

    metadata = SampleMetadata(
        source_url=f"https://{domain}",
        domain=domain,
        synthetic_family=family or f"family_{random.randint(1, 10)}",
        label_source=LabelSource.SYNTHETIC,
        label_confidence=0.9,
        rule_ids_triggered=[],  # Could be populated by running rules
    )

    return DatasetSample(
        feature_vector=features.model_dump(mode="json"),
        risk_tier=final_tier,
        risk_score=risk_score,
        metadata=metadata,
    )


def generate_dataset(
    version: str,
    n_samples: int,
    description: str | None = None,
    family_distribution: dict | None = None,
) -> Dataset:
    dataset = Dataset(
        version=DatasetVersion(
            version=version,
            description=description or f"Synthetic dataset v{version}",
        )
    )

    families = (
        list(family_distribution.keys())
        if family_distribution
        else [f"family_{i}" for i in range(1, 11)]
    )

    for _ in range(n_samples):
        family = (
            random.choices(families, weights=[family_distribution.get(f, 1) for f in families])[0]
            if family_distribution
            else random.choice(families)
        )
        sample = generate_sample(family=family)
        dataset.add_sample(sample)

    dataset.assign_splits()
    return dataset


def generate_balanced_dataset(version: str, n_per_tier: int = 100) -> Dataset:
    dataset = Dataset(
        version=DatasetVersion(
            version=version,
            description=f"Balanced synthetic dataset v{version}",
        )
    )

    for tier in RiskTier:
        for i in range(n_per_tier):
            sample = generate_sample(risk_tier=tier, family=f"{tier.value}_family_{i // 10}")
            dataset.add_sample(sample)

    dataset.assign_splits()
    return dataset
