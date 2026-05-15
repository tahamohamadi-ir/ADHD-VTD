from src.retrieval.bm25_index import BM25Index
from src.retrieval.chroma_store import ChromaStore
from src.retrieval.context_builder import ContextBuilder
from src.retrieval.hybrid_retriever import HybridRetriever
from src.retrieval.retrieval_scorer import RetrievalQuery


def _records():
    return [
        {
            "id": "a",
            "question_fa": "تعداد دانشجویان افسرده چقدر است؟",
            "text_for_embedding": "تعداد دانشجویان افسرده count_query student_depression",
            "sql": "SELECT COUNT(*) FROM student_depression WHERE depression_flag = 1;",
            "intent": "count_query",
            "tables": ["student_depression"],
            "columns": ["student_depression.depression_flag"],
            "skeleton": "SELECT COUNT(*) FROM table WHERE condition",
        },
        {
            "id": "b",
            "question_fa": "میانگین خواب چقدر است؟",
            "text_for_embedding": "میانگین خواب aggregation_query student_habits_performance",
            "sql": "SELECT AVG(sleep_hours) FROM student_habits_performance;",
            "intent": "aggregation_query",
            "tables": ["student_habits_performance"],
            "columns": ["student_habits_performance.sleep_hours"],
            "skeleton": "SELECT AVG(metric) FROM table",
        },
    ]


def test_bm25_retrieves_lexically_relevant_record():
    index = BM25Index.from_records(_records())
    results = index.search("چند دانشجو افسردگی دارند؟", top_k=1)
    assert results[0].record["id"] == "a"


def test_hybrid_retriever_uses_schema_and_intent():
    retriever = HybridRetriever(use_vector_store=False)
    retriever.records = _records()
    retriever._bm25 = BM25Index.from_records(_records())

    query = RetrievalQuery(
        text="چند دانشجو افسردگی دارند؟",
        intent="count_query",
        tables=["student_depression"],
        columns=["student_depression.depression_flag"],
    )
    results = retriever.retrieve(query, top_k=1)
    assert results[0].record["id"] == "a"
    assert "intent" in results[0].reasons
    assert "schema_overlap" in results[0].reasons


def test_context_builder_outputs_few_shot_examples():
    retriever = HybridRetriever(use_vector_store=False)
    retriever.records = _records()
    retriever._bm25 = BM25Index.from_records(_records())
    results = retriever.retrieve("میانگین خواب", top_k=1)
    context = ContextBuilder().build(results)
    assert context.examples[0]["sql"]
    assert "SQL:" in context.prompt_context


def test_chroma_store_json_backend_builds_and_searches(tmp_path):
    store = ChromaStore(persist_dir=tmp_path / "vectors", backend="json")
    path = store.build(_records())

    assert path.exists()
    results = store.search("sleep average", top_k=1)
    assert results
    assert results[0].record["id"] in {"a", "b"}


def test_chroma_store_persistent_backend_builds_and_searches(tmp_path):
    store = ChromaStore(persist_dir=tmp_path / "chroma", backend="chroma")
    path = store.build(_records())

    assert path.exists()
    assert store.active_backend == "chroma"
    results = store.search("sleep average", top_k=1)
    assert results
    assert results[0].record["id"] in {"a", "b"}
