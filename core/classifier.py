import re
import json
import os
from utils.helpers import get_app_dir


def load_keyword_map(path=None):
    if path is None:
        path = os.path.join(get_app_dir(), "keyword_map.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def classify(title, content, keyword_map):
    best_cat = "00-待分类"
    best_score = 0

    for cat, keywords in keyword_map.items():
        score = 0
        for kw in keywords:
            pattern = re.compile(re.escape(kw), re.IGNORECASE)
            if pattern.search(title):
                score += 4
            if pattern.search(content):
                score += 2
            if kw.lower() in title.lower():
                score += 1

        if score > best_score:
            best_score = score
            best_cat = cat

    return best_cat
