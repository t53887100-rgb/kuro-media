# kuro-media

Instagram @kuro_uriage に投稿する画像・動画の置き場です。

- `posts/YYYY-MM-DD/` … その日の投稿素材
- `assets/kuro/` … キャラクター「クロ」のイラスト素材
- `tools/` … 画像を作るためのスクリプト

## ツール
- `tools/render_carousel.py` … カルーセル画像（1080x1350）を作る
- `tools/render_reel.py` … クロが動くリール動画（1080x1920、吹き出し付き）と表紙画像を作る。使い方はファイル冒頭を参照
- `tools/render_reel_v3.py` … 標準のリール（明るい背景・強調演出・効果音）。同じフォルダに narration.wav があれば声も重ねる
- `tools/render_reel_v2.py` … 暗い背景の旧版

## リールの標準（2026-10-02 決定）
- 声：ElevenLabs「Mitsuwo」（voice_id zdWu2I1sJrZsmxJG5rie）、eleven_multilingual_v2、speed 1.15、stability 0.4、style 0.45
- 読み間違いしやすい語はカタカナにして読ませる（例：「はっ」→「ハッ」）。画面の文字は変えない
- 場面の長さは声の長さ＋0.3秒前後に合わせる
