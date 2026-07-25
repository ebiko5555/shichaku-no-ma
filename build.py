#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
文章.txt + assets/ の画像 + ひな型.html  →  index.html（1枚で完結する完成サイト）

・文章は「文章.txt」を書き換えるだけでよい（HTMLを触らなくてよい）
・画像は縮小してHTMLの中に埋め込む
  こうすることで、ダブルクリックで開いても、スマホに送っても、
  ネットがなくても、画像とシェーダーがきちんと動く
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
TEXTFILE = os.path.join(ROOT, '文章.txt')
OUTPUT   = os.path.join(ROOT, 'index.html')

# 作品ページ
W_TEMPLATE = os.path.join(ROOT, '作品ページのひな型.html')
W_LIST     = os.path.join(ROOT, '作品リスト.txt')
W_OUTPUT   = os.path.join(ROOT, 'works.html')
W_MEDIADIR = os.path.join(ASSETS, 'works')

VIDEO_EXTS = ('.mp4', '.mov', '.webm', '.m4v')

MAX_PX  = 1200   # 長辺の最大ピクセル（大きくすると綺麗／重い）
QUALITY = 72     # JPEG品質 1-100

EXTS = ('.png', '.jpg', '.jpeg', '.PNG', '.JPG', '.JPEG', '.webp')


def parse_blocks(path):
    """[見出し] → 本文 を順番に並べたリストにする（同じ見出しが複数あってもよい）"""
    head = re.compile(r'^[\[［]\s*(.+?)\s*[\]］]\s*$')
    out, key, buf = [], None, []
    for line in open(path, encoding='utf-8').read().splitlines():
        m = head.match(line)
        if m:
            if key is not None:
                out.append((key, '\n'.join(buf).strip('\n')))
            key, buf = m.group(1), []
        elif line.lstrip().startswith('#'):
            continue
        elif key is not None:
            buf.append(line)
    if key is not None:
        out.append((key, '\n'.join(buf).strip('\n')))
    return out


def load_text():
    """文章.txt を読み、[見出し] → 本文 の対応表にする"""
    if not os.path.exists(TEXTFILE):
        print('  ※ 文章.txt が見つかりません。文章は空になります。')
        return {}

    table, key, buf = {}, None, []

    def flush():
        if key is not None:
            # 前後の空行を落として保存
            table[key] = '\n'.join(buf).strip('\n')

    # 全角［］で書かれていても受け付ける
    head = re.compile(r'^[\[［]\s*(.+?)\s*[\]］]\s*$')

    for line in open(TEXTFILE, encoding='utf-8').read().splitlines():
        m = head.match(line)
        if m:
            flush()
            key, buf = m.group(1), []
        elif line.lstrip().startswith('#'):
            continue                      # 説明行は読み飛ばす
        elif key is not None:
            buf.append(line)
    flush()

    print('  ○ 文章.txt から %d項目を読み込みました' % len(table))
    return table


def esc(s):
    """HTMLとして安全な文字に置き換える"""
    return (s.replace('&', '&amp;')
             .replace('<', '&lt;')
             .replace('>', '&gt;')
             .replace('"', '&quot;'))


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


def build_works():
    """作品リスト.txt + 作品ページのひな型.html → works.html"""
    if not os.path.exists(W_TEMPLATE) or not os.path.exists(W_LIST):
        print('  ※ 作品ページのひな型.html か 作品リスト.txt がないため、作品ページは作りません。')
        return

    blocks = parse_blocks(W_LIST)

    # [作品] が出てくるまではページ全体の設定
    page, works, cur = {}, [], None
    for key, val in blocks:
        if key == '作品':
            cur = {'作品': val}
            works.append(cur)
        elif cur is None:
            page[key] = val
        else:
            cur[key] = val

    # 作品ひとつぶんのHTMLを組む
    parts, warn = [], []
    for i, w in enumerate(works, 1):
        media = (w.get('素材') or '').strip()
        if not media:
            warn.append('%s（素材のファイル名が空）' % w.get('作品', '?'))
            continue
        path = os.path.join(W_MEDIADIR, media)
        if not os.path.exists(path):
            warn.append('%s（assets/works/%s が見つからない）' % (w.get('作品', '?'), media))
            continue

        src = 'assets/works/' + media
        if media.lower().endswith(VIDEO_EXTS):
            base = os.path.splitext(media)[0]
            poster = base + '-poster.jpg'
            pattr = ''
            if os.path.exists(os.path.join(W_MEDIADIR, poster)):
                pattr = ' poster="assets/works/%s"' % poster
            inner = ('<video src="%s"%s muted loop playsinline preload="none" '
                     'disablepictureinpicture></video>\n'
                     '        <span class="tap"><span>PLAY</span></span>' % (src, pattr))
        else:
            inner = '<img src="%s" alt="%s" loading="lazy">' % (src, esc(w.get('作品', '')))

        parts.append(
            '  <section class="work">\n'
            '    <div class="media rev">\n        %s\n    </div>\n'
            '    <p class="no rev">WORK %02d</p>\n'
            '    <h2 class="rev">%s</h2>\n'
            '    <p class="en rev">%s</p>\n'
            '    <p class="rev d1">%s</p>\n'
            '  </section>'
            % (inner, i,
               esc(w.get('作品', '')),
               esc(w.get('英語', '')),
               esc(w.get('説明', '')).replace('\n', '<br>'))
        )

    html = open(W_TEMPLATE, encoding='utf-8').read()
    lost = []

    def put(m):
        kind, key = m.group(1), m.group(2)
        if key not in page:
            lost.append(key)
            return ''
        body = esc(page[key])
        return body.replace('\n', '<br>' if kind == 'T' else ' ')

    html = re.sub(r'\{\{(TP?):([^}]+)\}\}', put, html)
    html = html.replace('{{WORKS}}', '\n\n'.join(parts))

    with open(W_OUTPUT, 'w', encoding='utf-8') as f:
        f.write(html)

    print('  ○ 作品ページ works.html … 作品%d点' % len(parts))
    for w in warn:
        print('     × 飛ばした作品: ' + w)
    for k in sorted(set(lost)):
        print('     × 項目が見あたらない: ［%s］' % k)


def main():
    if not os.path.exists(TEMPLATE):
        print('ひな型.html が見つかりません。')
        return 1

    html = open(TEMPLATE, encoding='utf-8').read()

    # ── 1. 文章を差し込む ──
    print('文章を読み込んでいます…')
    text = load_text()
    lost = []

    def put_text(m):
        kind, key = m.group(1), m.group(2)
        if key not in text:
            lost.append(key)
            return ''
        body = esc(text[key])
        # {{T:}} は改行を <br> に、{{TP:}} は改行を空白にする
        return body.replace('\n', '<br>' if kind == 'T' else ' ')

    html = re.sub(r'\{\{(TP?):([^}]+)\}\}', put_text, html)

    # ── 2. 画像を埋め込む ──
    names = sorted(set(re.findall(r'\{\{IMG:([^}]+)\}\}', html)))
    print('画像を読み込んでいます…')
    cache = {n: embed(n) for n in names}
    missing = [n for n, v in cache.items() if not v]
    html = re.sub(r'\{\{IMG:([^}]+)\}\}', lambda m: cache.get(m.group(1), ''), html)

    with open(OUTPUT, 'w', encoding='utf-8') as f:
        f.write(html)

    # ── 3. 作品ページ ──
    print('作品ページを組んでいます…')
    build_works()

    size = os.path.getsize(OUTPUT) / 1024 / 1024
    print('')
    print('書き出しました → index.html  (%.2f MB)' % size)
    if lost:
        print('※ 文章.txt に見あたらなかった項目（空欄になりました）:')
        for k in sorted(set(lost)):
            print('   ［%s］' % k)
    if missing:
        print('※ 見つからなかった画像: ' + ', '.join(missing))
    print('index.html をダブルクリックすれば開きます。')
    print('スマホで見るときは、この index.html 1枚だけ送れば動きます。')
    return 0


if __name__ == '__main__':
    sys.exit(main())
