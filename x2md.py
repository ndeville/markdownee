"""
x2md - Convert documents (PDF, DOCX, PPTX, TXT) to Markdown.

Runs multiple conversion backends in parallel, then uses Claude to merge
the best elements from each into a single clean Markdown output.

Usage:
    python x2md.py document.pdf
    python x2md.py presentation.pptx
    python x2md.py report.docx

As a module:
    from x2md import convert2md
    markdown = convert2md("/path/to/file.pdf")
"""

from datetime import datetime
import os
import sys
import time
import argparse
import re
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

_running_as_cli = __name__ == '__main__'
if _running_as_cli:
    ts_time = datetime.now().strftime('%H:%M:%S')
    print(f"\n---------- {ts_time} starting {os.path.basename(__file__)}")
    start_time = time.time()


# ---------------------------------------------------------------------------
# File type detection
# ---------------------------------------------------------------------------

SUPPORTED_EXTENSIONS = {
    '.pdf', '.docx', '.pptx', '.txt', '.rtf', '.html', '.htm',
    '.csv', '.xlsx', '.xls', '.epub', '.md', '.json', '.xml',
}

PDF_EXTENSIONS = {'.pdf'}
DOCX_EXTENSIONS = {'.docx'}
PPTX_EXTENSIONS = {'.pptx'}
TEXT_EXTENSIONS = {'.txt', '.md', '.csv', '.json', '.xml', '.rtf'}


def detect_file_type(file_path: str) -> str:
    """Return the lowercase extension of the file."""
    return Path(file_path).suffix.lower()


# ---------------------------------------------------------------------------
# Converter backends
# ---------------------------------------------------------------------------

def convert_markitdown(file_path: str) -> str | None:
    """Microsoft MarkItDown - broad format support, clean LLM-friendly output."""
    try:
        from markitdown import MarkItDown
        md = MarkItDown()
        result = md.convert(file_path)
        text = result.text_content
        if text and text.strip():
            return text.strip()
    except Exception as e:
        print(f"  [markitdown] failed: {e}", file=sys.stderr)
    return None


def convert_pymupdf4llm(file_path: str) -> str | None:
    """PyMuPDF4LLM - LLM-optimized markdown from PDFs with layout awareness."""
    try:
        import pymupdf4llm
        text = pymupdf4llm.to_markdown(
            file_path,
            show_progress=False,
            force_text=True,
        )
        if text and text.strip():
            return text.strip()
    except Exception as e:
        print(f"  [pymupdf4llm] failed: {e}", file=sys.stderr)
    return None


def convert_mammoth(file_path: str) -> str | None:
    """Mammoth - semantic DOCX-to-markdown, preserves document structure."""
    try:
        import mammoth
        with open(file_path, 'rb') as f:
            result = mammoth.convert_to_markdown(f)
            text = result.value
            if text and text.strip():
                return text.strip()
    except Exception as e:
        print(f"  [mammoth] failed: {e}", file=sys.stderr)
    return None


def convert_pdfplumber(file_path: str) -> str | None:
    """pdfplumber - excellent table extraction from PDFs."""
    try:
        import pdfplumber
        parts = []
        with pdfplumber.open(file_path) as pdf:
            for i, page in enumerate(pdf.pages):
                page_parts = []

                # Extract tables
                tables = page.extract_tables()
                table_bboxes = []
                if tables:
                    for tbl in page.find_tables():
                        table_bboxes.append(tbl.bbox)

                    for table in tables:
                        if not table:
                            continue
                        # Build markdown table
                        cleaned = []
                        for row in table:
                            cleaned.append([
                                (cell or '').strip().replace('\n', ' ')
                                for cell in row
                            ])
                        if not cleaned:
                            continue
                        header = cleaned[0]
                        md_table = '| ' + ' | '.join(header) + ' |\n'
                        md_table += '| ' + ' | '.join(['---'] * len(header)) + ' |\n'
                        for row in cleaned[1:]:
                            # Pad row if shorter than header
                            while len(row) < len(header):
                                row.append('')
                            md_table += '| ' + ' | '.join(row[:len(header)]) + ' |\n'
                        page_parts.append(md_table)

                # Extract text (outside tables where possible)
                text = page.extract_text()
                if text and text.strip():
                    page_parts.insert(0, text.strip())

                if page_parts:
                    parts.append(f"<!-- Page {i + 1} -->\n\n" + '\n\n'.join(page_parts))

        if parts:
            return '\n\n---\n\n'.join(parts)
    except Exception as e:
        print(f"  [pdfplumber] failed: {e}", file=sys.stderr)
    return None


def convert_pptx_native(file_path: str) -> str | None:
    """python-pptx - direct slide-by-slide extraction with structure."""
    try:
        from pptx import Presentation
        from pptx.util import Inches
        prs = Presentation(file_path)
        parts = []

        for slide_num, slide in enumerate(prs.slides, 1):
            slide_parts = [f"## Slide {slide_num}"]

            # Get slide title
            if slide.shapes.title and slide.shapes.title.text.strip():
                slide_parts[0] = f"## Slide {slide_num}: {slide.shapes.title.text.strip()}"

            # Extract notes
            notes_text = None
            if slide.has_notes_slide and slide.notes_slide.notes_text_frame:
                notes_text = slide.notes_slide.notes_text_frame.text.strip()

            for shape in slide.shapes:
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        text = para.text.strip()
                        if not text:
                            continue
                        # Detect bullet level
                        level = para.level or 0
                        if level > 0:
                            indent = '  ' * (level - 1)
                            slide_parts.append(f"{indent}- {text}")
                        else:
                            # Skip if it's the title (already captured)
                            if shape == slide.shapes.title:
                                continue
                            slide_parts.append(text)

                if shape.has_table:
                    table = shape.table
                    rows = []
                    for row in table.rows:
                        cells = [cell.text.strip().replace('\n', ' ') for cell in row.cells]
                        rows.append(cells)
                    if rows:
                        header = rows[0]
                        md_table = '| ' + ' | '.join(header) + ' |\n'
                        md_table += '| ' + ' | '.join(['---'] * len(header)) + ' |\n'
                        for row in rows[1:]:
                            while len(row) < len(header):
                                row.append('')
                            md_table += '| ' + ' | '.join(row[:len(header)]) + ' |\n'
                        slide_parts.append(md_table)

            if notes_text:
                slide_parts.append(f"\n> **Notes:** {notes_text}")

            parts.append('\n\n'.join(slide_parts))

        if parts:
            return '\n\n---\n\n'.join(parts)
    except Exception as e:
        print(f"  [pptx-native] failed: {e}", file=sys.stderr)
    return None


def convert_docx_native(file_path: str) -> str | None:
    """python-docx - direct paragraph/table extraction preserving styles."""
    try:
        from docx import Document
        from docx.enum.text import WD_ALIGN_PARAGRAPH
        doc = Document(file_path)
        parts = []

        for element in doc.element.body:
            tag = element.tag.split('}')[-1]

            if tag == 'p':
                # It's a paragraph
                for para in [p for p in doc.paragraphs if p._element is element]:
                    text = para.text.strip()
                    if not text:
                        continue
                    style_name = (para.style.name or '').lower()

                    if 'heading 1' in style_name:
                        parts.append(f"# {text}")
                    elif 'heading 2' in style_name:
                        parts.append(f"## {text}")
                    elif 'heading 3' in style_name:
                        parts.append(f"### {text}")
                    elif 'heading 4' in style_name:
                        parts.append(f"#### {text}")
                    elif 'heading' in style_name:
                        parts.append(f"##### {text}")
                    elif 'list' in style_name or 'bullet' in style_name:
                        level = para.paragraph_format.left_indent
                        if level and level > 0:
                            parts.append(f"  - {text}")
                        else:
                            parts.append(f"- {text}")
                    else:
                        # Check for bold/italic runs
                        formatted = _format_docx_runs(para)
                        parts.append(formatted)

            elif tag == 'tbl':
                # It's a table
                for table in [t for t in doc.tables if t._element is element]:
                    rows = []
                    for row in table.rows:
                        cells = [cell.text.strip().replace('\n', ' ') for cell in row.cells]
                        rows.append(cells)
                    if rows:
                        header = rows[0]
                        md_table = '| ' + ' | '.join(header) + ' |\n'
                        md_table += '| ' + ' | '.join(['---'] * len(header)) + ' |\n'
                        for row in rows[1:]:
                            while len(row) < len(header):
                                row.append('')
                            md_table += '| ' + ' | '.join(row[:len(header)]) + ' |\n'
                        parts.append(md_table)

        if parts:
            return '\n\n'.join(parts)
    except Exception as e:
        print(f"  [docx-native] failed: {e}", file=sys.stderr)
    return None


def _format_docx_runs(para) -> str:
    """Format a docx paragraph's runs with bold/italic markdown."""
    parts = []
    for run in para.runs:
        text = run.text
        if not text:
            continue
        if run.bold and run.italic:
            text = f"***{text}***"
        elif run.bold:
            text = f"**{text}**"
        elif run.italic:
            text = f"*{text}*"
        parts.append(text)
    result = ''.join(parts).strip()
    return result if result else para.text.strip()


def convert_text_direct(file_path: str) -> str | None:
    """Direct read for text-based files."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            text = f.read()
        if text and text.strip():
            return text.strip()
    except UnicodeDecodeError:
        try:
            with open(file_path, 'r', encoding='latin-1') as f:
                text = f.read()
            if text and text.strip():
                return text.strip()
        except Exception as e:
            print(f"  [text-direct] failed: {e}", file=sys.stderr)
    except Exception as e:
        print(f"  [text-direct] failed: {e}", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# Converter registry - maps file types to applicable backends
# ---------------------------------------------------------------------------

CONVERTERS = {
    '.pdf': [
        ('markitdown', convert_markitdown),
        ('pymupdf4llm', convert_pymupdf4llm),
        ('pdfplumber', convert_pdfplumber),
    ],
    '.docx': [
        ('markitdown', convert_markitdown),
        ('mammoth', convert_mammoth),
        ('docx-native', convert_docx_native),
    ],
    '.pptx': [
        ('markitdown', convert_markitdown),
        ('pptx-native', convert_pptx_native),
    ],
    '.txt': [('text-direct', convert_text_direct)],
    '.md': [('text-direct', convert_text_direct)],
    '.csv': [('text-direct', convert_text_direct), ('markitdown', convert_markitdown)],
    '.json': [('text-direct', convert_text_direct)],
    '.xml': [('text-direct', convert_text_direct)],
    '.rtf': [('markitdown', convert_markitdown)],
    '.html': [('markitdown', convert_markitdown)],
    '.htm': [('markitdown', convert_markitdown)],
    '.xlsx': [('markitdown', convert_markitdown)],
    '.xls': [('markitdown', convert_markitdown)],
    '.epub': [('markitdown', convert_markitdown)],
}


# ---------------------------------------------------------------------------
# Claude merge skill
# ---------------------------------------------------------------------------

MERGE_SYSTEM_PROMPT = """You are a document conversion specialist. You receive multiple Markdown
conversions of the same source document, each produced by a different conversion tool.

Your job: produce the single best Markdown version by merging the strengths of each input.

Rules:
- Preserve ALL content from the original document. Do not drop sections, paragraphs, or data.
- Use the version with the best heading structure (proper # hierarchy).
- Use the version with the best table formatting (aligned pipes, complete cells).
- Use the version with the best list formatting (consistent bullets, proper nesting).
- Preserve bold, italic, and other inline formatting where any version captured it.
- Remove conversion artifacts: extra whitespace, repeated headers, garbled text.
- If one version has content another is missing, include it.
- Output clean Markdown only. No commentary, no explanations, no wrapper.
- Do not add any content that wasn't in the original document.
- Use standard hyphens for lists, never em-dashes."""

def merge_with_claude(
    results: dict[str, str],
    file_name: str,
    model: str = "claude-opus-4-6",
) -> str | None:
    """Send multiple converter outputs to Claude and get a merged best version."""
    try:
        import anthropic
        client = anthropic.Anthropic()

        # Build the prompt with each converter's output
        sections = []
        for name, text in results.items():
            # Truncate very long outputs to stay within context limits
            truncated = text[:80_000] if len(text) > 80_000 else text
            sections.append(
                f"=== OUTPUT FROM: {name.upper()} ===\n\n{truncated}\n\n"
                f"=== END {name.upper()} ==="
            )

        user_prompt = (
            f"Source file: {file_name}\n\n"
            f"Below are {len(results)} different Markdown conversions of the same document. "
            f"Merge them into the single best Markdown output.\n\n"
            + "\n\n".join(sections)
        )

        # Check total size - if too large, use extended thinking or trim
        total_chars = len(user_prompt)
        print(f"  [claude-merge] sending {total_chars:,} chars from {len(results)} converters")

        response = client.messages.create(
            model=model,
            max_tokens=16384,
            system=MERGE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )

        merged = response.content[0].text
        if merged and merged.strip():
            return merged.strip()

    except Exception as e:
        print(f"  [claude-merge] failed: {e}", file=sys.stderr)
    return None


# ---------------------------------------------------------------------------
# Core conversion logic
# ---------------------------------------------------------------------------

def convert2md(file_path: str, use_claude: bool = True) -> str:
    """Convert a document to Markdown.

    Runs all applicable backends in parallel, then optionally merges via Claude.
    Returns the Markdown string.
    """
    file_path = os.path.abspath(file_path)
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = detect_file_type(file_path)
    file_name = os.path.basename(file_path)

    if ext not in CONVERTERS:
        raise ValueError(
            f"Unsupported file type: {ext}\n"
            f"Supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    converters = CONVERTERS[ext]
    print(f"  Converting {file_name} ({ext}) with {len(converters)} backend(s)...")

    # Run converters in parallel
    results: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=len(converters)) as executor:
        future_to_name = {
            executor.submit(fn, file_path): name
            for name, fn in converters
        }
        for future in as_completed(future_to_name):
            name = future_to_name[future]
            try:
                output = future.result()
                if output:
                    results[name] = output
                    print(f"  [{name}] OK ({len(output):,} chars)")
                else:
                    print(f"  [{name}] returned empty")
            except Exception as e:
                print(f"  [{name}] crashed: {e}", file=sys.stderr)

    if not results:
        raise RuntimeError(f"All converters failed for {file_name}")

    # If only one converter produced output, return it directly
    if len(results) == 1:
        print(f"  Single converter succeeded, using directly.")
        return list(results.values())[0]

    # Multiple outputs - merge with Claude if enabled
    if use_claude and len(results) > 1:
        print(f"  Merging {len(results)} outputs with Claude...")
        merged = merge_with_claude(results, file_name)
        if merged:
            print(f"  [claude-merge] OK ({len(merged):,} chars)")
            return merged
        print(f"  [claude-merge] failed, falling back to best single output")

    # Fallback: return the longest output (usually most complete)
    best_name = max(results, key=lambda k: len(results[k]))
    print(f"  Using [{best_name}] as best single output ({len(results[best_name]):,} chars)")
    return results[best_name]


def convert_and_save(file_path: str, output_path: str | None = None, use_claude: bool = True) -> str:
    """Convert a document and save the Markdown to a file.

    Returns the output file path.
    """
    markdown = convert2md(file_path, use_claude=use_claude)

    if output_path is None:
        base, _ = os.path.splitext(file_path)
        output_path = f"{base}.md"

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(markdown)

    return output_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Convert documents (PDF, DOCX, PPTX, TXT, etc.) to Markdown'
    )
    parser.add_argument('input', nargs='?', help='File path to convert')
    parser.add_argument('-o', '--output', help='Output .md file path (default: same name as input)')
    parser.add_argument('--no-claude', action='store_true', help='Skip Claude merge, use best single converter')
    parser.add_argument('--no-open', action='store_true', help='Do not open the output file in VS Code')
    args = parser.parse_args()

    input_path = args.input
    if not input_path:
        input_path = input("\nEnter file path to convert: ").strip()

    # Strip quotes that might come from drag-and-drop
    input_path = input_path.strip("'\"")

    if not os.path.isfile(input_path):
        print(f"\nFile not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    try:
        output_file = convert_and_save(
            input_path,
            output_path=args.output,
            use_claude=not args.no_claude,
        )
        print(f"\nMarkdown saved to: {output_file}")

        if not args.no_open:
            os.system(f"open -a 'Visual Studio Code' '{output_file}'")

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)

    print('\n-------------------------------')
    run_time = round((time.time() - start_time), 3)
    if run_time < 1:
        print(f'\n{os.path.basename(__file__)} finished in {round(run_time*1000)}ms at {datetime.now().strftime("%H:%M:%S")}.\n')
    elif run_time < 60:
        print(f'\n{os.path.basename(__file__)} finished in {round(run_time)}s at {datetime.now().strftime("%H:%M:%S")}.\n')
    elif run_time < 3600:
        print(f'\n{os.path.basename(__file__)} finished in {round(run_time/60)}mns at {datetime.now().strftime("%H:%M:%S")}.\n')
    else:
        print(f'\n{os.path.basename(__file__)} finished in {round(run_time/3600, 2)}hrs at {datetime.now().strftime("%H:%M:%S")}.\n')
