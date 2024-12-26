from url_parser import URLParser
import os
from tqdm import tqdm
import logging
from datetime import datetime
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
import chromedriver_autoinstaller
from urllib.parse import urlparse
import json
import base64
from typing import Optional, List, Dict
import psutil
import subprocess

class PDFScraper:
    def __init__(self, url_parser: URLParser, output_dir: str = "pdfs"):
        self.url_parser = url_parser
        self.output_dir = output_dir
        self.visited_urls: set = set()
        self.routes_log: List[str] = []
        self.driver = None
        
        # Setup
        chromedriver_autoinstaller.install()
        self._setup_directories()
        self._setup_logging()

    def _setup_directories(self) -> None:
        """Create necessary directories"""
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'raw_content'), exist_ok=True)

    def _setup_logging(self) -> None:
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('pdf_scraper.log'),
                logging.StreamHandler()
            ]
        )

    def _get_chrome_options(self) -> Options:
        """Setup Chrome options"""
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--window-size=1920,1080')
        return chrome_options

    def _kill_chrome_instances(self):
        """Kill any existing Chrome processes"""
        try:
            subprocess.run(['pkill', '-f', 'chrome'], check=False)
            for proc in psutil.process_iter(['name']):
                if 'chrome' in proc.info['name'].lower():
                    try:
                        proc.kill()
                    except:
                        pass
        except Exception as e:
            logging.warning(f"Error killing Chrome instances: {e}")

    def _create_driver(self) -> None:
        """Create new ChromeDriver instance"""
        if self.driver:
            self.driver.quit()
        
        chrome_options = self._get_chrome_options()
        service = Service()
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_page_load_timeout(30)
        self.driver.set_script_timeout(30)

    def _handle_popups(self) -> None:
        """Handle common pop-ups and overlays"""
        try:
            time.sleep(2)
            
            # Handle popups and overlays
            self.driver.execute_script("""
                // Remove overlays and popups
                document.querySelectorAll('[class*="overlay"], [class*="modal"], [class*="popup"]')
                    .forEach(el => el.remove());
                    
                // Enable scrolling
                document.body.style.overflow = 'visible';
            """)
            
        except Exception as e:
            logging.warning(f"Error handling popups: {e}")

    def _generate_filename(self, url: str) -> str:
        """Generate safe filename from URL"""
        filename = url.replace(self.url_parser.start_url, '').replace('/', '_')
        if not filename:
            filename = 'index'
        return filename.strip('_') + '.json'

    def save_complete_page(self, url: str) -> Optional[dict]:
        """Save complete page content including dynamic and hidden elements"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._create_driver()
                logging.info(f"Attempting to extract content from: {url}")
                
                # Load page and wait for content
                self.driver.get(url)
                WebDriverWait(self.driver, 20).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
                
                self._handle_popups()
                
                # Expand hidden content and scroll
                self.driver.execute_script("""
                    // Click show more buttons
                    ['show-more', 'read-more', 'view-more', 'expand'].forEach(className => {
                        document.querySelectorAll(`[class*="${className}"]`).forEach(el => {
                            try { el.click(); } catch(e) {}
                        });
                    });
                    
                    // Expand hidden elements
                    document.querySelectorAll('*').forEach(el => {
                        if (getComputedStyle(el).display === 'none') {
                            el.style.display = 'block';
                        }
                    });
                    
                    // Scroll to load lazy content
                    window.scrollTo(0, document.body.scrollHeight);
                """)
                
                time.sleep(3)  # Wait for dynamic content
                
                # Extract content
                page_content = {
                    'url': url,
                    'timestamp': datetime.now().isoformat(),
                    'title': self.driver.title,
                    'html': self.driver.page_source,
                    'text_content': self.driver.execute_script("""
                        return Array.from(document.querySelectorAll('*'))
                            .map(el => el.textContent)
                            .filter(text => text.trim().length > 0)
                            .join('\\n');
                    """),
                    'metadata': {
                        'headers': self.driver.execute_script("""
                            return Array.from(document.querySelectorAll('h1,h2,h3,h4,h5,h6'))
                                .map(h => ({
                                    level: h.tagName,
                                    text: h.textContent.trim()
                                }));
                        """),
                        'links': self.driver.execute_script("""
                            return Array.from(document.querySelectorAll('a[href]'))
                                .map(a => ({
                                    text: a.textContent.trim(),
                                    href: a.href
                                }));
                        """)
                    }
                }
                
                # Save content
                filename = self._generate_filename(url)
                output_path = os.path.join(self.output_dir, 'raw_content', filename)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(page_content, f, ensure_ascii=False, indent=2)
                
                logging.info(f"Successfully saved content for: {url}")
                return page_content
                
            except Exception as e:
                if attempt == max_retries - 1:
                    logging.error(f"Failed to save content for {url}: {str(e)}")
                    return None
                logging.warning(f"Attempt {attempt + 1} failed for {url}: {str(e)}, retrying...")
                time.sleep(5 * (attempt + 1))
            finally:
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                self.driver = None
                self._kill_chrome_instances()
        
        return None

    def scrape(self, max_depth: int = 2) -> None:
        """Scrape all URLs and save complete content"""
        try:
            urls_to_visit = [url for url in self.url_parser.get_all_urls(max_depth)
                            if 'email-protection' not in url]
            urls_to_visit = list(set(urls_to_visit))
            total_urls = len(urls_to_visit)
            
            logging.info(f"Starting content extraction for {total_urls} URLs")
            
            collected_content = []
            failed_urls = []
            
            with tqdm(total=total_urls, desc="Extracting Content") as pbar:
                for index, url in enumerate(urls_to_visit, 1):
                    if url not in self.visited_urls:
                        logging.info(f"Processing URL {index}/{total_urls}: {url}")
                        content = self.save_complete_page(url)
                        
                        if content:
                            collected_content.append(content)
                            self.visited_urls.add(url)
                            self.routes_log.append(urlparse(url).path)
                            logging.info(f"Successfully processed: {url}")
                        else:
                            failed_urls.append(url)
                            logging.warning(f"Failed to process: {url}")
                        
                        pbar.update(1)
                        time.sleep(3)
            
            # Save summary
            if collected_content:
                summary_path = os.path.join(self.output_dir, 'content_summary.json')
                with open(summary_path, 'w', encoding='utf-8') as f:
                    json.dump({
                        'total_urls': total_urls,
                        'successful': len(collected_content),
                        'failed': len(failed_urls),
                        'timestamp': datetime.now().isoformat(),
                        'content': collected_content
                    }, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            logging.error(f"Scraping error: {e}")
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass
            self._kill_chrome_instances()

def main():
    website_url = "https://cimex.com.np"
    output_directory = "cimex_pdfs"
    max_depth = 2
    
    url_parser = URLParser(website_url)
    scraper = PDFScraper(url_parser, output_directory)
    
    try:
        scraper.scrape(max_depth)
    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        print(f"\nScrape Complete!")
        print(f"Content saved in: {output_directory}")
        print(f"Total pages processed: {len(scraper.visited_urls)}")
        print(f"Total unique routes found: {len(scraper.routes_log)}")
        print(f"See content_summary.json for complete results")

if __name__ == "__main__":
    main()