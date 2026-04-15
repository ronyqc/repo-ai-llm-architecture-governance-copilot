import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.rag import AzureSearchRetriever, RetrievalRequest

def run_test(query: str, knowledge_domain: str | None = None, top_k: int = 3):
    retriever = AzureSearchRetriever.from_settings()

    results = retriever.retrieve_as_dict(
        RetrievalRequest(
            query=query,
            top_k=top_k,
            knowledge_domain=knowledge_domain,
        )
    )

    print("=" * 80)
    print(f"QUERY: {query}")
    print(f"DOMAIN: {knowledge_domain}")
    print(f"RESULTADOS: {len(results)}")
    print("-" * 80)

    for i, item in enumerate(results, start=1):
        print(f"Resultado {i}")
        print(f"  title: {item.get('title')}")
        print(f"  knowledge_domain: {item.get('knowledge_domain')}")
        print(f"  document_name: {item.get('document_name')}")
        print(f"  chunk_id: {item.get('chunk_id')}")
        print(f"  score: {item.get('score')}")
        print(f"  content: {item.get('content')}")
        print("-" * 80)


if __name__ == "__main__":
    run_test("customer profile", "bian")
    run_test("product directory", "bian")
    run_test("authentication gateway", "building_blocks")
    run_test("api governance", "guidelines_patterns")