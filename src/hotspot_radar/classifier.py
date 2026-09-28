from __future__ import annotations

import re
from collections import Counter

from .models import Article


CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "军事安全": (
        "war", "military", "missile", "attack", "troops", "army", "navy",
        "defence", "defense", "security", "ceasefire", "nuclear", "weapon",
        "战争", "军事", "导弹", "袭击", "军队", "停火", "核武", "安全",
    ),
    "国际政治": (
        "election", "president", "minister", "government", "diplomatic",
        "sanction", "summit", "parliament", "treaty", "border", "united nations",
        "选举", "总统", "政府", "外交", "制裁", "峰会", "议会", "条约",
    ),
    "经济金融": (
        "economy", "inflation", "interest rate", "central bank", "market", "stocks",
        "bond", "currency", "trade", "tariff", "gdp", "recession", "financial",
        "经济", "通胀", "利率", "央行", "市场", "股市", "债券", "汇率", "关税",
    ),
    "科技AI": (
        "artificial intelligence", " ai ", "semiconductor", "chip", "technology",
        "cyber", "robot", "space", "quantum", "data center", "software",
        "人工智能", "芯片", "半导体", "科技", "网络安全", "机器人", "量子",
    ),
    "能源资源": (
        "oil", "gas", "energy", "opec", "pipeline", "mining", "copper", "lithium",
        "electricity", "renewable", "climate", "carbon", "原油", "天然气", "能源",
        "矿产", "锂", "电力", "可再生", "气候",
    ),
    "产业供应链": (
        "supply chain", "shipping", "factory", "manufacturing", "export", "import",
        "port", "logistics", "automotive", "airline", "container", "供应链", "航运",
        "制造", "出口", "进口", "港口", "物流", "汽车产业",
    ),
    "社会突发": (
        "earthquake", "flood", "wildfire", "hurricane", "storm", "explosion",
        "accident", "protest", "outbreak", "pandemic", "evacuation", "death",
        "地震", "洪水", "山火", "飓风", "爆炸", "事故", "抗议", "疫情", "撤离",
    ),
}

CATEGORY_PRIORITY = [
    "军事安全", "国际政治", "经济金融", "科技AI", "能源资源", "产业供应链", "社会突发"
]


def classify_articles(articles: list[Article]) -> tuple[str, dict[str, int]]:
    title_text = " ".join(item.title for item in articles).lower()
    summary_text = " ".join(item.summary for item in articles).lower()
    scores: Counter[str] = Counter()
    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            normalized = keyword.strip()
            if re.fullmatch(r"[a-z0-9 -]+", normalized):
                pattern = rf"\b{re.escape(normalized)}\b"
                title_matches = len(re.findall(pattern, title_text))
                summary_matches = len(re.findall(pattern, summary_text))
            else:
                title_matches = title_text.count(normalized)
                summary_matches = summary_text.count(normalized)
            scores[category] += min(title_matches, 3) * 2 + min(summary_matches, 3)
    if not scores or max(scores.values(), default=0) == 0:
        return "国际政治", dict(scores)
    winner = max(CATEGORY_PRIORITY, key=lambda name: (scores[name], -CATEGORY_PRIORITY.index(name)))
    return winner, dict(scores)
