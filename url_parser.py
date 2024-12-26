import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import logging
import time
from typing import Set, List
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry



class URLParser:
    def __init__(self, start_url: str):
        self.start_url = start_url
        self.domain = urlparse(start_url).netloc
        self.visited_urls: Set[str] = set()
        self.discovered_urls: List[str] = []
        
        # Setup session with retries
        self.session = self._setup_session()
        self._setup_logging()

    def _setup_session(self) -> requests.Session:
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
        return session

    def _setup_logging(self) -> None:
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('url_parser.log'),
                logging.StreamHandler()
            ]
        )

    def is_valid_url(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc) and parsed.netloc == self.domain
        except:
            return False

    def get_all_urls(self, max_depth: int = 2) -> List[str]:
        """Get all unique URLs from the website, excluding email protection URLs"""
        self.visited_urls.clear()
        self.discovered_urls.clear()
        
        def crawl(url: str, depth: int) -> None:
            if depth <= 0 or url in self.visited_urls:
                return

            self.visited_urls.add(url)
            logging.info(f"Crawling: {url}")

            try:
                response = self.session.get(url, timeout=10)
                response.raise_for_status()
                time.sleep(1)  # Be nice to the server

                soup = BeautifulSoup(response.content, "html.parser")

                for link in soup.find_all("a", href=True):
                    next_url = urljoin(url, link["href"])
                    if self.is_valid_url(next_url) and 'email-protection' not in next_url:
                        normalized_url = next_url.rstrip('/')
                        if normalized_url not in self.discovered_urls:
                            self.discovered_urls.append(normalized_url)
                            crawl(normalized_url, depth - 1)

            except Exception as e:
                logging.error(f"Error crawling {url}: {e}")

        # Start crawling from the initial URL
        crawl(self.start_url, max_depth)
        
        # Return unique, filtered URLs
        return list(set(self.discovered_urls))
    def crawl(self, url: str, max_depth: int = 2) -> List[str]:
        if max_depth == 0 or url in self.visited_urls:
            return self.discovered_urls

        self.visited_urls.add(url)
        logging.info(f"Crawling: {url}")

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            time.sleep(1)  # Add delay between requests

            soup = BeautifulSoup(response.content, "html.parser")

            for link in soup.find_all("a", href=True):
                next_url = urljoin(url, link["href"])
                if self.is_valid_url(next_url) and next_url not in self.visited_urls:
                    self.discovered_urls.append(next_url)
                    self.crawl(next_url, max_depth - 1)

        except requests.exceptions.RequestException as e:
            logging.error(f"Error crawling {url}: {e}")

        return list(set(self.discovered_urls))  # Remove duplicates

def get_all_urls(self, max_depth: int = 2) -> List[str]:
    """
    Get all unique URLs from the website, excluding email protection URLs
    
    Args:
        max_depth (int): Maximum depth to crawl
        
    Returns:
        List[str]: List of filtered, unique URLs
    """
    self.visited_urls.clear()
    self.discovered_urls.clear()
    
    # Get all URLs first
    all_urls = self.crawl(self.start_url, max_depth)
    
    # Filter and ensure uniqueness
    filtered_urls = []
    seen_urls = set()
    
    for url in all_urls:
        # Skip if URL contains email-protection
        if 'email-protection' in url:
            logging.info(f"Skipping email protection URL: {url}")
            continue
            
        # Normalize URL by removing trailing slash
        normalized_url = url.rstrip('/')
        
        # Add only if not seen before
        if normalized_url not in seen_urls:
            seen_urls.add(normalized_url)
            filtered_urls.append(url)
    
    logging.info(f"Found {len(all_urls)} total URLs")
    logging.info(f"Filtered to {len(filtered_urls)} unique, non-email-protection URLs")
    
    return filtered_urls