from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from scripts.run_benchmark import build_parser, retrieval_prediction
from src.retrieval.retrieval_scorer import RetrievedExample


class FakeRetriever:
    def retrieve(self, query, *, top_k=5, candidate_pool_size=25):
        return [
            RetrievedExample(
                record={"id": "a", "tables": ["student_depression"], "columns": []}, score=0.8
            ),
            RetrievedExample(
                record={"id": "b", "tables": ["student_depression"], "columns": []}, score=0.7
            ),
        ]


def test_run_benchmark_parser_accepts_reranker_flag():
    args = build_parser().parse_args(
        [
            "--mode",
            "retrieval",
            "--dataset",
            "dev",
            "--retrieval-backend",
            "hybrid",
            "--reranker",
            "bge-reranker-v2-m3",
        ]
    )

    assert args.reranker == "bge-reranker-v2-m3"


def test_retrieval_prediction_records_placeholder_warning_for_model_reranker():
    record = retrieval_prediction(
        {
            "id": "VTD-1",
            "question_fa": "تعداد دانشجوها؟",
            "sql": "SELECT COUNT(*) AS n FROM student_depression",
        },
        FakeRetriever(),
        top_k=1,
        use_reranker=True,
        reranker_name="bge-reranker-v2-m3",
    )

    assert record["retrieval_reranker"] == "bge-reranker-v2-m3"
    assert record["retrieval_reranker_backend"] == "identity"
    assert (
        record["retrieval_reranker_warning"]
        == "model_backed_reranker_not_implemented_identity_placeholder_used"
    )
