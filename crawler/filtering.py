from datetime import datetime
import re
from crawler.query import *
from crawler.openreview_crawling import *
from datetime import datetime, timezone

# 최종 업데이트 기준
def arxiv_date_filter(documents: list[dict[str, any]], date: list[int]) -> list[dict[str, any]]:

    print(f"{len(documents)}개 중에서 date filtering을 시작합니다.")
    start_year, end_year = date[0], date[1]
    filtered_documents = []

    # paper_year가 start_year와 end_year 사이라면 filtered_documents에 append
    for doc in documents:
        paper_year = doc['updated_date'].year
        if start_year <= paper_year <= end_year:
            filtered_documents.append(doc)

    print(f"{len(filtered_documents)}개를 filtering 하였습니다.")
    return filtered_documents


# openreview에서는 날짜가 여러 형태로 들어가 있음.
# 그래서 우선순위를 두고 content.year(또는 year) > mdate(ms) > cdate(ms) 순으로 살펴본다
def openreview_date_filter(documents: list[dict[str, any]], date: list[int]) -> list[dict[str, any]]:
    print(f"{len(documents)}개 중에서 date filtering을 시작합니다.")

    start_year, end_year = date[0], date[1]
    filtered_documents = []

    for doc in documents:
        paper_year = None

        # content.year 또는 year가 있다면 이걸 paper_year로 삼는다
        if isinstance(doc.get('year'), int):
            paper_year = doc['year']
        elif isinstance(doc.get('content_year'), int):
            paper_year = doc['content_year']

        # 만약 content.year or year가 없다면, mdate를 이용한다
        # mdate(수정 시각, ms)
        if paper_year is None and isinstance(doc.get('mdate'), (int, float)):
            try:
                paper_year = datetime.fromtimestamp(doc['mdate'] / 1000, tz=timezone.utc).year
            except Exception:
                pass

        # mdate도 사용할 수 없다면 cdate(생성 시각, ms)를 이용한다
        if paper_year is None and isinstance(doc.get('cdate'), (int, float)):
            try:
                paper_year = datetime.fromtimestamp(doc['cdate'] / 1000, tz=timezone.utc).year
            except Exception:
                pass

        # 필터 적용
        # paper_year 정보를 얻을 수 있었으며 start_year와 end_year 사이라면 filered_document에 추가
        if paper_year is not None and start_year <= paper_year <= end_year:
            filtered_documents.append(doc)
        print(f"{len(filtered_documents)}개를 filtering 하였습니다.")

    return filtered_documents

