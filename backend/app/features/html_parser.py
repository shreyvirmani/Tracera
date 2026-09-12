from urllib.parse import urlparse

from bs4 import BeautifulSoup

from app.collector.collector import CollectorResponse
from app.features.schema import HTMLFeatures


def extract_html_features(response: CollectorResponse, final_url: str) -> HTMLFeatures:
    content_type = response.content_type or ""
    if "text/html" not in content_type.lower():
        return HTMLFeatures(
            html_size_bytes=len(response.content),
            script_count=0,
            stylesheet_count=0,
            image_count=0,
            iframe_count=0,
            form_count=0,
            external_domain_count=0,
            mixed_content_count=0,
        )

    try:
        soup = BeautifulSoup(response.content, "lxml")
    except Exception:
        return HTMLFeatures(
            html_size_bytes=len(response.content),
            script_count=0,
            stylesheet_count=0,
            image_count=0,
            iframe_count=0,
            form_count=0,
            external_domain_count=0,
            mixed_content_count=0,
        )

    base_domain = urlparse(final_url).netloc.lower()
    is_https = final_url.startswith("https://")

    scripts = soup.find_all("script", src=True)
    script_count = len(scripts)

    stylesheets = soup.find_all("link", rel="stylesheet")
    stylesheet_count = len(stylesheets)

    images = soup.find_all("img", src=True)
    image_count = len(images)

    iframes = soup.find_all("iframe", src=True)
    iframe_count = len(iframes)

    forms = soup.find_all("form")
    form_count = len(forms)

    has_password_field = any(
        inp.get("type") == "password" for form in forms for inp in form.find_all("input")
    )

    has_file_upload = any(
        inp.get("type") == "file" for form in forms for inp in form.find_all("input")
    )

    external_domains = set()
    mixed_content = 0

    for tag in scripts + stylesheets + images + iframes:
        src = tag.get("src") or tag.get("href")
        if src:
            parsed = urlparse(src)
            if parsed.netloc and parsed.netloc.lower() != base_domain:
                external_domains.add(parsed.netloc.lower())

            if is_https and parsed.scheme == "http":
                mixed_content += 1

    for form in forms:
        action = form.get("action")
        if action:
            parsed = urlparse(action)
            if parsed.netloc and parsed.netloc.lower() != base_domain:
                external_domains.add(parsed.netloc.lower())
            if is_https and parsed.scheme == "http":
                mixed_content += 1

    return HTMLFeatures(
        html_size_bytes=len(response.content),
        script_count=script_count,
        stylesheet_count=stylesheet_count,
        image_count=image_count,
        iframe_count=iframe_count,
        form_count=form_count,
        external_domain_count=len(external_domains),
        mixed_content_count=mixed_content,
        has_password_field=has_password_field,
        has_file_upload=has_file_upload,
    )
