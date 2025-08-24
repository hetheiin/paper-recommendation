import arxiv
import random

from crawler.parsing import *
from crawler.openreview_crawling import *


# arxiv 특유의 파일명 추출
ID_PAT = re.compile(r"/abs/([^/]+)$")  # YYMM.NNNNNvX 추출

# arxiv 논문 url이나 entry id에서 논문 아이디 추출
def paper_id(entry_id: str) -> str:
    m = ID_PAT.search(entry_id or "")
    return m.group(1) if m else (entry_id or "")

# arxiv api로 논문을 crawling하는 함수
def crawling_basic(search_query: str, num: int = 50, sort_op: str = "submitted") -> list[dict[str, any]]:
    documents: list[dict[str, any]] = []
    seen_title = set()

    try:

        # arxiv client setting
        client = arxiv.Client(
            page_size=100,
            delay_seconds=3,
            num_retries=5
        )

        max_empty_retries = 2
        empty_retries = 0

        while len(documents) < num and empty_retries < max_empty_retries:
            print(f"document crawling을 진행합니다. 현재 {len(documents)}개 찾았습니다.")
            try:
                # sort_op에 따른 search setting
                if sort_op == "submitted":
                    search = arxiv.Search(
                        query=search_query,
                        max_results=num - len(documents),
                        sort_by=arxiv.SortCriterion.SubmittedDate
                    )
                elif sort_op == "relevance":
                    search = arxiv.Search(
                        query=search_query,
                        max_results=num - len(documents),
                        sort_by=arxiv.SortCriterion.Relevance
                    )
                else:
                    search = arxiv.Search(
                        query=search_query,
                        max_results=num - len(documents),
                        sort_by=arxiv.SortCriterion.LastUpdatedDate
                    )

                paper_get_num = 0

                for result in client.results(search):
                    # 가져와야 하는 paper 수보다 현재 가져온 documents length가 같거나 더 크면 반복문을 빠져나감
                    if len(documents) >= num:
                        break


                    # title이 이미 본 title이라면 이번 loop는 continue
                    # 그렇지 않다면 seen_title에 추가해둠
                    if result.title in seen_title:
                        continue
                    seen_title.add(result.title)


                    documents.append({
                        'title': result.title,
                        'url': result.pdf_url,
                        'abstract': result.summary,
                        'updated_date': result.updated,
                    })
                    paper_get_num += 1

                    # 500개를 가져올 때마다 7초 쉬어주기
                    if len(documents) % 500 == 0 and len(documents) < num:
                        print(f"document: {len(documents)}. waiting 7 seconds…")
                        time.sleep(7)

                # 만약 page에서 가져온 paper가 0개라면
                # unexpactedly empty error로 판단, 5초 후 retry
                if paper_get_num == 0:
                    empty_retries += 1
                    print(f"[warn] empty page error → {empty_retries}/2 try (waiting 5 secondes)")
                    time.sleep(5)
                else:
                    empty_retries = 0

                # unexpectedly empty error 발생 시, 5초 후 retry
            except Exception as e:
                if "unexpectedly empty" in str(e).lower():
                    empty_retries += 1
                    print(f"[warn] empty page error → {empty_retries}/2 try (waiting 5 secondes)")
                    time.sleep(5)
                    continue
                # 그 외 에러는 break
                else:
                    print(f"[stop] error: {e}")
                    break

    # 에러로 멈추어도 지금까지 가져온 document는 return
    except Exception as e:
        print(f"\n[!] stop error and return: {e}")

    if len(documents) < num:
        print(f"크롤링이 끝났습니다. {len(documents)}개 반환합니다.")
        return documents

    print(f"크롤링이 끝났습니다. {num}개 반환합니다.")
    return documents[:num]


# 전체 크롤링을 담당하는 함수
# keyword_dict, field 등을 받아 분기하여 적절한 parding 함수, 크롤러, 필터를 실행시킴
def main_crawling(keyword_dict: dict,
                  field: str = "all",
                  num: int = 50,
                  sort_op: str = "sumitted",
                  date: list[int] = None, accept = False, openreview: bool = False) -> list[dict[str, any]]:

    if openreview:
        search_query = soft_parsing_openreview(keyword_dict, field=field)
        documents = crawling_openreview_v2(search_query, num, accept)
        if date is None:
            return documents
        else:
            documents = openreview_date_filter(documents, date)
            return documents

    if date is None:
        if accept == True:
            search_query = soft_parsing_openreview(keyword_dict, field)
            documents = crawling_openreview_v2(search_query, num, accept)
        else:
            search_query = soft_parsing_arxiv(keyword_dict, field)
            documents = crawling_basic(search_query, num, sort_op)
    else:
        if accept == True:
            new_num = 3 * num
            search_query = soft_parsing_openreview(keyword_dict, field)
            documents = crawling_openreview_v2(search_query, num, accept)
            documents = openreview_date_filter(documents, date)
        else:
            new_num = 3 * num
            search_query = soft_parsing_arxiv(keyword_dict, field)
            documents = crawling_basic(search_query, new_num, sort_op)
            documents = arxiv_date_filter(documents, date)

    if len(documents) > num:
        documents = documents[:num]

    return documents



def random_crawling(sample_size: int = 20, num: int = 10) -> list[dict[str, str]]:
    """
    Fetches random crawling results.

    Args:
        sample_size: The number of candidates to sample from.
        num: The actual number of documents to return.

    Returns:
        Documents crawled using a random query.
    """

    # List for generating random queries
    query_list = ["the", "a", "is", "of", "and", "in", "to"]

    # Randomly select one item from query_list
    random_query1 = random.choice(query_list)
    random_query2 = random.choice(query_list)
    random_query3 = random.choice(query_list)

    # Crawl using different sort options for the selected query
    doc_relevance = crawling_basic(random_query1, num=sample_size, sort_op="relevance")
    doc_lastupdate = crawling_basic(random_query2, num=sample_size, sort_op="lastupdate")
    doc_submitted = crawling_basic(random_query3, num=sample_size, sort_op="submitted")

    # Combine into one
    random_candidate = doc_relevance + doc_lastupdate + doc_submitted
    # shuffle
    random.shuffle(random_candidate)

    # Slice to keep only 'num' items
    random_document = random_candidate[:num]

    return random_document

