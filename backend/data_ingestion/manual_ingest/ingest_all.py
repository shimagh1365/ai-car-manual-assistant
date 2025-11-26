import os
from convert_pdf import pdf_to_text
from chunk_text import chunk_text
from embed_store import add_chunks_to_db

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
MANUAL_ROOT = os.path.join(PROJECT_ROOT, "manuals", "ali-and-sons")


def ingest_all_manuals():
    print("📘 Starting ingestion of manuals...\n")

    if not os.path.exists(MANUAL_ROOT):
        print(f"❌ Manuals folder not found: {MANUAL_ROOT}")
        return

    for brand in os.listdir(MANUAL_ROOT):
        brand_folder = os.path.join(MANUAL_ROOT, brand)
        if not os.path.isdir(brand_folder):
            continue

        print(f"\n🔍 Brand: {brand}")

        for filename in os.listdir(brand_folder):
            if not filename.lower().endswith(".pdf"):
                continue

            pdf_path = os.path.join(brand_folder, filename)
            vehicle_key = filename.replace(".pdf", "")
            collection_name = f"{brand.lower()}_manuals"

            print(f"   📄 Ingesting: {filename}")

            try:
                # Extract including OCR if needed
                text = pdf_to_text(pdf_path)

                if not text or len(text.strip()) < 50:
                    raise Exception("❌ PDF contains no readable text — even after OCR")

                # Chunk safely
                chunks = chunk_text(text, chunk_size=500, overlap=50)

                if not chunks:
                    raise Exception("❌ No chunks produced from PDF text")

                add_chunks_to_db(collection_name, vehicle_key, chunks)

                print(f"   ✅ Done: {filename} — added {len(chunks)} chunks to `{collection_name}`")

            except Exception as e:
                print(f"   ❌ Error processing {filename}: {e}")

    print("\n🎉 Ingestion completed with text + OCR support!")


# ---------------------------------------------------------
# AUTO-RUN WHEN EXECUTED DIRECTLY
# ---------------------------------------------------------
if __name__ == "__main__":
    ingest_all_manuals()
