# Lender Scraper

Mortgage lenders publish their lending criteria (income rules, LTV limits, buy-to-let stress rates and so on) across dozens of intermediary web pages, each laid out differently. This tool crawls those pages and turns them into clean, chunked, keyword-tagged text files: one per lender, ready to give to an AI assistant so a broker can ask questions such as *"which of these lenders accept bonus income?"* without opening every site.

## How it works

1. **Load the lender list.** `main.py` reads start pages, and an optional crawl scope for each, from `lenders.txt`.
2. **Fetch each page.** `scraper.py` tries a plain HTTP request first. If that fails, or returns a page with no readable text (a sign the site builds its content with JavaScript), it renders the page in headless Chromium with Playwright.
3. **Extract the text.** It keeps headings, paragraphs and list items from the page's `<main>` region, so menus and footers don't repeat on every page.
4. **Crawl the criteria pages.** It follows links from the start page that stay on the same site and inside the scope. `#anchor` links count as the same page, PDFs and images are skipped, and it waits one second between requests.
5. **Prepare the output for an AI assistant.** Each page's text is tagged with its top TF-IDF keywords (scikit-learn) and split into 500-word chunks that fit comfortably in a model's context window.

## Setup

Requires Python 3.10+.

```bash
pip install -r requirements.txt
playwright install chromium   # only needed for JavaScript-rendered sites
```

## Usage

List the lender pages in `lenders.txt`, one per line:

```text
# <start url> [scope]
https://www.nationwide-intermediary.co.uk/lending-criteria/a-z
https://www.halifax-intermediaries.co.uk/criteria.html /criteria
```

Without a scope, the crawler stays inside the start page's own folder, so `/lending-criteria/a-z` covers everything under `/lending-criteria/`. Give an explicit path prefix when the start page sits at the top of the site.

Then run:

```bash
python main.py
```

Each lender gets one file in `output/`, named after its domain. A lender with several start pages, such as residential and buy-to-let, shares one file:

```text
##### WWW.NATIONWIDE-INTERMEDIARY.CO.UK #####
Source: https://www.nationwide-intermediary.co.uk/lending-criteria/a-z

=== /LENDING-CRITERIA/INCOME ===
Keywords: income, latest, ll, criteria, client, mortgage, payslip, payment, months, affordability, pension, ...

--- CHUNK 1 ---
...
```

`output/` is git-ignored. Scraped content belongs to the lenders and isn't redistributed here.

## Settings

Tune these constants at the top of `scraper.py` and `main.py`:

| Setting | Default | Purpose |
|---|---|---|
| `REQUEST_DELAY` | 1.0s | Pause between page loads |
| `MAX_SUBPAGES` | 50 | Cap on pages crawled per start page |
| `CHUNK_SIZE` | 500 words | Size of each text chunk |

## Limitations

- Crawls one level deep: the start page plus the pages it links to.
- Criteria change often. Treat the output as a research aid and always confirm against the lender's current published criteria before placing a case.
- Check each site's terms of use before scraping it.
