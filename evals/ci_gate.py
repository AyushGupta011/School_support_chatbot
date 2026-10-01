import json
import sys

def check():
    with open("evals/results/hybrid_rerank_results.json", "r") as f:
        res = json.load(f)
        
    metrics = res["metrics"]
    if metrics["faithfulness"] < 0.8:
        print("Faithfulness below threshold")
        sys.exit(1)
    if metrics["leakage_prevention"] < 1.0:
        print("Leakage detected")
        sys.exit(1)
        
    # Generate markdown
    with open("evals/results/report.md", "w") as f:
        f.write("# Eval Results\n\n")
        f.write("| Metric | Score |\n")
        f.write("|---|---|\n")
        for k, v in metrics.items():
            f.write(f"| {k} | {v} |\n")
            
    print("CI Gate Passed")

if __name__ == "__main__":
    check()
