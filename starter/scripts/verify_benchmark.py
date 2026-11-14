"""Verify benchmark questions against extracted PDF content."""
import json
from pathlib import Path
import sys

# Ensure starter is in sys.path
root_dir = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root_dir))

from starter.src.ingestion import load_pdf

starter_dir = root_dir / "starter"
pdf_path = starter_dir / "data" / "De-an-mo-nganh-AI_Final.pdf"
pages = load_pdf(pdf_path, "de_an_ai_ptit_2024", "De-an-mo-nganh-AI_Final.pdf")
page_dict = {p.page: p.text for p in pages}

benchmark_path = starter_dir / "benchmark" / "benchmark.json"
with open(benchmark_path, encoding="utf-8") as f:
    benchmark = json.load(f)

print(f"Total questions: {len(benchmark)}")
dev_q = [q for q in benchmark if q["split"] == "dev"]
test_q = [q for q in benchmark if q["split"] == "test"]
filter_q = [q for q in benchmark if q["filter"] is not None]
test_filter_q = [q for q in test_q if q["filter"] is not None]

print(f"Split: Dev = {len(dev_q)}, Test = {len(test_q)}")
print(f"Filter count: Total = {len(filter_q)}, in Test = {len(test_filter_q)}")

errors = 0
for q in benchmark:
    p_num = q["gold_page"]
    page_txt = page_dict.get(p_num, "")
    quote = q["evidence_quote"]
    if quote not in page_txt:
        print(f"FAIL: {q['id']} (Page {p_num}) - quote not found!")
        errors += 1
    else:
        print(f"PASS: {q['id']} (Page {p_num}) | {q['split']} | Filter: {q['filter']} | {q['type']}")

if errors == 0:
    print("\nSUCCESS: All 20 benchmark questions verified 100% against corpus text!")
else:
    print(f"\nFAILURE: {errors} errors found.")

