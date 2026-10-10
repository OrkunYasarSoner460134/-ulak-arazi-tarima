import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
KNOWLEDGE = Path(__file__).with_name("knowledge.json")
BASE_MODEL = ROOT / "models" / "base"
ADAPTER = ROOT / "models" / "adapter"

SYSTEM_PROMPT = (
    "Sen Ulak'ın Türkçe heyelan ve zemin bilgisi asistanısın. "
    "Yalnızca verilen kaynak kartındaki bilgilerle yanıt ver. "
    "Bir parsel için inşaat izni, temel tasarımı, kesin güvenlik kararı veya sayısal heyelan olasılığı verme. "
    "Kaynak kartı yetersizse bunu açıkça söyle. Kısa, anlaşılır Türkçe kullan. "
    "Kaynak URL'si uydurma; kaynak bağlantıları sistem tarafından ayrıca gösterilir."
)


def load_cards():
    return json.loads(KNOWLEDGE.read_text(encoding="utf-8"))


def _normalize(value):
    return value.casefold().replace("i\u0307", "i").translate(str.maketrans("çğıöşü", "cgiosu"))


def _matches(term, question, question_tokens):
    """Match Turkish terms while tolerating common inflection suffixes."""
    if " " in term:
        return term in question
    if term in question_tokens:
        return True
    if len(term) >= 5:
        return any(token.startswith(term) or term.startswith(token) for token in question_tokens if len(token) >= 5)
    return False


def select_cards(question, limit=2):
    question = _normalize(question)
    tokens = set(re.findall(r"\w+", question))
    ranked = []
    for card in load_cards():
        keywords = [_normalize(word) for word in card["keywords"]]
        matches = [word for word in keywords if _matches(word, question, tokens)]
        if not matches:
            continue
        score = 5 * len(matches)
        relevant_words = set(re.findall(r"\w+", _normalize(card["title"] + " " + " ".join(card["questions"]))))
        score += 2 * len(tokens & relevant_words)
        if any(_normalize(example) in question for example in card["questions"]):
            score += 8
        if score:
            ranked.append((score, card))
    ranked.sort(key=lambda item: (-item[0], item[1]["id"]))
    if len(ranked) > 1 and ranked[0][0] >= ranked[1][0] + 8:
        return [ranked[0][1]]
    return [card for _, card in ranked[:limit]]


def context_for(cards):
    return "\n".join(f"[{card['id']}] {card['title']}: {card['fact']}" for card in cards)


def user_message(question, cards):
    return f"Kaynak kartları:\n{context_for(cards)}\n\nSoru: {question}"
