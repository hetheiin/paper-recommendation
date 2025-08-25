# llm/generater_research_cards.py
from __future__ import annotations
from typing import List, Dict, Any, Tuple
from .base_model import BaseLocalLLM, LocalLLMConfig
from .prompt_builder import PromptBuilder

def generate_research_cards_markdown(
    docs: List[Dict[str,Any]],
    query: str,
    model_id: str = "Qwen/Qwen3-0.6B",
    device: str = "cpu",
    dtype: str = "auto",
    style: str = "standard",
    max_new_tokens: int = 2048,
    load_in_4bit: bool = False,
    load_in_8bit: bool = False,
    model = None,
    tokenizer = None,
) -> str:
    prompts = PromptBuilder(style=style).research_cards(
        user_instruction=query, docs=docs, show_scores=True
    )
    cfg = LocalLLMConfig(
        model_id=model_id, device=device, dtype=dtype,
        max_new_tokens=max_new_tokens,
        temperature=0.2, top_p=0.9, do_sample=True,
        load_in_4bit=load_in_4bit, load_in_8bit=load_in_8bit,
    )

    if model is None or tokenizer is None:
        llm = BaseLocalLLM(cfg)
    else:
        llm = BaseLocalLLM(cfg, model, tokenizer)
    return llm.generate(system=prompts["system"], user=prompts["user"])


def generate_single_card_markdown(
    doc: Dict[str, Any],
    query: str,
    model_id: str = "Qwen/Qwen3-1.7B",
    device: str = "cpu",
    dtype: str = "auto",
    style: str = "standard",
    max_new_tokens: int = 1200,
    load_in_4bit: bool = False,
    load_in_8bit: bool = False,
    model = None,
    tokenizer = None,
) -> str:
    return generate_research_cards_markdown(
        docs=[doc],
        query=query,
        model_id=model_id,
        device=device,
        dtype=dtype,
        style=style,
        max_new_tokens=max_new_tokens,
        load_in_4bit=load_in_4bit,
        load_in_8bit=load_in_8bit,
        model=model,
        tokenizer=tokenizer,
    )


# 2) 여러 카드(문자열)로부터 최종 비교표만 생성
def generate_comparison_table_from_cards(
    cards_md: List[str],
    query: str,
    model_id: str = "Qwen/Qwen3-1.7B",
    device: str = "cpu",
    dtype: str = "auto",
    max_new_tokens: int = 800,
    load_in_4bit: bool = False,
    load_in_8bit: bool = False,
    model = None,
    tokenizer = None,
) -> str:
    """
    cards_md: generate_single_card_markdown() 로 만든 카드 MD 문자열들의 리스트.
    반환: 모델이 생성한 '최종 비교표' 마크다운
    """
    # 비교표 생성 전용 간단 프롬프트
    system = (
        "당신은 정확한 연구 요약가입니다. 출력은 GitHub‑Flavored Markdown으로 작성합니다. "
        "오직 최종 결과만 한국어로 작성합니다."
        "결과는 반드시 <final> ... </final> 로 감싸서 출력합니다.\n"
    )
    # 카드 리스트를 그대로 넣어, 표만 만들도록 요구
    joined_cards = "\n\n---\n\n".join(cards_md)
    user = (
        "아래 여러 논문의 '리서치 카드' 요약을 입력으로 제공합니다. "
        "이 정보를 종합하여, 다음 열 순서를 가진 단 하나의 비교표만 생성하세요.\n\n"
        "| 순위 | 제목 | 설명 | 링크 |\n\n"
        "규칙:\n"
        "1) 표만 출력합니다. 불릿/문단/설명은 출력하지 않습니다.\n"
        "2) 수치가 없으면 해당 셀은 '-' 로 표기합니다.\n"
        "3) 링크는 카드 내에 있는 URL만 사용합니다.\n"
        "4) 결과는 반드시 <final> ... </final> 로 감싸서 출력합니다.\n"
        
        f"사용자 질의: {query}\n\n"
        "입력 카드들:\n"
        f"{joined_cards}\n"
    )

    cfg = LocalLLMConfig(
        model_id=model_id, device=device, dtype=dtype,
        max_new_tokens=max_new_tokens,
        temperature=0.2, top_p=0.9, do_sample=True,
        load_in_4bit=load_in_4bit, load_in_8bit=load_in_8bit,
    )
    if model is None or tokenizer is None:
        llm = BaseLocalLLM(cfg)
    else:
        llm = BaseLocalLLM(cfg, model, tokenizer)
    return llm.generate(system=system, user=user)
