# gamechat-ai (MVP)

ゲームカードの攻略情報をチャット形式で回答する、Next.js + FastAPI 製の RAG アシスタント MVP です。ブラウザから質問を送信すると、バックエンドがシンプルな検索拡張生成フローで Upstash Vector から関連テキストを取り出し、OpenAI Chat API へ渡して回答を生成します。

> このリポジトリは「まず遊べる最小限の機能」に特化しています。高度なクエリ分類やハイブリッド検索、認証などは含まれていません。

---

## 機能概要

### できること
- ブラウザのチャット UI から攻略に関する質問を送信
- OpenAI Embeddings で質問をベクトル化し、Upstash Vector で類似ドキュメントを top-k 検索
- 検索結果をコンテキストとして OpenAI Chat API に渡し、回答を生成
- 回答をチャット画面に即時表示

### 含まれていないもの（今後の拡張候補）
- LLM によるクエリ分類や高度なハイブリッド検索
- 構造化 DB 検索（HP/タイプ/ダメージ等のフィルタリング）
- 認証・ユーザー管理・履歴永続化
- 監視や CI/CD などの本番向け仕組み

---

## アーキテクチャ

```txt
Frontend (Next.js, TypeScript, Tailwind)
      ↓ HTTP (JSON)
Backend (FastAPI, Python)
      ↓
OpenAI API（Embeddings + Chat Completion）
Upstash Vector（ベクトル検索）
```

### ディレクトリ構成（抜粋）

```txt
gamechat-ai/
├── frontend/            # Next.js (App Router) + TypeScript + Tailwind
│   └── src/
│       ├── app/
│       │   ├── layout.tsx            # ルートレイアウト
│       │   └── page.tsx              # チャット画面
│       ├── components/
│       │   └── ChatMessage.tsx       # メッセージ表示コンポーネント
│       └── lib/
│           └── api.ts                # バックエンド呼び出しラッパー
├── backend/
│   └── app/
│       ├── main.py                   # FastAPI エントリポイント
│       ├── models.py                 # Pydantic モデル
│       └── services.py               # RAG ロジック（埋め込み/検索/回答生成）
├── .env.example                      # 共通環境変数サンプル
└── README.md
```

---

## 技術スタック

### フロントエンド
- Next.js 15（App Router）
- React + TypeScript
- Tailwind CSS

### バックエンド
- Python 3.11+
- FastAPI + Uvicorn
- Pydantic
- httpx（Upstash Vector REST 呼び出し）
- OpenAI Python SDK

### 外部サービス
- OpenAI API
  - Embeddings（例: `text-embedding-3-small`）
  - Chat Completion（例: `gpt-4o-mini`）
- Upstash Vector（Dense ベクトル検索）

---

## API 仕様（MVP）

### `POST /api/v1/chat`
ユーザーの最新メッセージと履歴を受け取り、RAG で生成した回答を返します。

**Request body**
```json
{
  "message": "水タイプで序盤に強いカードを教えて",
  "history": [
    { "role": "user", "content": "さっきのおすすめ、もう一度教えて" },
    { "role": "assistant", "content": "～前回の回答～" }
  ]
}
```

**Response body**
```json
{
  "answer": "水タイプで序盤に使いやすいカードは〇〇です。理由は…",
  "meta": {
    "used_context_count": 3,
    "matched_titles": ["ストームブラスト"]
  }
}
```

エラー時は FastAPI の `HTTPException` により JSON 形式で 4xx / 5xx ステータスを返します。

### 効果テキスト検索（namespace 指定）

- 入力文のどこかに `effect_数字`（例: `effect_3 相手の場のフォロワー…`）というトークンを含めると、Upstash Vector の同名 namespace（`effect_3`）に限定して検索します。
- 質問文を `効果 ...`（例: `効果 相手リーダーにダメージ`）のように始めると、`effect_1` ～ `effect_n` に分割された効果テキスト namespace すべてを横断検索します。必要に応じて `EFFECT_NAMESPACE_MAX` もしくは `EFFECT_NAMESPACE_LIST` で対象を拡張できます。
- 一致したドキュメントの `metadata.title` を抽出し、回答テキスト冒頭に「候補タイトル: ...」として表示します。またレスポンスの `meta.matched_titles` でも取得できます。
- `effect_数字` を含めない通常の質問は、従来通りデフォルト namespace（未指定）で検索します。

---

## 環境変数

ルートに `.env` を作成し、`.env.example` を参考に設定してください。

```env
OPENAI_API_KEY=your_openai_api_key
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
OPENAI_CHAT_MODEL=gpt-4o-mini
UPSTASH_VECTOR_URL=your_upstash_vector_rest_url
UPSTASH_VECTOR_TOKEN=your_upstash_vector_rest_token
NEXT_PUBLIC_API_URL=http://localhost:8000
USE_FAKE_RAG=false
# OPTION:EFFECT_NAMESPACE_MAX=5
# OPTION:EFFECT_NAMESPACE_LIST=effect_1,effect_2,effect_3
# OPTION:EFFECT_NAMESPACE_DIRECTIVE=効果
```

> ⚠️ 本番環境ではこのファイルをコミットしないでください。

### 開発用スタブモード

OpenAI / Upstash をまだ用意していない場合は、`.env` に `USE_FAKE_RAG=true` を設定するとローカル専用の疑似 RAG モードになります。外部 API へのリクエストをスキップし、簡易的なダミー回答を返すため、UI や配線の動作確認に便利です（本番では必ず `false` に戻してください）。

---

## セットアップ

### 1. リポジトリ取得
```bash
git clone <this-repo-url> gamechat-ai
cd gamechat-ai
cp .env.example .env
```

### 2. バックエンド
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
- 開発用ドキュメント: `http://localhost:8000/docs`

### 3. フロントエンド
（別ターミナルで）
```bash
cd frontend
npm install
npm run dev
```
- 開発用フロントエンド: `http://localhost:3000`

ブラウザからアクセスしてチャットを送信すると、バックエンド経由で OpenAI + Upstash Vector を呼び出して回答が表示されます。

---

## データについて
- Upstash Vector には、事前にカード攻略テキストを埋め込み済みである想定です。
- 例（`jsonl`）:
  ```jsonl
  {"id": "card-001", "text": "カード名：〇〇。水タイプ。序盤に強い理由は…"}
  {"id": "card-002", "text": "カード名：△△。炎タイプ。終盤で強力なフィニッシャー…"}
  ```
- MVP では `metadata` フィルタや構造化検索を行わず、全文テキストに対する単純な類似度検索のみを実行します。

---

## 制限事項（MVP）
- 検索は意味的な類似度に基づく単純な top-k のみ
- HP/タイプ/ダメージなどの数値条件フィルタに非対応
- 挨拶検出や検索スキップなどの高度な最適化は未実装
- 認証・ユーザー管理・履歴永続化なし（ブラウザメモリ内のみ）
