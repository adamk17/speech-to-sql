"""
Extracts relevant chapters from PostgreSQL 15 documentation PDF.
Saves all selected chapters as a single merged file.

Page numbers are based on the PDF page index (0-based),
not the printed page numbers in the document.
Offset 38: PDF page index = printed page number + 38 - 1
"""

import pikepdf
import os

INPUT_PDF = "data/postgresql-15-A4.pdf"
OUTPUT_DIR = "data/pg_docs_extracted"
OUTPUT_FILE = "extracted.pdf"

# Offset between printed page numbers and 0-based PDF page index.
# Verified manually: printed page 109 = PDF index 146 → offset = 38
OFFSET = 38

# Printed page ranges from Table of Contents
CHAPTERS = [
    {
        "name": "03_advanced_features",
        "title": "Chapter 3: Advanced Features (views tutorial, window functions tutorial)",
        "start": 17,
        "end": 24,
    },
    {
        "name": "05_data_definition",
        "title": "Chapter 5: Data Definition (CREATE TABLE, constraints, schemas, partitioning)",
        "start": 58,
        "end": 107,
    },
    {
        "name": "06_data_manipulation",
        "title": "Chapter 6: Data Manipulation (INSERT, UPDATE, DELETE)",
        "start": 109,
        "end": 112,
    },
    {
        "name": "07_queries",
        "title": "Chapter 7: Queries (SELECT, JOIN, CTE, subqueries)",
        "start": 113,
        "end": 143,
    },
    {
        "name": "08_data_types",
        "title": "Chapter 8: Data Types (numeric, text, date, boolean)",
        "start": 144,
        "end": 216,
    },
    {
        "name": "09_functions_operators",
        "title": "Chapter 9: Functions and Operators",
        "start": 217,
        "end": 407,
    },
    {
        "name": "10_type_conversion",
        "title": "Chapter 10: Type Conversion (CAST, ::)",
        "start": 408,
        "end": 420,
    },
    {
        "name": "41_views",
        "title": "Chapter 41.2-41.3: CREATE VIEW and MATERIALIZED VIEW",
        "start": 1244,
        "end": 1254,
    },
]


def extract_chapters():
    print(f"Reading: {INPUT_PDF}")
    pdf = pikepdf.open(INPUT_PDF)
    total_pages = len(pdf.pages)
    print(f"Total PDF pages: {total_pages}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    merged = pikepdf.Pdf.new()
    total_extracted = 0

    for chapter in CHAPTERS:
        pdf_start = chapter["start"] + OFFSET - 1  # 0-based index
        pdf_end = chapter["end"] + OFFSET           # exclusive

        pdf_start = max(0, min(pdf_start, total_pages - 1))
        pdf_end = max(0, min(pdf_end, total_pages))

        for page_num in range(pdf_start, pdf_end):
            merged.pages.append(pdf.pages[page_num])

        pages_extracted = pdf_end - pdf_start
        total_extracted += pages_extracted
        print(f"  + {chapter['name']} — {pages_extracted} pages "
              f"(printed {chapter['start']}–{chapter['end']})")

    output_path = os.path.join(OUTPUT_DIR, OUTPUT_FILE)
    merged.save(output_path)

    print(f"\nDone! {output_path} ({total_extracted} pages)")


if __name__ == "__main__":
    extract_chapters()