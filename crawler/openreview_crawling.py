import random
import openreview
from datetime import datetime
import time
import re
from crawler.filtering import *


def change_str(x) -> str:
    """
    Converts the input value to a string unconditionally.

    Args:
        x: The input value to be converted into a string.

    Returns:
        x converted into a string.
    """

    # Handle dict type
    if isinstance(x, dict) and 'value' in x:
        v = x.get('value')
        return '' if v is None else str(v)

    # Handle None
    if x is None:
        return ''

    # Handle list or tuple
    if isinstance(x, (list, tuple)):
        return ', '.join(str(item) for item in x)

    # Otherwise, simply convert to string
    return str(x)


def parsing_reset_time(err) -> str | None:
    """
    Parses the rate limit value triggered by the OpenReview API after 20 requests
    and returns the reset time.

    Args:
        err: The error raised by the OpenReview API.

    Returns:
        The resetTime obtained by parsing the rateLimit.
    """

    # When the error is in dict form
    if isinstance(err, dict):
        details = err.get('details') or {}
        if isinstance(details, dict) and details.get('resetTime'):
            return details['resetTime']
        if err.get('resetTime'):
            print(f"Rate limit error. Reset time is {err['resetTime']}.")
            return err['resetTime']

    # When received as an exception
    if hasattr(err, 'details') and isinstance(getattr(err, 'details'), dict):
        reset_time = err.details.get('resetTime')
        if reset_time:
            print(f"Rate limit error. Reset time is {reset_time}.")
            return reset_time

    # When received as a string
    msg = str(err)
    parsing_message = re.search(r'resetTime[\"\'\s:]*([=:]?)\s*[\"\']?([0-9T:\.\-]+Z)[\"\' ]?', msg)
    if parsing_message:
        print(f"Rate limit error. Reset time is {parsing_message.group(2)}.")
        return parsing_message.group(2)
    return None

def sleep_until_iso(iso: str, fallback_secs: int = 3):
    """
    Sleeps until the given ISO time.

    Args:
        iso: The resetTime in ISO format.
        fallback_secs: The duration to sleep if parsing fails.
    """

    try:
        # Use ZETOLS +00:00 to match datetime.fromisoformat
        # Convert the string into a datetime object
        reset_time = datetime.fromisoformat(iso.replace('Z', '+00:00'))

        # Get the current time and calculate how much time remains until reset_time -> sleep for that duration
        now = datetime.now(timezone.utc)
        wait = max(0.0, (reset_time - now).total_seconds())
        print(f"{wait} seconds remaining until the rate limit error is lifted.")
        time.sleep(wait)
    except Exception:
        time.sleep(fallback_secs)


def crawling_openreview_v2(
        search_query: str,
        limit: int,
        accept: bool = True
) -> list[dict[str, any]]:
    """
    Crawls papers using the OpenReview v2 API.

    Args:
        search_query: The query to pass to the OpenReview v2 API.
        limit: The number of papers to retrieve.
        accept: A boolean value indicating whether to filter by acceptance status.

    Returns:
        A list of crawled papers.
    """

    print("Starting OpenReview crawling.")

    documents = []
    # A set to store the titles of searched papers for duplicate checking
    seen_title = set()
    client = openreview.api.OpenReviewClient(baseurl='https://api2.openreview.net')

    # Filter out non-paper items
    no_paper = re.compile(r'/(Comment|Rebuttal|Review)\b', re.IGNORECASE)
    sleep_sec = 3
    batch = 100
    max_retries = 3

    try:
        paper_get_num = 0
        offset = 0

        while paper_get_num < limit:
            # Retrieve the smaller of batch size or the remaining number of papers to fetch
            print(f"Currently found {len(documents)} documents. {limit - paper_get_num} remaining.")
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
                    # Retry on error
                    print(f"error. retry ({attempt}/{max_retries}): {e}")
                    msg = str(e).lower()

                    # If the error is a 429 rate limit error, parse the reset time
                    # and wait for that duration.
                    # If parsing fails, just wait for sleep_sec before retrying.
                    # For general errors, also wait and then retry.
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

                    # If max_retries is reached, return the documents retrieved so far
                    if attempt == max_retries:
                        print(f"error and return {len(documents)} documents")
                        return documents

            # If no notes are received, terminate
            if not notes:
                break

            got_from_server = 0
            for note in notes:
                got_from_server += 1

                # If "replyto" exists, it's a comment or review (not a paper) -> continue
                if getattr(note, 'replyto', None):
                    continue

                # If the invitation corresponds to Comment/Rebuttal/Review, continue
                inv = getattr(note, 'invitation', '') or ''
                if no_paper.search(inv):
                    continue

                # Extract title and abstract from the retrieved paper; skip if not available
                c = note.content or {}
                title = change_str(c.get('title')).strip()
                abstract = change_str(c.get('abstract')).strip()

                if not title or not abstract:
                    continue

                # Contents such as accept or reject are stored in 'decision'.
                # Extract decision and venue.
                decision = change_str(c.get('decision'))
                venue = change_str(c.get('venue'))

                # If accept is True and only accepted papers should be retrieved,
                # exclude papers that contain "reject"
                if accept:
                    accept_check = f"{decision} {venue}".lower()
                    if 'reject' in accept_check:
                        continue
                    decision_info = decision or venue
                else:
                    decision_info = ""

                forum_id = getattr(note, 'forum', None) or note.id

                # Check for duplicates based on title
                title = title.strip()
                if title in seen_title:
                    continue
                seen_title.add(title)

                # Add the retrieved items to documents
                documents.append({
                    'title': title,
                    'url': f"https://openreview.net/forum?id={forum_id}",
                    'abstract': abstract,
                    'cdate': note.cdate,
                    'decision_info': decision_info
                })

                # Terminate if the number of retrieved papers is greater than or equal to the limit
                paper_get_num += 1
                if paper_get_num >= limit:
                    break

            # Implement paging. Wait for sleep_sec after each page.
            offset += got_from_server
            if paper_get_num < limit:
                time.sleep(sleep_sec)


    except Exception as e:
        print(f"error and return {len(documents)} documents")

    print(f"Completed crawling {len(documents)} documents.")
    return documents

