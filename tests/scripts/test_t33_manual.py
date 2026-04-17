import sys
from pathlib import Path
from uuid import uuid4

sys.path.append(str(Path(__file__).resolve().parents[2]))

from src.core.orchestrator import BasicQueryOrchestrator, QueryOrchestrationRequest


def run_test(query: str) -> None:
    orchestrator = BasicQueryOrchestrator.from_settings()
    result = orchestrator.answer(
        QueryOrchestrationRequest(
            query=query,
            trace_id=str(uuid4()),
        )
    )

    print("=" * 80)
    print(f"QUERY: {query}")
    print(f"TOKENS USED: {result.tokens_used}")
    print(f"SOURCES: {len(result.sources)}")
    print("-" * 80)
    print(result.answer)
    print("-" * 80)

    for index, source in enumerate(result.sources, start=1):
        print(
            f"{index}. [{source.source_type}] {source.title} "
            f"(source_id={source.source_id}, score={source.score})"
        )


if __name__ == "__main__":
    print("Manual validation for T34: grounded retrieval + structured Spanish answer generation")
    run_test("Que building blocks se recomiendan para autenticacion en arquitectura empresarial?")
    run_test("Que referencias BIAN se relacionan con customer profile?")
    run_test("Cual es el clima en Lima hoy?")
