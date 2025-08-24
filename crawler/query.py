
import re
from typing import Sequence, Union, Optional

# keyword, operator, field 정보를 받아 arxiv query를 만드는 함수다.
def make_query_arxiv(keyword_list: list[str], operator: list[str] = ["AND"], field: list[str] = ["title"]) -> str:

    if not keyword_list:
        return ""

    # field를 실제로 arxiv query에서 이용하는 이름으로 mapping하는 map을 만든다
    prefix_map = {'title': 'ti', 'abstract': 'abs', 'all': 'all'}
    num_keywords = len(keyword_list)

    # keyword가 하나일 때 query를 만드는 부분
    if num_keywords == 1:
        keyword = keyword_list[0]
        field_name = field[0]
        field_prefix = prefix_map.get(field_name)
        if not field_prefix:
            raise ValueError(f"Invalid field name: {field_name}")
        return f'{field_prefix}:"{keyword}"'

    # 만약 keyword_list의 length는 1이상인데 operator가 1개만 들어오면
    # keyword_list의 길이에 맞추어 확장한다.
    if len(operator) == 1:
        operators = operator * (num_keywords - 1)
    else:
        if len(operator) != num_keywords - 1:
            raise ValueError("operator len error.")
        operators = operator

    # field도 마찬가지로 길이를 맞추어 확장한다.
    if len(field) == 1:
        fields = field * num_keywords
    else:
        if len(field) != num_keywords:
            raise ValueError("operator len error.")
        fields = field

    # 키워드에 field name을 추가해서 서로 붙인다
    query_terms = []
    for i, keyword in enumerate(keyword_list):
        field_prefix = prefix_map.get(fields[i])
        if not field_prefix:
            raise ValueError(f"Invalid field name: {fields[i]}")
        query_terms.append(f'{field_prefix}:"{keyword}"')

    # field가 추가된 keyword query 사이를 oprator로 연결한다.
    query_parts = [query_terms[0]]
    for i in range(num_keywords - 1):
        query_parts.append(f" {operators[i]} ")
        query_parts.append(query_terms[i + 1])

    return "".join(query_parts)



# 단어의 ""를 벗겨내어 형태를 정리하는 함수
def strip_quotes(s: str) -> str:
    s = s.strip()
    if len(s) < 2:
        return s

    first, last = s[0], s[-1]
    if first == last and first in ("'", '"'):
        return s[1:-1]
    return s

# 단어의 따옴표를 제거하고, 큰따옴표로 감싸는 함수
def add_quotes(raw: str) -> str:
    x = strip_quotes("" if raw is None else str(raw))
    return f'"{x}"'

# 입력받은 field 네임을 openreview에서 사용하는 이름으로 mapping하는 함수
# arxiv와 field 네임을 통일하기 위해 이 함수를 만들었다.
def field_mapping(field_name: str) -> str:
    field_name = (field_name or "all").lower()
    mapping = {
        "title": "content.title.value",
        "abstract": "content.abstract.value",
        "all": ""
    }
    return mapping.get(field_name, field_name)

# 기본적인 openreview query를 만드는 함수
def make_query_openreview(keyword_list: list[str],
                          operator: list[str] = ["AND"],
                          field: list[str] = ["all"]) -> str:

# keyword_list에 아무것도 없으면 빈 문자열 반환
    if not keyword_list:
        return ""

    keyword_len = len(keyword_list)

    # operator가 하나라면 모든 keyword의 연결을 해당 operator로 진행하라는 것
    # keyword_len - 1만큼의 길이를 가진 operator 리스트로 확장한다.
    # 그래야 operator가 여러 개인 리스트와 같은 로직으로 쿼리를 만들 수 있다
    if len(operator) == 1:
        ops = [operator[0].upper()] * (keyword_len - 1)

    elif len(operator) == keyword_len - 1:
        ops = [op.upper() for op in operator]

    else:
        raise ValueError("operator length error.")

    # field 또한 operator와 마찬가지로 매핑을 이용하여 이름을 바꾼 후 길이를 통일시킨다
    if len(field) == 1:
        field_mapping_name = [field_mapping(field[0])] * keyword_len
    elif len(field) == keyword_len:
        field_mapping_name = [field_mapping(f) for f in field]
    else:
        raise ValueError("field length error")

    if keyword_len == 1:
        keyword_quotes = add_quotes(keyword_list[0])
        return f"{field_mapping_name[0]}:{keyword_quotes}" if field_mapping_name[0] else keyword_quotes

    # 여러 개 키워드에 필드를 합친다
    scoped_terms = []
    for k, field in zip(keyword_list, field_mapping_name):
        keyword_quotes = add_quotes(k)
        scoped_terms.append(f"{field}:{keyword_quotes}" if field else keyword_quotes)

    # operators와 필드를 합친 키워드를 서로 조합한다
    query_parts = []
    for term, op in zip(scoped_terms, ops + [""]):
        query_parts.append(term)
        if op:
            query_parts.append(f" {op} ")

    return "".join(query_parts)