import os
import re
import json
import asyncio
from typing import List, Dict, Tuple, Optional
from abc import ABC, abstractmethod
import httpx

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


class TranslationProvider(ABC):
    name: str
    display_name: str
    requires_key: bool = True
    base_url: str = ""

    @abstractmethod
    async def translate(self, text: str, api_key: str = "", model: str = "") -> str:
        pass

    def get_models(self) -> List[dict]:
        return []


class GoogleProvider(TranslationProvider):
    name = "google"
    display_name = "Google Translate"
    requires_key = False

    async def translate(self, text: str, api_key: str = "", model: str = "") -> str:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source='en', target='zh-CN')
        chunks = _split_text(text, 4500)
        results = []
        for chunk in chunks:
            try:
                r = await asyncio.to_thread(translator.translate, chunk)
                results.append(r or "")
            except Exception as e:
                results.append(f"[翻译错误]")
            await asyncio.sleep(0.1)
        return "".join(results)


class DeepLProvider(TranslationProvider):
    name = "deepl"
    display_name = "DeepL"
    requires_key = True
    base_url = "https://api-free.deepl.com/v2/translate"

    async def translate(self, text: str, api_key: str = "", model: str = "") -> str:
        async with httpx.AsyncClient(timeout=60) as client:
            chunks = _split_text(text, 50000)
            results = []
            for chunk in chunks:
                resp = await client.post(
                    self.base_url,
                    data={"auth_key": api_key, "text": chunk, "source_lang": "EN", "target_lang": "ZH"},
                )
                data = resp.json()
                results.append(data["translations"][0]["text"])
            return "".join(results)


class OpenAICompatibleProvider(TranslationProvider):
    name = "openai_compatible"
    display_name = "OpenAI Compatible"
    requires_key = True

    def __init__(self, name, display_name, base_url, default_model, models=None):
        self.name = name
        self.display_name = display_name
        self.base_url = base_url
        self.default_model = default_model
        self._models = models or [{"id": default_model, "name": default_model}]

    def get_models(self):
        return self._models

    async def translate(self, text: str, api_key: str = "", model: str = "") -> str:
        model = model or self.default_model
        chunks = _split_text(text, 4000)
        results = []
        async with httpx.AsyncClient(timeout=120) as client:
            for chunk in chunks:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                    json={
                        "model": model,
                        "messages": [
                            {"role": "system", "content": "You are a professional translator. Translate the following English text to Chinese (Simplified). Preserve paragraph breaks. Output ONLY the translation, no explanations."},
                            {"role": "user", "content": chunk}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 8000
                    }
                )
                data = resp.json()
                results.append(data["choices"][0]["message"]["content"])
                await asyncio.sleep(0.2)
        return "".join(results)


def _split_text(text: str, max_len: int) -> List[str]:
    if len(text) <= max_len:
        return [text]
    chunks = []
    paragraphs = text.split("\n\n")
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 2 <= max_len:
            current += ("\n\n" if current else "") + para
        else:
            if current:
                chunks.append(current)
            if len(para) > max_len:
                sentences = re.split(r'(?<=[.!?])\s+', para)
                sub_current = ""
                for sent in sentences:
                    if len(sub_current) + len(sent) + 1 <= max_len:
                        sub_current += (" " if sub_current else "") + sent
                    else:
                        if sub_current:
                            chunks.append(sub_current)
                        sub_current = sent
                if sub_current:
                    current = sub_current
                else:
                    current = ""
            else:
                current = para
    if current:
        chunks.append(current)
    return chunks


PROVIDERS: Dict[str, TranslationProvider] = {}


def _register_providers():
    global PROVIDERS
    PROVIDERS["google"] = GoogleProvider()
    PROVIDERS["deepl"] = DeepLProvider()

    PROVIDERS["gemini"] = OpenAICompatibleProvider(
        name="gemini", display_name="Google Gemini",
        base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        default_model="gemini-2.5-flash",
        models=[
            {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
            {"id": "gemini-2.5-pro", "name": "Gemini 2.5 Pro"},
            {"id": "gemini-2.0-flash", "name": "Gemini 2.0 Flash"},
        ]
    )

    PROVIDERS["claude"] = OpenAICompatibleProvider(
        name="claude", display_name="Anthropic Claude",
        base_url="https://api.anthropic.com/v1",
        default_model="claude-3-5-sonnet-20241022",
        models=[
            {"id": "claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet"},
            {"id": "claude-3-5-haiku-20241022", "name": "Claude 3.5 Haiku"},
        ]
    )

    PROVIDERS["deepseek"] = OpenAICompatibleProvider(
        name="deepseek", display_name="DeepSeek",
        base_url="https://api.deepseek.com/v1",
        default_model="deepseek-chat",
        models=[
            {"id": "deepseek-chat", "name": "DeepSeek V3"},
            {"id": "deepseek-reasoner", "name": "DeepSeek R1"},
        ]
    )

    PROVIDERS["qwen"] = OpenAICompatibleProvider(
        name="qwen", display_name="Qwen (通义千问)",
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        default_model="qwen-turbo",
        models=[
            {"id": "qwen-turbo", "name": "Qwen Turbo"},
            {"id": "qwen-plus", "name": "Qwen Plus"},
            {"id": "qwen-max", "name": "Qwen Max"},
            {"id": "qwen3-235b-a22b", "name": "Qwen3 235B"},
        ]
    )

    PROVIDERS["mimo"] = OpenAICompatibleProvider(
        name="mimo", display_name="MiMo (小米)",
        base_url="https://api.mimo.ai/v1",
        default_model="mimo-v2.5-pro",
        models=[{"id": "mimo-v2.5-pro", "name": "MiMo V2.5 Pro"}]
    )

    PROVIDERS["mimo_tokenplan"] = OpenAICompatibleProvider(
        name="mimo_tokenplan", display_name="MiMo Token Plan (小米订阅)",
        base_url="https://token-plan-cn.xiaomimimo.com/v1",
        default_model="mimo-v2.5-pro",
        models=[
            {"id": "mimo-v2.5-pro", "name": "MiMo V2.5 Pro"},
            {"id": "mimo-v2-flash", "name": "MiMo V2 Flash"},
        ]
    )

    PROVIDERS["openrouter"] = OpenAICompatibleProvider(
        name="openrouter", display_name="OpenRouter",
        base_url="https://openrouter.ai/api/v1",
        default_model="anthropic/claude-3.5-sonnet",
        models=[
            {"id": "anthropic/claude-3.5-sonnet", "name": "Claude 3.5 Sonnet"},
            {"id": "anthropic/claude-3.5-haiku", "name": "Claude 3.5 Haiku"},
            {"id": "google/gemini-2.5-flash", "name": "Gemini 2.5 Flash"},
            {"id": "deepseek/deepseek-chat-v3", "name": "DeepSeek V3"},
            {"id": "deepseek/deepseek-r1", "name": "DeepSeek R1"},
            {"id": "qwen/qwen3-235b-a22b", "name": "Qwen3 235B"},
        ]
    )

    PROVIDERS["siliconflow"] = OpenAICompatibleProvider(
        name="siliconflow", display_name="SiliconFlow (硅基流动)",
        base_url="https://api.siliconflow.cn/v1",
        default_model="deepseek-ai/DeepSeek-V3",
        models=[
            {"id": "deepseek-ai/DeepSeek-V3", "name": "DeepSeek V3"},
            {"id": "deepseek-ai/DeepSeek-R1", "name": "DeepSeek R1"},
            {"id": "Qwen/Qwen3-235B-A22B", "name": "Qwen3 235B"},
            {"id": "Pro/deepseek-ai/DeepSeek-V3", "name": "DeepSeek V3 (Pro)"},
        ]
    )

    PROVIDERS["custom"] = OpenAICompatibleProvider(
        name="custom", display_name="Custom (自定义)",
        base_url="", default_model="", models=[]
    )

    # Ollama (local)
    PROVIDERS["ollama"] = OpenAICompatibleProvider(
        name="ollama", display_name="Ollama (本地)",
        base_url="http://localhost:11434/v1",
        default_model="qwen2.5:7b",
        models=[
            {"id": "qwen2.5:7b", "name": "Qwen2.5 7B"},
            {"id": "qwen2.5:14b", "name": "Qwen2.5 14B"},
            {"id": "qwen2.5:32b", "name": "Qwen2.5 32B"},
            {"id": "llama3.1:8b", "name": "Llama 3.1 8B"},
            {"id": "llama3.1:70b", "name": "Llama 3.1 70B"},
            {"id": "deepseek-r1:7b", "name": "DeepSeek R1 7B"},
            {"id": "deepseek-r1:14b", "name": "DeepSeek R1 14B"},
            {"id": "deepseek-r1:32b", "name": "DeepSeek R1 32B"},
            {"id": "gemma2:9b", "name": "Gemma 2 9B"},
            {"id": "mistral:7b", "name": "Mistral 7B"},
        ]
    )

    # LM Studio / LocalAI (local)
    PROVIDERS["local"] = OpenAICompatibleProvider(
        name="local", display_name="Local (本地自定义)",
        base_url="http://localhost:1234/v1",
        default_model="",
        models=[]
    )


_register_providers()


def get_provider(name: str) -> Optional[TranslationProvider]:
    return PROVIDERS.get(name)


def get_all_providers() -> List[dict]:
    result = []
    for p in PROVIDERS.values():
        result.append({
            "name": p.name,
            "display_name": p.display_name,
            "requires_key": p.requires_key,
            "models": p.get_models()
        })
    return result


def parse_paragraphs(text: str) -> List[str]:
    """Split text into meaningful paragraphs for translation."""
    paragraphs = re.split(r'\n\s*\n|\n', text)
    result = []
    for p in paragraphs:
        p = p.strip()
        if len(p) > 10:
            result.append(p)
    return result


async def translate_paragraphs(
    paragraphs: List[str],
    provider_name: str = "google", api_key: str = "", model: str = "",
    custom_url: str = "", custom_model: str = ""
) -> List[str]:
    """Translate each paragraph individually."""
    provider = get_provider(provider_name)
    if not provider:
        raise ValueError(f"Unknown provider: {provider_name}")

    if provider_name == "custom" and custom_url:
        provider = OpenAICompatibleProvider(
            name="custom", display_name="Custom",
            base_url=custom_url, default_model=custom_model or "gpt-4o-mini"
        )

    translated = []
    for i, para in enumerate(paragraphs):
        try:
            result = await provider.translate(para, api_key=api_key, model=model)
            translated.append(result)
        except Exception as e:
            translated.append(f"[翻译失败]")
        await asyncio.sleep(0.1)

    return translated


async def translate_chapter(
    text: str, ielts_words: Dict[str, dict],
    provider_name: str = "google", api_key: str = "", model: str = "",
    custom_url: str = "", custom_model: str = ""
) -> Tuple[str, List[dict]]:
    marked_text, found_words = mark_ielts_words(text, ielts_words)

    paragraphs = parse_paragraphs(text)
    translated_paras = await translate_paragraphs(
        paragraphs, provider_name, api_key, model, custom_url, custom_model
    )

    bilingual_parts = []
    for orig, trans in zip(paragraphs, translated_paras):
        bilingual_parts.append(f'<div class="para-pair"><p class="orig">{orig}</p><p class="trans">{trans}</p></div>')

    return "\n".join(bilingual_parts), found_words
