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

# Singleton model cache
_bert_pipeline = None


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


async def score_article_llm(
    text: str,
    api_key: str,
    ticker: str = "",
) -> dict[str, Any] | None:
    """Score a single article using Claude Haiku (LLM escalation).

    Used when BERT confidence is below threshold.

    Args:
        text: Article title + description.
        api_key: Anthropic API key.
        ticker: Stock ticker for context.

    Returns:
        {sentiment_raw, sentiment_label, sentiment_confidence, scoring_method}
    """
    if not api_key:
        return None

    try:
        import anthropic

        client = anthropic.AsyncAnthropic(api_key=api_key)

        prompt = f"""주식 종목 {ticker}에 대한 다음 뉴스 기사의 감성을 분석해주세요.

기사: {text[:1000]}

다음 형식으로만 응답해주세요:
sentiment: [positive/neutral/negative]
score: [0.0~1.0 사이의 확신도]
reason: [한 줄 이유]"""

        response = await client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )

        response_text = response.content[0].text.strip()

        # Parse structured response
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

    except Exception as e:
        logger.warning("LLM scoring failed: %s", e)
        return None


async def score_articles(
    articles: list[dict[str, Any]],
    confidence_threshold: float = 0.70,
    anthropic_api_key: str = "",
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

    # Stage 2: Apply results, escalate low confidence to LLM
    scored: list[dict[str, Any]] = []
    for idx, article in enumerate(valid_articles):
        bert_result = bert_results[idx]

        if bert_result and bert_result["sentiment_confidence"] >= confidence_threshold:
            article.update(bert_result)
            scored.append(article)
            continue

        # LLM escalation for low-confidence results
        if anthropic_api_key:
            llm_result = await score_article_llm(
                texts[idx], anthropic_api_key, article.get("ticker", "")
            )
            if llm_result:
                article.update(llm_result)
                scored.append(article)
                continue

        # Fallback: use BERT result even if low confidence
        if bert_result:
            article.update(bert_result)
            scored.append(article)
        else:
            article.update({
                "sentiment_raw": 0.0,
                "sentiment_label": "neutral",
                "sentiment_confidence": 0.0,
                "scoring_method": "fallback",
            })
            scored.append(article)

    return pre_scored + scored
