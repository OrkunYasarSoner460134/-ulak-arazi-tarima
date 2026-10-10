"""Download shallow, openly licensed Turkish WoSIS texture measurements."""

import csv
from pathlib import Path

import requests


SERVICE = "https://maps.isric.org/mapserv/wosis_latest"
OUTPUT = Path(__file__).with_name("wosis_turkey_texture.csv")
LONGITUDE_TILES = [(26, 30), (30, 34), (34, 38), (38, 42), (42, 45)]


def get_layer(kind):
    samples = {}
    for west, east in LONGITUDE_TILES:
        response = requests.get(
            SERVICE,
            params={
                "service": "WFS",
                "version": "2.0.0",
                "request": "GetFeature",
                "typeNames": f"wosis_latest_{kind}",
                "count": 1000,
                "outputFormat": "geojson",
                "bbox": f"{west},35,{east},43,urn:ogc:def:crs:OGC:1.3:CRS84",
            },
            timeout=60,
        )
        response.raise_for_status()
        for feature in response.json()["features"]:
            props = feature["properties"]
            if props["country_name"] != "Turkey":
                continue
            if "CC BY 4.0" not in (props.get("licence") or ""):
                continue
            upper, lower = props["upper_depth"], props["lower_depth"]
            value = props["value_avg"]
            if upper is None or lower is None or value is None:
                continue
            if upper > 10 or lower > 35 or not 0 <= value <= 100:
                continue
            if kind == "clay" and "0 - 0.002 mm" not in (props.get("method_options") or ""):
                continue
            if kind == "sand" and "0.05 - 2 mm" not in (props.get("method_options") or ""):
                continue
            samples[props["layer_id"]] = {
                "profile_id": props["profile_id"],
                "layer_id": props["layer_id"],
                "latitude": feature["geometry"]["coordinates"][1],
                "longitude": feature["geometry"]["coordinates"][0],
                "upper_depth_cm": upper,
                "lower_depth_cm": lower,
                kind: value,
            }
    return samples


def main():
    clay, sand = get_layer("clay"), get_layer("sand")
    rows = []
    for layer_id in clay.keys() & sand.keys():
        c, s = clay[layer_id], sand[layer_id]
        if c["profile_id"] != s["profile_id"] or c["latitude"] != s["latitude"]:
            continue
        rows.append({**c, "sand": s["sand"]})
    rows.sort(key=lambda row: (row["longitude"], row["latitude"], row["layer_id"]))
    fields = ["profile_id", "layer_id", "latitude", "longitude", "upper_depth_cm", "lower_depth_cm", "clay", "sand"]
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"WoSIS shallow Turkey layers: clay={len(clay)}, sand={len(sand)}, paired={len(rows)}")


if __name__ == "__main__":
    main()
