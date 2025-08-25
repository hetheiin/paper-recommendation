# llm/base_model.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Optional, Dict, Any
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

import re #think 태그 제거용

THINK_RE = re.compile(r"<\s*think\s*>.*?<\s*/\s*think\s*>", re.DOTALL | re.IGNORECASE)
FINAL_RE = re.compile(r"<\s*final\s*>(.*?)<\s*/\s*final\s*>", re.DOTALL | re.IGNORECASE)
FINAL_RE_2 = re.compile(r"끝\s*(.*)", re.DOTALL | re.IGNORECASE)

def _strip_think(text: str) -> str:
    text_wo_think = re.sub(THINK_RE, "", text).strip()
    return text_wo_think

def extract_final(text: str) -> str:
    final_contents = FINAL_RE_2.search(text)
    return final_contents.group(1).strip()

try:
    from transformers import BitsAndBytesConfig
except Exception:
    BitsAndBytesConfig = None

@dataclass
class LocalLLMConfig:
    model_id: str = "Qwen/Qwen3-0.6B"     # 0.6B 시작. 품질 필요시 "Qwen/Qwen3-1.7B" or "Qwen/Qwen3-4B-Instruct-2507"
    device: str = "cpu"                    # "cpu" | "cuda"
    dtype: str = "auto"                    # "auto" | "float16" | "bfloat16" | "float32"
    load_in_4bit: bool = False             # GPU로 로드할때 양자화해서 로드
    load_in_8bit: bool = False

    trust_remote_code: bool = True         # Hugging Face 모델 로드시 신뢰할 수 있는 코드 사용
    max_new_tokens: int = 2048              # 생성할 최대 토큰 수
    temperature: float = 0.2               # 생성 온도 (0.0–1.0)
    top_p: float = 0.9                     # Top-p 샘플링 (0.0–1.0)
    repetition_penalty: float = 1.05       # 반복 패널티 (1.0–2.0)
    do_sample: bool = True                 # 샘플링 여부 (True/False)

class BaseLocalLLM:
    def __init__(self, cfg: LocalLLMConfig, model=None, tokenizer=None):
        self.cfg = cfg
        torch_dtype = self._resolve_dtype(cfg.dtype) # 상태 보고 타입 선택
        quant = None
        if (cfg.load_in_4bit or cfg.load_in_8bit) and BitsAndBytesConfig is not None: #양자화
            quant = BitsAndBytesConfig(
                load_in_4bit=cfg.load_in_4bit,
                load_in_8bit=cfg.load_in_8bit,
                bnb_4bit_compute_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )



        model_kwargs: Dict[str, Any] = dict(trust_remote_code=cfg.trust_remote_code)
        if quant:
            model_kwargs["quantization_config"] = quant
            model_kwargs["device_map"] = "auto"
        else:
            if torch_dtype is not None:
                model_kwargs["torch_dtype"] = torch_dtype

        if model is None:
            self.model = AutoModelForCausalLM.from_pretrained(cfg.model_id, **model_kwargs)
            self.tok = AutoTokenizer.from_pretrained(cfg.model_id, trust_remote_code=cfg.trust_remote_code,
                                                     use_fast=True)
            if not quant and cfg.device in ("cpu", "cuda"):
                self.model.to(cfg.device)
        else:
            self.model = model
            self.tok = tokenizer

    def _resolve_dtype(self, dtype: str): #상태 보고 타입 선택
        if dtype == "auto":
            if torch.cuda.is_available():
                return torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
            return torch.float32
        return {"float16": torch.float16, "bfloat16": torch.bfloat16, "float32": torch.float32}.get(dtype, None)

    def _build_chat(self, system: str, user: str) -> Dict[str, torch.Tensor]:
        if hasattr(self.tok, "apply_chat_template"):
            messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
            s = self.tok.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
            return self.tok(s, return_tensors="pt").to(self.model.device)
        # fallback
        prompt = f"<<SYS>>\n{system}\n<</SYS>>\n[USER]\n{user}\n[/USER]\n[ASSISTANT]"
        return self.tok(prompt, return_tensors="pt").to(self.model.device)

    def generate(self, system: str, user: str) -> str:
        inputs = self._build_chat(system, user)
        out = self.model.generate(
            **inputs,
            max_new_tokens=self.cfg.max_new_tokens,
            temperature=self.cfg.temperature,
            top_p=self.cfg.top_p,
            repetition_penalty=self.cfg.repetition_penalty,
            do_sample=self.cfg.do_sample,
        )
        raw = self.tok.decode(out[0], skip_special_tokens=True).strip()
        txt = _strip_think(raw)

        return txt
