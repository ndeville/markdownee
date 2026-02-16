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
BROWSERBASE_API_KEY = os.getenv("BROWSERBASE_API_KEY")
BROWSERBASE_PROJECT_ID = os.getenv("BROWSERBASE_PROJECT_ID")

import pprint
pp = pprint.PrettyPrinter(indent=4)

####################
# Download local copy of a website using Stagehand + Browserbase
"""
stagehand_site_to_markdown.py

Crawls a JS-rendered website using Stagehand (backed by Browserbase cloud browsers)
and saves page *content only* as Markdown files.

Requirements:
  pip install stagehand beautifulsoup4 markdownify browserbase-sdk
  (Stagehand Python SDK: https://github.com/browserbase/stagehand-python)

Usage:
  python stagehand_site_to_markdown.py
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
import re
from urllib.parse import urljoin, urlparse, unquote
import subprocess

from stagehand import Stagehand, StagehandConfig
from bs4 import BeautifulSoup
from markdownify import markdownify as md

from aggregate_md import aggregate_md_files

# Define a set of file extensions to skip (non-HTML resources).
SKIP_EXTENSIONS = {
    ".pdf", ".mp4", ".mov", ".avi", ".mp3", ".wav", ".zip", ".tar", ".gz", ".rar", ".7z",
    ".exe", ".doc", ".docx", ".ppt", ".pptx", ".xls", ".xlsx", ".rtf", ".odt", ".swf",
    ".apk", ".dmg", ".iso", ".ogg", ".webm", ".mkv", ".flv", ".wmv", ".m4v"
}

import requests
import xml.etree.ElementTree as ET

def get_sitemap_urls(base_url: str, domain: str) -> set[str]:
    urls = set()
    sitemap_locations = [
        f"{base_url}/sitemap.xml",
        f"{base_url}/sitemap_index.xml",
        f"{base_url}/sitemap/sitemap.xml",
    ]

    for sitemap_url in sitemap_locations:
        try:
            resp = requests.get(sitemap_url, timeout=10)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                # Handle both sitemap index and regular sitemaps
                for elem in root.iter():
                    if elem.tag.endswith('loc'):
                        url = elem.text.strip()
                        if urlparse(url).netloc == domain:
                            urls.add(url)
        except:
            continue

    print(f"📍 Found {len(urls)} URLs from sitemaps")
    return urls


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

START_URL = get_chrome_active_tab_url()

MAX_PAGES = 10000  # safety limit

count = 0
count_total = 0

def url_to_dl_folder(url: str, base_dir: str = "/Users/nic/dl") -> str:
    domain = urlparse(url).netloc.replace("www.", "")
    name = domain.rsplit(".", 1)[0]
    return f"{base_dir}/{name}-website"

def url_to_final_folder(url: str, base_dir: str = "/Users/nic/ai/websites") -> str:
    domain = urlparse(url).netloc.replace("www.", "")
    name = domain.rsplit(".", 1)[0]
    return f"{base_dir}/{name}"

def safe_path(path: str) -> str:
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
    parsed = urlparse(url)
    path = parsed.path.strip("/")
    if not path:
        return "index.md"
    if path.endswith("/"):
        folder = safe_path(path)
        return os.path.join(folder, "index.md")
    if "." not in os.path.basename(path):
        folder = safe_path(path)
        return os.path.join(folder, "index.md")
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

        if parsed.netloc == domain:
            if should_skip_url(abs_url):
                continue
            links.add(parsed.scheme + "://" + parsed.netloc + parsed.path)

    return links

def extract_main_content(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "svg", "iframe"]):
        tag.decompose()

    for tag in soup.find_all(["header", "footer", "nav"]):
        tag.decompose()

    for selector in [
        {"id": re.compile(r"(header|footer|nav|menu|sidebar|cookie|banner)", re.I)},
        {"class_": re.compile(r"(header|footer|nav|menu|sidebar|cookie|banner|top-bar|bottom-bar)", re.I)},
        {"role": re.compile(r"(banner|navigation|contentinfo)", re.I)},
    ]:
        for tag in soup.find_all(**selector):
            tag.decompose()

    for tag in soup.find_all(attrs={"data-section": re.compile(r"(header|footer)", re.I)}):
        tag.decompose()

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
    to_visit.extend(get_sitemap_urls(START_URL, domain))

    # ── Stagehand + Browserbase configuration ──────────────────────────
    stagehand_config = StagehandConfig(
        env="BROWSERBASE",                        # run in the Browserbase cloud
        api_key=BROWSERBASE_API_KEY,              # Browserbase API key
        project_id=BROWSERBASE_PROJECT_ID,        # Browserbase project ID
        model_name="gpt-4o",                      # LLM backing Stagehand's act/observe/extract
        headless=True,                            # headless cloud browser
    )

    async with Stagehand(stagehand_config) as stagehand:
        page = stagehand.page                     # Stagehand exposes a Playwright-compatible page

        while to_visit and len(visited) < MAX_PAGES:
            url = to_visit.pop(0)
            if url in visited:
                continue

            if should_skip_url(url):
                print(f"  ↩️  Skipping non-HTML resource: {url}")
                continue

            count_total += 1

            print(f"→ Fetching #{count_total}: {url}")
            visited.add(url)

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                # Give JS a moment to render dynamic content
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

    print(f"\n✅ Done! Saved {count}/{count_total} pages to {OUT_DIR}")

asyncio.run(crawl())

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
