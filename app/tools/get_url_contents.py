import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import List

from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
import requests

logger = logging.getLogger(__name__)


def chunk_text(text: str, chunk_size: int = 250) -> List[str]:
    """
    A simple function to split text into smaller chunks.
    For a job description, splitting by newline characters is often very effective.
    """
    lines = text.split('\n')
    chunks: List[str] = []
    current_chunk = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue # Skip empty lines
            
        if len(current_chunk) + len(line) + 1 < chunk_size:
            current_chunk += f" {line}"
        else:
            if current_chunk: # Ensure non-empty chunk is added
                chunks.append(current_chunk.strip())
            current_chunk = line
    
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

async def _fetch_with_playwright(url: str, do_chunk: bool = True) -> list[str]:
    """
    Internal: use Playwright to render the page and extract main content.
    """
    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"]) 
            context = await browser.new_context(ignore_https_errors=True)
            page = await context.new_page()

            # Try networkidle first, fall back to load if necessary.
            try:
                await page.goto(url, wait_until='networkidle', timeout=20000)
            except Exception as e_nav:
                logger.warning("Playwright navigation (networkidle) failed: %s; retrying with 'load'", e_nav)
                await page.goto(url, wait_until='load', timeout=20000)

            html_content = await page.content()
            soup = BeautifulSoup(html_content, 'html.parser')
            main_content = soup.find('main') or soup.find('article') or soup.find('body')

            if main_content:
                text = main_content.get_text(separator=' ', strip=True)
                return chunk_text(text) if do_chunk else [text]
            else:
                return ["Could not find the main content of the page."]
    finally:
        if browser:
            try:
                await browser.close()
            except Exception as e_close:
                logger.debug("Error closing Playwright browser: %s", e_close)


async def _fetch_with_requests(url: str, do_chunk: bool = True) -> list[str]:
    """Fallback: plain HTTP fetch without JS rendering."""
    def sync_get():
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.text

    try:
        html = await asyncio.to_thread(sync_get)
        soup = BeautifulSoup(html, 'html.parser')
        main_content = soup.find('main') or soup.find('article') or soup.find('body')
        if main_content:
            text = main_content.get_text(separator=' ', strip=True)
            return chunk_text(text) if do_chunk else [text]
        return ["Could not find the main content of the page (requests fallback)."]
    except Exception as e:
        logger.exception("Requests fallback failed")
        return [f"Requests fallback failed: {e}"]


async def get_url_contents(url: str, do_chunk: bool = True) -> list[str]:
    """
    Asynchronously fetches a URL using a headless browser to render JavaScript,
    then parses the main content and returns it as a list of text chunks.
    """
    try:
        try:
            return await _fetch_with_playwright(url, do_chunk)
        except Exception as e:
            logger.exception("Playwright fetch failed: %s", e)
            return await _fetch_with_requests(url, do_chunk)
    except Exception as e_outer:
        logger.exception("Unexpected error in get_url_contents")
        return [f"An error occurred while fetching or parsing the URL: {e_outer}"]

def _run_coro_in_thread(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


def get_url_content(url: str, chunk: bool = True) -> str:
    """
    Synchronous compatibility wrapper that runs the async playwright function.
    """
    try:
        try:
            # Normal case: no running loop
            chunks = asyncio.run(get_url_contents(url, chunk))
            return "\n\n".join(chunks)
        except RuntimeError as e:
            # If an event loop is already running, run the coroutine in a separate thread
            logger.warning("asyncio.run failed (loop running). Running in thread: %s", e)
            with ThreadPoolExecutor(max_workers=1) as ex:
                future = ex.submit(_run_coro_in_thread, get_url_contents(url, chunk))
                chunks = future.result()
                return "\n\n".join(chunks)
    except Exception as e:
        logger.exception("Synchronous wrapper failed")
        return f"An error occurred in the synchronous wrapper: {e}"