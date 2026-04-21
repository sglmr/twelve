# your_app/management/commands/checklinks.py

import asyncio
import sys
from collections import defaultdict  # <<< MODIFIED: Added defaultdict
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from fake_useragent import UserAgent  # <<< NEW: Import UserAgent
from rich import print

CONCURRENT_REQUESTS = 40
POLITE_DELAY_SECONDS = 0.5

# <<< REMOVED: Static HEADERS dict is gone. We generate dynamic headers now.

LINK_CHECKER_SKIP_URLS = [
    "http://www.yelp.com/biz/8vFJH_paXsMocmEO_KAa3w",
    "http://www.yelp.com/biz/rp17Dfjdh7JR4GGZwj6nqg",
    "https://example.com/account/signup",
    "https://fonts.googleapis.com",
    "https://fonts.gstatic.com",
    "https://recorda.day",
    "https://www.jetpens.com/blog/Maruman-Mnemosyne-A-Comprehensive-Guide/pt/964",
    "https://esd.wa.gov/employer-taxes/about-soc",
    "https://smittenkitchen.com",
    "https://www.digitalocean.com/community/tutorials/how-to-harden-openssh-on-ubuntu-18-04",
]
LINK_CHECKER_SKIP_DOMAINS = [
    "www.axios.com",
    "stackoverflow.com",
    "en.wikipedia.org",
    "reddit.com",
]


class LinkChecker:
    crawled_links = set()
    dead_links = defaultdict(lambda: {"status": None, "sources": set()})
    skip_urls = set(LINK_CHECKER_SKIP_URLS)
    skip_domains = set(LINK_CHECKER_SKIP_DOMAINS)
    base_domain = None
    client = None
    semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS)
    dead_links_lock = asyncio.Lock()
    ua = UserAgent()

    def __init__(self, base_url: str):
        """
        Main entry point for the management command.
        """
        base_url = base_url
        self.base_domain = urlparse(base_url).netloc

        if not self.base_domain:
            print(f"[red]Invalid base_url:[/red] {base_url}")
            sys.exit(1)

        print(f"Starting crawl at: {base_url}")
        print(f"Limiting to {CONCURRENT_REQUESTS} concurrent requests.")
        print(f"Using a polite delay of {POLITE_DELAY_SECONDS}s between requests.")

        try:
            asyncio.run(self.run_crawler(base_url))
        except KeyboardInterrupt:
            print("\nCrawl interrupted by user.")
        finally:
            self.print_results()

    def get_headers(self):
        """
        Generates a new set of headers with a random User-Agent.
        """
        if self.ua:
            user_agent = self.ua.random
        else:
            # Fallback in case fake-useragent fails
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"

        return {
            "User-Agent": user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Accept-Language": "en-US,en;q=0.9",
            "Connection": "keep-alive",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Referer": "https://www.google.com/",
            "Dnt": "1",
        }

    async def record_dead_link(self, url: str, status, source_page: str):
        """
        Safely records a dead link and its source page.
        """
        async with self.dead_links_lock:
            # Only set the status the first time we see this dead link
            if self.dead_links[url]["status"] is None:
                self.dead_links[url]["status"] = status
            # Add the source page (this will handle duplicates)
            if source_page:
                self.dead_links[url]["sources"].add(source_page)

    async def run_crawler(self, base_url: str):
        """
        Sets up the async client and the main TaskGroup.
        """
        # <<< MODIFIED: Client now handles cookies and has no static headers
        async with httpx.AsyncClient(
            follow_redirects=True, verify=False, cookies=httpx.Cookies()
        ) as client:
            self.client = client

            async with asyncio.TaskGroup() as tg:
                # Start the crawl from the base URL
                # <<< MODIFIED: Pass the initial source page
                await self.crawl_page(tg, base_url, source_page="N/A (Base URL)")

    async def crawl_page(
        self, tg: asyncio.TaskGroup, url: str, source_page: str
    ):  # <<< MODIFIED: Added source_page
        """
        Recursively crawls a single page.
        """
        if url in self.crawled_links:
            return

        self.crawled_links.add(url)

        # Check Skip Lists
        if url in self.skip_urls:
            print(f"[gold1]SKIPPING URL:[/gold1] {url} (settings)")
            return
        try:
            domain = urlparse(url).netloc
            if domain in self.skip_domains:
                print(f"[gold1]SKIPPING DOMAIN:[/gold1] {domain} for {url} (settings)")
                return
        except ValueError:
            print(print(f"[gold1]Could not parse url:[/gold1] {url}"))
            return

        # <<< NEW: Add a small, polite delay to avoid rate-limiting
        await asyncio.sleep(POLITE_DELAY_SECONDS)

        # Acquire Semaphore to limit concurrency
        async with self.semaphore:
            # <<< NEW: Get fresh headers for *this specific request*
            headers = self.get_headers()

            try:
                # <<< MODIFIED: Pass dynamic headers
                response = await self.client.head(url, timeout=10, headers=headers)

                if not response.is_success:
                    # <<< MODIFIED: Pass dynamic headers (for GET fallback)
                    response = await self.client.get(url, timeout=10, headers=headers)

            except httpx.RequestError as e:
                # <<< MODIFIED: Show source_page and use new record_dead_link
                print(
                    f"[red]DEAD:[/red] {url} -> {type(e).__name__} (Found on: {source_page})"
                )
                await self.record_dead_link(url, str(e), source_page)
                return

        # --- Handle HTTP Status ---
        if response.is_error:
            # <<< MODIFIED: Show source_page and use new record_dead_link
            print(
                f"[red]DEAD:[/red] {url} -> {response.status_code} (Found on: {source_page})"
            )
            await self.record_dead_link(url, response.status_code, source_page)
            return

        print(f"[green]OK:[/green] {url} ({response.status_code})")

        # --- Check if we should crawl this page's links ---
        current_domain = urlparse(str(response.url)).netloc
        if current_domain != self.base_domain:
            return  # It's an external link, we checked it, we're done.

        content_type = response.headers.get("content-type", "").lower()
        if "text/html" not in content_type:
            return  # Not an HTML page, we can't parse it for more links

        # --- It's an internal HTML page, let's parse it ---
        try:
            async with self.semaphore:
                # <<< NEW: Get fresh headers for the *content* GET request
                get_headers = self.get_headers()

                # <<< MODIFIED: Pass dynamic headers
                real_response = await self.client.get(
                    url, timeout=10, headers=get_headers
                )

            links = self.parse_links(real_response.text, str(real_response.url))

            # <<< MODIFIED: This page's URL is the source_page for links found on it
            current_page_url = str(real_response.url)

            for link in links:
                if link not in self.crawled_links:
                    # <<< MODIFIED: Pass the current_page_url as the source_page
                    tg.create_task(
                        self.crawl_page(tg, link, source_page=current_page_url)
                    )

        except httpx.RequestError as e:
            # <<< MODIFIED: Show source_page and use new record_dead_link
            print(
                f"[red]DEAD[/red] (on GET): {url} -> {type(e).__name__} (Found on: {source_page})"
            )
            await self.record_dead_link(url, str(e), source_page)
        except Exception as e:
            print(f"[red]Error parsing {url}: {e}[/red]")

    def parse_links(self, html: str, page_url: str) -> set[str]:
        """
        Finds all links (<a>, <img>, <script>, <link>) on a page.
        Returns a set of absolute URLs.
        """
        soup = BeautifulSoup(html, "html.parser")
        found_links = set()

        tags_to_check = {
            "a": "href",
            "link": "href",
            "img": "src",
            "script": "src",
        }

        for tag_name, attribute in tags_to_check.items():
            for tag in soup.find_all(tag_name):
                url = tag.get(attribute)
                if not url:
                    continue

                if url.startswith(("mailto:", "tel:", "#", "javascript:")):
                    continue

                absolute_url = urljoin(page_url, url)
                absolute_url = urlparse(absolute_url)._replace(fragment="").geturl()
                found_links.add(absolute_url)

        return found_links

    def print_results(self):
        """
        Prints a summary of the crawl.
        """
        print("\n[green]--- Crawl Complete ---[/green]")
        print(f"Total links checked: {len(self.crawled_links)}")

        if not self.dead_links:
            print("[green]🎉 Hooray! No dead links found.[/green]")
            return

        # <<< MODIFIED: Updated print loop to show all sources
        print(f"[red]Found {len(self.dead_links)} dead links:[/red]")

        # Sort by URL for a consistent report
        for url, data in sorted(self.dead_links.items()):
            status = data["status"]
            sources = data["sources"]

            print(f"\n  * {url} (Status: {status})")

            if sources:
                print("    Found on:")
                for source in sorted(list(sources)):
                    print(f"      - {source}")
            else:
                print(
                    "    (Source page not recorded, likely an issue with the link itself)"
                )
