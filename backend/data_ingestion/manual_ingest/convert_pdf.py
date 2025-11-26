import fitz  # PyMuPDF

def pdf_to_text(pdf_path: str) -> str:
    """
    Extracts text from a PDF.
    If no meaningful text is found, automatically performs OCR on each page.
    """

    doc = fitz.open(pdf_path)
    full_text = ""

    # Pass 1 — normal extraction
    for page in doc:
        text = page.get_text("text")
        if text and len(text.strip()) > 50:
            full_text += text + "\n"
    
    # If normal extraction worked, return it
    if len(full_text.strip()) > 100:
        doc.close()
        return full_text

    # Otherwise: PASS 2 — perform OCR
    print(f"🔄 OCR mode activated for: {pdf_path}")

    ocr_text = ""
    for page in doc:
        text = page.get_text("text", flags=fitz.TEXTFLAGS_TEXT)
        if text:
            ocr_text += text + "\n"

        # If still no text, fallback: convert to image + OCR
        if not text.strip():
            pix = page.get_pixmap(dpi=200)
            img_bytes = pix.tobytes("png")
            try:
                # PyMuPDF now supports OCR via page.get_text("ocr")
                ocr_page = page.get_text("ocr")
                ocr_text += ocr_page + "\n"
            except:
                ocr_text += ""

    doc.close()
    return ocr_text
