from app.rules.configuration import (
    ServerVersionDisclosureRule,
    WildcardCORSWithCredentialsRule,
    XPoweredByDisclosureRule,
)
from app.rules.cookies import (
    InsecureCookieRule,
    MissingHttpOnlyRule,
    WeakSameSiteRule,
)
from app.rules.performance import (
    ExcessiveResponseSizeRule,
    MixedContentRule,
)
from app.rules.registry import registry
from app.rules.security import (
    HTTPSOnlyRule,
    MissingCSPRule,
    MissingHSTSRule,
    MissingPermissionsPolicyRule,
    MissingReferrerPolicyRule,
    MissingXContentTypeOptionsRule,
    MissingXFrameOptionsRule,
)

registry.register(HTTPSOnlyRule())
registry.register(MissingHSTSRule())
registry.register(MissingCSPRule())
registry.register(MissingXContentTypeOptionsRule())
registry.register(MissingXFrameOptionsRule())
registry.register(MissingReferrerPolicyRule())
registry.register(MissingPermissionsPolicyRule())
registry.register(InsecureCookieRule())
registry.register(MissingHttpOnlyRule())
registry.register(WeakSameSiteRule())
registry.register(ServerVersionDisclosureRule())
registry.register(XPoweredByDisclosureRule())
registry.register(WildcardCORSWithCredentialsRule())
registry.register(MixedContentRule())
registry.register(ExcessiveResponseSizeRule())

__all__ = ["registry"]
