
import re
from typing import Sequence, Union, Optional


def make_query_arxiv(keyword_list: list[str], operator: list[str] = ["AND"], field: list[str] = ["title"]) -> str:
    """
    Builds an arXiv query using the given keyword, operator, and field information.

    Args:
        keyword_list: A list of keywords.
        operator: The operator used to connect the keywords.
        field: The search field to which the keywords will be applied.

    Returns:
        The constructed arXiv query.
    """

    if not keyword_list:
        return ""

    # Create a map that converts field names to the actual names used in arXiv queries
    prefix_map = {'title': 'ti', 'abstract': 'abs', 'all': 'all'}
    num_keywords = len(keyword_list)

    # Build the query when there is only one keyword
    if num_keywords == 1:
        keyword = keyword_list[0]
        field_name = field[0]
        field_prefix = prefix_map.get(field_name)
        if not field_prefix:
            raise ValueError(f"Invalid field name: {field_name}")
        return f'{field_prefix}:"{keyword}"'

    # If the length of keyword_list is greater than 1 but only one operator is given,
    # extend the operator to match the length of keyword_list.
    if len(operator) == 1:
        operators = operator * (num_keywords - 1)
    else:
        if len(operator) != num_keywords - 1:
            raise ValueError("operator len error.")
        operators = operator

    # Do the same for field by extending it to match the length
    if len(field) == 1:
        fields = field * num_keywords
    else:
        if len(field) != num_keywords:
            raise ValueError("operator len error.")
        fields = field

    # Append the field name to each keyword and combine them
    query_terms = []
    for i, keyword in enumerate(keyword_list):
        field_prefix = prefix_map.get(fields[i])
        if not field_prefix:
            raise ValueError(f"Invalid field name: {fields[i]}")
        query_terms.append(f'{field_prefix}:"{keyword}"')

    # Connect the field-appended keyword queries with the operator
    query_parts = [query_terms[0]]
    for i in range(num_keywords - 1):
        query_parts.append(f" {operators[i]} ")
        query_parts.append(query_terms[i + 1])

    return "".join(query_parts)


def strip_quotes(s: str) -> str:
    """
    Removes quotation marks from a word and normalizes its form.

    Args:
        s: The word to remove quotation marks from.

    Returns:
        The word without quotation marks.
    """

    s = s.strip()
    if len(s) < 2:
        return s

    first, last = s[0], s[-1]
    if first == last and first in ("'", '"'):
        return s[1:-1]
    return s

# A function that removes quotation marks from a word and wraps it in double quotes
def add_quotes(raw: str) -> str:
    x = strip_quotes("" if raw is None else str(raw))
    return f'"{x}"'


def field_mapping(field_name: str) -> str:
    """
    Maps the given field name to the corresponding name used in OpenReview.
    This function was created to unify field names with those used in arXiv.

    Args:
        field_name: The field name used in the keyword.

    Returns:
        The field name as used in OpenReview.
    """

    field_name = (field_name or "all").lower()
    mapping = {
        "title": "content.title.value",
        "abstract": "content.abstract.value",
        "all": ""
    }
    return mapping.get(field_name, field_name)


def make_query_openreview(keyword_list: list[str],
                          operator: list[str] = ["AND"],
                          field: list[str] = ["all"]) -> str:
    """
    Builds a basic OpenReview query.

    Args:
        keyword_list: A list of keywords.
        operator: The operator used to connect the keywords.
        field: The search field to which the keywords will be applied.

    Returns:
        The constructed OpenReview query.
    """

# Return an empty string if keyword_list is empty
    if not keyword_list:
        return ""

    keyword_len = len(keyword_list)

    # If there is only one operator, it means all keywords should be connected with that operator.
    # Extend it into a list of operators with length (keyword_len - 1).
    # This ensures the query is built using the same logic as when multiple operators are provided.

    if len(operator) == 1:
        ops = [operator[0].upper()] * (keyword_len - 1)

    elif len(operator) == keyword_len - 1:
        ops = [op.upper() for op in operator]

    else:
        raise ValueError("operator length error.")

    # Like the operator, map the field to its proper name and extend it to match the length
    if len(field) == 1:
        field_mapping_name = [field_mapping(field[0])] * keyword_len
    elif len(field) == keyword_len:
        field_mapping_name = [field_mapping(f) for f in field]
    else:
        raise ValueError("field length error")

    if keyword_len == 1:
        keyword_quotes = add_quotes(keyword_list[0])
        return f"{field_mapping_name[0]}:{keyword_quotes}" if field_mapping_name[0] else keyword_quotes

    # Combine multiple keywords with their fields
    scoped_terms = []
    for k, field in zip(keyword_list, field_mapping_name):
        keyword_quotes = add_quotes(k)
        scoped_terms.append(f"{field}:{keyword_quotes}" if field else keyword_quotes)

    # Combine the keywords with their operators and fields
    query_parts = []
    for term, op in zip(scoped_terms, ops + [""]):
        query_parts.append(term)
        if op:
            query_parts.append(f" {op} ")

    return "".join(query_parts)