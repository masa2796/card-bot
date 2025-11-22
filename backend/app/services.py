from __future__ import annotations
import json
import logging
import math
import os
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple
import httpx
from fastapi import HTTPException
from openai import AsyncOpenAI
from dotenv import load_dotenv
from .models import ChatMessage, ChatResponse, ChatResponseMeta, CardSummary

load_dotenv()

logger = logging.getLogger(__name__)

# Load card master data
CARD_MASTER_DATA: Dict[str, dict] = {}

def _load_card_master_data():
    global CARD_MASTER_DATA
    try:
        # Assuming backend/app/services.py is the location, data is in ../../data/data.json
        base_dir = Path(__file__).resolve().parent.parent.parent
        data_path = base_dir / "data" / "data.json"
        
        if not data_path.exists():
            logger.warning(f"Card master data not found at {data_path}")
            return

        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                if "id" in item:
                    CARD_MASTER_DATA[str(item["id"])] = item
        logger.info(f"Loaded {len(CARD_MASTER_DATA)} cards from master data.")
    except Exception as e:
        logger.error(f"Failed to load card master data: {e}")

_load_card_master_data()

def get_card_master(card_id: str) -> dict | None:
    return CARD_MASTER_DATA.get(str(card_id))


def _load_effect_namespaces() -> Tuple[str, ...]:
    env_value = os.getenv("EFFECT_NAMESPACE_LIST")
    if env_value:
        namespaces = tuple(token.strip().lower() for token in env_value.split(",") if token.strip())
        return namespaces

    max_raw = os.getenv("EFFECT_NAMESPACE_MAX", "5")
    try:
        max_count = int(max_raw)
    except ValueError:
        logger.warning("Invalid EFFECT_NAMESPACE_MAX=%s. Falling back to default range.", max_raw)
        max_count = 5

    if max_count < 1:
        logger.warning("EFFECT_NAMESPACE_MAX resolved to < 1. Multi-namespace search disabled.")
        return tuple()

    return tuple(f"effect_{idx}" for idx in range(1, max_count + 1))

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_EMBEDDING_MODEL = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
UPSTASH_VECTOR_URL = os.getenv("UPSTASH_VECTOR_URL")
UPSTASH_VECTOR_TOKEN = os.getenv("UPSTASH_VECTOR_TOKEN")
CONTEXT_CHAR_LIMIT = int(os.getenv("RAG_CONTEXT_CHAR_LIMIT", "2000"))
TOP_K = int(os.getenv("RAG_TOP_K", "5"))
USE_FAKE_RAG = os.getenv("USE_FAKE_RAG", "false").lower() in {"1", "true", "yes"}
EFFECT_NAMESPACE_PATTERN = re.compile(r"(effect_\d+)", re.IGNORECASE)
EFFECT_DIRECTIVE_KEYWORD = os.getenv("EFFECT_NAMESPACE_DIRECTIVE", "効果").strip() or "効果"
EFFECT_MULTI_NAMESPACE_LABEL = "effect_multi"
EFFECT_NAMESPACE_LIST = _load_effect_namespaces()

SearchDiagnostics = Dict[str, Any]
def extract_effect_namespace(text: str) -> tuple[str, str | None]:
    match = EFFECT_NAMESPACE_PATTERN.search(text)
    if not match:
        return text, None

    namespace = match.group(1).lower()
    cleaned = EFFECT_NAMESPACE_PATTERN.sub("", text, count=1).strip()
    return cleaned or text, namespace


def strip_effect_directive(text: str) -> tuple[str, bool]:
    keyword = EFFECT_DIRECTIVE_KEYWORD
    if not keyword:
        return text, False

    normalized = text.strip()
    lowered = normalized.lower()

    def _trim_remainder(remainder: str) -> str:
        remainder = remainder.lstrip()
        if remainder.startswith(":") or remainder.startswith("："):
            remainder = remainder[1:].lstrip()
        return remainder

    if normalized.startswith(keyword):
        remainder = _trim_remainder(normalized[len(keyword) :])
        return remainder or keyword, True

    directive_prefix = f"namespace {keyword}".lower()
    if lowered.startswith(directive_prefix):
        start_index = len("namespace ") + len(keyword)
        remainder = _trim_remainder(normalized[start_index:])
        return remainder or keyword, True

    return text, False


if OPENAI_API_KEY:
    openai_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
else:
    openai_client = None


def _stage_error(stage: str, message: str, *, status_code: int, exc: Exception | None = None) -> HTTPException:
    detail: dict[str, str] = {"stage": stage, "message": message}
    if exc is not None:
        detail["upstream_error"] = str(exc)
        logger.error("RAG %s failed: %s", stage, exc)
    else:
        logger.error("RAG %s failed: %s", stage, message)
    return HTTPException(status_code=status_code, detail=detail)


async def create_query_embedding(text: str) -> List[float]:
    if not openai_client:
        raise _stage_error(
            "openai_embeddings_config",
            "OpenAI API key is not configured",
            status_code=500,
        )

    try:
        result = await openai_client.embeddings.create(
            model=OPENAI_EMBEDDING_MODEL,
            input=text,
        )
    except Exception as exc:
        raise _stage_error(
            "openai_embeddings",
            "Embedding request failed",
            status_code=502,
            exc=exc,
        ) from exc

    return result.data[0].embedding


async def search_similar_docs(
    embedding: Iterable[float],
    top_k: int | None = None,
    namespace: str | None = None,
) -> Tuple[List[dict], SearchDiagnostics]:
    if not UPSTASH_VECTOR_URL or not UPSTASH_VECTOR_TOKEN:
        raise _stage_error(
            "upstash_config",
            "Upstash Vector credentials are not configured",
            status_code=500,
        )

    base_url = UPSTASH_VECTOR_URL.rstrip("/")
    if namespace:
        query_url = f"{base_url}/query/{namespace}"
    else:
        query_url = f"{base_url}/query"

    vector = list(embedding)

    payload: dict[str, object] = {
        "topK": top_k or TOP_K,
        "vector": vector,
        "includeVectors": False,
        "includeMetadata": True,
    }

    diagnostics: SearchDiagnostics = {
        "namespace": namespace or "default",
        "payload_top_k": payload["topK"],
    }

    headers = {"Authorization": f"Bearer {UPSTASH_VECTOR_TOKEN}"}

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            response = await client.post(query_url, json=payload, headers=headers)
            diagnostics["upstash_status_code"] = response.status_code
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise _stage_error(
                "upstash_query",
                f"Vector search failed (namespace={namespace or 'default'})",
                status_code=502,
                exc=exc,
            ) from exc

    data = response.json()

    matches: list = []
    direct_matches = data.get("matches")
    result_payload = data.get("result")

    if isinstance(direct_matches, list):
        matches = direct_matches
    elif isinstance(result_payload, dict):
        nested_matches = result_payload.get("matches")
        if isinstance(nested_matches, list):
            matches = nested_matches
        else:
            maybe_list = result_payload.get("result")
            if isinstance(maybe_list, list):
                matches = maybe_list
    elif isinstance(result_payload, list):
        matches = result_payload

    if not isinstance(matches, list):
        logger.warning("Upstash response did not contain a matches list: %s", data)
        matches = []

    diagnostics["raw_match_count"] = len(matches)
    docs: List[dict] = []

    def _pick_dict(candidate: object) -> dict | None:
        if isinstance(candidate, dict):
            return candidate
        if isinstance(candidate, (list, tuple)):
            for element in candidate:
                if isinstance(element, dict):
                    return element
        return None

    for raw_item in matches:
        item = _pick_dict(raw_item)
        if not item:
            logger.warning("Upstash match entry ignored due to unexpected format: %s", raw_item)
            continue
        metadata = item.get("metadata") or {}
        text = metadata.get("text") or item.get("text") or item.get("data")
        title = metadata.get("title") or item.get("title")
        card_id = metadata.get("card_id")
        if not text:
            continue
        docs.append({"text": text, "title": title, "card_id": card_id})

    if not docs:
        logger.warning("Upstash returned no usable documents. Raw matches: %s", matches)
        diagnostics["warning"] = "no_usable_docs"

    diagnostics["usable_doc_count"] = len(docs)
    logger.info(
        "Upstash search namespace=%s topK=%s raw=%s usable=%s",
        diagnostics["namespace"],
        diagnostics["payload_top_k"],
        diagnostics["raw_match_count"],
        diagnostics["usable_doc_count"],
    )

    return docs, diagnostics


def _per_namespace_top_k(top_k: int | None, namespace_count: int) -> int:
    effective_top_k = top_k or TOP_K
    if namespace_count <= 0:
        return effective_top_k
    return max(1, math.ceil(effective_top_k / namespace_count))


async def search_effect_namespaces(
    embedding: Iterable[float],
    top_k: int | None = None,
) -> Tuple[List[dict], SearchDiagnostics]:
    namespaces = EFFECT_NAMESPACE_LIST
    diagnostics: SearchDiagnostics = {
        "namespace": EFFECT_MULTI_NAMESPACE_LABEL,
        "searched_effect_namespaces": namespaces,
        "payload_top_k": top_k or TOP_K,
    }

    if not namespaces:
        diagnostics["warning"] = "no_effect_namespaces_configured"
        return [], diagnostics

    per_namespace_k = _per_namespace_top_k(top_k, len(namespaces))
    aggregated_docs: List[dict] = []
    nested: List[SearchDiagnostics] = []
    status_codes: List[int] = []
    total_raw_matches = 0

    for namespace in namespaces:
        docs, diag = await search_similar_docs(embedding, top_k=per_namespace_k, namespace=namespace)
        aggregated_docs.extend(docs)
        total_raw_matches += diag.get("raw_match_count", 0) or 0
        nested.append(
            {
                "namespace": namespace,
                "usable_doc_count": diag.get("usable_doc_count"),
                "raw_match_count": diag.get("raw_match_count"),
            }
        )
        status_code = diag.get("upstash_status_code")
        if status_code is not None:
            status_codes.append(status_code)

    diagnostics["raw_match_count"] = total_raw_matches
    diagnostics["usable_doc_count"] = len(aggregated_docs)
    diagnostics["effect_namespace_results"] = nested
    if status_codes:
        diagnostics["upstash_status_code"] = status_codes[-1]
        diagnostics["upstash_status_codes"] = status_codes

    limit = top_k or TOP_K
    if len(aggregated_docs) > limit:
        aggregated_docs = aggregated_docs[:limit]

    return aggregated_docs, diagnostics


def build_context_text(docs: List[dict]) -> str:
    text_chunks = [doc["text"].strip() for doc in docs if doc.get("text")]
    context = "\n\n".join(chunk for chunk in text_chunks if chunk)
    if CONTEXT_CHAR_LIMIT and len(context) > CONTEXT_CHAR_LIMIT:
        return context[:CONTEXT_CHAR_LIMIT]
    return context


async def generate_answer(
    query: str,
    context: str,
    history: List[ChatMessage] | None,
    titles: List[str] | None,
) -> str:
    if not openai_client:
        raise _stage_error(
            "openai_chat_config",
            "OpenAI API key is not configured",
            status_code=500,
        )

    system_prompt = (
        "あなたはカードゲームの攻略アシスタントです。"
        "与えられた参考情報の範囲で、簡潔に（200文字以内を目安）で回答してください。"
        "参考情報にない内容は無理に断定せず、わからないと伝えてください。"
    )

    messages = [
        {"role": "system", "content": system_prompt},
    ]

    if history:
        for message in history[-5:]:
            messages.append({"role": message.role, "content": message.content})

    supplemental = []
    if titles:
        supplemental.append("候補カードタイトル: " + ", ".join(titles))
    if context:
        supplemental.append(f"参考情報:\n{context}")
    else:
        supplemental.append("参考情報は見つかりませんでした。")

    user_content = "\n\n".join(supplemental) + "\n\n質問: " + query
    messages.append({"role": "user", "content": user_content})

    try:
        completion = await openai_client.chat.completions.create(
            model=OPENAI_CHAT_MODEL,
            messages=messages,
            temperature=0.3,
            max_tokens=400,
        )
    except Exception as exc:
        raise _stage_error(
            "openai_chat",
            "Answer generation failed",
            status_code=502,
            exc=exc,
        ) from exc

    answer_text = completion.choices[0].message.content or ""
    if titles:
        title_line = "候補タイトル: " + ", ".join(titles)
        return f"{title_line}\n\n{answer_text}".strip()
    return answer_text


async def chat(query: str, history: List[ChatMessage] | None) -> ChatResponse:
    if USE_FAKE_RAG:
        return _fake_chat(query, history)

    try:
        cleaned_query, namespace = extract_effect_namespace(query)
        cleaned_query, multi_effect_directive = strip_effect_directive(cleaned_query)
        embedding = await create_query_embedding(cleaned_query)

        docs: List[dict]
        diagnostics: SearchDiagnostics

        if namespace:
            docs, diagnostics = await search_similar_docs(embedding, namespace=namespace)
            if not docs:
                fallback_docs, fallback_diag = await search_similar_docs(embedding, namespace=None)
                fallback_diag["fallback_namespace"] = namespace
                docs = fallback_docs
                diagnostics = fallback_diag
        else:
            if multi_effect_directive:
                docs, diagnostics = await search_effect_namespaces(embedding)
                if not docs:
                    fallback_docs, fallback_diag = await search_similar_docs(embedding, namespace=None)
                    fallback_diag["fallback_namespace"] = EFFECT_MULTI_NAMESPACE_LABEL
                    docs = fallback_docs
                    diagnostics = fallback_diag
            else:
                docs, diagnostics = await search_similar_docs(embedding, namespace=None)

        context_text = build_context_text(docs)
        titles = [doc.get("title") for doc in docs if doc.get("title")]
        
        # Build card summaries
        card_summaries: List[CardSummary] = []
        seen_card_ids = set()
        
        for doc in docs:
            c_id = doc.get("card_id")
            if c_id and c_id not in seen_card_ids:
                master = get_card_master(c_id)
                if master:
                    seen_card_ids.add(c_id)
                    
                    # Collect all effect_N fields
                    effects_list = []
                    for k, v in master.items():
                        if k.startswith("effect_") and v:
                            try:
                                idx = int(k.split("_")[1])
                                effects_list.append((idx, v))
                            except ValueError:
                                pass
                    effects_list.sort(key=lambda x: x[0])
                    sorted_effects = [val for _, val in effects_list]

                    card_summaries.append(CardSummary(
                        card_id=str(c_id),
                        name=master.get("name", "Unknown"),
                        class_=master.get("class", "-"),
                        rarity=master.get("rarity", "-"),
                        cost=master.get("cost", 0),
                        attack=master.get("attack", 0),
                        hp=master.get("hp", 0),
                        effect=master.get("effect_1") or doc.get("text", ""),
                        effects=sorted_effects,
                        keywords=master.get("keywords", []),
                        image_before=master.get("image_before", ""),
                        image_after=master.get("image_after", "")
                    ))

        answer = await generate_answer(query, context_text, history, titles)
        return ChatResponse(
            answer=answer,
            meta=ChatResponseMeta(
                used_context_count=len(docs),
                matched_titles=titles,
                used_namespace=diagnostics.get("namespace"),
                fallback_namespace=diagnostics.get("fallback_namespace"),
                raw_match_count=diagnostics.get("raw_match_count"),
                upstash_status_code=diagnostics.get("upstash_status_code"),
                upstash_error=diagnostics.get("warning"),
                cards=card_summaries,
            ),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise _stage_error(
            "rag_pipeline",
            "Unexpected error while running the RAG pipeline",
            status_code=500,
            exc=exc,
        ) from exc


def _fake_chat(query: str, history: List[ChatMessage] | None) -> ChatResponse:
    """Return a deterministic but helpful-sounding answer without external APIs."""

    canned_tips = [
        "序盤はエナジーを安定供給できるカードを優先すると立ち上がりが安定します。",
        "サーチ手段を1～2枚追加しておくと必要なコンボパーツを素早く集められます。",
        "弱点を突かれないようサブプランのタイプも用意しておくと安心です。",
        "終盤は手札管理が勝負。無駄なカードは早めに消費して選択肢を広げましょう。",
    ]

    history_tail = "\n".join(f"{msg.role}: {msg.content}" for msg in (history or [])[-3:])
    tip = canned_tips[hash(query) % len(canned_tips)]
    answer = (
        "(開発用ダミー回答)\n"
        "質問内容: "
        + query
        + "\n"
        + (f"直近の履歴:\n{history_tail}\n" if history_tail else "")
        + tip
    )
    return ChatResponse(
        answer=answer,
        meta=ChatResponseMeta(
            used_context_count=0,
            matched_titles=[],
            used_namespace="fake_mode",
            fallback_namespace=None,
            raw_match_count=0,
            upstash_status_code=None,
            upstash_error="fake_mode",
        ),
    )
