from __future__ import annotations

import json
import os
import re
from typing import Any

import requests

from .models import Event


CATEGORY_CONTEXT = {
    "国际政治": {
        "importance": "事件可能改变外交关系、政策预期或地区力量平衡。",
        "china": "关注相关外交立场、双边经贸安排以及对中国企业海外经营环境的影响。",
        "market": "政策与制裁预期可能通过风险偏好、汇率和跨境资本流动影响市场。",
        "indicators": ["官方声明与后续会谈", "制裁或政策文本落地", "主要经济体立场变化"],
    },
    "军事安全": {
        "importance": "安全局势升级会带来人员、贸易通道和地缘政治层面的连锁反应。",
        "china": "关注中国公民与企业安全、航运通道、能源进口和地区外交空间。",
        "market": "避险资产、能源价格、航运费率及国防板块可能出现波动。",
        "indicators": ["冲突范围与烈度", "停火或斡旋进展", "关键航线与基础设施状态"],
    },
    "经济金融": {
        "importance": "宏观政策与金融条件变化会影响全球增长、融资成本和资产定价。",
        "china": "关注外需、人民币汇率、跨境资金以及国内政策对冲空间。",
        "market": "利率、汇率、股票与大宗商品可能根据数据和政策预期重新定价。",
        "indicators": ["央行与财政部门表态", "通胀和就业数据", "利率、汇率与资金流向"],
    },
    "科技AI": {
        "importance": "技术突破与监管变化可能重塑产业竞争、资本开支和标准体系。",
        "china": "关注关键技术获取、国产替代、监管衔接与中国企业的全球竞争位置。",
        "market": "芯片、云计算、软件和设备产业链的估值与订单预期可能调整。",
        "indicators": ["产品与模型实际能力", "监管与出口限制", "企业资本开支和商业化数据"],
    },
    "能源资源": {
        "importance": "能源与关键资源供需变化会传导至通胀、工业成本和国家安全。",
        "china": "关注进口成本、供应稳定性、战略储备以及新能源产业链影响。",
        "market": "油气、金属、电力及相关运输和化工资产可能率先反应。",
        "indicators": ["产量与库存", "运输设施运行", "现货、期货与运费变化"],
    },
    "产业供应链": {
        "importance": "生产、物流或贸易规则变化可能造成跨行业交付与成本冲击。",
        "china": "关注出口订单、关键零部件供给、航运成本及产业链迁移。",
        "market": "制造、航运、港口和受影响行业公司的盈利预期可能变化。",
        "indicators": ["港口和工厂运行率", "交货周期与运价", "企业订单及库存"],
    },
    "社会突发": {
        "importance": "突发事件通常具有高不确定性，可能迅速扩大人道、治理和经济影响。",
        "china": "关注当地中国公民和项目安全、救援协作以及相关商品供给。",
        "market": "影响通常集中在当地资产、保险、交通和相关商品，需观察是否外溢。",
        "indicators": ["伤亡和受影响范围", "救援与基础设施恢复", "次生灾害或跨境扩散"],
    },
}


def _participants(event: Event) -> list[str]:
    text = " ".join(article.title for article in event.articles)
    candidates = re.findall(r"\b(?:[A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3}|[A-Z]{2,})\b", text)
    blocked = {
        "A", "An", "The", "This", "After", "Before", "How", "Live", "Latest",
        "New", "One", "Two", "Three", "World", "News", "Watch",
    }
    ordered: list[str] = []
    for candidate in candidates:
        if candidate not in blocked and candidate not in ordered:
            ordered.append(candidate)
    return ordered[:8] or event.sources[:5]


def fallback_analysis(event: Event) -> dict[str, Any]:
    context = CATEGORY_CONTEXT[event.category]
    newest = event.articles[:3]
    source_names = "、".join(event.sources[:4])
    what_happened = (
        f"据{source_names}等来源的{len(event.articles)}篇报道，"
        f"当前关注的{event.category}事件为“{event.title}”。"
        "以下内容依据标题和摘要自动整理；具体事实请核对原文。"
    )
    return {
        "what_happened": what_happened,
        "why_important": context["importance"],
        "participants": _participants(event),
        "latest_progress": [
            f"{article.published_at.strftime('%m月%d日 %H:%M')} UTC，"
            f"{article.source}报道：“{article.title}”。"
            for article in newest
        ],
        "china_impact": context["china"],
        "market_impact": context["market"],
        "watch_indicators": context["indicators"],
        "analysis_mode": "规则模板",
    }


class EventAnalyzer:
    endpoint = "https://api.openai.com/v1/responses"

    def __init__(self, api_key: str | None = None, model: str | None = None, timeout: int = 45):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPENAI_MODEL", "gpt-4.1-mini")
        self.timeout = timeout

    def analyze(self, event: Event) -> dict[str, Any]:
        fallback = fallback_analysis(event)
        if not self.api_key:
            return fallback
        try:
            result = self._call_api(event)
            result["analysis_mode"] = f"AI · {self.model}"
            return result
        except (requests.RequestException, ValueError, KeyError, json.JSONDecodeError):
            fallback["analysis_mode"] = "规则模板（AI 调用失败）"
            return fallback

    def _call_api(self, event: Event) -> dict[str, Any]:
        sources = [
            {
                "title": item.title,
                "summary": item.summary,
                "source": item.source,
                "published_at": item.published_at.isoformat(),
            }
            for item in event.articles[:12]
        ]
        prompt = (
            "你是全球事件分析编辑。仅依据给定报道，用简体中文输出严格 JSON。"
            "字段必须为 what_happened(string)、why_important(string)、participants(string array)、"
            "latest_progress(string array)、china_impact(string)、market_impact(string)、"
            "watch_indicators(string array)。区分事实、推断与待验证信息，不得虚构。\n"
            f"事件分类：{event.category}\n报道：{json.dumps(sources, ensure_ascii=False)}"
        )
        response = requests.post(
            self.endpoint,
            headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
            json={
                "model": self.model,
                "input": prompt,
                "text": {"format": {"type": "json_object"}},
                "temperature": 0.2,
            },
            timeout=self.timeout,
        )
        response.raise_for_status()
        payload = response.json()
        text = payload.get("output_text")
        if not text:
            for output in payload.get("output", []):
                for content in output.get("content", []):
                    if content.get("type") == "output_text":
                        text = content.get("text")
                        break
        if not text:
            raise ValueError("AI response did not contain output text")
        parsed = json.loads(text)
        required = {
            "what_happened", "why_important", "participants", "latest_progress",
            "china_impact", "market_impact", "watch_indicators",
        }
        if not required.issubset(parsed):
            raise ValueError("AI response is missing required fields")
        return parsed
