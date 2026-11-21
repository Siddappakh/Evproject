from __future__ import annotations

import argparse
from pathlib import Path
from urllib.request import urlretrieve


DATASETS = {
    "owid-energy": (
        "https://raw.githubusercontent.com/owid/energy-data/master/owid-energy-data.csv",
        "Our World in Data Energy dataset; global energy and emissions context.",
    ),
}


def download(output_dir: Path) -> list[dict[str, str]]:
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    for name, (url, description) in DATASETS.items():
        destination = output_dir / f"{name}.csv"
        urlretrieve(url, destination)
        results.append({"name": name, "url": url, "path": str(destination), "description": description})
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download documented public datasets.")
    parser.add_argument("--output", type=Path, default=Path("data/external"))
    args = parser.parse_args()
    for item in download(args.output):
        print(item)

