from src.retrieval.bm25_index import BM25Index
from src.retrieval.chroma_store import ChromaStore, VectorSearchResult
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


def test_hybrid_retriever_can_run_vector_only_mode():
    class FakeVectorStore:
        def search(self, text, top_k=25):
            return [VectorSearchResult(record=_records()[1], score=1.0)]

    retriever = HybridRetriever(retrieval_mode="vector")
    retriever.records = _records()
    retriever._vector_store = FakeVectorStore()

    results = retriever.retrieve("unrelated lexical text", top_k=1)
    assert results[0].record["id"] == "b"


def test_hybrid_retriever_keeps_schema_evidence_when_text_scores_dominate():
    records = [
        {
            "id": "wrong_a",
            "question_fa": "distribution family history",
            "text_for_embedding": "distribution family history",
            "sql": "SELECT COUNT(*) FROM student_depression;",
            "intent": "grouping_query",
            "tables": ["student_depression"],
            "columns": [],
        },
        {
            "id": "wrong_b",
            "question_fa": "distribution family history",
            "text_for_embedding": "distribution family history",
            "sql": "SELECT COUNT(*) FROM workplace_mental_health_survey;",
            "intent": "grouping_query",
            "tables": ["workplace_mental_health_survey"],
            "columns": [],
        },
        {
            "id": "right_schema",
            "question_fa": "university survey gender",
            "text_for_embedding": "university survey gender",
            "sql": "SELECT year_of_study, COUNT(*) FROM university_student_mental_health GROUP BY year_of_study;",
            "intent": "grouping_query",
            "tables": ["university_student_mental_health"],
            "columns": ["year_of_study"],
        },
    ]
    retriever = HybridRetriever(retrieval_mode="hybrid")
    retriever.records = records
    retriever._bm25 = BM25Index.from_records(records)

    query = RetrievalQuery(
        text="distribution family history",
        tables=["university_student_mental_health"],
        columns=["year_of_study"],
    )
    results = retriever.retrieve(query, top_k=2)

    assert any(result.record["id"] == "right_schema" for result in results)


def test_retrieval_skeleton_prefers_grouped_rate_examples():
    records = [
        {
            "id": "scalar_count",
            "question_fa": "depression count",
            "text_for_embedding": "depression count by gender",
            "sql": "SELECT COUNT(*) FROM student_depression WHERE depression_flag = 1;",
            "intent": "rate_query",
            "tables": ["student_depression"],
            "columns": ["depression_flag"],
        },
        {
            "id": "grouped_rate",
            "question_fa": "depression rate by gender",
            "text_for_embedding": "depression rate by gender",
            "sql": (
                "SELECT gender, COUNT(*) AS total, SUM(depression_flag) AS depressed, "
                "ROUND(100.0 * SUM(depression_flag) / COUNT(*), 2) AS rate_pct "
                "FROM student_depression GROUP BY gender ORDER BY rate_pct DESC;"
            ),
            "intent": "rate_query",
            "tables": ["student_depression"],
            "columns": ["gender", "depression_flag"],
        },
    ]
    retriever = HybridRetriever(use_vector_store=False)
    retriever.records = records
    retriever._bm25 = BM25Index.from_records(records)

    query = RetrievalQuery(
        text="depression rate by gender",
        intent="rate_query",
        tables=["student_depression"],
        columns=["gender", "depression_flag"],
        skeleton="group count sum rate",
    )
    results = retriever.retrieve(query, top_k=1)

    assert results[0].record["id"] == "grouped_rate"
    assert "skeleton" in results[0].reasons


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
