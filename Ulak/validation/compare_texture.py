"""Compare Ulak outputs with field-measured WoSIS texture samples."""

import csv
import json
import statistics
from datetime import date
from pathlib import Path

import requests


HERE = Path(__file__).resolve().parent
API = "http://127.0.0.1:8000/analiz-et"


def main():
    with (HERE / "wosis_turkey_texture.csv").open(encoding="utf-8", newline="") as handle:
        samples = list(csv.DictReader(handle))
    # One topmost field layer per profile, so a single site is not counted twice.
    samples.sort(key=lambda row: (int(row["profile_id"]), float(row["upper_depth_cm"]), float(row["lower_depth_cm"])))
    unique = {row["profile_id"]: row for row in reversed(samples)}

    results = []
    for sample in unique.values():
        lat, lon = float(sample["latitude"]), float(sample["longitude"])
        response = requests.post(API, json={"lat": lat, "lng": lon}, timeout=90)
        if not response.ok:
            print(f"SKIP {sample['profile_id']}: HTTP {response.status_code}", flush=True)
            continue
        predicted = response.json()["metrics"]["soil"]
        measured_clay, measured_sand = float(sample["clay"]), float(sample["sand"])
        row = {
            "profile_id": sample["profile_id"],
            "latitude": lat,
            "longitude": lon,
            "field_depth_cm": sample["lower_depth_cm"],
            "field_clay_percent": measured_clay,
            "map_clay_percent": predicted["clay_percent"],
            "field_sand_percent": measured_sand,
            "map_sand_percent": predicted["sand_percent"],
            "clay_error_pp": round(predicted["clay_percent"] - measured_clay, 2),
            "sand_error_pp": round(predicted["sand_percent"] - measured_sand, 2),
        }
        results.append(row)
        print(f"OK {sample['profile_id']} ({len(results)}/{len(unique)})", flush=True)

    if not results:
        raise SystemExit("No successful comparisons")
    with (HERE / "texture_comparison.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    summary = {
        "date": date.today().isoformat(),
        "source": "ISRIC WoSIS latest, CC BY 4.0 Turkish shallow clay/sand field observations",
        "sample_count": len(results),
        "attempted_count": len(unique),
        "clay_mae_percentage_points": round(statistics.mean(abs(row["clay_error_pp"]) for row in results), 2),
        "sand_mae_percentage_points": round(statistics.mean(abs(row["sand_error_pp"]) for row in results), 2),
        "clay_bias_percentage_points": round(statistics.mean(row["clay_error_pp"] for row in results), 2),
        "sand_bias_percentage_points": round(statistics.mean(row["sand_error_pp"] for row in results), 2),
        "clay_within_10pp": sum(abs(row["clay_error_pp"]) <= 10 for row in results),
        "sand_within_10pp": sum(abs(row["sand_error_pp"]) <= 10 for row in results),
    }
    (HERE / "texture_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
