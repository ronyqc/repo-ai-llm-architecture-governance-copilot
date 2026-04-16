import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.rag import AzureSearchRetriever, RetrievalRequest


def run_test(query: str, knowledge_domain: str | None = None, top_k: int = 2):
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
    print("Manual validation for T32: Azure OpenAI query embeddings + Azure AI Search vector retrieval")

    print("\n🔥 VALIDACIÓN DE PRECISIÓN (top_k = 1)\n")

    run_test(
        "service domain que gestiona el perfil del cliente y su informacion en el banco",
        "bian",
        1,
    )

    run_test(
        "dominio que permite consultar especificaciones de productos bancarios",
        "bian",
        1,
    )

    run_test(
        "componente que centraliza autenticacion validacion de identidad y tokens",
        "building_blocks",
        1,
    )

    run_test(
        "lineamientos para disenar APIs reutilizables y versionadas en arquitectura",
        "guidelines_patterns",
        1,
    )

    print("\n📚 VALIDACIÓN DE CONTEXTO (top_k = 2)\n")

    run_test(
        "service domain que gestiona el perfil del cliente y su informacion en el banco",
        "bian",
        2,
    )

    run_test(
        "dominio que permite consultar especificaciones de productos bancarios",
        "bian",
        2,
    )

    run_test(
        "componente que centraliza autenticacion validacion de identidad y tokens",
        "building_blocks",
        2,
    )

    run_test(
        "lineamientos para disenar APIs reutilizables y versionadas en arquitectura",
        "guidelines_patterns",
        2,
    )
