#!/bin/sh
set -eu

repo="Vladush/LinuxCamPAM"
api_latest="https://api.github.com/repos/${repo}/releases/latest"
tag=""
output_dir="."
spec="linuxcampam.spec"

while [ "$#" -gt 0 ]; do
    case "$1" in
        --tag)
            tag="$2"
            shift 2
            ;;
        --output-dir)
            output_dir="$2"
            shift 2
            ;;
        --spec)
            spec="$2"
            shift 2
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 2
            ;;
    esac
done

repo_root="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
if [ "${spec#/}" = "$spec" ]; then
    spec="${repo_root}/${spec}"
fi

download() {
    url="$1"
    destination="$2"
    mkdir -p "$(dirname "$destination")"
    curl -fL --retry 3 --retry-delay 2 --connect-timeout 30 --max-time 600 \
        -A "linuxcampam-copr-srpm" \
        -o "${destination}.tmp" \
        "$url"
    mv "${destination}.tmp" "$destination"
}

if [ -z "$tag" ]; then
    release_json="$(curl -fsSL --retry 3 --connect-timeout 30 -A "linuxcampam-copr-srpm" "$api_latest")"
    tag="$(printf '%s\n' "$release_json" | sed -n 's/.*"tag_name"[[:space:]]*:[[:space:]]*"\([^"]*\)".*/\1/p' | head -n 1)"
fi

if [ -z "$tag" ]; then
    echo "Unable to determine latest LinuxCamPAM release tag" >&2
    exit 1
fi

archive_version="${tag#v}"
case "$archive_version" in
    *-*)
        upstream_version="${archive_version%-*}"
        upstream_release="${archive_version##*-}"
        ;;
    *)
        upstream_version="$archive_version"
        upstream_release="1"
        ;;
esac

if ! printf '%s\n' "$upstream_version" | grep -Eq '^[A-Za-z0-9._+~]+$'; then
    echo "Invalid RPM Version derived from tag ${tag}: ${upstream_version}" >&2
    exit 1
fi
if ! printf '%s\n' "$upstream_release" | grep -Eq '^[A-Za-z0-9._+~]+$'; then
    echo "Invalid RPM Release derived from tag ${tag}: ${upstream_release}" >&2
    exit 1
fi

topdir="$(mktemp -d)"
cleanup() {
    rm -rf "$topdir"
}
trap cleanup EXIT INT TERM

sources="${topdir}/SOURCES"
srpms="${topdir}/SRPMS"
mkdir -p \
    "${topdir}/BUILD" \
    "${topdir}/BUILDROOT" \
    "${topdir}/RPMS" \
    "${topdir}/SOURCES" \
    "${topdir}/SPECS" \
    "${topdir}/SRPMS"

download \
    "https://github.com/${repo}/archive/refs/tags/${tag}.tar.gz" \
    "${sources}/LinuxCamPAM-${archive_version}.tar.gz"
download \
    "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx" \
    "${sources}/face_detection_yunet_2023mar.onnx"
download \
    "https://huggingface.co/opencv/face_recognition_sface/resolve/main/face_recognition_sface_2021dec.onnx" \
    "${sources}/face_recognition_sface_2021dec.onnx"

rpmbuild -bs "$spec" \
    --define "_topdir ${topdir}" \
    --define "upstream_tag ${tag}" \
    --define "archive_version ${archive_version}" \
    --define "upstream_version ${upstream_version}" \
    --define "upstream_release ${upstream_release}"

latest_srpm="$(find "$srpms" -maxdepth 1 -name '*.src.rpm' -type f | sort | tail -n 1)"
if [ -z "$latest_srpm" ]; then
    echo "rpmbuild did not produce a source RPM" >&2
    exit 1
fi

mkdir -p "$output_dir"
cp -p "$latest_srpm" "$output_dir/"
echo "Built ${output_dir}/$(basename "$latest_srpm")"
echo "Upstream release: ${tag}"
