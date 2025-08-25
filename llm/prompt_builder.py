# llm/prompt_builder.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Dict, Any
import json, re

def _clip(s: str, n: int) -> str:
    if s is None: return ""
    s = re.sub(r"\s+", " ", str(s)).strip()
    return s[:n] + "…" if len(s) > n else s

def _coerce_doc(d: Dict[str,Any], tmax=180, amax=1200) -> Dict[str,Any]:
    return {
        "title": _clip(d.get("title",""), tmax),
        "url": d.get("url",""),
        "abstract": _clip(d.get("abstract",""), amax),
        "venue": _clip(d.get("venue",""), 80),
        "year": d.get("year",""),
        "authors": d.get("authors", [])[:10],
        "keywords": d.get("keywords", [])[:8],
        "scores": d.get("scores", {}),      # {"hybrid":..,"dense":..,"ce":..}
        "evidence": d.get("evidence", {}),  # {"numbers":[...], "code":"...", "pdf":"..."}
    }

@dataclass
class PromptBuilder:
    style: str = "standard"  # "concise"|"standard"|"detailed"

    @property
    def system_ko(self) -> str:
        return (
            "당신은 정확한 연구 요약가입니다. 출력은 GitHub‑Flavored Markdown으로 작성합니다. "
            "사적 추론(<think> ... </think>)은 절대 출력하지 마세요. "
            "최종 답변은 <final> ... </final> 로 감싸서 출력하라"
            "오직 최종결과만 한국어로 작성합니다. "
            "링크는 입력 url만 사용하고, '~입니다' 톤으로 간결하게 작성합니다."
        )

    def _docs_json(self, docs: List[Dict[str,Any]]) -> str:
        safe = [_coerce_doc(d) for d in docs]
        return json.dumps({"papers": safe}, ensure_ascii=False, indent=2)

    def research_cards(self, user_instruction: str, docs: List[Dict[str,Any]], show_scores: bool=True) -> Dict[str,str]:
        length = {
            "concise": "TL;DR 20–30자, 카드당 불릿 4–6개.",
            "standard": "TL;DR 30–50자, 카드당 불릿 6–9개.",
            "detailed": "TL;DR 50–80자, 카드당 불릿 8–12개."
        }[self.style]
        user = f"""아래 JSON의 user_instruction과 papers를 바탕으로,
각 논문을 '리서치 카드' 형식으로 요약
제목, 요약, 링크 순서로 작성

입력 JSON:
```
json{{
  "user_instruction": "{_clip(user_instruction, 400)}",
  "papers": []
}}
papers 데이터:

{self._docs_json(docs)}
"""
        
        return {"system": self.system_ko, "user": user}
