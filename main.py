import os
from scraper import scrape_site, chunk_text, extract_keywords

# --------------------------
# Configuration
# --------------------------
OUTPUT_DIR = "output"
LENDERS_FILE = "lenders.txt"
CHUNK_SIZE = 500  # words per chunk

# Ensure output folder exists
os.makedirs(OUTPUT_DIR, exist_ok=True)

# --------------------------
# Load lender URLs
# --------------------------
def load_lenders():
    """Each line is `<start url> [scope]`. Blank lines and # comments are skipped.
    The optional scope is a path prefix limiting which subpages get crawled."""
    lenders = []
    with open(LENDERS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            lenders.append((parts[0], parts[1] if len(parts) > 1 else None))
    return lenders

# --------------------------
# Run scraper
# --------------------------
def run():
    lenders = load_lenders()
    written = set()  # a lender with several start pages shares one output file

    for url, scope in lenders:
        bank_name = url.split("//")[1].split("/")[0]  # crude name from domain
        filename = os.path.join(OUTPUT_DIR, f"{bank_name}.txt")

        data = scrape_site(url, bank_name=bank_name, scope=scope)
        if not data:
            continue  # skip if scrape failed

        mode = "a" if filename in written else "w"
        with open(filename, mode, encoding="utf-8") as f:
            if mode == "w":
                f.write(f"##### {data['bank'].upper()} #####\n")
            f.write(f"Source: {data['source']}\n\n")

            for sec, lines in data["sections"].items():
                section_text = " ".join(lines)
                f.write(f"=== {sec.upper()} ===\n")

                # Dynamic keyword extraction
                keywords = extract_keywords([section_text], top_n=15)
                f.write(f"Keywords: {', '.join(keywords)}\n\n")

                # Split into chunks
                chunks = chunk_text(section_text, CHUNK_SIZE)
                for idx, chunk in enumerate(chunks, 1):
                    f.write(f"--- CHUNK {idx} ---\n")
                    f.write(chunk + "\n\n")

        written.add(filename)
        print(f"✅ Saved {data['source']} to {filename}")

if __name__ == "__main__":
    run()
