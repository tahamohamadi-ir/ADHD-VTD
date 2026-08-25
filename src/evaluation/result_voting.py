from __future__ import annotations

from typing import Any, Sequence

ROW_RATIO_TOLERANCE = 0.10
CELL_JACCARD_THRESHOLD = 0.70


def _normalize_cell(value: Any) -> str:
    if isinstance(value, float):
        return f"{round(value, 4)}"
    return str(value).strip().lower()


def _row_cells(row: Any) -> tuple[str, ...]:
    if isinstance(row, dict):
        return tuple(sorted(_normalize_cell(v) for v in row.values()))
    if isinstance(row, (list, tuple)):
        return tuple(sorted(_normalize_cell(v) for v in row))
    return (_normalize_cell(row),)


def _cell_set(rows: Sequence[Any]) -> set[str]:
    return {c for row in rows for c in _row_cells(row)}


def results_equivalent(
    rows_a: Sequence[Any],
    rows_b: Sequence[Any],
    *,
    row_ratio_tolerance: float = ROW_RATIO_TOLERANCE,
    jaccard_threshold: float = CELL_JACCARD_THRESHOLD,
) -> bool:
    """Fuzzy result equivalence: similar row counts AND overlapping cell values."""
    len_a, len_b = len(list(rows_a)), len(list(rows_b))
    smaller, larger = min(len_a, len_b), max(len_a, len_b)
    if larger == 0:
        return True
    if larger > 0 and smaller / larger < 1 - row_ratio_tolerance:
        return False
    cells_a, cells_b = _cell_set(rows_a), _cell_set(rows_b)
    union = cells_a | cells_b
    if not union:
        return True
    jaccard = len(cells_a & cells_b) / len(union)
    return jaccard >= jaccard_threshold


def select_candidate_by_fuzzy_clusters(
    candidates: list[tuple[str, Sequence[Any]]],
) -> str | None:
    """Greedy fuzzy-cluster vote over executed candidate results.

    Args:
        candidates: list of (candidate_id, rows). Rows must be already-executed
            runtime-only evidence; no gold or labels may enter here.
    Returns:
        candidate_id of the largest cluster's first member, or None on empty input.
    """
    if not candidates:
        return None
    remaining = list(candidates)
    best_id: str | None = None
    best_size = 0
    while remaining:
        seed_id, seed_rows = remaining.pop(0)
        cluster = [seed_id]
        kept: list[tuple[str, Sequence[Any]]] = []
        for other_id, other_rows in remaining:
            if results_equivalent(seed_rows, other_rows):
                cluster.append(other_id)
            else:
                kept.append((other_id, other_rows))
        remaining = kept
        if len(cluster) > best_size:
            best_size = len(cluster)
            best_id = seed_id
    return best_id
