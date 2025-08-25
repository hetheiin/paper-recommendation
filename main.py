from rag.run import setup as setup_rag
from preprocess.src.run import setup as setup_preprocess, get_model

from rag.run import run as run_rag
from preprocess.src.run import run as run_preprocess

from crawler import *

from llm.generater_research_cards import generate_single_card_markdown, generate_comparison_table_from_cards


REALTIMETEST = True

def print_guidelines():
    print()
    print("=== Real-time Web-based Research Paper Search Tool ===")
    print("This tool allows you to input a query sentence and retrieve relevant research papers in real time.")
    print()
    print("Query Sentence Guidelines:")
    print("- Write short and concise sentence-style queries.")
    print("- Do not use abbreviations; always write terms in full form.")
    print()
    print("Examples:")
    print("- Bad: find me a paper about survey on MAS")
    print("- Good: survey on multi-agent system")
def pretty_print_cards(docs, qu, model, tokenizer):
    print("\n============================")
    print(" Research Output ")
    print("============================\n")

    outputs = []
    for doc in docs:
        md = generate_single_card_markdown(
            doc=doc,
            query=qu,
            model_id="Qwen/Qwen3-1.7B",
            device="cpu",            # GPU면 "cuda"
            dtype="auto",
            style="standard",
            max_new_tokens=2048,
            load_in_4bit=False,
            load_in_8bit=False,
            model=model,
            tokenizer=tokenizer,
        )
        print("============================")
        print("Title:", doc["title"])
        print("Summary:\n", md.replace(". ", ". \n"))       # 개별 카드 출력
        print("link:", doc["url"])
        print("\n")
        outputs.append(doc["title"] +" "+ md +" "+ doc["url"])

    # 카드들로 최종 비교표 생성
    final_table = generate_comparison_table_from_cards(
        cards_md=outputs,
        query=qu,
        model_id="Qwen/Qwen3-1.7B",
        device="cpu",
        dtype="auto",
        max_new_tokens=800,
        load_in_4bit=False,
        load_in_8bit=False,
        model=model,
        tokenizer=tokenizer,
    )
    print("\n============================")
    print(" Final Comparison Table ")
    print("============================\n")
    print(final_table)

def setups():
    setup_rag()
    setup_preprocess()

def main():
    setups()

    # print guidelines
    print_guidelines()

    # receive user query input
    query = input("Input a query sentence for paper search: ")
    # receive top_k
    top_k = int(input("Input the number of top-k papers: "))

    # extract keywords
    keywords = run_preprocess(query)
    print("extracted keywords: ", keywords)

    # --- search

    is_accepted = True if input("Only ACCEPTED papers? yes/no: ") == "yes" else False
    datalist_str = input("Date range for paper search? ex) '2022-2023' or 'anytime': ").strip()
    date_list = []
    if "anytime" in datalist_str:
        date_list = None
    else:
        date_list = [int(element) for element in datalist_str.split("-")]

    documents = main_crawling(keywords, field="all", num=300, sort_op="relevance", date=date_list, accept = is_accepted, openreview = REALTIMETEST)
    document_print(documents)

    # filter documents
    filtered_documents = run_rag(query, documents, top_k=top_k)

    # --- pretty print
    model, tokenizer = get_model()
    pretty_print_cards(filtered_documents, query, model, tokenizer)


if __name__ == '__main__':
    main()