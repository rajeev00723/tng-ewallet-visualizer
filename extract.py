import pdfplumber
import re
from pdf2image import convert_from_path
import pytesseract

def extract_with_pdfplumber(pdf_path, password):
    transactions = []
    try:
        with pdfplumber.open(pdf_path, password=password) as pdf:
            for page_number, page in enumerate(pdf.pages, start=1):
                text = page.extract_text()
                if not text:
                    print(f"⚠️ Page {page_number} has no extractable text.")
                    continue

                print(f"\n--- Page {page_number} Text Sample ---\n{text[:500]}")

                matches = re.findall(
                    r'(?P<date>\d{1,2}/\d{1,2}/2025).*?(?P<type>Receive from Wallet|PayDirect Payment|DUITNOW_RECEI).*?(?P<name>[A-Z\s\/]+)?\s+.*?RM(?P<amount>\d+\.\d{2})\s+RM(?P<balance>\d+\.\d{2})',
                    text,
                    flags=re.DOTALL
                )

                for match in matches:
                    transactions.append({
                        "date": match[0],
                        "type": match[1].strip(),
                        "name": match[2].strip() if match[2] else "",
                        "amount": float(match[3]),
                        "balance": float(match[4])
                    })
    except Exception as e:
        print(f"❌ Error using pdfplumber: {e}")
    return transactions


def extract_with_ocr(pdf_path):
    print("🔁 Falling back to OCR...")
    transactions = []
    try:
        pages = convert_from_path(pdf_path)
        for i, page in enumerate(pages, start=1):
            print(f"🔍 OCR processing page {i}...")
            text = pytesseract.image_to_string(page)

            print(f"\n--- OCR Page {i} Text Sample ---\n{text[:500]}")

            matches = re.findall(
                r'(?P<date>\d{1,2}/\d{1,2}/2025).*?(?P<type>Receive from Wallet|PayDirect Payment|DUITNOW_RECEI).*?(?P<name>[A-Z\s\/]+)?\s+.*?RM(?P<amount>\d+\.\d{2})\s+RM(?P<balance>\d+\.\d{2})',
                text,
                flags=re.DOTALL
            )

            for match in matches:
                transactions.append({
                    "date": match[0],
                    "type": match[1].strip(),
                    "name": match[2].strip() if match[2] else "",
                    "amount": float(match[3]),
                    "balance": float(match[4])
                })
    except Exception as e:
        print(f"❌ Error using OCR: {e}")
    return transactions


if __name__ == "__main__":
    pdf_path = "tng.pdf"
    pdf_password = "196657848"
    
    print(f"📥 Extracting from: {pdf_path} with password")
    
    txns = extract_with_pdfplumber(pdf_path, pdf_password)
    
    if not txns:
        print("⚠️ No transactions found with pdfplumber.")
        txns = extract_with_ocr(pdf_path)

    if not txns:
        print("❌ Still no transactions found.")
    else:
        print(f"✅ Extracted {len(txns)} transactions:\n")
        for txn in txns:
            print(txn)
