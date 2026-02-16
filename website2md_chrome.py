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
DB_BTOB = os.getenv("DB_BTOB")
DB_MAILINGEE = os.getenv("DB_MAILINGEE")

import pprint
pp = pprint.PrettyPrinter(indent=4)

####################
# Download local copy of the Kaltura website
"""
playwright_site_to_markdown.py

Crawls a JS-rendered website using Playwright and saves page *content only*
as Markdown files. No CSS, JS, images, fonts, or analytics are downloaded.

Requirements:
  pip install playwright beautifulsoup4 markdownify
  playwright install

Usage:
  python playwright_site_to_markdown.py https://corp.kaltura.com ./out
"""

"""
2026-01-26 UPDATE: now run using Alfred `web2md` which takes the active Chrome window as input
"""

# GLOBALS

test = 1
verbose = 1

count_row = 0
count_total = 0
count = 0


# IMPORTS

import asyncio
import sys
import os
import re
from urllib.parse import urljoin, urlparse, unquote
import subprocess

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# Removed aggregate_md import as the flattening is not used anymore.
# from aggregate_md import aggregate_md_files

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

START_URL = get_chrome_active_tab_url()
MAX_PAGES = 5000  # safety limit

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

def extract_links(html: str, base_url: str, domain: str) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = set()

    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if href.startswith(("mailto:", "tel:", "#", "javascript:")):
            continue

        abs_url = urljoin(base_url, href)
        parsed = urlparse(abs_url)

        # Normalize links to avoid duplicate crawling of the same resource via different URLs
        if parsed.netloc == domain:
            clean = parsed.scheme + "://" + parsed.netloc + parsed.path
            links.add(clean)

    return links


def extract_main_content(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    # Remove junk tags
    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    # Remove header/footer/nav elements
    for tag in soup.find_all(["header", "footer", "nav"]):
        tag.decompose()

    # Remove common header/footer classes and IDs
    for selector in [
        {"id": re.compile(r"(header|footer|nav|menu|sidebar|cookie|banner)", re.I)},
        {"class_": re.compile(r"(header|footer|nav|menu|sidebar|cookie|banner|top-bar|bottom-bar)", re.I)},
        {"role": re.compile(r"(banner|navigation|contentinfo)", re.I)},
    ]:
        for tag in soup.find_all(**selector):
            tag.decompose()

    # Remove elements with common footer/header data attributes
    for tag in soup.find_all(attrs={"data-section": re.compile(r"(header|footer)", re.I)}):
        tag.decompose()

    # Prefer semantic main content containers
    main_content = (
        soup.find("main") or
        soup.find("article") or
        soup.find(id=re.compile(r"(main|content|primary)", re.I)) or
        soup.find(class_=re.compile(r"(main-content|page-content|entry-content|post-content)", re.I)) or
        soup.find(role="main") or
        soup.body
    )

    if not main_content:
        return ""

    # Final cleanup: remove any remaining nav-like elements inside main
    for tag in main_content.find_all(class_=re.compile(r"(breadcrumb|pagination|share|social)", re.I)):
        tag.decompose()

    return str(main_content)

OUT_DIR = url_to_dl_folder(START_URL)

async def crawl():
    global count, count_total

    os.makedirs(OUT_DIR, exist_ok=True)

    visited = set()
    to_visit = [START_URL]
    domain = urlparse(START_URL).netloc

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080},
            locale="en-US",
        )
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)

        page = await context.new_page()

        while to_visit and len(visited) < MAX_PAGES:
            url = to_visit.pop(0)
            if url in visited:
                continue

            count_total += 1

            print(f"→ Fetching #{count_total}: {url}")
            visited.add(url)

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                await page.wait_for_timeout(3000)
                html = await page.content()
            except Exception as e:
                print(f"  ! Failed: {e}")
                continue

            main_html = extract_main_content(html)
            markdown = md(main_html, heading_style="ATX", strip=["a"])

            markdown = re.sub(r"\n{3,}", "\n\n", markdown).strip()

            relative_outfile = clean_filepath(url)
            outfile = os.path.join(OUT_DIR, relative_outfile)
            os.makedirs(os.path.dirname(outfile), exist_ok=True)

            with open(outfile, "w", encoding="utf-8") as f:
                f.write(f"<!-- Source: {url} -->\n\n{markdown}")

            count += 1

            new_links = extract_links(html, url, domain)
            for link in new_links:
                if link not in visited:
                    to_visit.append(link)

        await browser.close()

    print(f"\n✅ Done! Saved {count}/{count_total} pages to {OUT_DIR}")

asyncio.run(crawl())

# -------- Skipping aggregate_md_files in favor of keeping the folder hierarchy ---------
FINAL_DIR = url_to_final_folder(START_URL)

print(f"\nAll .md files are saved under:\n    {OUT_DIR}\nin their corresponding subfolders (folder structure is preserved).\n")
print(f"If you wish to process/aggregate them further, do so using the preserved folder structure from {OUT_DIR}.")

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