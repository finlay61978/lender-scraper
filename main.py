import os
from scraper import scrape_site

OUTPUT_DIR = "output"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "Lender_scrape_export.txt")
LENDERS_FILE = "lenders.txt"


def load_lenders():
    with open(LENDERS_FILE, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def run():
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    lenders = load_lenders()

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for url in lenders:
            bank_name = url.split("//")[1].split("/")[0]  # crude name from domain
            data = scrape_site(url, bank_name=bank_name)

            f.write(f"##### {data['bank'].upper()} #####\n")
            f.write(f"Source: {data['source']}\n\n")

            for sec, lines in data["sections"].items():
                f.write(f"=== {sec.upper()} ===\n")
                f.write("\n".join(lines))
                f.write("\n\n")

    print(f"✅ Scrape complete. Results saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    run()
