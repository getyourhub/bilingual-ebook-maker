import os
import re
import html as html_lib
from pathlib import Path
from typing import List, Dict, Tuple, Optional

import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup


def parse_epub(filepath) -> Tuple[List[dict], dict]:
    filepath = str(filepath)
    book = epub.read_epub(filepath)

    metadata = {
        "title": _get_meta(book, "DC", "title") or Path(filepath).stem,
        "author": _get_meta(book, "DC", "creator") or "Unknown",
        "language": _get_meta(book, "DC", "language") or "en",
        "source": filepath
    }

    chapters = []
    for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
        soup = BeautifulSoup(item.get_content(), "html.parser")
        text = soup.get_text(separator="\n", strip=True)
        if len(text.strip()) < 50:
            continue

        title_tag = soup.find(["h1", "h2", "h3", "title"])
        title = title_tag.get_text(strip=True) if title_tag else f"Chapter {len(chapters)+1}"

        chapters.append({
            "title": title[:100],
            "text": text,
            "html": str(soup),
            "item_name": item.get_name()
        })

    if not chapters:
        raise ValueError("No readable chapters found in EPUB")

    return chapters, metadata


def parse_pdf(filepath) -> Tuple[List[dict], dict]:
    filepath = str(filepath)
    import pdfplumber

    metadata = {
        "title": Path(filepath).stem,
        "author": "Unknown",
        "language": "en",
        "source": filepath
    }

    chapters = []
    current_text = []
    chapter_num = 0

    with pdfplumber.open(filepath) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if not text.strip():
                continue

            lines = text.strip().split("\n")
            for line in lines:
                if _is_chapter_heading(line) and current_text:
                    chapter_num += 1
                    full_text = "\n".join(current_text)
                    if len(full_text.strip()) > 100:
                        chapters.append({
                            "title": f"Chapter {chapter_num}",
                            "text": full_text
                        })
                    current_text = []
                current_text.append(line)

    if current_text:
        full_text = "\n".join(current_text)
        if len(full_text.strip()) > 50:
            chapters.append({
                "title": f"Chapter {len(chapters)+1}",
                "text": full_text
            })

    if not chapters:
        raise ValueError("No readable content found in PDF")

    return chapters, metadata


def _is_chapter_heading(line: str) -> bool:
    line = line.strip()
    patterns = [
        r'^(chapter|CHAPTER)\s+\d+',
        r'^\d+\.\s+[A-Z]',
        r'^PART\s+[IVX\d]+',
    ]
    return any(re.match(p, line) for p in patterns)


def _get_meta(book, ns, name):
    try:
        vals = book.get_metadata(ns, name)
        if vals:
            return vals[0][0]
    except:
        pass
    return None


def get_book_info(filepath) -> dict:
    filepath = str(filepath)
    try:
        if filepath.lower().endswith(".epub"):
            book = epub.read_epub(filepath)
            return {
                "title": _get_meta(book, "DC", "title") or Path(filepath).stem,
                "author": _get_meta(book, "DC", "creator") or "Unknown",
                "type": "EPUB"
            }
        else:
            return {
                "title": Path(filepath).stem,
                "author": "Unknown",
                "type": "PDF"
            }
    except Exception as e:
        return {
            "title": Path(filepath).stem,
            "author": "Unknown",
            "type": "Unknown",
            "error": str(e)
        }


def build_bilingual_epub(
    original_chapters: List[dict],
    translated_chapters: List[dict],
    metadata: dict,
    output_path: str,
    ielts_stats: dict
):
    book = epub.EpubBook()

    book.set_identifier(f"bilingual-{id(book)}")
    book.set_title(f"{metadata['title']} (Bilingual EN/CN)")
    book.set_language("en")
    book.add_author(metadata.get("author", "Unknown"))

    style = _get_epub_css()
    css_item = epub.EpubItem(
        uid="style",
        file_name="style/default.css",
        media_type="text/css",
        content=style.encode("utf-8")
    )
    book.add_item(css_item)

    toc = []
    spine = ["nav"]

    for i, (orig, trans) in enumerate(zip(original_chapters, translated_chapters)):
        chapter_html = _build_chapter_html(orig, trans, i+1)
        ch = epub.EpubHtml(
            title=orig["title"],
            file_name=f"chapter_{i+1:03d}.xhtml",
            lang="en"
        )
        ch.content = chapter_html.encode("utf-8")
        ch.add_item(css_item)
        book.add_item(ch)
        toc.append(ch)
        spine.append(ch)

    ielts_page = _build_ielts_page(translated_chapters, ielts_stats)
    ielts_ch = epub.EpubHtml(
        title="IELTS Vocabulary / 雅思词汇",
        file_name="ielts_vocabulary.xhtml",
        lang="en"
    )
    ielts_ch.content = ielts_page.encode("utf-8")
    ielts_ch.add_item(css_item)
    book.add_item(ielts_ch)
    toc.append(ielts_ch)
    spine.append(ielts_ch)

    book.toc = toc
    book.spine = spine

    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    epub.write_epub(output_path, book)


def _build_chapter_html(orig: dict, trans: dict, num: int) -> str:
    title = html_lib.escape(orig["title"])
    translated_content = trans.get("translated", "")

    body_parts = [f'<h1 class="chapter-title">{title}</h1>']

    if translated_content:
        body_parts.append(translated_content)
    else:
        paragraphs = orig["text"].split("\n")
        for para in paragraphs:
            if para.strip():
                body_parts.append(f'<p>{html_lib.escape(para)}</p>')

    ielts_marks = trans.get("ielts_words", [])
    if ielts_marks:
        words_html = ""
        for w in ielts_marks[:50]:
            words_html += f'''
            <div class="word-card">
                <span class="word">{html_lib.escape(w["word"])}</span>
                <span class="phonetic">{html_lib.escape(w.get("phonetic", ""))}</span>
                <span class="pos">{html_lib.escape(w.get("pos", ""))}</span>
                <span class="meaning">{html_lib.escape(w.get("meaning", ""))}</span>
            </div>'''
        body_parts.append(f'''
        <div class="ielts-section">
            <h2>📚 IELTS Vocabulary in This Chapter / 本章雅思词汇</h2>
            <div class="word-grid">{words_html}</div>
        </div>
        ''')

    return "\n".join(body_parts)


def _build_ielts_page(chapters: list, stats: dict) -> str:
    all_words = {}
    for ch in chapters:
        for w in ch.get("ielts_words", []):
            key = w["word"].lower()
            if key not in all_words:
                all_words[key] = w

    words_html = ""
    for w in sorted(all_words.values(), key=lambda x: x["word"].lower()):
        words_html += f'''
        <tr>
            <td class="word">{html_lib.escape(w["word"])}</td>
            <td class="phonetic">{html_lib.escape(w.get("phonetic", ""))}</td>
            <td class="pos">{html_lib.escape(w.get("pos", ""))}</td>
            <td class="meaning">{html_lib.escape(w.get("meaning", ""))}</td>
        </tr>'''

    return f'''
    <h1>📚 IELTS 7+ Vocabulary / 雅思7分词汇</h1>
    <p class="summary">Total unique words found: {len(all_words)} / 共发现 {len(all_words)} 个雅思高频词汇</p>
    <table class="ielts-table">
        <thead>
            <tr>
                <th>Word / 词汇</th>
                <th>Phonetic / 音标</th>
                <th>POS / 词性</th>
                <th>Meaning / 释义</th>
            </tr>
        </thead>
        <tbody>
            {words_html}
        </tbody>
    </table>
    '''


def _get_epub_css() -> str:
    return '''
    @import url('https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;700&family=Merriweather:ital,wght@0,400;0,700;1,400&display=swap');

    body {
        font-family: 'Merriweather', 'Noto Serif SC', Georgia, serif;
        line-height: 1.8;
        color: #2c2c2c;
        padding: 1em;
        max-width: 800px;
        margin: 0 auto;
        background-color: #fdfaf6;
    }

    h1.chapter-title {
        font-size: 1.8em;
        color: #1a3a5c;
        border-bottom: 2px solid #c8a96e;
        padding-bottom: 0.5em;
        margin-bottom: 1.5em;
        text-align: center;
    }

    .para-pair {
        margin-bottom: 1.5em;
        padding: 0.8em;
        border-left: 3px solid #c8a96e;
        background: #faf8f5;
        border-radius: 0 6px 6px 0;
    }

    .para-pair .orig {
        font-size: 1.05em;
        color: #2c2c2c;
        margin-bottom: 0.5em;
        line-height: 1.9;
    }

    .para-pair .trans {
        font-size: 0.95em;
        color: #5a6e82;
        line-height: 1.8;
        padding-left: 0.5em;
        border-left: 2px solid #d4d4d4;
    }

    .ielts-word {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        padding: 1px 4px;
        border-radius: 3px;
        border-bottom: 2px solid #e17055;
        cursor: help;
        font-weight: 600;
    }

    .ielts-section {
        margin-top: 2em;
        padding: 1.5em;
        background: #f8f5f0;
        border-radius: 8px;
        border: 1px solid #e0d5c5;
    }

    .ielts-section h2 {
        color: #1a3a5c;
        font-size: 1.3em;
        margin-bottom: 1em;
    }

    .word-grid {
        display: flex;
        flex-wrap: wrap;
        gap: 0.8em;
    }

    .word-card {
        display: inline-block;
        padding: 0.5em 0.8em;
        background: white;
        border-radius: 6px;
        border: 1px solid #d4c5a9;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }

    .word-card .word {
        font-weight: 700;
        color: #c0392b;
        margin-right: 0.5em;
    }

    .word-card .phonetic {
        color: #7f8c8d;
        font-size: 0.9em;
        margin-right: 0.5em;
    }

    .word-card .pos {
        color: #2980b9;
        font-size: 0.85em;
        margin-right: 0.5em;
        font-style: italic;
    }

    .word-card .meaning {
        color: #555;
        font-size: 0.9em;
    }

    .summary {
        color: #5a6e82;
        font-style: italic;
        margin-bottom: 1.5em;
    }

    .ielts-table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 1em;
    }

    .ielts-table th {
        background: #1a3a5c;
        color: white;
        padding: 0.8em;
        text-align: left;
    }

    .ielts-table td {
        padding: 0.6em 0.8em;
        border-bottom: 1px solid #e0d5c5;
    }

    .ielts-table tr:nth-child(even) {
        background: #f8f5f0;
    }

    .ielts-table .word {
        font-weight: 700;
        color: #c0392b;
    }

    .ielts-table .phonetic {
        color: #7f8c8d;
    }

    .ielts-table .pos {
        color: #2980b9;
        font-style: italic;
    }
    '''
