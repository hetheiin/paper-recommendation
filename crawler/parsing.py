from crawler.query import *

# main 단어들끼리는 AND, optional 단어들끼리는 OR로 묶고,
# main 단어와 optional 단어들 간에는 AND로 묶었다.
def soft_parsing_arxiv(keyword_dict: dict, field: str = "all") -> str:
    """
    (Main1 AND Main2) AND (Optional1 OR Optional2)
    """
    # keyword_dict에 'main'이 있으면 리스트로 만들고, 없어도 빈 리스트로 만든다.
    # optional_list도 마찬가지다
    main_list = keyword_dict.get('main', [])
    optional_list = keyword_dict.get('optional', [])

    # main 리스트 내의 keyword는 동의어가 함께 리스트 형태로 있을 수 있음
    # 그래서 sub_query를 만들어 합치는 방식을 사용
    # 동의어 간에는 OR로 연결
    # main 단어 간에는 AND로 연결
    main_sub_queries = []
    for synonym_list in main_list:
        sub_query = make_query_arxiv(synonym_list, operator=["OR"], field=[field])
        main_sub_queries.append(f"({sub_query})")
    main_query_block = " AND ".join(main_sub_queries)

    # optional 단어 간에는 OR로 연결
    optional_query_block = ""
    if optional_list:
        sub_query = make_query_arxiv(optional_list, operator=["OR"], field=[field])
        optional_query_block = f"({sub_query})"

    # main 단어와 optional 단어 간에는 AND로 연결
    if main_query_block and optional_query_block:
        return f"({main_query_block}) AND ({optional_query_block})"
    elif main_query_block:
        return main_query_block
    else:
        return optional_query_block



def soft_parsing_openreview(keyword_dict: dict, field: str = "all") -> str:
    """
    (Main1 AND Main2) AND (Optional1 OR Optional2)
    """

    # keyword_dict의 "main", "optional"키를 이용해 리스트를 만듦
    # 없으면 빈 리스트로 만든다
    main_list = keyword_dict.get("main", [])
    optional_list = keyword_dict.get("optional", [])

    main_blocks = []

    # main 키워드를 연결해서 sub query를 만든다
    for synonyms in main_list:
        sub = make_query_openreview(synonyms, operator=["OR"], field=[field])
        main_blocks.append(f"({sub})")
    main_query = " AND ".join(main_blocks)

    # optional 키워드를 연결해서 sub query를 만든다
    opt_query = ""
    if optional_list:
        sub = make_query_openreview(optional_list, operator=["OR"], field=[field])
        opt_query = f"({sub})"

    # 두 sub query를 하나로 합친다
    if main_query and opt_query:
        return f"({main_query}) AND ({opt_query})"
    elif main_query:
        return main_query
    else:
        return opt_query

