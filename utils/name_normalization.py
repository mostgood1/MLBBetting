import unicodedata

def normalize_name(name: str | None) -> str:
    if not name:
        return ''
    try:
        text = unicodedata.normalize('NFD', name)
        text = ''.join(ch for ch in text if unicodedata.category(ch) != 'Mn')
        return ' '.join(text.lower().strip().split())
    except Exception:
        return name.lower().strip() if name else ''
