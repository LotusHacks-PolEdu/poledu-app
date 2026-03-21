import asyncio
import os
import json
from llama_parse import LlamaParse

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))


async def parse_pdf(pdf_path: str) -> list:
    """Parse a PDF file using LlamaParse and return a list of page pages.

    Args:
        pdf_path: Path to the PDF file.

    Returns:
        List of parsed page objects.
    """
    # Load API key from credentials.json
    creds_path = os.path.join(_BASE_DIR, "credentials.json")
    with open(creds_path, "r", encoding="utf-8") as f:
        creds = json.load(f)

    parser = LlamaParse(
        api_key=creds["llama_parse"],
        result_type="markdown",
        split_by_page=True,
        verbose=True,
    )

    pages = await parser.aload_data(pdf_path)
    with open(pdf_path+".txt","w", encoding="utf-8") as f:
        for i, page in enumerate(pages):
                page_text = page.text if hasattr(page, "text") else str(page)
                f.write(f"--- Chunk {i} (Length: {len(page_text)} | Page {i + 1}) ---\n")
                f.write(page_text + "\n\n")
    return pages


if __name__ == "__main__":
    result = asyncio.run(parse_pdf("sudic.pdf"))
    print(f"Parsed {len(result)} pages")
