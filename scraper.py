
## 2. `scraper.py`

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import re
import logging

logging.basicConfig(level=logging.INFO)

HEADERS = {"User-Agent": "MortgageBot/1.0 (+mailto:you@example.com)"}


def fetch(url):
    logging.info(f"Fetching {url}")
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    return r.text


def clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def extract_text_from_page(url):
    """Extract headings, paragraphs, bullet points from a page"""
    html = fetch(url)
    soup = BeautifulSoup(html, "html.parser")

    content = []
    for elem in soup.select("h1, h2, h3, h4, p, li"):
        txt = clean(elem.get_text())
        if txt:
            content.append(txt)
    return content


def get_internal_links(start_url, base_url):
    """Find subpages under the same domain (only within start URL path)."""
    html = fetch(start_url)
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.select("a"):
        href = a.get("href")
        if href and href.startswith("/"):
            full = urljoin(base_url, href)
            if start_url.split("/")[3] in full:  # only include relevant section
                if full not in links:
                    links.append(full)
    return links


def scrape_site(start_url, bank_name="Unknown Bank"):
    """Scrape main page + subpages for one lender"""
    all_text = {}

    # main page
    all_text["main"] = extract_text_from_page(start_url)

    # try to get subpages
    base = start_url.split("/home/")[0] if "/home/" in start_url else start_url
    subpages = get_internal_links(start_url, base)
    for sp in subpages:
        key = sp.replace(start_url, "").strip("/") or "overview"
        all_text[key] = extract_text_from_page(sp)

    return {
        "bank": bank_name,
        "source": start_url,
        "sections": all_text
    }
