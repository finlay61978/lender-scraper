# Lender Scraper

This tool scrapes lender criteria pages (like Barclays, Halifax, etc.) and exports all free-text content into a single `.txt` file.  
You can then feed the text into an AI assistant to help with placing mortgage business.

## How it works
- **`scraper.py`** contains the core logic (fetching pages, extracting text).
- **`main.py`** loads a list of lender websites from `lenders.txt` and runs the scraper on each.
- All results are appended into `output/Lender_scrape_export.txt`.

## Usage
1. Install requirements:
   ```bash
   pip install requests beautifulsoup4
