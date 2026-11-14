"""Evaluate retrieved evidence and preserve per-query traces."""
from typing import Any


def is_chunk_evidence_hit(gold_page: int, evidence_quote: str, hit: dict[str, Any]) -> bool:
    """Check if a retrieved hit contains the gold evidence and matches the gold page."""
    hit_page = hit.get("page")
    if hit_page != gold_page:
        return False
        
    hit_text = hit.get("text", "")
    # Check direct substring
    if evidence_quote in hit_text:
        return True
        
    # Check normalized whitespace
    norm_quote = " ".join(evidence_quote.split())
    norm_hit = " ".join(hit_text.split())
    return norm_quote in norm_hit


def evaluate_query(question: dict[str, Any], hits: list[dict[str, Any]]) -> dict[str, Any]:
    """Check source/page and evidence containment; keep hit@1 and hit@3 trace."""
    gold_page = question["gold_page"]
    evidence_quote = question["evidence_quote"]
    
    evaluated_hits = []
    hit1 = False
    hit3 = False
    
    for rank, hit in enumerate(hits, start=1):
        has_hit = is_chunk_evidence_hit(gold_page, evidence_quote, hit)
        if rank == 1 and has_hit:
            hit1 = True
        if has_hit:
            hit3 = True
            
        evaluated_hits.append({
            "rank": rank,
            "chunk_id": hit.get("chunk_id"),
            "page": hit.get("page"),
            "section": hit.get("section"),
            "score": hit.get("score"),
            "distance": hit.get("distance"),
            "text": hit.get("text"),
            "is_evidence_hit": has_hit
        })
        
    return {
        "question_id": question["id"],
        "split": question["split"],
        "type": question.get("type", "unknown"),
        "question": question["question"],
        "expected_answer": question.get("expected_answer", ""),
        "gold_page": gold_page,
        "evidence_quote": evidence_quote,
        "filter_used": question.get("filter"),
        "hit_at_1": hit1,
        "hit_at_3": hit3,
        "hits": evaluated_hits
    }


def summarize(traces: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate Hit@1 and Evidence Hit@3 by dev and test split."""
    splits = ["all", "dev", "test"]
    summary: dict[str, Any] = {}
    
    for sp in splits:
        if sp == "all":
            subset = traces
        else:
            subset = [t for t in traces if t["split"] == sp]
            
        total = len(subset)
        if total == 0:
            continue
            
        hit1_count = sum(1 for t in subset if t["hit_at_1"])
        hit3_count = sum(1 for t in subset if t["hit_at_3"])
        
        summary[sp] = {
            "total_queries": total,
            "hit_at_1_count": hit1_count,
            "hit_at_1_ratio": f"{hit1_count}/{total}",
            "hit_at_1_pct": round(hit1_count / total * 100, 2),
            "hit_at_3_count": hit3_count,
            "hit_at_3_ratio": f"{hit3_count}/{total}",
            "hit_at_3_pct": round(hit3_count / total * 100, 2)
        }
        
    return summary
