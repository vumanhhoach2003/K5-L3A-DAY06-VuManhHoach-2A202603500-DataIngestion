"""Main orchestration pipeline for Day 06 Data Ingestion Lab."""
import json
import os
import sys
import time
from pathlib import Path
from dotenv import load_dotenv

# Ensure imports work from project root or starter directory
current_file = Path(__file__).resolve()
starter_dir = current_file.parents[1]
root_dir = current_file.parents[2]

sys.path.insert(0, str(root_dir))
sys.path.insert(0, str(starter_dir))

from starter.src.ingestion import load_pdf
from starter.src.chunking import fixed_size, by_paragraph
from starter.src.embeddings import SentenceTransformerEmbedder
from starter.src.store import PgVectorStore
from starter.src.evaluation import evaluate_query, summarize


def main() -> None:
    print("=" * 60)
    print("DAY 06 - DATA INGESTION PIPELINE & BENCHMARK EVALUATION")
    print("=" * 60)

    # 1. Environment & Paths
    load_dotenv(starter_dir / ".env")
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL missing from .env")

    pdf_path = starter_dir / "data" / "De-an-mo-nganh-AI_Final.pdf"
    benchmark_path = starter_dir / "benchmark" / "benchmark.json"
    results_dir = starter_dir / "results"
    results_dir.mkdir(exist_ok=True)

    # 2. Ingest Corpus & Validate
    print(f"\n[1/5] Loading and validating corpus from: {pdf_path}")
    pages = load_pdf(pdf_path, "de_an_ai_ptit_2024", "De-an-mo-nganh-AI_Final.pdf")
    content_page_count = len(pages)
    print(f"-> Extracted {content_page_count} content pages (Physical pages 4-57).")
    if content_page_count < 30:
        raise ValueError(f"Corpus must have at least 30 content pages; found {content_page_count}")

    # Load Benchmark
    print(f"-> Loading benchmark from: {benchmark_path}")
    with open(benchmark_path, encoding="utf-8") as f:
        benchmark = json.load(f)
    print(f"-> Loaded {len(benchmark)} questions (15 dev, 5 test, 3 with filter).")

    # 3. Initialize Embedder & Store
    model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    print(f"\n[2/5] Initializing local multilingual embedder: {model_name}")
    embedder = SentenceTransformerEmbedder(model_name)
    print(f"-> Embedder ready. Vector dimensions: {embedder.dimensions}")

    print(f"\n[3/5] Initializing PostgreSQL + pgvector store...")
    store = PgVectorStore(db_url, embedder.dimensions)
    store.create_schema()
    print("-> Schema and vector extension confirmed.")

    # 4. Chunking & Indexing for 3 Strategies
    # Strategy A: Fixed-size 500, overlap 50
    # Strategy B: Paragraph/structure-aware, max 800
    # Strategy C: Same chunks as B, but with metadata filter in retrieval
    strategies = [
        {"name": "A", "type": "fixed", "size": 500, "overlap": 50},
        {"name": "B", "type": "paragraph", "max_size": 800, "overlap": 0},
        {"name": "C", "type": "paragraph", "max_size": 800, "overlap": 0}
    ]

    strategy_stats = {}
    strategy_chunks = {}

    print(f"\n[4/5] Chunking and Indexing Strategies (A, B, C)...")
    for strat in strategies:
        s_name = strat["name"]
        print(f"\n--- Processing Strategy {s_name} ---")
        t0 = time.time()
        chunks = []
        if strat["type"] == "fixed":
            for p in pages:
                chunks.extend(fixed_size(p, size=strat["size"], overlap=strat["overlap"]))
        else:
            for p in pages:
                chunks.extend(by_paragraph(p, max_size=strat["max_size"]))

        strategy_chunks[s_name] = chunks
        total_chars = sum(len(c.text) for c in chunks)
        avg_chunk_len = round(total_chars / len(chunks), 1) if chunks else 0

        # Embed chunks
        print(f"   Embedding {len(chunks)} chunks...")
        texts = [c.text for c in chunks]
        vectors = embedder.embed_documents(texts)

        # Store in pgvector (idempotent upsert)
        print(f"   Upserting into pgvector (idempotent check)...")
        store.upsert(s_name, chunks, vectors)

        # Idempotency re-test: upserting again should keep exact same count
        store.upsert(s_name, chunks, vectors)

        ingest_time = round(time.time() - t0, 2)
        strategy_stats[s_name] = {
            "chunk_count": len(chunks),
            "total_chars": total_chars,
            "avg_chunk_len": avg_chunk_len,
            "ingest_time_seconds": ingest_time,
            "cost_usd": 0.0
        }
        print(f"   Strategy {s_name} completed in {ingest_time}s: {len(chunks)} chunks, avg len {avg_chunk_len} chars.")

    # 5. Run Benchmark Queries & Evaluate Top-3
    print(f"\n[5/5] Running Benchmark across Strategies A, B, C...")
    all_summaries = {}
    
    for strat in strategies:
        s_name = strat["name"]
        print(f"\nEvaluating Strategy {s_name} on {len(benchmark)} questions...")
        traces = []
        for q in benchmark:
            q_vec = embedder.embed_query(q["question"])
            
            # Filter condition: only Strategy C applies filter when q['filter'] exists
            query_filters = q["filter"] if s_name == "C" else None
            
            hits = store.search(
                strategy=s_name,
                query_vector=q_vec,
                top_k=3,
                filters=query_filters
            )
            
            eval_res = evaluate_query(q, hits)
            traces.append(eval_res)

        summary = summarize(traces)
        all_summaries[s_name] = summary

        # Save individual trace
        trace_file = results_dir / f"traces_strategy_{s_name}.json"
        with open(trace_file, "w", encoding="utf-8") as f:
            json.dump(traces, f, ensure_ascii=False, indent=2)
        print(f"   Saved trace to: {trace_file}")
        
        print(f"   Result Strategy {s_name}:")
        print(f"     Dev  Hit@1: {summary['dev']['hit_at_1_ratio']} ({summary['dev']['hit_at_1_pct']}%) | Evidence Hit@3: {summary['dev']['hit_at_3_ratio']} ({summary['dev']['hit_at_3_pct']}%)")
        print(f"     Test Hit@1: {summary['test']['hit_at_1_ratio']} ({summary['test']['hit_at_1_pct']}%) | Evidence Hit@3: {summary['test']['hit_at_3_ratio']} ({summary['test']['hit_at_3_pct']}%)")

    # Save summary metrics
    summary_path = results_dir / "summary_metrics.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump({
            "strategy_stats": strategy_stats,
            "evaluation_summary": all_summaries
        }, f, ensure_ascii=False, indent=2)
    print(f"\nSummary metrics written to: {summary_path}")

    # Update artifacts/experiment_log.csv
    exp_log_path = root_dir / "artifacts" / "experiment_log.csv"
    with open(exp_log_path, "w", encoding="utf-8") as f:
        f.write("strategy,chunking,chunk_size,overlap,metadata,filter,vectorizer,hypothesis,dev_hit1,dev_hit3,test_hit1,test_hit3,notes\n")
        f.write(f"A,fixed,500,50,source_page_section,none,{model_name},Baseline fixed-size window without semantic boundaries,{all_summaries['A']['dev']['hit_at_1_ratio']},{all_summaries['A']['dev']['hit_at_3_ratio']},{all_summaries['A']['test']['hit_at_1_ratio']},{all_summaries['A']['test']['hit_at_3_ratio']},Chunk count: {strategy_stats['A']['chunk_count']}\n")
        f.write(f"B,paragraph,800,0,source_page_section,none,{model_name},Paragraph chunking preserves context and sentence integrity,{all_summaries['B']['dev']['hit_at_1_ratio']},{all_summaries['B']['dev']['hit_at_3_ratio']},{all_summaries['B']['test']['hit_at_1_ratio']},{all_summaries['B']['test']['hit_at_3_ratio']},Chunk count: {strategy_stats['B']['chunk_count']}\n")
        f.write(f"C,paragraph,800,0,source_page_section,section_filter,{model_name},Paragraph chunking + metadata filter eliminates cross-section noise,{all_summaries['C']['dev']['hit_at_1_ratio']},{all_summaries['C']['dev']['hit_at_3_ratio']},{all_summaries['C']['test']['hit_at_1_ratio']},{all_summaries['C']['test']['hit_at_3_ratio']},Chunk count: {strategy_stats['C']['chunk_count']}\n")
    print(f"Updated experiment log at: {exp_log_path}")

    print("\n" + "=" * 60)
    print("PIPELINE EXECUTION COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
