from dataclasses import dataclass

from app.collector.collector import CollectorResponse
from app.features.schema import CookieFeatures


@dataclass
class ParsedCookie:
    name: str
    value: str
    secure: bool = False
    httponly: bool = False
    samesite: str | None = None
    domain: str | None = None
    path: str | None = None
    expires: str | None = None
    max_age: int | None = None


def parse_set_cookie_header(cookie_header: str) -> ParsedCookie:
    parts = cookie_header.split(";")
    name_value = parts[0].strip()

    if "=" not in name_value:
        return ParsedCookie(name=name_value, value="")

    name, value = name_value.split("=", 1)
    cookie = ParsedCookie(name=name.strip(), value=value.strip())

    for part in parts[1:]:
        part = part.strip().lower()
        if part == "secure":
            cookie.secure = True
        elif part == "httponly":
            cookie.httponly = True
        elif part.startswith("samesite="):
            cookie.samesite = part.split("=", 1)[1].strip()
        elif part.startswith("domain="):
            cookie.domain = part.split("=", 1)[1].strip()
        elif part.startswith("path="):
            cookie.path = part.split("=", 1)[1].strip()
        elif part.startswith("expires="):
            cookie.expires = part.split("=", 1)[1].strip()
        elif part.startswith("max-age="):
            try:
                cookie.max_age = int(part.split("=", 1)[1].strip())
            except ValueError:
                pass

    return cookie


def parse_cookies(headers: dict[str, str]) -> list[ParsedCookie]:
    cookies = []
    set_cookie_headers = []

    for k, v in headers.items():
        if k.lower() == "set-cookie":
            if isinstance(v, list):
                set_cookie_headers.extend(v)
            else:
                set_cookie_headers.append(v)

    for header in set_cookie_headers:
        if "," in header and not header.strip().startswith(","):
            parts = [p.strip() for p in header.split(",") if "=" in p]
            for part in parts:
                try:
                    cookies.append(parse_set_cookie_header(part))
                except Exception:
                    continue
        else:
            try:
                cookies.append(parse_set_cookie_header(header))
            except Exception:
                continue

    return cookies


def extract_cookie_features(response: CollectorResponse) -> CookieFeatures:
    cookies = parse_cookies(response.headers)

    total = len(cookies)
    secure = sum(1 for c in cookies if c.secure)
    httponly = sum(1 for c in cookies if c.httponly)
    samesite = sum(
        1 for c in cookies if c.samesite and c.samesite.lower() in ("strict", "lax", "none")
    )
    session = sum(1 for c in cookies if not c.expires and not c.max_age)
    persistent = total - session

    third_party = 0
    for cookie in cookies:
        if cookie.domain and cookie.domain.startswith("."):
            third_party += 1

    return CookieFeatures(
        total_cookies=total,
        secure_cookies=secure,
        httponly_cookies=httponly,
        samesite_cookies=samesite,
        session_cookies=session,
        persistent_cookies=persistent,
        third_party_indicators=third_party,
    )
