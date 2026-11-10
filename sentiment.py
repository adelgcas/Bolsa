"""Puntuación de sentimiento de titulares en [-1, 1]. FinBERT si está disponible; si no, léxico simple."""
import re

_POS = {"surge", "soar", "beat", "beats", "record", "growth", "profit", "upgrade", "rally", "gain",
        "gains", "strong", "boost", "wins", "approval", "expands", "rises", "jumps", "cut rates"}
_NEG = {"plunge", "fall", "falls", "miss", "misses", "loss", "losses", "downgrade", "lawsuit", "probe",
        "recall", "weak", "cuts", "layoffs", "fraud", "ban", "tariff", "tariffs", "drops", "slump",
        "recession", "default", "crisis", "war", "sanctions"}

_pipe = None


def _load_finbert():
    global _pipe
    if _pipe is None:
        try:
            from transformers import pipeline
            _pipe = pipeline("text-classification", model="ProsusAI/finbert", top_k=None, truncation=True)
        except Exception:
            _pipe = False
    return _pipe


def _lexicon(text):
    words = re.findall(r"[a-z]+", text.lower())
    pos = sum(w in _POS for w in words)
    neg = sum(w in _NEG for w in words)
    return 0.0 if pos + neg == 0 else (pos - neg) / (pos + neg)


def score(texts, batch_size=32):
    texts = [str(t) for t in texts]
    pipe = _load_finbert()
    if not pipe:
        return [_lexicon(t) for t in texts]
    out = []
    for i in range(0, len(texts), batch_size):
        for res in pipe(texts[i:i + batch_size]):
            d = {r["label"].lower(): r["score"] for r in res}
            out.append(d.get("positive", 0.0) - d.get("negative", 0.0))
    return out
