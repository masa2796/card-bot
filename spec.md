## プロンプト（AIエージェント用）

あなたは、このリポジトリ内のコードを安全に変更するフルスタックエンジニアです。
以下の要件を満たすように、**backend と frontend の両方を実装・修正**してください。

---

### ■ 現状と前提

* ディレクトリ構成（主要なもの）

  * `backend/` … FastAPI + Python ベースの RAG API
  * `frontend/` … Next.js + TypeScript + Tailwind のチャットUI
  * `data/` … カードのマスターデータをまとめた JSON などを配置

* RAG の流れ：

  1. OpenAI Embeddings（`text-embedding-3-small`）でクエリをベクトル化
  2. Upstash Vector の `/query` を叩いて類似ドキュメントを検索
  3. `metadata.card_id` などでカードを特定し、チャットの回答を生成

* すでに `search_similar_docs` などを使った RAG バックエンドは実装済み。

* カードのマスターデータは `data/data.json`（もしくはそれに相当するファイル）にまとまっている想定。

  * 各要素は以下のような構造：

    ```jsonc
    {
      "id": "10012110",
      "url": "...",
      "name": "アドベンチャーエルフ・メイ",
      "image_before": "https://...png",
      "image_after": "https://...png",
      "type": "-",
      "rarity": "シルバーレア",
      "class": "エルフ",
      "cv": "門脇舞以",
      "illustrator": "ツネくん",
      "crest": "",
      "qa": [ ... ],
      "cost": 1,
      "attack": 1,
      "hp": 1,
      "effect_1": "【ファンファーレ】【コンボ_3】相手の場のフォロワー1枚を選ぶ。それに3ダメージ。",
      "keywords": ["コンボ", "ファンファーレ"]
    }
    ```

* `frontend/ui_test.html` に、カード一覧 UI の参考デザインが置いてある。

---

### ■ やりたいこと（タスク概要）

1. **Upstash のベクトル検索結果から `id` を取得する**

   * すでに Upstash Vector から取得している `metadata` の中に、カードを特定できる `card_id` や `source` などがある前提。
   * RAG のバックエンド処理で、この `card_id` を使ってカード情報を引けるようにする。

2. **取得した `id` を使って `data/data.json` から必要情報を抽出する**

   * `data/data.json`（または似た位置にあるマスターファイル）を読み込み、

     * `id === card_id` にマッチするカードを検索
     * 以下のような情報を最低限含む「カードサマリー構造体」を作成する：

       * `card_id` (`id`)
       * `name`
       * `class`
       * `rarity`
       * `cost`
       * `attack`
       * `hp`
       * `effect`（`effect_1` を主に使用）
       * `keywords`
       * `image_before` / `image_after`
   * これを RAG のレスポンス（FastAPI の `ChatResponse` / `ChatResponseMeta`）に載せてフロントに返す。

3. **`ui_test.html` の UI を参考に、チャットボットに適したカード一覧をフロントで表示する**

   * `frontend/ui_test.html` のレイアウト・スタイルを参考に、Next.js + Tailwind で「カード一覧コンポーネント」を作る。
   * 要件：

     * チャット回答（GPT のテキスト）の **下** に、「今回の検索でヒットしたカード一覧」を表示する。
     * 1カードあたり：

       * 画像（`image_before`）を小さめに表示
       * カード名 / クラス / レアリティ
       * コスト・攻撃・体力（例：`コスト 1 / 1 / 1` など）
       * 効果テキスト（`effect`）
       * キーワードタグ（`#コンボ` など）
     * 複数カードが返ってきた場合には、縦に一覧で並ぶようにする。
   * 可能であれば、`frontend/src/components/` 以下に `CardList.tsx` / `CardItem.tsx` などのコンポーネントを切り出し、

     * 既存のチャットメッセージUI（`ChatMessage` コンポーネントなど）がレスポンスの `meta.cards` を受け取ってカード一覧をレンダリングできるようにする。

---

### ■ 具体的な実装ステップ（指示）

#### 1. バックエンド：カード情報の紐付け

1. `backend/` 配下の RAG 関連コード（`chat` 関数・`search_similar_docs` など）を確認する。
2. Upstash のレスポンス `matches` / `result` の `metadata` に `card_id` や `source` が含まれていることを前提に、

   * `search_similar_docs` の `docs.append(...)` 部分に `card_id` と `source` を含めるようにする。
3. `data/data.json` を読み込み、`card_id` → カードマスターデータを返すヘルパー関数を作る：

   * 例：`load_card_master(card_id: str) -> dict`
   * 毎回ファイルを読むと重い場合は、プロセス起動時に読み込んでメモリにキャッシュする形でもよい（パフォーマンスを見て判断）。
4. `chat()` 内で、RAG から返ってきた `docs` を元に、カードマスタを結合して「カードサマリー配列」を生成する。

   * 例：

     ```python
     card_summaries = []
     for doc in docs:
         card_id = doc.get("card_id")
         if not card_id:
             continue
         master = load_card_master(card_id)
         card_summaries.append({
             "card_id": card_id,
             "name": master["name"],
             "class": master["class"],
             "rarity": master["rarity"],
             "cost": master["cost"],
             "attack": master["attack"],
             "hp": master["hp"],
             "effect": master.get("effect_1") or doc["text"],
             "keywords": master.get("keywords", []),
             "image_before": master["image_before"],
             "image_after": master["image_after"],
         })
     ```
5. `ChatResponseMeta` 型に `cards: List[CardSummary]` のようなフィールドを追加し、APIレスポンスの `meta.cards` に `card_summaries` を載せる。
6. FastAPI の OpenAPI スキーマが自動生成されている場合は、新しいフィールドが反映されるように Pydantic モデルも更新する。

#### 2. フロントエンド：カード一覧 UI の実装

1. `frontend/ui_test.html` を開き、カード一覧のデザイン・クラス名・レイアウトを確認する。
2. `frontend/src/components/` 配下に、以下のようなコンポーネントを作成する：

   * `CardItem.tsx`：単一カードの表示
   * `CardList.tsx`：カード配列全体の表示
3. `CardItem` コンポーネントでは、`ui_test.html` のデザインをベースに、Tailwind クラスへ置き換えて実装する。

   * 画像・タイトル・クラス/レアリティ・ステータス・効果テキスト・キーワードタグを表示。
4. `CardList` コンポーネントは、`props.cards`（`CardSummary[]`）を受け取り、リストとして `CardItem` を並べる。
5. チャットのメインページ（`src/app/page.tsx` など）で、

   * バックエンドのレスポンス型（`ChatMessagePayload` / `ChatResponse`）に `meta.cards` が含まれるよう更新する。
   * アシスタントからのメッセージを表示する箇所に、`meta.cards` が存在する場合のみ `CardList` をレンダリングする。

#### 3. 動作確認

1. バックエンドを起動し、フロントエンドのチャットから RAG 検索が行われるようにする。
2. カード効果に関連するクエリ（例：「メイの効果教えて」「コンボ3で3ダメージ与えるカード」など）を投げて、

   * チャット回答テキストが表示される
   * その下に、`ui_test.html` をベースにしたカード一覧 UI が表示される
   * カード名・画像・ステータス・効果などが正しく表示されている
     ことを確認する。
3. ヒット件数が 0 件の場合は、カード一覧を表示しない or 「該当カードが見つかりませんでした」のようなメッセージを表示するようにする。

---

### ■ 完了条件

* Upstash の検索結果から `metadata.card_id` を用いて、`data/data.json` のカードマスターデータを取得できること。
* チャット API のレスポンスに、カードサマリー情報（`meta.cards`）が含まれていること。
* フロントエンドのチャット画面において、

  * チャット回答テキストの下に、
  * `ui_test.html` の UI を参考にしたカード一覧が表示されること。
* 上記機能が型エラーやビルドエラーなく動作すること（`npm run lint` / `npm run build` が通るのが望ましい）。