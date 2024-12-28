# Standard library imports
import os
import logging
import time
import tempfile
import json
from datetime import datetime
from typing import Dict, Optional, List
from urllib.parse import urlparse
from pathlib import Path

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
from selenium.common.exceptions import WebDriverException
import html2text
import markdown
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO

# Local imports
from url_parser import URLParser

class ContentConverter:
    def __init__(self):
        self.html_converter = html2text.HTML2Text()
        self.html_converter.ignore_links = False
        self.html_converter.ignore_images = False
        self.html_converter.body_width = 0  # No wrapping

    def html_to_markdown(self, html_content: str) -> str:
        """Convert HTML to Markdown"""
        return self.html_converter.handle(html_content)

    def markdown_to_text(self, markdown_content: str) -> str:
        """Convert Markdown to plain text"""
        # Simple markdown to text conversion
        text = markdown_content
        # Remove links
        text = text.replace('[', '').replace(']', '')
        # Remove images
        text = text.replace('![', '').replace('](', ' ').replace(')', '')
        # Remove headers
        text = text.replace('#', '')
        return text.strip()

class WebScraper:
    def __init__(self, url_parser: URLParser, output_dir: str = "website_content"):
        self.url_parser = url_parser
        self.output_dir = output_dir
        self.converter = ContentConverter()
        self.driver = None
        
        # Setup
        self._setup_directories()
        self._setup_logging()
        self._setup_selenium()

    def _setup_directories(self):
        """Create necessary directories"""
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'markdown'), exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, 'text'), exist_ok=True)

    def _setup_logging(self):
        """Setup logging configuration"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('webscraper.log'),
                logging.StreamHandler()
            ]
        )

    def _setup_selenium(self):
        """Setup Selenium WebDriver"""
        chrome_options = Options()
        chrome_options.add_argument('--headless=new')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--no-sandbox')
        self.driver = webdriver.Chrome(options=chrome_options)

    def get_page_content(self, url: str) -> Optional[str]:
        """Get page content using Selenium"""
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, 10).until(
                lambda d: d.execute_script('return document.readyState') == 'complete'
            )
            return self.driver.page_source
        except Exception as e:
            logging.error(f"Error getting content from {url}: {e}")
            return None

    def process_url(self, url: str) -> Optional[Dict[str, str]]:
        """Process a single URL and return content in different formats"""
        try:
            logging.info(f"Processing URL: {url}")
            
            # Get HTML content
            html_content = self.get_page_content(url)
            if not html_content:
                return None

            # Convert to markdown
            markdown_content = self.converter.html_to_markdown(html_content)
            
            # Convert to text
            text_content = self.converter.markdown_to_text(markdown_content)
            
            return {
                'url': url,
                'markdown': markdown_content,
                'text': text_content
            }
        except Exception as e:
            logging.error(f"Error processing {url}: {e}")
            return None

    def create_pdf(self, contents: List[Dict[str, str]], output_path: str) -> bool:
        """Create PDF from processed contents"""
        try:
            doc = SimpleDocTemplate(
                output_path,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            styles = getSampleStyleSheet()
            story = []
            
            # Create custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                spaceAfter=30
            )
            
            url_style = ParagraphStyle(
                'URL',
                parent=styles['Normal'],
                textColor='blue',
                fontSize=10,
                spaceAfter=20
            )
            
            content_style = ParagraphStyle(
                'Content',
                parent=styles['Normal'],
                fontSize=11,
                leading=14,
                spaceAfter=30
            )
            
            # Add content for each URL
            for i, content in enumerate(contents, 1):
                # Add page break after first page
                if i > 1:
                    story.append(Spacer(1, 30))
                
                # Add URL as title
                story.append(Paragraph(f"Page {i}", title_style))
                story.append(Paragraph(content['url'], url_style))
                
                # Add main content
                text_chunks = content['text'].split('\n\n')
                for chunk in text_chunks:
                    if chunk.strip():
                        story.append(Paragraph(chunk, content_style))
            
            # Build PDF
            doc.build(story)
            return True
            
        except Exception as e:
            logging.error(f"Error creating PDF: {e}")
            return False

    def scrape_and_convert(self, max_depth: int = 2) -> Optional[str]:
        """Main method to scrape website and create PDF"""
        try:
            # Get URLs from parser
            urls = self.url_parser.get_all_urls(max_depth)
            if not urls:
                logging.error("No URLs found to process")
                return None

            # Process each URL
            processed_contents = []
            with tqdm(total=len(urls), desc="Processing URLs") as pbar:
                for url in urls:
                    content = self.process_url(url)
                    if content:
                        processed_contents.append(content)
                    pbar.update(1)

            if not processed_contents:
                logging.error("No content processed successfully")
                return None

            # Create output filename
            website_name = urlparse(self.url_parser.start_url).netloc.split('.')[0]
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            output_path = os.path.join(
                self.output_dir,
                f"{website_name}_content_{timestamp}.pdf"
            )

            # Create PDF
            if self.create_pdf(processed_contents, output_path):
                logging.info(f"Successfully created PDF: {output_path}")
                return output_path
            else:
                logging.error("Failed to create PDF")
                return None

        except Exception as e:
            logging.error(f"Error in scrape_and_convert: {e}")
            return None
        finally:
            if self.driver:
                self.driver.quit()

def main():
    # Configuration
    website_url = "https://cimex.com.np"
    output_directory = "website_content"
    max_depth = 2
    
    # Initialize
    url_parser = URLParser(website_url)
    scraper = WebScraper(url_parser, output_directory)
    
    try:
        # Run scraper
        output_path = scraper.scrape_and_convert(max_depth)
        if output_path:
            print(f"\nSuccessfully created PDF at: {output_path}")
        else:
            print("\nFailed to create PDF")
    except KeyboardInterrupt:
        print("\nProcess interrupted by user")
    except Exception as e:
        print(f"\nAn error occurred: {e}")
    finally:
        print("\nProcess complete!")

if __name__ == "__main__":
    main()