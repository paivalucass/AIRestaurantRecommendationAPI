import re

def clean_text(text: str):
    text = text.lower()
    text = re.sub(r"[^a-z0-9áéíóúãõç ]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()