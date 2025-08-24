import random
import openreview
from datetime import datetime
import time
import re
from crawler.filtering import *


# venue마다 형식이 달라서, 다 v2에서 사용하는 문자열로 변환
# def as_str(x) -> str:
#     if isinstance(x, dict) and 'value' in x:
#         v = x.get('value', '')
#         return '' if v is None else str(v)
#
#     return '' if x is None else (', '.join(map(str, x)) if isinstance(x, (list, tuple)) else str(x))

# 입력값을 무조건 str로 바꿔주는 함수
def change_str(x) -> str:
    # dict 타입 & 'value' 키 처리
    if isinstance(x, dict) and 'value' in x:
        v = x.get('value')
        return '' if v is None else str(v)

    # None 처리
    if x is None:
        return ''

    # list나 tuple 처리
    if isinstance(x, (list, tuple)):
        return ', '.join(str(item) for item in x)

    # 그 외는 그냥 문자열 변환
    return str(x)

# openreview api가 20번의 request 후 일으키는 레이트리밋 값을 파싱해서 그 시간을 리턴
def parsing_reset_time(err) -> str | None:
    # error가 dict 형태로 들어온 경우
    if isinstance(err, dict):
        details = err.get('details') or {}
        if isinstance(details, dict) and details.get('resetTime'):
            return details['resetTime']
        if err.get('resetTime'):
            print(f"레이트리밋 에러입니다. 시간은 {err['resetTime']}입니다.")
            return err['resetTime']

    # exception으로 들어온 경우
    if hasattr(err, 'details') and isinstance(getattr(err, 'details'), dict):
        reset_time = err.details.get('resetTime')
        if reset_time:
            print(f"레이트리밋 에러입니다. 시간은 {reset_time}입니다.")
            return reset_time

    # 문자열로 들어온 경우
    msg = str(err)
    parsing_message = re.search(r'resetTime[\"\'\s:]*([=:]?)\s*[\"\']?([0-9T:\.\-]+Z)[\"\' ]?', msg)
    if parsing_message:
        print(f"레이트리밋 에러입니다. 시간은 {parsing_message.group(2)}입니다.")
        return parsing_message.group(2)
    return None

def sleep_until_iso(iso: str, fallback_secs: int = 3):
    """ISO8601(Z) 시간까지 대기. 실패 시 fallback 대기."""
    try:
        # datatime.fromisoformat에 맞게 ZEOTLS +00:00을 사용
        # 문자열을 datatime 객체로 변환
        reset_time = datetime.fromisoformat(iso.replace('Z', '+00:00'))

        # 현재 시간 가져와서 reset time이 얼마나 남았는지 계산 -> 남은 시간만큼 sleep
        now = datetime.now(timezone.utc)
        wait = max(0.0, (reset_time - now).total_seconds())
        print(f"레이트리밋 에러가 해제되는 시간까지 {wait}초 만큼 남았습니다")
        time.sleep(wait)
    except Exception:
        time.sleep(fallback_secs)

# search_notes를 사용하는데, 이건 relevance로 가져온다
# 100개 넘으면 끊어서 가져온다. 그 사이는 3초 쉬기
# 오류나면 3번 재시도. 만약 그 쉬라는 에러면 정말로 쉰다
# 중복 제거
def crawling_openreview_v2(
        search_query: str,
        limit: int,
        accept: bool = True
) -> list[dict[str, any]]:
    print("openreview 크롤링을 시작합니다.")

    documents = []
    # 중복을 확인하기 위해 search한 paper의 title을 저장할 set
    seen_title = set()
    client = openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net')

    # paper가 아닌 것을 필터링
    no_paper = re.compile(r'/(Comment|Rebuttal|Review)\b', re.IGNORECASE)
    sleep_sec = 3
    batch = 100
    max_retries = 3

    try:
        paper_get_num = 0
        offset = 0

        while paper_get_num < limit:
            # batch와 가져와야 할 남은 paper 개수 중 더 작은 수 만큼 가져옴
            print(f"현재 {len(documents)}개 찾았습니다. {limit - paper_get_num}개 남았습니다.")
            get_paper = min(batch, max(1, limit - paper_get_num))

            notes = None
            for attempt in range(1, max_retries + 1):
                try:
                    notes = client.search_notes(
                        term=search_query,
                        limit=get_paper,
                        offset=offset
                    )
                    break
                except Exception as e:
                    # 에러 발생 시 retry
                    print(f"error. retry ({attempt}/{max_retries}): {e}")
                    msg = str(e).lower()

                    # error가 429 ratelimit error면 reset time을 parsing해서
                    # 그 시간만큼 기다림
                    # parsing에 실패하면 그냥 sleep_sec만큼 기다렸다가 시도
                    # 일반 에러도 기다린 후 다시 retry
                    if '429' in msg or 'ratelimiterror' in msg or 'too many requests' in msg:
                        reset_iso = None
                        if hasattr(e, 'args') and e.args:
                            reset_iso = parsing_reset_time(e.args[0])
                        if not reset_iso:
                            reset_iso = parsing_reset_time(e)
                        if reset_iso:
                            print(f"limit error: resetTime={reset_iso}.")
                            sleep_until_iso(reset_iso, fallback_secs=sleep_sec)
                        else:
                            time.sleep(sleep_sec)
                    else:
                        time.sleep(sleep_sec if attempt == max_retries else max(1, attempt - 1))

                    # max_retries에 도달하면 현재까지 찾은 documents를 리턴
                    if attempt == max_retries:
                        print(f"error and return {len(documents)} documents")
                        return documents

            # 만약 받아온 notes가 없으면 종료
            if not notes:
                break

            got_from_server = 0
            for note in notes:
                got_from_server += 1

                # "replyto"가 있으면 paper가 아닌 댓글이나 리뷰 -> continue
                if getattr(note, 'replyto', None):
                    continue

                # invitation이 Comment/Rebuttal/Review에 해당하면 continue
                inv = getattr(note, 'invitation', '') or ''
                if no_paper.search(inv):
                    continue

                # 찾은 논문에서 title, abstract 추출. 없으면 skip
                c = note.content or {}
                title = change_str(c.get('title')).strip()
                abstract = change_str(c.get('abstract')).strip()

                if not title or not abstract:
                    continue

                # accept, reject 등의 내용은 decision이다.
                # decision, venue 추출
                decision = change_str(c.get('decision'))
                venue = change_str(c.get('venue'))

                # 만약 accept이 true라서 accept된 논문만 가져와야 한다면
                # "reject"가 포함된 논문은 제외시킴
                if accept:
                    accept_check = f"{decision} {venue}".lower()
                    if 'reject' in accept_check:
                        continue
                    decision_info = decision or venue
                else:
                    decision_info = ""

                forum_id = getattr(note, 'forum', None) or note.id

                # 제목 기준으로 중복 체크
                if title in seen_title:
                    continue
                seen_title.add(forum_id)

                # 찾은 것들 document에 추가
                documents.append({
                    'title': title,
                    'url': f"https://openreview.net/forum?id={forum_id}",
                    'abstract': abstract,
                    'cdate': note.cdate,
                    'decision_info': decision_info
                })

                # 가져온 paper 개수가 limit과 같거나 넘으면 종료
                paper_get_num += 1
                if paper_get_num >= limit:
                    break

            # 페이징 구현. 페이징마다 sleep_sec만큼 기다림
            offset += got_from_server
            if paper_get_num < limit:
                time.sleep(sleep_sec)


    except Exception as e:
        print(f"error and return {len(documents)} documents")

    print(f"{len(documents)}개의 크롤링을 완료하였습니다.")
    return documents

