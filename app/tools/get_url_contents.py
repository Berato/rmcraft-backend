import asyncio
import requests
from bs4 import BeautifulSoup


def chunk_text(text: str, chunk_size: int = 250) -> list[str]:
    """
    A simple function to split text into smaller chunks.
    For a job description, splitting by newline characters is often very effective.
    """
    # Splitting by newline is a great start for structured text like job descriptions
    lines = text.split('\n')
    
    chunks = []
    current_chunk = ""
    for line in lines:
        line = line.strip()
        if not line:
            continue # Skip empty lines
            
        if len(current_chunk) + len(line) + 1 < chunk_size:
            current_chunk += f" {line}"
        else:
            chunks.append(current_chunk.strip())
            current_chunk = line
    
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks

def _fetch_and_parse(url: str, do_chunk: bool = True) -> list[str]:
    """Blocking helper: fetch and parse the given URL, return a list of text chunks.

    This helper keeps the parsing logic synchronous so it can safely be run in a thread
    from the async wrapper.
    """
    try:
        # Set a user-agent to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')
        main_content = soup.find('main') or soup.find('article') or soup.find('body')

        if main_content:
            text = main_content.get_text(separator=' ', strip=True)
            if do_chunk:
                return chunk_text(text)
            return [text]
        else:
            return ["Could not find the main content of the page."]

    except requests.exceptions.RequestException as e:
        return [f"Error fetching URL: {e}"]
    except Exception as e:
        return [f"An unexpected error occurred: {e}"]


async def get_url_contents(url: str, do_chunk: bool = True) -> list[str]:
    """Asynchronously fetch a URL and return a list of cleaned text chunks.

    This function runs the blocking HTTP and parsing work in a thread using
    asyncio.to_thread so the caller can await it without blocking the event loop.
    Returns a list of string chunks. If parsing fails, a single-element list with
    an error message is returned.
    """
    return await asyncio.to_thread(_fetch_and_parse, url, do_chunk)


def get_url_content(url: str, chunk: bool = True) -> str:
    """Synchronous compatibility wrapper kept for callers that expect a string.

    It calls the blocking helper directly and joins chunks with blank lines to
    preserve the previous behaviour.
    """
    chunks = _fetch_and_parse(url, chunk)
    return "\n\n".join(chunks)
