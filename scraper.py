import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

logging.basicConfig(level=logging.INFO)

HEADERS = {"User-Agent": "MortgageBot/1.0 (+mailto:you@example.com)"}

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
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
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
# Extract main text from page
# --------------------------
def extract_text_from_page(url):
    try:
        html = fetch(url)
    except Exception as e:
        logging.warning(f"Requests fetch failed for {url}: {e}")
        html = fetch_js(url)
        if not html:
            logging.error(f"Could not fetch page even with JS render: {url}")
            return []

    soup = BeautifulSoup(html, "html.parser")
    content = []

    for elem in soup.select("h1, h2, h3, h4, p, li"):
        txt = clean(elem.get_text())
        if txt:
            content.append(txt)

    if not content:
        logging.warning(f"No content found at {url}")
    return content

# --------------------------
# Get internal subpages
# --------------------------
def get_internal_links(start_url, base_url):
    try:
        html = fetch(start_url)
    except Exception as e:
        logging.warning(f"Failed to fetch for internal links {start_url}: {e}")
        return []

    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.select("a"):
        href = a.get("href")
        if href and href.startswith("/"):
            full = urljoin(base_url, href)
            if full not in links:
                links.append(full)
    return links

# --------------------------
# Scrape a lender site
# --------------------------
def scrape_site(start_url, bank_name="Unknown Bank"):
    all_text = {}
    main_content = extract_text_from_page(start_url)
    if not main_content:
        logging.error(f"Skipping {bank_name}, main page empty")
        return None
    all_text["main"] = main_content

    base = start_url.split("/home/")[0] if "/home/" in start_url else start_url
    subpages = get_internal_links(start_url, base)
    for sp in subpages:
        key = sp.replace(start_url, "").strip("/") or "overview"
        sub_content = extract_text_from_page(sp)
        if sub_content:
            all_text[key] = sub_content

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
    tfidf_matrix = vectorizer.fit_transform(texts)
    scores = tfidf_matrix.sum(axis=0)
    words = vectorizer.get_feature_names_out()
    word_scores = [(words[i], scores[0,i]) for i in range(len(words))]
    word_scores.sort(key=lambda x: x[1], reverse=True)
    return [w for w, _ in word_scores[:top_n]]
