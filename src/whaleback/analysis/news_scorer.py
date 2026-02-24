"""Hybrid BERT + LLM news sentiment scorer.

Stage 1: BERT local inference (KLUE-RoBERTa) for all articles
Stage 2: LLM escalation (Claude Haiku) for low-confidence results
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# BERT model config
BERT_MODEL_NAME = "FISA-conclave/klue-roberta-news-sentiment"
BERT_LABEL_MAP = {
    "LABEL_0": ("negative", -1.0),
    "LABEL_1": ("neutral", 0.0),
    "LABEL_2": ("positive", 1.0),
    # Some models use text labels
    "negative": ("negative", -1.0),
    "neutral": ("neutral", 0.0),
    "positive": ("positive", 1.0),
}

# Singleton caches
_bert_pipeline = None
_anthropic_client = None
_anthropic_api_key_cached = None


def _get_anthropic_client(api_key: str):
    """Lazy-load Anthropic async client (singleton)."""
    global _anthropic_client, _anthropic_api_key_cached
    if _anthropic_client is not None and _anthropic_api_key_cached == api_key:
        return _anthropic_client
    import anthropic
    _anthropic_client = anthropic.AsyncAnthropic(api_key=api_key, max_retries=5)
    _anthropic_api_key_cached = api_key
    return _anthropic_client


def _get_bert_pipeline():
    """Lazy-load BERT sentiment pipeline (singleton)."""
    global _bert_pipeline
    if _bert_pipeline is not None:
        return _bert_pipeline

    try:
        from transformers import pipeline
        _bert_pipeline = pipeline(
            "text-classification",
            model=BERT_MODEL_NAME,
            top_k=None,  # return all class probabilities
            truncation=True,
            max_length=512,
        )
        logger.info("BERT sentiment model loaded: %s", BERT_MODEL_NAME)
        return _bert_pipeline
    except Exception as e:
        logger.warning("Failed to load BERT model: %s", e)
        return None


def score_article_bert(text: str) -> dict[str, Any] | None:
    """Score a single article using BERT.

    Args:
        text: Article title + description text.

    Returns:
        {sentiment_raw, sentiment_label, sentiment_confidence, scoring_method}
        or None if model unavailable.
    """
    pipe = _get_bert_pipeline()
    if pipe is None:
        return None

    try:
        results = pipe(text[:512])  # truncate input
        if not results:
            return None

        # results is list of list of dicts: [[{label, score}, ...]]
        predictions = results[0] if isinstance(results[0], list) else results

        # Find best prediction
        best = max(predictions, key=lambda x: x["score"])
        label_key = best["label"]
        confidence = float(best["score"])

        label_info = BERT_LABEL_MAP.get(label_key)
        if label_info is None:
            # Try to infer from label text
            label_lower = label_key.lower()
            if "pos" in label_lower:
                label_info = ("positive", 1.0)
            elif "neg" in label_lower:
                label_info = ("negative", -1.0)
            else:
                label_info = ("neutral", 0.0)

        sentiment_label, base_score = label_info

        # Refine score using class probabilities for a continuous [-1, +1] value
        pos_score = 0.0
        neg_score = 0.0
        for pred in predictions:
            pred_label = pred["label"].lower()
            if "pos" in pred_label or pred_label == "label_2":
                pos_score = pred["score"]
            elif "neg" in pred_label or pred_label == "label_0":
                neg_score = pred["score"]

        # Continuous score: positive probability - negative probability
        sentiment_raw = pos_score - neg_score
        sentiment_raw = max(-1.0, min(1.0, sentiment_raw))

        return {
            "sentiment_raw": round(sentiment_raw, 4),
            "sentiment_label": sentiment_label,
            "sentiment_confidence": round(confidence, 3),
            "scoring_method": "bert",
        }

    except Exception as e:
        logger.warning("BERT scoring failed: %s", e)
        return None


def _build_sentiment_prompt(text: str, ticker: str) -> str:
    """Build sentiment analysis prompt for LLM."""
    return f"""주식 종목 {ticker}에 대한 다음 뉴스 기사의 감성을 분석해주세요.

기사: {text[:500]}

다음 형식으로만 응답해주세요:
sentiment: [positive/neutral/negative]
score: [0.0~1.0 사이의 확신도]
reason: [한 줄 이유]"""


def _parse_llm_response(response_text: str) -> dict[str, Any]:
    """Parse structured LLM sentiment response."""
    sentiment_label = "neutral"
    confidence = 0.5
    for line in response_text.split("\n"):
        line = line.strip().lower()
        if line.startswith("sentiment:"):
            val = line.split(":", 1)[1].strip()
            if "positive" in val:
                sentiment_label = "positive"
            elif "negative" in val:
                sentiment_label = "negative"
            else:
                sentiment_label = "neutral"
        elif line.startswith("score:"):
            try:
                confidence = float(line.split(":", 1)[1].strip())
            except ValueError:
                confidence = 0.5

    score_map = {"positive": 1.0, "neutral": 0.0, "negative": -1.0}
    raw_base = score_map.get(sentiment_label, 0.0)
    sentiment_raw = raw_base * confidence

    return {
        "sentiment_raw": round(sentiment_raw, 4),
        "sentiment_label": sentiment_label,
        "sentiment_confidence": round(confidence, 3),
        "scoring_method": "llm",
    }


async def score_article_llm(
    text: str,
    api_key: str,
    ticker: str = "",
) -> dict[str, Any] | None:
    """Score a single article using Claude Haiku (LLM escalation).

    Used when BERT confidence is below threshold.
    """
    if not api_key:
        return None

    try:
        client = _get_anthropic_client(api_key)
        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": _build_sentiment_prompt(text, ticker)}],
        )
        return _parse_llm_response(response.content[0].text.strip())

    except Exception as e:
        logger.warning("LLM scoring failed: %s", e)
        return None


# Minimum articles to use Batch API (below this, concurrent calls are faster)
_BATCH_API_THRESHOLD = 20


async def _score_articles_batch(
    texts: list[str],
    llm_pending: list[tuple[int, int, str]],
    api_key: str,
    poll_interval: float = 10.0,
    max_wait: float = 1800.0,
) -> dict[int, dict[str, Any]]:
    """Score articles using Anthropic Message Batches API (50% cost savings).

    Submits all pending articles as a single batch, polls for completion,
    and streams results back mapped by scored_idx.

    Args:
        texts: All article texts (indexed by text_idx).
        llm_pending: List of (scored_idx, text_idx, ticker) tuples.
        api_key: Anthropic API key.
        poll_interval: Seconds between status polls.
        max_wait: Maximum seconds to wait for batch completion.

    Returns:
        Dict mapping scored_idx -> sentiment result dict.
    """
    import asyncio
    from anthropic.types.message_create_params import MessageCreateParamsNonStreaming
    from anthropic.types.messages.batch_create_params import Request

    client = _get_anthropic_client(api_key)

    # Build batch requests with custom_id mapping
    requests: list[Request] = []
    id_map: dict[str, int] = {}  # custom_id -> scored_idx

    for scored_idx, text_idx, ticker in llm_pending:
        cid = f"s{scored_idx}"
        id_map[cid] = scored_idx
        requests.append(Request(
            custom_id=cid,
            params=MessageCreateParamsNonStreaming(
                model="claude-haiku-4-5-20251001",
                max_tokens=200,
                messages=[{
                    "role": "user",
                    "content": _build_sentiment_prompt(texts[text_idx], ticker),
                }],
            ),
        ))

    # Submit batch
    batch = await client.messages.batches.create(requests=requests)
    logger.info("Batch API submitted: %s (%d requests, 50%% cost)", batch.id, len(requests))

    # Poll until completion
    elapsed = 0.0
    while elapsed < max_wait:
        batch = await client.messages.batches.retrieve(batch.id)
        if batch.processing_status == "ended":
            break
        c = batch.request_counts
        logger.info(
            "Batch %s: processing=%d succeeded=%d errored=%d",
            batch.id, c.processing, c.succeeded, c.errored,
        )
        await asyncio.sleep(poll_interval)
        elapsed += poll_interval
    else:
        logger.warning("Batch %s timed out after %.0fs", batch.id, max_wait)
        return {}

    logger.info(
        "Batch %s ended: succeeded=%d errored=%d canceled=%d expired=%d",
        batch.id,
        batch.request_counts.succeeded,
        batch.request_counts.errored,
        batch.request_counts.canceled,
        batch.request_counts.expired,
    )

    # Stream results — AsyncAnthropic.results() is a coroutine returning async iterator
    results: dict[int, dict[str, Any]] = {}
    result_stream = await client.messages.batches.results(batch.id)

    async for item in result_stream:
        scored_idx = id_map.get(item.custom_id)
        if scored_idx is not None and item.result.type == "succeeded":
            text = item.result.message.content[0].text.strip()
            results[scored_idx] = _parse_llm_response(text)
        elif scored_idx is not None:
            logger.warning("Batch item %s: %s", item.custom_id, item.result.type)

    return results


async def score_articles(
    articles: list[dict[str, Any]],
    confidence_threshold: float = 0.70,
    anthropic_api_key: str = "",
    use_batch_api: bool = False,
    max_llm_escalation: int = 0,
) -> list[dict[str, Any]]:
    """Score all articles using hybrid BERT + LLM pipeline.

    Stage 1: Batch score all articles with BERT (much faster than one-by-one)
    Stage 2: Escalate low-confidence results to LLM

    Args:
        articles: List of article dicts with 'title' and 'description'.
        confidence_threshold: BERT confidence threshold for LLM escalation.
        anthropic_api_key: API key for LLM fallback.

    Returns:
        Articles with sentiment fields added.
    """
    if not articles:
        return []

    # Separate pre-scored articles (e.g. DART rule-based) from those needing scoring
    pre_scored: list[dict[str, Any]] = []
    texts: list[str] = []
    valid_articles: list[dict[str, Any]] = []
    for article in articles:
        if article.get("scoring_method"):
            pre_scored.append(article)
            continue
        text = f"{article.get('title', '')} {article.get('description', '')}".strip()
        if text:
            texts.append(text[:512])
            valid_articles.append(article)

    if not texts:
        return pre_scored

    # Stage 1: Batch BERT scoring
    pipe = _get_bert_pipeline()
    bert_results: list[dict[str, Any] | None] = [None] * len(texts)

    if pipe is not None:
        try:
            batch_output = pipe(texts, batch_size=32)
            for idx, predictions in enumerate(batch_output):
                if not isinstance(predictions, list):
                    predictions = [predictions]

                best = max(predictions, key=lambda x: x["score"])
                label_key = best["label"]
                confidence = float(best["score"])

                label_info = BERT_LABEL_MAP.get(label_key)
                if label_info is None:
                    label_lower = label_key.lower()
                    if "pos" in label_lower:
                        label_info = ("positive", 1.0)
                    elif "neg" in label_lower:
                        label_info = ("negative", -1.0)
                    else:
                        label_info = ("neutral", 0.0)

                sentiment_label, _ = label_info

                # Continuous score from class probabilities
                pos_score = 0.0
                neg_score = 0.0
                for pred in predictions:
                    pred_label = pred["label"].lower()
                    if "pos" in pred_label or pred_label == "label_2":
                        pos_score = pred["score"]
                    elif "neg" in pred_label or pred_label == "label_0":
                        neg_score = pred["score"]

                sentiment_raw = max(-1.0, min(1.0, pos_score - neg_score))

                bert_results[idx] = {
                    "sentiment_raw": round(sentiment_raw, 4),
                    "sentiment_label": sentiment_label,
                    "sentiment_confidence": round(confidence, 3),
                    "scoring_method": "bert",
                }
        except Exception as e:
            logger.warning("Batch BERT scoring failed: %s", e)

    # Stage 2: Apply BERT results, collect low-confidence for LLM batch
    scored: list[dict[str, Any]] = []
    llm_pending: list[tuple[int, int, str]] = []  # (scored_idx, text_idx, ticker)

    for idx, article in enumerate(valid_articles):
        bert_result = bert_results[idx]

        if bert_result and bert_result["sentiment_confidence"] >= confidence_threshold:
            article.update(bert_result)
            scored.append(article)
            continue

        # Mark for LLM escalation
        scored_idx = len(scored)
        scored.append(article)  # placeholder, will be updated with LLM result
        if anthropic_api_key:
            llm_pending.append((scored_idx, idx, article.get("ticker", "")))
        elif bert_result:
            article.update(bert_result)
        else:
            article.update({
                "sentiment_raw": 0.0,
                "sentiment_label": "neutral",
                "sentiment_confidence": 0.0,
                "scoring_method": "fallback",
            })

    # Stage 2: LLM escalation (Batch API for large sets, concurrent for small)
    if llm_pending:
        import asyncio

        # Cap LLM escalation to control cost
        if max_llm_escalation and len(llm_pending) > max_llm_escalation:
            logger.info(
                "LLM escalation capped: %d → %d (cost limit)",
                len(llm_pending), max_llm_escalation,
            )
            # Keep lowest-confidence articles (most benefit from LLM)
            llm_pending.sort(
                key=lambda x: (bert_results[x[1]] or {}).get("sentiment_confidence", 0.0),
            )
            overflow = llm_pending[max_llm_escalation:]
            llm_pending = llm_pending[:max_llm_escalation]
            # Apply BERT results to capped articles
            for scored_idx, text_idx, _ in overflow:
                article = scored[scored_idx]
                br = bert_results[text_idx]
                if br:
                    article.update(br)
                else:
                    article.update({
                        "sentiment_raw": 0.0, "sentiment_label": "neutral",
                        "sentiment_confidence": 0.0, "scoring_method": "fallback",
                    })

        llm_results: dict[int, dict[str, Any]] = {}

        if use_batch_api and len(llm_pending) >= _BATCH_API_THRESHOLD:
            # Use Message Batches API (50% cost savings, higher latency)
            try:
                llm_results = await _score_articles_batch(
                    texts, llm_pending, anthropic_api_key,
                )
                logger.info(
                    "Batch API: %d/%d succeeded", len(llm_results), len(llm_pending),
                )
            except Exception as e:
                logger.warning("Batch API failed, falling back to concurrent: %s", e)

        # Concurrent fallback for remaining items (small batches or batch failures)
        remaining = [p for p in llm_pending if p[0] not in llm_results]
        if remaining:
            sem = asyncio.Semaphore(5)
            logger.info("LLM concurrent escalation: %d articles", len(remaining))

            async def _llm_one(scored_idx: int, text_idx: int, ticker: str):
                async with sem:
                    return scored_idx, await score_article_llm(
                        texts[text_idx], anthropic_api_key, ticker
                    )

            tasks = [_llm_one(si, ti, tk) for si, ti, tk in remaining]
            concurrent_results = await asyncio.gather(*tasks, return_exceptions=True)

            for result in concurrent_results:
                if isinstance(result, Exception):
                    logger.warning("LLM escalation error: %s", result)
                    continue
                scored_idx, llm_result = result
                if llm_result:
                    llm_results[scored_idx] = llm_result

        # Apply all LLM results to articles, fallback to BERT or neutral
        for scored_idx, text_idx, _ in llm_pending:
            article = scored[scored_idx]
            llm_result = llm_results.get(scored_idx)
            if llm_result:
                article.update(llm_result)
            else:
                bert_result = bert_results[text_idx]
                if bert_result:
                    article.update(bert_result)
                else:
                    article.update({
                        "sentiment_raw": 0.0,
                        "sentiment_label": "neutral",
                        "sentiment_confidence": 0.0,
                        "scoring_method": "fallback",
                    })

    return pre_scored + scored
