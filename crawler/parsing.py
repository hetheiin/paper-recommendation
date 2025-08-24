from crawler.query import *

# 근데 이거 반드시 ''로 감싼 키워드를 주든가 내가 ''를 없애고 다시 붙여서 사용해야 할듯
def hard_parsing_arxiv(keyword_dict: dict, field: str = "all") -> str:
    """
    (Main1 AND Main2) AND (Optional1 AND Optional2)
    """
    main_list = keyword_dict.get('main', [])
    optional_list = keyword_dict.get('optional', [])

    main_sub_queries = []
    for synonym_list in main_list:
        sub_query = make_query_arxiv(synonym_list, operator=["OR"], field=[field])
        main_sub_queries.append(f"({sub_query})")

    main_query_block = " AND ".join(main_sub_queries)

    optional_query_block = ""
    if optional_list:
        sub_query = make_query_arxiv(optional_list, operator=["AND"], field=[field])
        optional_query_block = f"({sub_query})"

    if main_query_block and optional_query_block:
        return f"({main_query_block}) AND ({optional_query_block})"
    elif main_query_block:
        return main_query_block
    else:
        return optional_query_block

def soft_parsing_arxiv(keyword_dict: dict, field: str = "all") -> str:
    """
    (Main1 AND Main2) AND (Optional1 OR Optional2)
    """
    main_list = keyword_dict.get('main', [])
    optional_list = keyword_dict.get('optional', [])

    main_sub_queries = []
    for synonym_list in main_list:
        sub_query = make_query_arxiv(synonym_list, operator=["OR"], field=[field])
        main_sub_queries.append(f"({sub_query})")
    main_query_block = " AND ".join(main_sub_queries)

    optional_query_block = ""
    if optional_list:
        sub_query = make_query_arxiv(optional_list, operator=["OR"], field=[field])
        optional_query_block = f"({sub_query})"

    if main_query_block and optional_query_block:
        return f"({main_query_block}) AND ({optional_query_block})"
    elif main_query_block:
        return main_query_block
    else:
        return optional_query_block


def _strip_outer_quotes(s: str) -> str:
    s = s.strip()
    if len(s) >= 2 and ((s[0] == s[-1] == "'") or (s[0] == s[-1] == '"')):
        return s[1:-1]
    return s

def _as_es_token(raw: str, phrase: bool = True) -> str:
    x = _strip_outer_quotes(str(raw or ""))
    if phrase and any(ch.isspace() for ch in x):
        return f"\"{x}\""
    return x

def _or_field_path(name: str) -> str:
    name = (name or "all").lower()
    mapping = {
        "title": "content.title.value",
        "abstract": "content.abstract.value",
        # "authors": "content.authors.value",
        # "authorids": "content.authorids.value",
        # "keywords": "content.keywords.value",
        # "venue": "content.venue.value",
        # "venueid": "content.venueid.value",
        "all": ""  # 빈 문자열이면 필드 스코핑 없이 전역 검색
    }
    return mapping.get(name, name)

def make_query_openreview(keyword_list: list[str],
                          operator: list[str] = ["AND"],
                          field: list[str] = ["all"],
                          phrase: bool = True) -> str:

    if not keyword_list:
        return ""

    n = len(keyword_list)

    if len(operator) == 1:
        ops = [operator[0].upper()] * (n - 1)
    elif len(operator) == n - 1:
        ops = [op.upper() for op in operator]
    else:
        raise ValueError("operator len error.")

    if len(field) == 1:
        fpaths = [_or_field_path(field[0])] * n
    elif len(field) == n:
        fpaths = [_or_field_path(f) for f in field]
    else:
        raise ValueError("field len error")

    if n == 1:
        tok = _as_es_token(keyword_list[0], phrase=phrase)
        return f"{fpaths[0]}:{tok}" if fpaths[0] else tok

    terms = []
    for i, kw in enumerate(keyword_list):
        tok = _as_es_token(kw, phrase=phrase)
        scoped = f"{fpaths[i]}:{tok}" if fpaths[i] else tok
        terms.append(scoped)

    parts = [terms[0]]
    for i in range(n - 1):
        parts.append(f" {ops[i]} ")
        parts.append(terms[i + 1])

    return "".join(parts)

def hard_parsing_openreview(keyword_dict: dict, field: str = "all") -> str:
    """
    (Main1 AND Main2) AND (Optional1 AND Optional2)
    """
    main_list = keyword_dict.get("main", [])
    optional_list = keyword_dict.get("optional", [])

    main_blocks = []
    for synonyms in main_list:
        sub = make_query_openreview(synonyms, operator=["OR"], field=[field])
        main_blocks.append(f"({sub})")
    main_query = " AND ".join(main_blocks)

    opt_query = ""
    if optional_list:
        sub = make_query_openreview(optional_list, operator=["AND"], field=[field])
        opt_query = f"({sub})"

    if main_query and opt_query:
        return f"({main_query}) AND ({opt_query})"
    elif main_query:
        return main_query
    else:
        return opt_query

def soft_parsing_openreview(keyword_dict: dict, field: str = "all") -> str:
    """
    (Main1 AND Main2) AND (Optional1 OR Optional2)
    """
    main_list = keyword_dict.get("main", [])
    optional_list = keyword_dict.get("optional", [])

    main_blocks = []
    for synonyms in main_list:
        sub = make_query_openreview(synonyms, operator=["OR"], field=[field])
        main_blocks.append(f"({sub})")
    main_query = " AND ".join(main_blocks)

    opt_query = ""
    if optional_list:
        sub = make_query_openreview(optional_list, operator=["OR"], field=[field])
        opt_query = f"({sub})"

    if main_query and opt_query:
        return f"({main_query}) AND ({opt_query})"
    elif main_query:
        return main_query
    else:
        return opt_query

