from app.collector.collector import CollectorResponse
from app.features.cookie_parser import extract_cookie_features
from app.features.html_parser import extract_html_features
from app.features.http_extractor import extract_http_features
from app.features.schema import FeatureVector
from app.features.security_headers import extract_security_headers
from app.features.technology import extract_technology_features
from app.features.tls_extractor import extract_tls_features


def extract_features(response: CollectorResponse) -> FeatureVector:
    http = extract_http_features(response)
    security_headers = extract_security_headers(response)
    cookies = extract_cookie_features(response)
    tls = extract_tls_features(response)
    html = extract_html_features(response, response.final_url)
    technology = extract_technology_features(response)

    return FeatureVector(
        http=http,
        security_headers=security_headers,
        cookies=cookies,
        tls=tls,
        html=html,
        technology=technology,
    )
