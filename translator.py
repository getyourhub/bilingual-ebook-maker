import os
import re
import json
import asyncio
from typing import List, Dict, Tuple
from deep_translator import GoogleTranslator

translator = GoogleTranslator(source='en', target='zh-CN')

IELTS_PATH = os.path.join(os.path.dirname(__file__), "data", "ielts_words.json")

_ielts_cache = None


def load_ielts_words() -> Dict[str, dict]:
    global _ielts_cache
    if _ielts_cache:
        return _ielts_cache

    words = {}
    try:
        with open(IELTS_PATH, "r", encoding="utf-8") as f:
            raw = json.load(f)
            for item in raw:
                word = item["word"].lower().strip()
                words[word] = {
                    "word": item["word"],
                    "phonetic": item.get("phonetic", ""),
                    "meaning": item.get("meaning", ""),
                    "pos": item.get("pos", "")
                }
    except Exception as e:
        print(f"Warning: Could not load IELTS words: {e}")
        words = {}
    _ielts_cache = words
    return words


def mark_ielts_words(text: str, ielts_words: Dict[str, dict]) -> Tuple[str, List[dict]]:
    found = []
    seen = set()

    def replace_match(m):
        word = m.group(0)
        lower = word.lower().strip(".,!?;:\"'()[]{}")
        if lower in ielts_words and lower not in seen:
            seen.add(lower)
            info = ielts_words[lower]
            found.append(info)
            return f'<span class="ielts-word" data-word="{info["word"]}" data-phonetic="{info["phonetic"]}" data-meaning="{info["meaning"]}" data-pos="{info["pos"]}">{word}</span>'
        return word

    pattern = r'\b[a-zA-Z]{3,}\b'
    marked = re.sub(pattern, replace_match, text)
    return marked, found


async def translate_text(text: str, max_chunk: int = 4500) -> str:
    if not text.strip():
        return ""

    chunks = split_text(text, max_chunk)
    translated_parts = []

    for chunk in chunks:
        try:
            result = await asyncio.to_thread(
                translator.translate, chunk
            )
            translated_parts.append(result or "")
        except Exception as e:
            print(f"Translation error: {e}")
            translated_parts.append(f"[Translation Error] {chunk[:100]}...")
        await asyncio.sleep(0.1)

    return "".join(translated_parts)


def split_text(text: str, max_len: int) -> List[str]:
    if len(text) <= max_len:
        return [text]

    chunks = []
    sentences = re.split(r'(?<=[.!?])\s+', text)
    current = ""

    for sent in sentences:
        if len(current) + len(sent) + 1 <= max_len:
            current += (" " if current else "") + sent
        else:
            if current:
                chunks.append(current)
            if len(sent) > max_len:
                sub = [sent[i:i+max_len] for i in range(0, len(sent), max_len)]
                chunks.extend(sub[:-1])
                current = sub[-1]
            else:
                current = sent

    if current:
        chunks.append(current)

    return chunks


async def translate_chapter(
    text: str, ielts_words: Dict[str, dict]
) -> Tuple[str, List[dict]]:
    marked_text, found_words = mark_ielts_words(text, ielts_words)
    translated = await translate_text(text)
    return translated, found_words
