# Standard library imports
import os
import logging
import time
import tempfile  # Add this import
import base64
import json
import shutil
from datetime import datetime
from typing import Dict, Optional, List
from urllib.parse import urlparse

# Third-party imports
import PyPDF2
from bs4 import BeautifulSoup
import requests
from tqdm import tqdm
import chromedriver_autoinstaller
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import WebDriverException
import psutil
import subprocess

# Local imports
from url_parser import URLParser


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
            # Increase timeouts
            self.driver.set_page_load_timeout(180)  # 3 minutes
            self.driver.set_script_timeout(180)     # 3 minutes
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
                
                # Create directory if it doesn't exist
                output_dir = os.path.join(self.output_dir, 'raw_content')
                os.makedirs(output_dir, exist_ok=True)
                
                # Save content
                filename = self._generate_filename(url)
                output_path = os.path.join(output_dir, filename)
                
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(page_content, f, ensure_ascii=False, indent=2)
                
                logging.info(f"Successfully saved content to: {output_path}")
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
        
        def try_selenium_save() -> Optional[bytes]:
            """Try to save using Selenium"""
            try:
                logging.info(f"Attempting to load URL with Selenium: {url}")
                self._create_driver()
                self.driver.get(url)
                self._handle_popups()
                
                # Get PDF content
                pdf_data = self.driver.execute_cdp_cmd("Page.printToPDF", {
                    "printBackground": True,
                    "preferCSSPageSize": True,
                    "scale": 1,
                })
                
                if pdf_data and "data" in pdf_data:
                    pdf_bytes = base64.b64decode(pdf_data["data"])
                    logging.info(f"Successfully generated PDF using Selenium: {url}")
                    return pdf_bytes
                    
            except Exception as e:
                logging.error(f"Selenium method failed for {url} after 1 attempts: {str(e)}")
            finally:
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
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
        def try_requests_save() -> Optional[bytes]:
            """Try to save using requests"""
            try:
                logging.info(f"Attempting to save using requests: {url}")
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                # Create a temporary HTML file
                with tempfile.NamedTemporaryFile(suffix='.html', delete=False) as temp_html:
                    temp_html.write(response.content)
                    temp_html_path = temp_html.name
                
                # Convert HTML to PDF using Chrome
                self._create_driver()
                self.driver.get(f'file://{temp_html_path}')
                self._handle_popups()
                
                # Get PDF content
                pdf_data = self.driver.execute_cdp_cmd("Page.printToPDF", {
                    "printBackground": True,
                    "preferCSSPageSize": True,
                    "scale": 1,
                })
                
                if pdf_data and "data" in pdf_data:
                    pdf_bytes = base64.b64decode(pdf_data["data"])
                    logging.info(f"Successfully generated PDF using requests: {url}")
                    return pdf_bytes
                    
            except Exception as e:
                logging.warning(f"Requests method failed for {url}: {str(e)}")
            finally:
                if self.driver:
                    try:
                        self.driver.quit()
                    except:
                        pass
                try:
                    os.unlink(temp_html_path)
                except:
                    pass
            return None

        # Try each method in sequence
        logging.info(f"Attempting to save PDF for {url}")
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Try Selenium first
                pdf_content = try_selenium_save()
                if pdf_content:
                    return pdf_content
                    
                # Try requests next
                pdf_content = try_requests_save()
                if pdf_content:
                    return pdf_content
                    
                if attempt < max_retries - 1:
                    logging.warning(f"Attempt {attempt + 1} failed for {url}, retrying...")
                    time.sleep(5 * (attempt + 1))  # Exponential backoff
                else:
                    logging.error(f"Error processing {url} (attempt {attempt + 1}/{max_retries}): All methods failed")
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    logging.warning(f"Attempt {attempt + 1} failed for {url}: {str(e)}, retrying...")
                    time.sleep(5 * (attempt + 1))
                else:
                    logging.error(f"Error processing {url} (attempt {attempt + 1}/{max_retries}): {str(e)}")
        
        return None


        def try_bs4_save() -> Optional[bytes]:
            """Try to save using BeautifulSoup"""
            try:
                response = requests.get(url, timeout=30)
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
                    from reportlab.lib.styles import getSampleStyleSheet
                    from reportlab.platypus import SimpleDocTemplate, Paragraph
                    from io import BytesIO
                    
                    buffer = BytesIO()
                    doc = SimpleDocTemplate(buffer, pagesize=letter)
                    styles = getSampleStyleSheet()
                    story = []
                    
                    # Split text into paragraphs and create PDF content
                    for para in text.split('\n\n'):
                        if para.strip():
                            p = Paragraph(para.strip(), styles['Normal'])
                            story.append(p)
                    
                    doc.build(story)
                    pdf_content = buffer.getvalue()
                    
                    if pdf_content and len(pdf_content) > 1000:
                        logging.info(f"Successfully saved PDF using BeautifulSoup/reportlab: {url}")
                        return pdf_content
                        
                except Exception as e:
                    logging.warning(f"PDF generation failed in BS4 method: {str(e)}")
                    
            except Exception as e:
                logging.warning(f"BeautifulSoup method failed for {url}: {str(e)}")
            return None

        # Try each method in sequence with proper logging
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
        """Generate safe filename from URL"""
        filename = url.replace(self.url_parser.start_url, '').replace('/', '_')
        if not filename:
            filename = 'index'
        final_name = filename.strip('_') + '.json'
        logging.info(f"Generated filename: {final_name}")
        return final_name


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
        """
        Merge multiple PDFs into a single file with outline items
        """
        merger = None
        try:
            merger = PyPDF2.PdfMerger(strict=False)
            total_pdfs = len(pdf_contents)
            successful_merges = 0
            
            logging.info(f"Attempting to merge {total_pdfs} PDFs...")
            
            # Create a temporary directory for processing
            with tempfile.TemporaryDirectory() as temp_dir:
                # Process each PDF content
                for index, content in enumerate(pdf_contents, 1):
                    if not content:
                        logging.warning(f"Skipping empty PDF content at index {index}")
                        continue
                        
                    try:
                        # Save content to temporary file
                        temp_path = os.path.join(temp_dir, f'temp_{index}.pdf')
                        with open(temp_path, 'wb') as temp_file:
                            temp_file.write(content)
                        
                        # Verify the PDF is valid
                        try:
                            with open(temp_path, 'rb') as pdf_file:
                                PyPDF2.PdfReader(pdf_file)
                        except Exception as e:
                            logging.error(f"Invalid PDF at index {index}: {str(e)}")
                            continue
                        
                        # Add PDF to merger with outline item
                        merger.append(
                            fileobj=temp_path,
                            outline_item=f"Page {index}",  # Using outline_item instead of bookmark
                            import_outline=True  # Using import_outline instead of import_bookmarks
                        )
                        successful_merges += 1
                        logging.info(f"Successfully added PDF {index}/{total_pdfs}")
                        
                    except Exception as e:
                        logging.error(f"Error processing PDF {index}: {str(e)}")
                
                if successful_merges > 0:
                    # Ensure output directory exists
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)
                    
                    # Write the merged PDF
                    with open(output_path, 'wb') as output_file:
                        merger.write(output_file)
                    
                    # Verify the output file
                    file_size = os.path.getsize(output_path)
                    logging.info(f"""
                    PDF Merge Summary:
                    - Total PDFs: {total_pdfs}
                    - Successfully merged: {successful_merges}
                    - Output file: {output_path}
                    - File size: {file_size / 1024:.2f} KB
                    """)
                    
                    return True
                else:
                    logging.error("No PDFs were successfully processed for merging")
                    return False
                    
        except Exception as e:
            logging.error(f"Error merging PDFs: {str(e)}")
            return False
        finally:
            if merger:
                try:
                    merger.close()
                except:
                    pass

    def scrape(self, max_depth: int = 2) -> None:
        """Scrape all URLs and save as a single merged PDF"""
        os.makedirs(self.output_dir, exist_ok=True)
        
        try:
            # Get URLs and limit to 10
            urls_to_visit = [url for url in self.url_parser.get_all_urls(max_depth)
                            if 'email-protection' not in url]
            urls_to_visit = list(set(urls_to_visit))  # Ensure uniqueness
            urls_to_visit = urls_to_visit[:10]  # Take first 10 URLs
            total_urls = len(urls_to_visit)

            logging.info(f"Selected {total_urls} URLs to process:")
            for idx, url in enumerate(urls_to_visit, 1):
                logging.info(f"{idx}. {url}")

            pdf_contents = []
            failed_urls = []
            
            with tqdm(total=total_urls, desc="Extracting Content") as pbar:
                for index, url in enumerate(urls_to_visit, 1):
                    if url not in self.visited_urls:
                        logging.info(f"\nProcessing URL {index}/{total_urls}: {url}")
                        
                        # Try to save content with multiple retries
                        max_retries = 3
                        for attempt in range(max_retries):
                            try:
                                pdf_content = self.save_as_pdf(url)
                                
                                if pdf_content:
                                    pdf_contents.append(pdf_content)
                                    self.visited_urls.add(url)
                                    logging.info(f"Successfully processed: {url}")
                                    break  # Success - exit retry loop
                                
                                if attempt == max_retries - 1:  # Last attempt failed
                                    failed_urls.append(url)
                                    logging.error(f"Failed to process after {max_retries} attempts: {url}")
                                    
                            except Exception as e:
                                if attempt == max_retries - 1:  # Last attempt
                                    failed_urls.append(url)
                                    logging.error(f"Error processing {url} (attempt {attempt + 1}/{max_retries}): {str(e)}")
                                else:
                                    logging.warning(f"Attempt {attempt + 1} failed for {url}: {str(e)}, retrying...")
                                    time.sleep(5 * (attempt + 1))  # Exponential backoff
                            
                        pbar.update(1)
                        time.sleep(3)  # Delay between URLs

            # Create the merged PDF
            if pdf_contents:
                # Generate filename with website name and timestamp
                website_name = urlparse(self.url_parser.start_url).netloc.split('.')[0]
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                merged_filename = f"{website_name}_merged_{timestamp}.pdf"
                merged_pdf_path = os.path.join(self.output_dir, merged_filename)
                
                if self.merge_pdfs(pdf_contents, merged_pdf_path):
                    logging.info(f"Successfully created merged PDF at: {merged_pdf_path}")
                else:
                    logging.error("Failed to create merged PDF")
                    
                # Clean up individual PDFs and directories
                try:
                    if os.path.exists(os.path.join(self.output_dir, 'pdfs')):
                        import shutil
                        shutil.rmtree(os.path.join(self.output_dir, 'pdfs'))
                    if os.path.exists(os.path.join(self.output_dir, 'raw_content')):
                        shutil.rmtree(os.path.join(self.output_dir, 'raw_content'))
                except Exception as e:
                    logging.warning(f"Error cleaning up directories: {e}")
                    
            logging.info(f"\nScraping completed:")
            logging.info(f"- Total URLs: {total_urls}")
            logging.info(f"- Successfully processed: {len(pdf_contents)}")
            logging.info(f"- Failed: {len(failed_urls)}")
            
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
        print("\nScrape Complete!")

if __name__ == "__main__":
    main()