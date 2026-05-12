#!/usr/bin/env python3
"""Build a LinuxCamPAM source RPM from the latest upstream GitHub release."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import urllib.parse
import urllib.request


REPO = "Vladush/LinuxCamPAM"
API_LATEST = f"https://api.github.com/repos/{REPO}/releases/latest"
SPEC = "linuxcampam.spec"
MODEL_SOURCES = {
    "face_detection_yunet_2023mar.onnx": (
        "https://github.com/opencv/opencv_zoo/raw/main/models/"
        "face_detection_yunet/face_detection_yunet_2023mar.onnx"
    ),
    "face_recognition_sface_2021dec.onnx": (
        "https://huggingface.co/opencv/face_recognition_sface/resolve/main/"
        "face_recognition_sface_2021dec.onnx"
    ),
}


def request(url: str) -> urllib.request.Request:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "linuxcampam-copr-srpm",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return urllib.request.Request(url, headers=headers)


def read_json(url: str) -> dict:
    with urllib.request.urlopen(request(url), timeout=60) as response:
        return json.load(response)


def download(url: str, destination: pathlib.Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    tmp = destination.with_suffix(destination.suffix + ".tmp")
    with urllib.request.urlopen(request(url), timeout=300) as response, tmp.open("wb") as out:
        shutil.copyfileobj(response, out)
    tmp.replace(destination)


def latest_tag() -> str:
    release = read_json(API_LATEST)
    tag = release.get("tag_name")
    if not tag:
        raise RuntimeError("GitHub latest release did not include a tag_name")
    if release.get("draft") or release.get("prerelease"):
        raise RuntimeError(f"Refusing to package non-final release: {tag}")
    return tag


def rpm_parts(tag: str) -> tuple[str, str, str]:
    archive_version = tag[1:] if tag.startswith("v") else tag
    if "-" in archive_version:
        version, release = archive_version.rsplit("-", 1)
    else:
        version, release = archive_version, "1"

    valid = re.compile(r"^[A-Za-z0-9._+~]+$")
    if not valid.match(version):
        raise RuntimeError(f"Release tag {tag!r} produced invalid RPM Version {version!r}")
    if not valid.match(release):
        raise RuntimeError(f"Release tag {tag!r} produced invalid RPM Release {release!r}")
    return archive_version, version, release


def run(command: list[str], cwd: pathlib.Path) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag", help="Package this upstream tag instead of GitHub's latest release")
    parser.add_argument("--output-dir", default=".", help="Directory where the resulting .src.rpm is copied")
    args = parser.parse_args()

    repo_root = pathlib.Path(__file__).resolve().parents[1]
    tag = args.tag or latest_tag()
    archive_version, version, release = rpm_parts(tag)

    topdir = repo_root / ".build" / "rpmbuild"
    sources = topdir / "SOURCES"
    srpms = topdir / "SRPMS"
    for subdir in ("BUILD", "BUILDROOT", "RPMS", "SOURCES", "SPECS", "SRPMS"):
        (topdir / subdir).mkdir(parents=True, exist_ok=True)

    encoded_tag = urllib.parse.quote(tag, safe="")
    archive_name = f"LinuxCamPAM-{archive_version}.tar.gz"
    archive_url = f"https://github.com/{REPO}/archive/refs/tags/{encoded_tag}.tar.gz"
    download(archive_url, sources / archive_name)
    for filename, url in MODEL_SOURCES.items():
        download(url, sources / filename)

    run(
        [
            "rpmbuild",
            "-bs",
            str(repo_root / SPEC),
            "--define",
            f"_topdir {topdir}",
            "--define",
            f"upstream_tag {tag}",
            "--define",
            f"archive_version {archive_version}",
            "--define",
            f"upstream_version {version}",
            "--define",
            f"upstream_release {release}",
        ],
        repo_root,
    )

    built = sorted(srpms.glob("*.src.rpm"), key=lambda path: path.stat().st_mtime)
    if not built:
        raise RuntimeError("rpmbuild did not produce a source RPM")

    output_dir = (repo_root / args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / built[-1].name
    shutil.copy2(built[-1], output)
    print(f"Built {output}")
    print(f"Upstream release: {tag}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)

