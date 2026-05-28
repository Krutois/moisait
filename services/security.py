from urllib.parse import urljoin, urlparse

from flask import request


UNSAFE_REDIRECT_PATHS = {"/login", "/logout"}
UNSAFE_REDIRECT_PREFIXES = ("/set-language/",)


def is_safe_url(target, *, allow_current_path=False):
    if not target:
        return False

    ref_url = urlparse(request.host_url)
    test_url = urlparse(urljoin(request.host_url, target))

    if test_url.scheme not in {"http", "https"} or ref_url.netloc != test_url.netloc:
        return False

    path = test_url.path or "/"
    if not allow_current_path and path == request.path:
        return False
    if path in UNSAFE_REDIRECT_PATHS or path.startswith(UNSAFE_REDIRECT_PREFIXES):
        return False

    return True


def safe_redirect_target(target, fallback, *, allow_current_path=False):
    return target if is_safe_url(target, allow_current_path=allow_current_path) else fallback
