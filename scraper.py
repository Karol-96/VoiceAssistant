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
import base64
from typing import Dict, Optional, List
import chromedriver_autoinstaller
from urllib.parse import urlparse
import PyPDF2
import io
from selenium.common.exceptions import WebDriverException
import subprocess
import psutil
import requests
import json


class PDFScraper:
    def __init__(self, url_parser: URLParser, output_dir: str = "pdfs"):
        self.url_parser = url_parser
        self.output_dir = output_dir
        self.visited_urls: set = set()
        self.routes_log: List[str] = []
        self.driver = None
        
        # Setup
        chromedriver_autoinstaller.install()  # Ensure compatible ChromeDriver
        self._setup_directories()
        self._setup_logging()
        self.chrome_processes = []
    def _kill_chrome_instances(self):
        """Kill any existing Chrome processes"""
        try:
            # Kill Chrome processes on Mac/Linux
            subprocess.run(['pkill', '-f', 'chrome'], check=False)
            
            # Kill ChromeDriver processes
            for proc in psutil.process_iter(['name']):
                if 'chrome' in proc.info['name'].lower() or 'chromedriver' in proc.info['name'].lower():
                    try:
                        proc.kill()
                    except:
                        pass
        except Exception as e:
            logging.warning(f"Error killing Chrome instances: {e}")

    def _create_driver(self) -> None:
        """Create new ChromeDriver instance with error handling"""
        try:
            if self.driver:
                self.driver.quit()
        except:
            pass
        
        self._kill_chrome_instances()  # Kill any hanging processes
        
        try:
            chrome_options = self._get_chrome_options()
            service = Service()
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.set_page_load_timeout(30)
            self.driver.set_script_timeout(30)
        except Exception as e:
            logging.error(f"Error creating driver: {e}")
            raise

    def _setup_directories(self) -> None:
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def _setup_logging(self) -> None:
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
        chrome_options.add_argument('--disable-software-rasterizer')
        chrome_options.add_argument('--disable-extensions')
        chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        return chrome_options
    
    def _handle_popups(self) -> None:
        """Handle common pop-ups and overlays"""
        try:
            # Wait a short time for any popups to appear
            time.sleep(2)
            
            # List of common popup/overlay selectors
            popup_selectors = [
                "button.close",
                ".modal-close",
                ".popup-close",
                ".close-button",
                "#close-button",
                ".modal .close",
                "[aria-label='Close']",
                ".advertisement-close",
                ".ad-close",
                "#cookieConsent .close",
                ".cookie-banner .close",
                ".dialog-close",
                ".popup .close",
                ".modal-dialog .close",
                ".modal-content .close",
                ".overlay-close"
            ]
            
            # Try to close each potential popup
            for selector in popup_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    for element in elements:
                        if element.is_displayed():
                            element.click()
                            time.sleep(0.5)  # Short wait after closing each popup
                except:
                    continue
                    
            # Remove overlay divs that might interfere
            overlay_selectors = [
                ".modal",
                ".popup",
                ".overlay",
                "#overlay",
                ".modal-backdrop",
                ".advertisement",
                ".ad-overlay",
                "#cookie-banner",
                ".cookie-notice"
            ]
            
            # Try to remove overlays using JavaScript
            for selector in overlay_selectors:
                try:
                    self.driver.execute_script(f"""
                        var elements = document.querySelectorAll('{selector}');
                        for(var i=0; i<elements.length; i++) {{
                            elements[i].remove();
                        }}
                    """)
                except:
                    continue
                    
            # Remove any fixed position elements that might interfere
            self.driver.execute_script("""
                var elements = document.querySelectorAll('*');
                for(var i=0; i<elements.length; i++) {
                    var style = window.getComputedStyle(elements[i]);
                    if(style.position === 'fixed' || style.position === 'sticky') {
                        elements[i].remove();
                    }
                }
            """)
            
        except Exception as e:
            logging.warning(f"Error handling popups: {e}")

    def _create_driver(self) -> None:
        """Create new ChromeDriver instance"""
        if self.driver:
            self.driver.quit()
        
        chrome_options = self._get_chrome_options()
        service = Service()
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
        self.driver.set_page_load_timeout(30)
        self.driver.set_script_timeout(30)
    def save_complete_page(self, url: str) -> Optional[dict]:
        """Save complete page content including dynamic and hidden elements"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self._create_driver()
                logging.info(f"Attempting to extract content from: {url}")
                
                # Load page
                self.driver.get(url)
                
                # Wait for initial load
                WebDriverWait(self.driver, 20).until(
                    lambda d: d.execute_script('return document.readyState') == 'complete'
                )
                
                # Handle popups
                self._handle_popups()
                
                # Execute JavaScript to expand all hidden content
                self.driver.execute_script("""
                    // Click all common "show more" buttons
                    [
                        '[class*="show-more"]', '[class*="read-more"]', 
                        '[class*="view-more"]', '[class*="view-details"]',
                        '[class*="expand"]', '[class*="toggle"]',
                        'button:contains("Show")', 'button:contains("View")',
                        'a:contains("more")', 'a:contains("details")',
                        '[aria-expanded="false"]', '[data-toggle]',
                        '.collapsed', '.expandable'
                    ].forEach(selector => {
                        document.querySelectorAll(selector).forEach(el => {
                            try {
                                el.click();
                            } catch(e) {}
                        });
                    });
                    
                    // Expand all collapsed/hidden elements
                    document.querySelectorAll('*').forEach(el => {
                        const style = window.getComputedStyle(el);
                        if (style.display === 'none' || style.visibility === 'hidden') {
                            el.style.display = 'block';
                            el.style.visibility = 'visible';
                        }
                    });
                    
                    // Remove overlay masks
                    document.querySelectorAll('[class*="overlay"], [class*="modal"]').forEach(el => {
                        el.remove();
                    });
                """)
                
                # Wait for any dynamic content to load
                time.sleep(3)
                
                # Scroll through the page to trigger lazy loading
                self.driver.execute_script("""
                    window.scrollTo(0, 0);
                    let lastHeight = document.body.scrollHeight;
                    let scrollAttempts = 0;
                    
                    function scrollDown() {
                        window.scrollBy(0, window.innerHeight);
                        setTimeout(() => {
                            let newHeight = document.body.scrollHeight;
                            if (newHeight > lastHeight && scrollAttempts < 10) {
                                lastHeight = newHeight;
                                scrollAttempts++;
                                scrollDown();
                            }
                        }, 1000);
                    }
                    
                    scrollDown();
                """)
                
                # Wait for scrolling to complete
                time.sleep(5)
                
                # Extract all content
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
                        """),
                        'images': self.driver.execute_script("""
                            return Array.from(document.querySelectorAll('img[src]'))
                                .map(img => ({
                                    alt: img.alt,
                                    src: img.src
                                }));
                        """)
                    }
                }
                
                # Save as JSON
                filename = self._generate_filename(url).replace('.pdf', '.json')
                output_path = os.path.join(self.output_dir, 'raw_content', filename)
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
                
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

    def save_as_pdf(self, url: str) -> Optional[bytes]:
        """Try multiple methods to save page as PDF"""
        
        def try_requests_save() -> Optional[bytes]:
            """Try to save using requests"""
            try:
                import requests
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                # Convert HTML to PDF using pdfkit if available
                try:
                    import pdfkit
                    pdf_content = pdfkit.from_string(response.text, False)
                    if pdf_content and len(pdf_content) > 1000:
                        logging.info(f"Successfully saved PDF using requests/pdfkit: {url}")
                        return pdf_content
                except:
                    pass
                    
                # If pdfkit fails, at least log the HTML
                html_path = os.path.join(self.output_dir, "html_backups", f"{urlparse(url).path.strip('/')}.html")
                os.makedirs(os.path.dirname(html_path), exist_ok=True)
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(response.text)
                logging.info(f"Saved HTML backup: {html_path}")
                
            except Exception as e:
                logging.warning(f"Requests method failed for {url}: {str(e)}")
            return None

        def try_selenium_save() -> Optional[bytes]:
            """Try to save using Selenium"""
            max_retries = 1
            for attempt in range(max_retries):
                try:
                    # First check if URL is accessible
                    response = requests.head(url, timeout=10)
                    if response.status_code != 200:
                        logging.error(f"URL not accessible: {url}")
                        return None

                    self._create_driver()
                    logging.info(f"Attempting to load URL with Selenium: {url}")
                    
                    # Load URL with wait
                    self.driver.get(url)
                    WebDriverWait(self.driver, 20).until(
                        lambda d: d.execute_script('return document.readyState') == 'complete'
                    )

                    # Handle popups and wait for content
                    self._handle_popups()
                    time.sleep(2)

                    # Generate PDF
                    print_options = self._get_print_options()
                    pdf = self.driver.execute_cdp_cmd('Page.printToPDF', print_options)
                    pdf_content = base64.b64decode(pdf['data'])

                    if pdf_content and len(pdf_content) > 1000:
                        logging.info(f"Successfully generated PDF using Selenium: {url}")
                        return pdf_content

                except Exception as e:
                    if attempt == max_retries - 1:
                        logging.error(f"Selenium method failed for {url} after {max_retries} attempts: {str(e)}")
                    else:
                        logging.warning(f"Selenium attempt {attempt + 1} failed for {url}: {str(e)}, retrying...")
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

        def try_bs4_save() -> Optional[bytes]:
            """Try to save using BeautifulSoup"""
            try:
                response = requests.get(url, timeout=10)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Clean up the HTML
                for script in soup(["script", "style"]):
                    script.decompose()
                
                # Get text content
                text = soup.get_text()
                
                # Convert to PDF using reportlab
                try:
                    from reportlab.pdfgen import canvas
                    from reportlab.lib.pagesizes import letter
                    from io import BytesIO
                    
                    buffer = BytesIO()
                    c = canvas.Canvas(buffer, pagesize=letter)
                    y = 750  # Starting y position
                    
                    # Write text to PDF
                    for line in text.split('\n'):
                        if line.strip():
                            if y < 50:  # New page if near bottom
                                c.showPage()
                                y = 750
                            c.drawString(50, y, line[:100])  # Limit line length
                            y -= 12
                    
                    c.save()
                    pdf_content = buffer.getvalue()
                    
                    if pdf_content and len(pdf_content) > 1000:
                        logging.info(f"Successfully saved PDF using BeautifulSoup/reportlab: {url}")
                        return pdf_content
                        
                except Exception as e:
                    logging.warning(f"PDF generation failed in BS4 method: {str(e)}")
                    
            except Exception as e:
                logging.warning(f"BeautifulSoup method failed for {url}: {str(e)}")
            return None

        # Try each method in sequence
        logging.info(f"Attempting to save PDF for {url}")
        
        # Try Selenium first
        pdf_content = try_selenium_save()
        if pdf_content:
            return pdf_content
            
        # Try requests/pdfkit next
        pdf_content = try_requests_save()
        if pdf_content:
            return pdf_content
            
        # Try BeautifulSoup as last resort
        pdf_content = try_bs4_save()
        if pdf_content:
            return pdf_content
        
        logging.error(f"All methods failed for {url}")
        return None


    def _generate_filename(self, url: str) -> str:
        filename = url.replace(self.url_parser.start_url, '').replace('/', '_')
        if not filename:
            filename = 'index'
        return filename.strip('_') + '.pdf'


    def _get_print_options(self) -> Dict:
        """Get optimized PDF print options"""
        return {
            'paperWidth': 8.27,  # A4 width in inches
            'paperHeight': 11.7,  # A4 height in inches
            'marginTop': 0.4,     # Small margins for better formatting
            'marginBottom': 0.4,
            'marginLeft': 0.4,
            'marginRight': 0.4,
            'printBackground': True,
            'scale': 0.9,         # Slightly reduced scale to prevent content cutoff
            'preferCSSPageSize': True,
            'landscape': False
        }

    def merge_pdfs(self, pdf_contents: List[bytes], output_path: str) -> bool:
        """Merge multiple PDFs into a single file"""
        try:
            merger = PyPDF2.PdfMerger()
            
            for pdf_content in pdf_contents:
                if pdf_content:
                    pdf_file = io.BytesIO(pdf_content)
                    merger.append(pdf_file)
            
            with open(output_path, 'wb') as output_file:
                merger.write(output_file)
            
            return True
            
        except Exception as e:
            logging.error(f"Error merging PDFs: {e}")
            return False

    def scrape(self, max_depth: int = 2) -> None:
        """Scrape all URLs and save complete content"""
        try:
            urls_to_visit = [url for url in self.url_parser.get_all_urls(max_depth)
                            if 'email-protection' not in url]
            urls_to_visit = list(set(urls_to_visit))  # Ensure uniqueness
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
        print(f"PDFs saved in: {output_directory}")
        print(f"Total pages processed: {len(scraper.visited_urls)}")
        print(f"Total unique routes found: {len(scraper.routes_log)}")
        print(f"See routes_summary.txt for complete list of routes")

if __name__ == "__main__":
    main()