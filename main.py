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
    with open(LENDERS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

# --------------------------
# Run scraper
# --------------------------
def run():
    lenders = load_lenders()

    for url in lenders:
        bank_name = url.split("//")[1].split("/")[0]  # crude name from domain
        filename = os.path.join(OUTPUT_DIR, f"{bank_name}.txt")

        data = scrape_site(url, bank_name=bank_name)
        if not data:
            continue  # skip if scrape failed

        with open(filename, "w", encoding="utf-8") as f:
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

        print(f"✅ Saved {filename}")

if __name__ == "__main__":
    run()
