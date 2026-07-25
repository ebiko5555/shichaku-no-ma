#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ひな型.html + assets/ の画像  →  index.html（1枚で完結する完成サイト）

画像を縮小してHTMLの中に埋め込みます。
こうすることで、ダブルクリックで開いても、スマホに送っても、
ネットがなくても、画像とシェーダーがきちんと動きます。
（ブラウザの安全機能で、ローカル画像を直接3D描画に使えないため）
"""

import base64
import os
import re
import shutil
import subprocess
import sys
import tempfile

ROOT     = os.path.dirname(os.path.abspath(__file__))
ASSETS   = os.path.join(ROOT, 'assets')
TEMPLATE = os.path.join(ROOT, 'ひな型.html')
OUTPUT   = os.path.join(ROOT, 'index.html')

MAX_PX  = 1200   # 長辺の最大ピクセル（大きくすると綺麗／重い）
QUALITY = 72     # JPEG品質 1-100

EXTS = ('.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG', '.webp')


def find_source(name):
    for ext in EXTS:
        p = os.path.join(ASSETS, name + ext)
        if os.path.exists(p):
            return p
    return None


def embed(name):
    """assets/<name>.* を縮小・JPEG化して data URI にする"""
    src = find_source(name)
    if not src:
        print('  × 画像が見つかりません: assets/%s.*' % name)
        return ''

    tmpdir = tempfile.mkdtemp()
    try:
        out = os.path.join(tmpdir, name + '.jpg')
        subprocess.run(
            ['sips', '-Z', str(MAX_PX),
             '-s', 'format', 'jpeg',
             '-s', 'formatOptions', str(QUALITY),
             src, '--out', out],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        raw = open(out, 'rb').read()
        print('  ○ %-28s %6.1f KB' % (os.path.basename(src), len(raw) / 1024))
        return 'data:image/jpeg;base64,' + base64.b64encode(raw).decode('ascii')
    except Exception as e:
        print('  × 変換に失敗: %s (%s)' % (src, e))
        return ''
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def main():
    if not os.path.exists(TEMPLATE):
        print('ひな型.html が見つかりません。')
        return 1

    html = open(TEMPLATE, encoding='utf-8').read()
    names = sorted(set(re.findall(r'\{\{IMG:([^}]+)\}\}', html)))
    if not names:
        print('ひな型に {{IMG:...}} の指定がありません。')
        return 1

    print('画像を読み込んでいます…')
    cache = {n: embed(n) for n in names}

    missing = [n for n, v in cache.items() if not v]
    html = re.sub(r'\{\{IMG:([^}]+)\}\}', lambda m: cache.get(m.group(1), ''), html)

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write(html)

    size = os.path.getsize(OUTPUT) / 1024 / 1024
    print('')
    print('書き出しました → index.html  (%.2f MB)' % size)
    if missing:
        print('※ 見つからなかった画像: ' + ', '.join(missing))
    print('index.html をダブルクリックすれば開きます。')
    print('スマホで見るときは、この index.html 1枚だけ送れば動きます。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
