"""
Разбиение длинного текста на чанки по границам предложений с перекрытием
(overlap), чтобы не терять контекст на стыках при последующем поиске.
"""
import re
from common.config import settings

# Разбиваем по предложениям: точка/!/?/перенос строки + пробел/конец
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def split_into_sentences(text: str) -> list[str]:
    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]
    return sentences


def chunk_text(
    text: str,
    max_chars: int = settings.CHUNK_MAX_CHARS,
    overlap_chars: int = settings.CHUNK_OVERLAP_CHARS,
) -> list[str]:
    """
    Короткие посты (меньше max_chars) остаются одним чанком.
    Длинные — режутся по предложениям с overlap_chars символов перекрытия
    между соседними чанками.
    """
    text = text.strip()
    if len(text) <= max_chars:
        return [text] if text else []

    sentences = split_into_sentences(text)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        candidate = f"{current} {sentence}".strip()
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
                # перекрытие: хвост предыдущего чанка переносим в начало следующего
                tail = current[-overlap_chars:] if overlap_chars > 0 else ""
                current = f"{tail} {sentence}".strip()
            else:
                # одно предложение длиннее max_chars — режем жёстко по символам
                for i in range(0, len(sentence), max_chars):
                    chunks.append(sentence[i:i + max_chars])
                current = ""

    if current:
        chunks.append(current)

    return chunks
