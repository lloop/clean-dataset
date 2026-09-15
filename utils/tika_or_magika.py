import json
import sys
from pathlib import Path
import pandas as pd

try:
    from magika import Magika
except ImportError:
    print("Error: 'magika' is not installed. Install it via 'pip install magika'.")
    sys.exit(1)


def normalize_magika_label(label: str) -> str:
    """Ensure Magika output label formats consistently as a dot-extension."""
    if not label:
        return "unknown"
    label = label.lower().strip()
    label_map = {
        "python": ".py",
        "jpeg": ".jpg",
        "text": ".txt",
        "javascript": ".js",
    }
    mapped = label_map.get(label, label)
    return mapped if mapped.startswith(".") else f".{mapped}"


def evaluate_magika_accuracy(
    manifest_path: Path, dirty_dir: Path, output_report: Path
) -> None:
    if not manifest_path.exists():
        print(f"Manifest not found at: {manifest_path.resolve()}")
        return
    if not dirty_dir.exists():
        print(f"Dirty data directory not found at: {dirty_dir.resolve()}")
        return

    # Load Manifest Ground Truth
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    ground_truth_scrambled = set()

    # If top-level JSON is a dict, check for a "files" list inside it
    if isinstance(manifest_data, dict):
        file_entries = manifest_data.get("files", [])
        if isinstance(file_entries, dict):
            file_entries = file_entries.values()
    elif isinstance(manifest_data, list):
        file_entries = manifest_data
    else:
        file_entries = []

    # Iterate over actual file dict entries safely
    for entry in file_entries:
        if isinstance(entry, dict) and entry.get("extension_scrambled") is True:
            fname = entry.get("filename") or entry.get("target_path")
            if fname:
                ground_truth_scrambled.add(fname)

    magika = Magika()
    CONFIDENCE_THRESHOLD = 0.85

    tp = 0  # Magika correctly flagged as scrambled
    fp = 0  # Magika falsely flagged a clean file as scrambled
    fn = 0  # Magika missed a scrambled file
    tn = 0  # Magika correctly left a clean file alone

    report_lines = []
    report_lines.append(f"MANIFEST PATH: {manifest_path.resolve()}")
    report_lines.append(f"DATA DIR:      {dirty_dir.resolve()}")
    report_lines.append(
        f"TOTAL GROUND TRUTH SCRAMBLED: {len(ground_truth_scrambled)}\n"
    )
    report_lines.append(
        f"{'FILENAME':<35} | {'MANIFEST':<12} | {'MAGIKA FLAG':<22} | RESULT"
    )
    report_lines.append("-" * 80)

    for file_path in sorted(dirty_dir.iterdir()):
        if file_path.is_dir() or file_path.name == "metadata":
            continue

        fname = file_path.name
        current_ext = file_path.suffix.lower()
        is_truly_scrambled = fname in ground_truth_scrambled

        try:
            res = magika.identify_path(file_path)
            detected_ext = normalize_magika_label(res.output.label)
            confidence_score = res.score
        except Exception:
            detected_ext = "error"
            confidence_score = 0.0

        magika_detected_scramble = (
            (detected_ext != current_ext)
            and (detected_ext != "error")
            and (confidence_score >= CONFIDENCE_THRESHOLD)
        )

        if is_truly_scrambled and magika_detected_scramble:
            tp += 1
            status = "✅ True Positive"
        elif not is_truly_scrambled and magika_detected_scramble:
            fp += 1
            status = "❌ False Positive"
        elif is_truly_scrambled and not magika_detected_scramble:
            fn += 1
            status = "❌ False Negative (Missed)"
        else:
            tn += 1
            status = "✅ True Negative"

        manifest_str = "Scrambled" if is_truly_scrambled else "Clean"
        magika_str = (
            f"Detected ({confidence_score:.2f})"
            if magika_detected_scramble
            else "Clean"
        )

        report_lines.append(
            f"{fname:<35} | {manifest_str:<12} | {magika_str:<22} | {status}"
        )

    total_evaluated = tp + fp + fn + tn
    accuracy = ((tp + tn) / total_evaluated * 100) if total_evaluated > 0 else 0
    precision = (tp / (tp + fp) * 100) if (tp + fp) > 0 else 0
    recall = (tp / (tp + fn) * 100) if (tp + fn) > 0 else 0

    summary = [
        "\n" + "=" * 80,
        "MAGIKA BENCHMARK PERFORMANCE REPORT",
        "=" * 80,
        f"Total Files Evaluated:        {total_evaluated}",
        f"Ground Truth Scrambled Count: {len(ground_truth_scrambled)}",
        f"Magika Total Detections:      {tp + fp}",
        "-" * 40,
        f"True Positives (Correctly Repaired):  {tp}",
        f"False Positives (Over-Repaired):     {fp}",
        f"False Negatives (Missed Scrambles):  {fn}",
        f"True Negatives  (Left Clean Alone):  {tn}",
        "-" * 40,
        f"Accuracy:  {accuracy:.2f}%",
        f"Precision: {precision:.2f}%",
        f"Recall:    {recall:.2f}%",
        "=" * 80,
    ]

    full_output = "\n".join(report_lines + summary)

    with open(output_report, "w", encoding="utf-8") as f:
        f.write(full_output)

    print("\n".join(summary))
    print(f"\nFull breakdown written to: {output_report.resolve()}")


def benchmark_confidence_thresholds(
    manifest_path: Path, dirty_dir: Path, output_csv: Path
) -> None:
    if not manifest_path.exists():
        print(f"Manifest not found at: {manifest_path.resolve()}")
        return
    if not dirty_dir.exists():
        print(f"Dirty data directory not found at: {dirty_dir.resolve()}")
        return

    # Load Manifest Ground Truth
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    ground_truth_scrambled = set()

    if isinstance(manifest_data, dict):
        file_entries = manifest_data.get("files", [])
        if isinstance(file_entries, dict):
            file_entries = file_entries.values()
    elif isinstance(manifest_data, list):
        file_entries = manifest_data
    else:
        file_entries = []

    for entry in file_entries:
        if isinstance(entry, dict) and entry.get("extension_scrambled") is True:
            fname = entry.get("filename") or entry.get("target_path")
            if fname:
                ground_truth_scrambled.add(fname)

    magika = Magika()

    # Pre-run Magika predictions once to avoid redundant filesystem reads
    file_predictions = []
    for file_path in sorted(dirty_dir.iterdir()):
        if file_path.is_dir() or file_path.name == "metadata":
            continue

        fname = file_path.name
        current_ext = file_path.suffix.lower()
        is_truly_scrambled = fname in ground_truth_scrambled

        try:
            res = magika.identify_path(file_path)
            detected_ext = normalize_magika_label(res.output.label)
            confidence_score = res.score
        except Exception:
            detected_ext = "error"
            confidence_score = 0.0

        file_predictions.append({
            "fname": fname,
            "current_ext": current_ext,
            "detected_ext": detected_ext,
            "confidence_score": confidence_score,
            "is_truly_scrambled": is_truly_scrambled,
        })

    # Sweep across confidence threshold levels
    threshold_levels = [round(x * 0.05, 2) for x in range(0, 21)]  # 0.00 to 1.00
    results_records = []

    for threshold in threshold_levels:
        tp = 0
        fp = 0
        fn = 0
        tn = 0

        for item in file_predictions:
            magika_detected_scramble = (
                (item["detected_ext"] != item["current_ext"])
                and (item["detected_ext"] != "error")
                and (item["confidence_score"] >= threshold)
            )

            if item["is_truly_scrambled"] and magika_detected_scramble:
                tp += 1
            elif not item["is_truly_scrambled"] and magika_detected_scramble:
                fp += 1
            elif item["is_truly_scrambled"] and not magika_detected_scramble:
                fn += 1
            else:
                tn += 1

        total_evaluated = tp + fp + fn + tn
        accuracy = ((tp + tn) / total_evaluated * 100) if total_evaluated > 0 else 0
        precision = (tp / (tp + fp) * 100) if (tp + fp) > 0 else 0
        recall = (tp / (tp + fn) * 100) if (tp + fn) > 0 else 0

        results_records.append({
            "confidence_threshold": threshold,
            "accuracy_pct": round(accuracy, 2),
            "precision_pct": round(precision, 2),
            "recall_pct": round(recall, 2),
            "magika_detections": tp + fp,
            "true_positives": tp,
            "false_positives": fp,
            "false_negatives": fn,
            "true_negatives": tn,

        })

    # Save to CSV using pandas
    df = pd.DataFrame(results_records)
    df.to_csv(output_csv, index=False)
    print(f"Benchmark levels successfully exported to: {output_csv.resolve()}")
    

if __name__ == "__main__":
    MANIFEST = Path("./dataset_dirty/metadata/manifest.json")
    DIRTY_DIR = Path("./dataset_dirty")
    OUTPUT = Path("magika_accuracy_report.txt")

    if len(sys.argv) > 1:
        DIRTY_DIR = Path(sys.argv[1])
        MANIFEST = DIRTY_DIR / "metadata" / "manifest.json"

    evaluate_magika_accuracy(MANIFEST, DIRTY_DIR, OUTPUT)
    
    OUTPUT_CSV = Path("confidence_threshold_vs_levels.csv")
    benchmark_confidence_thresholds(MANIFEST, DIRTY_DIR, OUTPUT_CSV
)