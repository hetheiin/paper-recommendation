from datetime import datetime
import re
from crawler.query import *
from crawler.openreview_crawling import *
from datetime import datetime, timezone

def arxiv_date_filter(documents: list[dict[str, any]], date: list[int]) -> list[dict[str, any]]:
    """
    Filters the documents obtained from the arXiv API according to the given date.

    Args:
        documents: Paper documents retrieved by crawling.
        date: A list specifying the filtering years.

    Returns:
        Filtered documents.
    """

    print(f"Starting date filtering on {len(documents)} documents.")
    start_year, end_year = date[0], date[1]
    filtered_documents = []

    # If paper_year is between start_year and end_year, append it to filtered_documents
    for doc in documents:
        paper_year = doc['updated_date'].year
        if start_year <= paper_year <= end_year:
            filtered_documents.append(doc)

    print(f"Filtered {len(filtered_documents)} documents.")
    return filtered_documents


def openreview_date_filter(documents: list[dict[str, any]], date: list[int]) -> list[dict[str, any]]:
    """
    Filters the documents obtained from the arXiv API according to the given date.
    In OpenReview, dates can appear in multiple formats.
    Therefore, the fields are checked in the following priority order:
    content.year (or year) > mdate (ms) > cdate (ms).

    Args:
        documents: Paper documents retrieved by crawling.
        date: A list specifying the filtering years.

    Returns:
        Filtered documents.
    """

    print(f"Starting date filtering among {len(documents)} documents.")

    start_year, end_year = date[0], date[1]
    filtered_documents = []

    for doc in documents:
        paper_year = None

        # If content.year or year exists, use it as paper_year
        if isinstance(doc.get('year'), int):
            paper_year = doc['year']
        elif isinstance(doc.get('content_year'), int):
            paper_year = doc['content_year']

        # If content.year or year does not exist, use mdate instead
        # mdate (last modified time in ms)
        if paper_year is None and isinstance(doc.get('mdate'), (int, float)):
            try:
                paper_year = datetime.fromtimestamp(doc['mdate'] / 1000, tz=timezone.utc).year
            except Exception:
                pass

        # If mdate is also unavailable, use cdate (creation time in ms) instead
        if paper_year is None and isinstance(doc.get('cdate'), (int, float)):
            try:
                paper_year = datetime.fromtimestamp(doc['cdate'] / 1000, tz=timezone.utc).year
            except Exception:
                pass

        # If paper_year is available and falls between start_year and end_year, add it to filtered_documents
        if paper_year is not None and start_year <= paper_year <= end_year:
            filtered_documents.append(doc)
        print(f"Filtered {len(filtered_documents)} documents.")

    return filtered_documents

