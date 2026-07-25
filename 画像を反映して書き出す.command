#!/bin/bash
# assets/ の画像 + ひな型.html  →  index.html を書き出す
cd "$(dirname "$0")" || exit 1
echo "───────────────────────────────"
echo " 試着の間 ― サイトを書き出します"
echo "───────────────────────────────"
python3 build.py
echo ""
echo "このウィンドウは閉じてかまいません。"
