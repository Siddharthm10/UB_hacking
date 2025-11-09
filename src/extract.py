from trafilatura import fetch_url, extract

def pull_clean_text(url: str) -> str | None:
    html = fetch_url(url)
    if not html:
        return None
    # favor precision to reduce boilerplate; keep links for citations
    txt = extract(
        html, url=url, include_comments=False, include_links=True,
        favor_precision=True)
    return txt
