from crawler.query import *


def soft_parsing_arxiv(keyword_dict: dict, field: str = "all") -> str:
    """
    Parses keyword_dict and constructs an arXiv query.
    Main keywords are combined with AND, optional keywords are combined with OR,
    and main keywords are combined with optional keywords using AND.
    The resulting format is (Main1 AND Main2) AND (Optional1 OR Optional2).

    Args:
        keyword_dict: A dictionary containing keywords.
            - Important keywords are stored under the key "main".
            - Optional keywords are stored under the key "optional".
            - Each keyword is stored as an element of a nested list,
              where synonyms belong to the same list.
            - Therefore, the dictionary values are nested lists:
              synonyms are elements of the same nested list,
              and keywords of the same type are elements of the same list.
            The format is as follows:

            keyword_dict = {
                "main": [
                    ["multimodal", "vision-language", "vlm"],   # synonym group
                    ["reasoning", "chain of thought", "cot"],   # synonym group
                    ["memory", "long-term memory"]              # synonym group
                ],
                "optional": ["tool-use", "agent", "planning"]
            }

        field: The field in which to search for the keywords.
               Can be 'title', 'all', or 'abstract'.

    Returns:
        The parsed arXiv query.
    """

    # If 'main' exists in keyword_dict, create a list; otherwise, create an empty list.
    # Do the same for optional_list.
    main_list = keyword_dict.get('main', [])
    optional_list = keyword_dict.get('optional', [])

    # Keywords in the main list may include synonyms grouped together in a sublist.
    # Therefore, build sub_queries and combine them.
    # Connect synonyms with OR.
    # Connect main keywords with AND.
    main_sub_queries = []
    for synonym_list in main_list:
        sub_query = make_query_arxiv(synonym_list, operator=["OR"], field=[field])
        main_sub_queries.append(f"({sub_query})")
    main_query_block = " AND ".join(main_sub_queries)

    # Connect optional keywords with OR
    optional_query_block = ""
    if optional_list:
        sub_query = make_query_arxiv(optional_list, operator=["OR"], field=[field])
        optional_query_block = f"({sub_query})"

    # Connect main keywords and optional keywords with AND
    if main_query_block and optional_query_block:
        return f"({main_query_block}) AND ({optional_query_block})"
    elif main_query_block:
        return main_query_block
    else:
        return optional_query_block



def soft_parsing_openreview(keyword_dict: dict, field: str = "all") -> str:
    """
      keyword_dict를 받아 parsing하여 openreview query로 만드는 함수
      main 단어들끼리는 AND, optional 단어들끼리는 OR로 묶고,
      main 단어와 optional 단어들 간에는 AND로 묶었다.
      (Main1 AND Main2) AND (Optional1 OR Optional2)의 형태로 만든다.

      Args:
          keyword_dict: keyword가 담겨 있는 dictionary이다.
          중요한 키워드는 "main", 옵션 키워드는 "optional"이라는 키로 저장한다.
          각 키워드는 nested 리스트의 원소로 들어가 있으며, 동의어 기리는 또 같은 리스트 안에 속한다.
          따라서 dictionary의 value가 nested list이고, 동의어 끼리는 같은 nested list의 원소이며
          같은 종류의 키워드기리는 같은 list의 원소이다.
          format은 아래와 같다.

          keyword_dict = {
          "main": [
              ["multimodal", "vision-language", "vlm"],   # 동의어 그룹
              ["reasoning", "chain of thought", "cot"],   # 동의어 그룹
              ["memory", "long-term memory"]              # 동의어 그룹
                  ],
          "optional": ["tool-use", "agent", "planning"]

          field: 키워드를 검색할 필드명이다. title, all, abstract가 가능하다.

      Returns: parsing한 arxiv query
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

