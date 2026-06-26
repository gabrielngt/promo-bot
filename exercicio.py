
def _count_keywords(title: str, keywords: list[str]):
    t = title.lower()
    return sum(kw.lower() in t for kw in keywords)
