def ensure_protocol(url, suggestion="http"):
    if "http://" in url and suggestion is "https":
        return f"https://{url.strip('http://')}"
    if suggestion not in url:
        return f"{suggestion}://{url}"
    return url
