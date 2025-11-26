def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50):
    """
    Splits text into overlapping word-based chunks.
    """
    words = text.split()
    chunks = []
    start = 0

    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start = end - overlap

    return chunks
