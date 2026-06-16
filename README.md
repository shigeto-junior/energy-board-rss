# Energy Board RSS — METI審議会を受動収集する

[Energy Board Japan](https://energy-board.xvps.jp/) の審議会データ（経産省/METIの審議会・研究会の会議と資料）を **RSS 2.0 に変換**し、Inoreader などのRSSリーダーで受動的に追いかけるための仕組み。

経産省の審議会ページ自体はRSSを出していないが、Energy Board の公開API（`/api/meetings`）から会議データを取得できるので、そこからフィードを生成する。新着の「会議1回」が1アイテムになり、配布資料へのリンクとタグが本文に入る。

## 仕組み

```
energy-board /api/meetings  →  build_feed.py  →  docs/*.xml  →  GitHub Pages  →  Inoreader購読
                                                  （48時間ごとに自動更新）
```

依存ライブラリなし（Python標準ライブラリのみ）。

## ローカルで試す

```bash
# 全審議会の新着
python3 build_feed.py --out docs/all.xml

# キーワード絞り込み（APIの全文検索）
python3 build_feed.py --search 蓄電池 --out docs/storage.xml

# 審議会名で絞り込み（部分一致・複数可）
python3 build_feed.py --council 次世代電力系統 電力安定供給 --out docs/grid.xml

# 設定ファイルで複数フィードを一括生成
python3 build_feed.py --config feeds.json
```

## フィード設定（feeds.json）

`feeds.json` を編集すれば、欲しいテーマごとにフィードを増やせる。

- `search` … APIの全文検索（資料タイトル等も対象）。例: `"洋上風力"`
- `council` … 審議会名の部分一致フィルタ（配列、複数可）
- `limit` … 取得件数の上限
- `base_url` … 公開URLの基点（GitHub Pagesのもの）。`atom:self` に使う

利用可能な審議会は103種類（次世代電力系統WG、容量市場、原子力小委員会、洋上風力、CCS事業WG など）。

## 無料で自動ホスティング（GitHub Pages）

1. GitHubで新規リポジトリ `energy-board-rss` を作成。
2. このフォルダ一式（`build_feed.py` / `feeds.json` / `.github/`）をpush。
3. `feeds.json` の `base_url` を `https://<ユーザー名>.github.io/energy-board-rss` に書き換える。
4. リポジトリ設定 → **Settings → Pages → Source: GitHub Actions** を選択。
5. **Actions** タブで `Build Energy Board RSS` を一度手動実行（Run workflow）。
6. 数分後、`https://<ユーザー名>.github.io/energy-board-rss/` にフィード一覧ページができる。

以降は48時間ごとに自動更新される。

## 運用上の自動化（自動停止対策・失敗通知）

- **自動更新の継続**: ワークフローは毎回 `docs/*.xml` をリポジトリへコミットで戻す。これによりコミット活動が継続し、GitHub の「60日間リポジトリ無活動でスケジュール実行が自動停止」ルールに引っかからない（＝放置しても止まらない）。
- **失敗通知**: ビルドが失敗すると、リポジトリに通知用の Issue が自動で立つ（既存があればコメント追記）。また全フィード合計が 0 件になった場合は上流 API 障害の疑いとしてビルドを意図的に失敗させ、同じく通知に乗せる。Issue 通知に加え、GitHub からは設定に応じてメール通知も届く。

## Inoreaderで購読

1. Inoreaderの「フィードを追加」に、生成されたフィードURLを貼る。
   - 例: `https://<ユーザー名>.github.io/energy-board-rss/storage.xml`
2. テーマ別フィードをそれぞれ購読すれば、審議会の新着が受動的に流れてくる。

## メモ

- データ出典: 経済産業省ウェブサイト（https://www.meti.go.jp/shingikai/index.html ）。Energy Board Japan が収集・整形したものを利用している。
- 会議の開催日に時刻情報がないため、`pubDate` はJST正午で固定している（リーダー上の並び順は日付ベースで正しく出る）。
- APIの仕様変更でフィールド名が変わった場合は `build_feed.py` の `fetch()` 周辺を調整する。
