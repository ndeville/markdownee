#!/usr/bin/env python3

from datetime import datetime
import os
ts_db = f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"
ts_time = f"{datetime.now().strftime('%H:%M:%S')}"
print(f"\n---------- {ts_time} starting {os.path.basename(__file__)}")
import time
start_time = time.time()

from dotenv import load_dotenv
load_dotenv()

import pprint
pp = pprint.PrettyPrinter(indent=4)

####################
# Download local copy of a website using Firecrawl API
"""
website2md_firecrawl.py

Crawls a website using Firecrawl API and saves page content
as Markdown files. Firecrawl handles JS rendering, anti-bot,
and content extraction.

Requirements:
  pip install firecrawl-py python-dotenv

Usage:
  python website2md_firecrawl.py
  (Takes the active Chrome tab URL as input)
"""

# GLOBALS

test = 1
verbose = 1

count_row = 0
count_total = 0
count = 0

# IMPORTS

import re
import subprocess
from urllib.parse import urlparse, unquote

from firecrawl import Firecrawl

from aggregate_md import aggregate_md_files

# Define a set of file extensions to skip (non-HTML resources).
SKIP_EXTENSIONS = {
    ".pdf", ".mp4", ".mov", ".avi", ".mp3", ".wav", ".zip", ".tar", ".gz", ".rar", ".7z",
    ".exe", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".rtf", ".odt", ".swf",
    ".apk", ".dmg", ".iso", ".ogg", ".webm", ".mkv", ".flv", ".wmv", ".m4v"
}


def should_skip_url(url: str) -> bool:
    """Return True if URL points to a non-HTML resource (e.g. PDF, video, doc)."""
    parsed = urlparse(url)
    path = parsed.path.lower()
    for ext in SKIP_EXTENSIONS:
        if path.endswith(ext):
            return True
    if re.search(r"\.(" + "|".join(re.escape(ext.lstrip(".")) for ext in SKIP_EXTENSIONS) + r")(\?|$)", path):
        return True
    return False


# FUNCTIONS

def get_chrome_active_tab_url():
    try:
        script = '''
        tell application "Google Chrome"
            set activeTabUrl to URL of active tab of front window
            return activeTabUrl
        end tell
        '''
        result = subprocess.run(['osascript', '-e', script], capture_output=True, text=True)
        url = result.stdout.strip()
        print(f"\n🚹  Active tab URL: {url}")
        return url
    except Exception as e:
        print(f"Error: {e}")
        return None


# MAIN

# START_URL = input(f"\nEnter URL: ")
START_URL = get_chrome_active_tab_url()

MAX_PAGES = 100  # safety limit

count = 0
count_total = 0


def url_to_dl_folder(url: str, base_dir: str = "/Users/nic/dl") -> str:
    domain = urlparse(url).netloc.replace("www.", "")
    name = domain.rsplit(".", 1)[0]  # Remove TLD only
    return f"{base_dir}/{name}-website"


def url_to_final_folder(url: str, base_dir: str = "/Users/nic/ai/websites") -> str:
    domain = urlparse(url).netloc.replace("www.", "")
    name = domain.rsplit(".", 1)[0]  # Remove TLD only
    return f"{base_dir}/{name}"


def safe_path(path: str) -> str:
    """
    Sanitizes a file path for writing, preserving subfolders.
    """
    parts = []
    for part in path.split("/"):
        if not part:
            continue
        safe = re.sub(r"[^\w\-]", "_", unquote(part))
        parts.append(safe)
    if not parts:
        return "index"
    return os.path.join(*parts)


def clean_filepath(url: str) -> str:
    """
    Build a (sanitized) path (with subdirectories) from a URL.
    - root index is index.md
    - folders/names preserved
    - last part = filename (with .md), folders preserved
    """
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return "index.md"
    # If ends with "/", treat as folder: add index.md
    if path.endswith("/"):
        folder = safe_path(path)
        return os.path.join(folder, "index.md")
    # If no extension, treat as folder: add index.md
    if "." not in os.path.basename(path):
        folder = safe_path(path)
        return os.path.join(folder, "index.md")
    # else preserve subfolders, but .ext → .md
    folder, filename = os.path.split(path)
    filename_root = os.path.splitext(filename)[0]
    filename_md = re.sub(r"[^\w\-]", "_", unquote(filename_root)) + ".md"
    if folder:
        return os.path.join(safe_path(folder), filename_md)
    else:
        return filename_md


OUT_DIR = url_to_dl_folder(START_URL)


def crawl():
    global count, count_total

    os.makedirs(OUT_DIR, exist_ok=True)

    FIRECRAWL_API_KEY = os.getenv("FIRECRAWL_API_KEY")
    if not FIRECRAWL_API_KEY:
        print("❌ FIRECRAWL_API_KEY not set in environment")
        return

    app = Firecrawl(api_key=FIRECRAWL_API_KEY)

    print(f"\n🔥 Starting Firecrawl crawl of {START_URL} (limit: {MAX_PAGES} pages)")

    crawl_result = app.crawl(
        START_URL,
        limit=MAX_PAGES,
        scrape_options={
            "formats": ["markdown"],
            "onlyMainContent": True,
        },
    )

    # crawl_result is a CrawlResponse pydantic model with .data list
    pages = getattr(crawl_result, "data", None) or []
    if not pages:
        print("⚠️  No pages returned from crawl")
        return

    count_total = len(pages)
    print(f"\n📄 Firecrawl returned {count_total} pages")

    for i, page in enumerate(pages, 1):
        # page is a pydantic model with .metadata, .markdown attributes
        metadata = getattr(page, "metadata", None)
        source_url = ""
        if metadata:
            source_url = getattr(metadata, "sourceURL", "") or getattr(metadata, "url", "") or ""
        markdown = getattr(page, "markdown", "") or ""

        if not markdown:
            print(f"  ⏭️  #{i}: No markdown content, skipping")
            continue

        if source_url and should_skip_url(source_url):
            print(f"  ↩️  Skipping non-HTML resource: {source_url}")
            continue

        # Clean up excessive whitespace
        markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()

        # Determine output file path
        if source_url:
            relative_outfile = clean_filepath(source_url)
        else:
            relative_outfile = f"page_{i}.md"

        outfile = os.path.join(OUT_DIR, relative_outfile)
        os.makedirs(os.path.dirname(outfile), exist_ok=True)

        with open(outfile, "w", encoding="utf-8") as f:
            f.write(f"<!-- Source: {source_url} -->\n\n{markdown}")

        count += 1
        print(f"  ✓ #{i}: {source_url or f'page_{i}'}")

    print(f"\n✅ Done! Saved {count}/{count_total} pages to {OUT_DIR}")


crawl()

# Aggregate output

FINAL_DIR = url_to_final_folder(START_URL)

aggregate_md_files(OUT_DIR, FINAL_DIR + ".md", START_URL)

########################################################################################################

if __name__ == '__main__':
    print('\n\n-------------------------------')
    print(f"\ncount_row:\t{count_row:,}")
    print(f"count_total:\t{count_total:,}")
    print(f"count:\t\t{count:,}")
    run_time = round((time.time() - start_time), 3)
    if run_time < 1:
        print(f'\n{os.path.basename(__file__)} finished in {round(run_time*1000)}ms at {datetime.now().strftime("%H:%M:%S")}.\n')
    elif run_time < 60:
        print(f'\n{os.path.basename(__file__)} finished in {round(run_time)}s at {datetime.now().strftime("%H:%M:%S")}.\n')
    elif run_time < 3600:
        print(f'\n{os.path.basename(__file__)} finished in {round(run_time/60)}mns at {datetime.now().strftime("%H:%M:%S")}.\n')
    else:
        print(f'\n{os.path.basename(__file__)} finished in {round(run_time/3600, 2)}hrs at {datetime.now().strftime("%H:%M:%S")}.\n')
