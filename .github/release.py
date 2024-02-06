#!/bin/env python3


import os
import subprocess
import sys
from pathlib import Path

import yaml


def create_tag(tag: str) -> None:
    try:
        subprocess.check_call(
            ["git", "show-ref", "--tags", "--verify", "--quiet", f"refs/tags/{tag}"]
        )
    except subprocess.CalledProcessError:
        pass
    else:
        print(f"Tag {tag} already exists", file=sys.stderr)
        return

    subprocess.check_call(["git", "tag", tag])
    subprocess.check_call(["git", "push", tag])


def create_chart_tag(path: Path) -> None:
    chart_info = yaml.safe_load(
        subprocess.check_output(["helm", "show", "chart", str(path)])
    )

    version = chart_info["version"]
    name = chart_info["name"]
    tag = f"helm-{name}-v{version}"
    create_tag(tag)


if sys.argv[1] == "tag-release":
    version = subprocess.check_output(["hatch", "version"]).decode().rstrip()
    create_tag(f"v{version}")
elif sys.argv[1] == "tag-helm-releases":
    for chart_path in os.scandir("deployments/helm"):
        chart_file = Path(chart_path) / "Chart.yaml"
        if chart_file.is_file():
            create_chart_tag(chart_file.parent)
