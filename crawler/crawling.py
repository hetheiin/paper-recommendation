import arxiv
import random

from crawler.parsing import *
from crawler.openreview_crawling import *


# Extracts arXiv-specific filenames
ID_PAT = re.compile(r"/abs/([^/]+)$")

def paper_id(entry_id: str) -> str:
    """
    Extracts the paper ID from an arXiv entry ID.

    Args:
        entry_id: The entry_id obtained from the arXiv API.

    Returns:
        paper_id
    """

    m = ID_PAT.search(entry_id or "")
    return m.group(1) if m else (entry_id or "")

def crawling_basic(search_query: str, num: int = 50, sort_op: str = "submitted") -> list[dict[str, any]]:
    """
    Crawls papers from the arXiv API.

    Args:
        search_query: The search query to pass to the arXiv API.
        num: The number of papers to retrieve.
        sort_op: Sorting option. Can be 'relevance', 'submitted', or 'lastupdate',
                 which correspond to relevance, submission date, and last updated date, respectively.

    Returns:
        A list of crawled papers. Each element in the list is a dictionary containing
        the information of a single paper.
    """

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
            print(f"Starting document crawling... Currently found {len(documents)} documents.")
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
                    # Breaks out of the loop if the number of retrieved documents
                    # is greater than or equal to the number of papers requested

                    if len(documents) >= num:
                        break

                    # If the title has already been seen, continue to the next loop iteration
                    # Otherwise, add it to seen_title

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

                    # Pause for 7 seconds after every 500 retrieved items
                    if len(documents) % 500 == 0 and len(documents) < num:
                        print(f"document: {len(documents)}. waiting 7 seconds…")
                        time.sleep(7)

                # If no papers are retrieved from the page,
                # treat it as an unexpectedly empty error and retry after 5 seconds

                if paper_get_num == 0:
                    empty_retries += 1
                    print(f"[warn] empty page error → {empty_retries}/2 try (waiting 5 secondes)")
                    time.sleep(5)
                else:
                    empty_retries = 0

                # On unexpectedly empty error, retry after 5 seconds
            except Exception as e:
                if "unexpectedly empty" in str(e).lower():
                    empty_retries += 1
                    print(f"[warn] empty page error → {empty_retries}/2 try (waiting 5 secondes)")
                    time.sleep(5)
                    continue
                # For all other errors, break
                else:
                    print(f"[stop] error: {e}")
                    break

    # Even if stopped by an error, return the documents retrieved so far
    except Exception as e:
        print(f"\n[!] stop error and return: {e}")

    if len(documents) < num:
        print(f"Crawling finished. Returning {len(documents)} documents.")
        return documents

    print(f"Crawling finished. Returning {len(documents)} documents.")
    return documents[:num]



def main_crawling(keyword_dict: dict,
                  field: str = "all",
                  num: int = 50,
                  sort_op: str = "sumitted",
                  date: list[int] = None, accept = False, openreview: bool = False) -> list[dict[str, any]]:
    """
    Executes the appropriate parsing function, crawler, and filter
    by branching based on keyword_dict, field, and other arguments.

    Args:
        keyword_dict: A dictionary containing keywords.
            - Important keywords are stored under the key "main".
            - Optional keywords are stored under the key "optional".
            - Each keyword is stored as an element of a nested list,
              where synonyms belong to the same list.
            - Therefore, the dictionary values are nested lists.
              Synonyms are elements of the same nested list,
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

        field: The query field. Can be 'title', 'abstract', or 'all'.

        num: The number of papers to retrieve.

        sort_op: Sorting option. Can be 'relevance', 'submitted', or 'lastupdate',
                 which correspond to relevance, submission date, and last updated date, respectively.

        date: Used to filter by a specific period if provided.
              Format: [start_year, end_year].

        accept: If set to True, only accepted papers are filtered.

        openreview: If True, forces the search to be performed via the OpenReview API,
                    regardless of branch.

    Returns:
        A list of crawled papers. Each element in the list is a dictionary
        containing the information of a single paper.
    """

    # If openreview is True, search using the OpenReview API regardless of branching

    if openreview:
        search_query = soft_parsing_openreview(keyword_dict, field=field)
        documents = crawling_openreview_v2(search_query, num, accept)
        if date is None:
            return documents
        else:
            documents = openreview_date_filter(documents, date)
            return documents

    # When date filtering is not applied

    if date is None:
        # Since accept filtering is only available in the OpenReview API,
        # perform the search using the OpenReview API.
        # If accept filtering is not needed, use the arXiv API instead.

        if accept == True:
            search_query = soft_parsing_openreview(keyword_dict, field)
            documents = crawling_openreview_v2(search_query, num, accept)
        else:
            search_query = soft_parsing_arxiv(keyword_dict, field)
            documents = crawling_basic(search_query, num, sort_op)
    else:
        if accept == True:
            # Since filtering reduces the number of retrieved papers,
            # fetch three times as many papers from the start.
            # Perform crawling first, then apply filtering.

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

