import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urldefrag, urlparse
import re
import time
import logging
from sklearn.feature_extraction.text import TfidfVectorizer

logging.basicConfig(level=logging.INFO)

HEADERS = {"User-Agent": "LenderScraper/1.0 (+https://github.com/finlay61978/lender-scraper)"}
REQUEST_DELAY = 1.0  # seconds between page loads, so we don't hammer lender sites
MAX_SUBPAGES = 50    # safety cap on subpages crawled per lender
SKIP_EXTENSIONS = (".pdf", ".doc", ".docx", ".xls", ".xlsx", ".zip", ".jpg", ".jpeg", ".png", ".gif", ".svg")

# --------------------------
# Fetch HTML normally
# --------------------------
def fetch(url):
    logging.info(f"Fetching {url} with requests")
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text

# --------------------------
# Fetch HTML with JS rendering
# --------------------------
def fetch_js(url):
    logging.info(f"Fetching {url} with Playwright (JS-rendered)")
    try:
        # Imported here so Playwright is only needed when a page actually requires it
        from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    except ImportError:
        logging.error("Playwright is not installed - run `pip install playwright && playwright install chromium`")
        return ""
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent=HEADERS["User-Agent"])
            page.goto(url, timeout=30000)
            html = page.content()
            browser.close()
            return html
    except PlaywrightTimeout as e:
        logging.error(f"Playwright timed out for {url}: {e}")
        return ""

# --------------------------
# Clean text
# --------------------------
def clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# --------------------------
# Extract main text from HTML
# --------------------------
def extract_text(html):
    soup = BeautifulSoup(html, "html.parser")
    # Prefer the page's <main> region so menus and footers aren't repeated on every page
    root = soup.find("main") or soup.body or soup
    content = []

    for elem in root.select("h1, h2, h3, h4, p, li"):
        txt = clean(elem.get_text())
        if txt:
            content.append(txt)
    return content

# --------------------------
# Fetch a page, falling back to JS rendering
# --------------------------
def fetch_page(url):
    """Return (html, text lines). Falls back to Playwright if requests fails
    or returns a page with no readable text (typical of JS-rendered sites)."""
    try:
        html = fetch(url)
        content = extract_text(html)
        if content:
            return html, content
        logging.warning(f"No text in static HTML for {url}, trying JS render")
    except Exception as e:
        logging.warning(f"Requests fetch failed for {url}: {e}")

    html = fetch_js(url)
    content = extract_text(html) if html else []
    if not content:
        logging.error(f"Could not get any content from {url}")
    return html, content

# --------------------------
# Work out which URLs belong to a lender's criteria
# --------------------------
def default_scope(start_url):
    """The folder the start page sits in, e.g. /lending-criteria/a-z -> /lending-criteria/"""
    path = urlparse(start_url).path or "/"
    return path if path.endswith("/") else path.rsplit("/", 1)[0] + "/"

def in_scope(url, start_url, scope):
    parsed, start = urlparse(url), urlparse(start_url)
    return (
        parsed.scheme in ("http", "https")
        and parsed.netloc == start.netloc
        and parsed.path.startswith(scope)
        and not parsed.path.lower().endswith(SKIP_EXTENSIONS)
    )

def normalise(url):
    # Drop #anchors so /page#a and /page#b are treated as the same page
    return urldefrag(url)[0].rstrip("/")

# --------------------------
# Get internal subpages
# --------------------------
def get_internal_links(html, start_url, scope):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.select("a[href]"):
        full = urldefrag(urljoin(start_url, a["href"]))[0]
        if in_scope(full, start_url, scope) and full not in links:
            links.append(full)
    return links

# --------------------------
# Scrape a lender site
# --------------------------
def scrape_site(start_url, bank_name="Unknown Bank", scope=None):
    scope = scope or default_scope(start_url)
    html, main_content = fetch_page(start_url)
    if not main_content:
        logging.error(f"Skipping {bank_name}, main page empty")
        return None
    all_text = {"main": main_content}

    seen = {normalise(start_url)}
    subpages = []
    for link in get_internal_links(html, start_url, scope):
        if normalise(link) not in seen:
            seen.add(normalise(link))
            subpages.append(link)
    if len(subpages) > MAX_SUBPAGES:
        logging.warning(f"{bank_name}: {len(subpages)} subpages found, only crawling the first {MAX_SUBPAGES}")
        subpages = subpages[:MAX_SUBPAGES]

    for sp in subpages:
        time.sleep(REQUEST_DELAY)
        _, sub_content = fetch_page(sp)
        if sub_content:
            all_text[urlparse(sp).path] = sub_content

    return {
        "bank": bank_name,
        "source": start_url,
        "sections": all_text
    }

# --------------------------
# Split text into chunks
# --------------------------
def chunk_text(text, chunk_size=500):
    words = text.split()
    chunks = []
    for i in range(0, len(words), chunk_size):
        chunks.append(" ".join(words[i:i+chunk_size]))
    return chunks

# --------------------------
# Extract dynamic keywords
# --------------------------
def extract_keywords(texts, top_n=10):
    vectorizer = TfidfVectorizer(ngram_range=(1,2), stop_words='english')
    try:
        tfidf_matrix = vectorizer.fit_transform(texts)
    except ValueError:
        return []  # nothing left once stop words are removed
    scores = tfidf_matrix.sum(axis=0)
    words = vectorizer.get_feature_names_out()
    word_scores = [(words[i], scores[0,i]) for i in range(len(words))]
    word_scores.sort(key=lambda x: x[1], reverse=True)
    return [w for w, _ in word_scores[:top_n]]
