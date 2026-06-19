import re
import unicodedata

# Script detection: map each language code to its Unicode block range
SCRIPT_RANGES = {
    "arabic": (0x0600, 0x06FF),
    "devanagari": (0x0900, 0x097F),
    "cyrillic": (0x0400, 0x04FF),
    "greek": (0x0370, 0x03FF),
    "cjk": (0x4E00, 0x9FFF),  # CJK Unified Ideographs
    "hiragana": (0x3040, 0x309F),
    "katakana": (0x30A0, 0x30FF),
    "hangul": (0xAC00, 0xD7AF),
    "thai": (0x0E00, 0x0E7F),
    "latin": (0x0041, 0x024F),  # Basic Latin + Latin Extended
}


def detect_dominant_script(text: str) -> str:
    counts = {script: 0 for script in SCRIPT_RANGES}
    for ch in text:
        cp = ord(ch)
        for script, (lo, hi) in SCRIPT_RANGES.items():
            if lo <= cp <= hi:
                counts[script] += 1
                break
    if max(counts.values()) == 0:
        return "latin"  # safe default
    return max(counts, key=counts.get)


def normalize_unicode(text: str, script: str) -> str:
    if script in ("arabic", "devanagari"):
        return unicodedata.normalize("NFKD", text)
    else:
        return unicodedata.normalize("NFC", text)


def remove_noise(text: str) -> str:
    text = re.sub(r"https?://\S+|www\.\S+", " ", text)  # URLs
    text = re.sub(r"\S+@\S+\.\S+", " ", text)  # emails
    text = re.sub(r"<[^>]+>", " ", text)  # HTML tags
    text = re.sub(r"\d+", " ", text)  # numbers
    text = re.sub(r"[!\"#$%&'()*+,\-./:;<=>?@\[\\\]^_`{|}~]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def segment_cjk(text: str, lang: str) -> str:
    if lang == "zh":
        try:
            import jieba

            return " ".join(jieba.cut(text))
        except ImportError:
            pass
    elif lang == "ja":
        try:
            import fugashi

            tagger = fugashi.Tagger()
            return " ".join(w.surface for w in tagger(text))
        except ImportError:
            pass
    elif lang == "ko":
        try:
            from konlpy.tag import Okt

            okt = Okt()
            return " ".join(okt.morphs(text))
        except ImportError:
            pass
    return text


def segment_thai(text: str) -> str:
    try:
        from pythainlp.tokenize import word_tokenize

        return " ".join(word_tokenize(text, engine="newmm"))
    except ImportError:
        return text


def preprocess(text: str) -> str:
    """Standalone inference preprocessing that auto-detects script."""
    if not isinstance(text, str) or len(text.strip()) == 0:
        return ""

    script = detect_dominant_script(text)
    do_lower = script in ("latin", "cyrillic", "greek")

    text = normalize_unicode(text, script)
    if do_lower:
        text = text.lower()

    text = remove_noise(text)

    if script == "cjk":
        text = segment_cjk(text, "zh")
    elif script == "hiragana":
        text = segment_cjk(text, "ja")
    elif script == "hangul":
        text = segment_cjk(text, "ko")
    elif script == "thai":
        text = segment_thai(text)

    text = re.sub(r"\s+", " ", text).strip()
    return text
