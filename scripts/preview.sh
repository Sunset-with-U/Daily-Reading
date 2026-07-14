#!/usr/bin/env bash
# 本地预览看板：组装 _site（真实 data/ 或 mock 数据）并起本地服务器
set -euo pipefail
cd "$(dirname "$0")/.."

rm -rf _site
mkdir -p _site
cp -r site/* _site/

if [ -f data/index.json ]; then
  cp -r data _site/data
  echo "使用仓库 data/ 真实数据"
else
  python3 scripts/make_mock_data.py _site/data
  echo "使用 mock 数据"
fi

PORT="${PORT:-8000}"
echo "→ http://localhost:${PORT}"
python3 -m http.server "$PORT" -d _site
