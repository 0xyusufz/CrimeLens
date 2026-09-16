# ML quality measurement

`precision_benchmark_v1.json` is a synthetic, labeled regression benchmark.
It measures entity and relationship precision, recall, and F1 separately.

The desired 0.80–0.90 range is a target for the benchmark—not a claim of
production accuracy. A real accuracy claim requires investigator-reviewed,
representative labeled evidence that includes scans, PDFs, tables, CDRs,
transactions, aliases, and negative examples.

Run it with the existing entry point after Python test execution is available:

```python
from ml.evaluation import evaluate_benchmark
from ml.pipeline import process_document

report = evaluate_benchmark("ml/fixtures/precision_benchmark_v1.json", process_document)
print(report.as_dict())
```
