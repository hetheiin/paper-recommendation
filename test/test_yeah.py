from crawler import *

keyword_dict = {
    "main": [
        ["multimodal", "vision-language", "vlm"],   # 동의어 그룹 1 (OR)
        ["reasoning", "chain of thought", "cot"],   # 동의어 그룹 2 (OR)
        ["memory", "long-term memory"]              # 동의어 그룹 3 (OR)
    ],
    "optional": ["tool-use", "agent", "planning"]
}

instruction = "I want to read multimodal paper. for example, vision-language vlm. and reasoning chain of thought cot and memory long-term memory tool-use agent and planning paper."

query = soft_parsing_arxiv(keyword_dict)
print(query)

query2 = soft_parsing_openreview(keyword_dict)
print(query2)

# document = main_crawling(keyword_dict, field="all", num=150, date=None, accept=False, openreview=True)
# document_print(document)

document = main_crawling(keyword_dict, field="all", num=150, date=None, accept=True)
document_print(document)