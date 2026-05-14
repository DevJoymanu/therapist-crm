class NoStoreHtmlMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        content_type = response.get("Content-Type", "")
        if content_type.startswith("text/html"):
            response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"
        return response


class SecurityHeadersMiddleware:
    """
    Adds security-related HTTP response headers that are not covered by
    Django's built-in SecurityMiddleware or XFrameOptionsMiddleware.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        # Prevent MIME-type sniffing
        response.setdefault("X-Content-Type-Options", "nosniff")
        # Limit referrer information sent to third parties
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        # Disable browser features not needed by this app
        response.setdefault(
            "Permissions-Policy",
            "camera=(), microphone=(), geolocation=(), payment=()",
        )
        # Enforce framing restriction (belt-and-suspenders with XFrameOptionsMiddleware)
        response.setdefault("X-Frame-Options", "DENY")
        # Add HSTS only when the connection is already HTTPS
        if request.is_secure() and "Strict-Transport-Security" not in response:
            response["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains; preload"
            )
        return response
