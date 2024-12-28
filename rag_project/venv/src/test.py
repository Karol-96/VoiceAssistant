import fitz  # PyMuPDF
import os

def print_pdf_content(pdf_path, num_pages=3):
    try:
        # Verify file exists
        if not os.path.exists(pdf_path):
            print(f"Error: File not found at {pdf_path}")
            return

        # Open PDF
        print(f"\nOpening PDF: {pdf_path}")
        doc = fitz.open(pdf_path)
        print(f"Total pages in PDF: {len(doc)}")
        
        # Print content from first few pages
        for page_num in range(min(num_pages, len(doc))):
            page = doc[page_num]
            text = page.get_text()
            print(f"\n--- Page {page_num + 1} ---")
            print(f"Page length: {len(text)} characters")
            print("First 500 characters of content:")
            print("-" * 50)
            print(text[:500])
            print("-" * 50)

        doc.close()

    except Exception as e:
        print(f"Error reading PDF: {str(e)}")

# Your PDF path
pdf_path = "/Users/karolbhandari/Desktop/Customer Care/website_content/cimex_complete_20241228_202336.pdf"

# Run the test
print_pdf_content(pdf_path)