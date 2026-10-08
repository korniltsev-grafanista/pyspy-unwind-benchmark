#!/bin/sh
# usage: build.sh <py-spy checkout> <macro-benchmark tool dir> <bench out dir> <site dir> <ref> <commit>
set -eu
SRC=$1 TOOL=$2 OUT=$3 SITE=$4 REF=$5 COMMIT=$6
HERE=$(cd "$(dirname "$0")" && pwd)

printf 'baseline:\n  ref: reader=process\n  commit: %s\ncomparison:\n  ref: reader=local\n  commit: %s\n' "$COMMIT" "$COMMIT" > "$OUT/plan.yaml"
ARCHIVE=$(mktemp -d)/results.tar.gz
tar -czf "$ARCHIVE" -C "$OUT" plan.yaml status.yaml baseline comparison
rm -rf "$SITE/index.html" "$SITE/index.assets"
mkdir -p "$SITE"
(cd "$TOOL" && go run . report "$ARCHIVE" "$SITE/index.html")
python3 -I "$HERE/postprocess.py" --html "$SITE/index.html" --host "$OUT/host.txt" --status "$OUT/status.yaml" --ref "$REF" --commit "$COMMIT"
chmod -R a+rX "$SITE"
