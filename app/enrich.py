import time
import logging
import requests
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

logger = logging.getLogger("enrich")


def format_url(website: str) -> str:
    if not website:
        return ""
    website = website.strip()
    if not website.startswith("http://") and not website.startswith("https://"):
        return f"https://{website}"
    return website


def get_http_signal(website: str) -> str:
    """Plain HTTP call - basic reachability, response time, server headers, and content length."""
    url = format_url(website)
    if not url:
        return "status=skipped, reason='no website provided'"
    try:
        start_time = time.time()
        resp = requests.get(
            url,
            timeout=10,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            },
            allow_redirects=True
        )
        elapsed_ms = int((time.time() - start_time) * 1000)
        server = resp.headers.get("Server", "unknown")
        content_type = resp.headers.get("Content-Type", "unknown").split(";")[0]
        final_url = resp.url

        return (
            f"status={resp.status_code}, response_time={elapsed_ms}ms, "
            f"content_length={len(resp.content)} bytes, content_type='{content_type}', "
            f"server='{server}', final_url='{final_url}'"
        )
    except requests.exceptions.Timeout:
        return "http_error='Connection timed out after 10s'"
    except requests.exceptions.SSLError:
        return "http_error='SSL certificate verification failed'"
    except Exception as e:
        return f"http_error='{type(e).__name__}: {str(e)}'"


def get_browser_signal(website: str) -> str:
    """
    Real browser automation via Playwright headless Chromium.
    Navigates to page, extracts rendered page title, meta description, H1 header,
    and visible body text snippet. Catches JS-rendered content plain HTTP calls miss.
    """
    url = format_url(website)
    if not url:
        return "browser_signal='no website provided'"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            try:
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800}
                )
                page = context.new_page()

                # Navigate with 10s timeout
                page.goto(url, timeout=10000, wait_until="domcontentloaded")
                page.wait_for_timeout(500)  # brief wait for client-side JS rendering

                title = page.title() or "No Title"

                # Extract meta description
                meta_desc = ""
                desc_el = page.query_selector("meta[name='description'], meta[property='og:description']")
                if desc_el:
                    meta_desc = desc_el.get_attribute("content") or ""

                # Extract H1 headings
                h1_el = page.query_selector("h1")
                h1_text = h1_el.inner_text().strip() if h1_el else ""

                # Extract visible body text snippet
                body_text = ""
                try:
                    raw_body = page.inner_text("body")
                    body_text = " ".join(raw_body.split())[:400]
                except Exception:
                    body_text = "could not extract body text"

                signal_parts = [f"title='{title.strip()}'"]
                if meta_desc:
                    signal_parts.append(f"meta_desc='{meta_desc.strip()[:200]}'")
                if h1_text:
                    signal_parts.append(f"h1='{h1_text[:150]}'")
                signal_parts.append(f"rendered_snippet='{body_text}'")

                return " | ".join(signal_parts)
            finally:
                browser.close()
    except Exception as e:
        logger.warning(f"Browser automation warning for {url}: {e}")
        return f"browser_error='{type(e).__name__}: {str(e)}'"


def get_domain_signal(website: str) -> str:
    """Extracts domain metadata, protocol security, and TLD indicators."""
    url = format_url(website)
    if not url:
        return "domain_signal='none'"
    parsed = urlparse(url)
    domain = parsed.netloc or parsed.path
    scheme = parsed.scheme
    tld = domain.split(".")[-1] if "." in domain else "unknown"
    return f"domain='{domain}', protocol='{scheme}', tld='{tld}', secure_https={scheme == 'https'}"


def enrich_company(website: str) -> dict:
    logger.info(f"Enriching signals for website: {website}")
    http_sig = get_http_signal(website)
    browser_sig = get_browser_signal(website)
    domain_sig = get_domain_signal(website)

    return {
        "signal_http": http_sig,
        "signal_browser": browser_sig,
        "signal_domain": domain_sig,
    }

