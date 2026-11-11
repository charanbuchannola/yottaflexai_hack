"""Multilingual sentiment classification, theme assignment, PII detection, and sanitized feature construction."""

from datetime import datetime
import json
import re
from typing import Any

from voc_intel.core.identifiers import IDGenerator
from voc_intel.db.base import FeedbackSourceType, LabelingMethod, SentimentPolarity
from voc_intel.features.generation.templates import THEME_TAXONOMY

# Compiled regexes for PII / customer identity leak detection
PII_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("EMAIL_LEAK", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("PHONE_LEAK", re.compile(r"(?:\+\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b")),
    ("CREDENTIAL_OR_ID_LEAK", re.compile(r"\b(?:SSN-\d{3}-\d{2}-\d{4}|CUST_KEY_\d+|PIN[:=]\d{4,})\b", re.IGNORECASE)),
    ("NAMED_ACCOUNT_LEAK", re.compile(r"\b(?:account\s+holder|customer\s+name)\s*:\s*[A-Z][a-z]+\s+[A-Z][a-z]+\b")),
)

# Compiled regex for test-label leakage in model inputs
TEST_LEAK_TOKEN_RE = re.compile(
    r"\[(?:TEST_GOLD_LABEL|GOLD_LABEL|EVAL_TARGET)\s*[:=]", re.IGNORECASE
)
LEAK_METADATA_KEYS = frozenset(
    {"gold_polarity", "leaked_gold_sentiment", "gold_themes", "ground_truth", "is_eval_holdout", "test_label"}
)

_CONTRAST_SPLIT_RE = re.compile(
    r"\b(?:however|although|on the other hand|sin embargo|aunque|cependant|toutefois|allerdings|jedoch)\b",
    re.IGNORECASE,
)

_NEGATION_PREFIXES = ("not ", "never ", "no ", "zero ", "sin ", "aucun ", "aucune ", "n'est ", "keine ", "nicht ", "kein ")

_POSITIVE_LEXICON: dict[str, tuple[str, ...]] = {
    "en": (
        "rock solid", "zero crashes", "outstanding", "no error 500", "fast", "snappy",
        "instant", "responsive", "effortless", "clean and accurate", "reconciled seamlessly",
        "transparent pricing", "fair value", "straightforward", "improved sharply", "prompt",
        "knowledgeable", "helpful agent", "resolved quickly", "above and beyond", "solved",
        "smooth setup", "easy onboarding", "productively", "clean design", "intuitive",
        "thoughtful", "pleasure to use", "rich exports", "save our ops", "real-time sync",
        "accurate numbers", "passed our full audit", "zero discrepancies", "reliable api",
        "seamless", "cleanly", "passed security review", "meet our enterprise compliance",
        "thank you", "applied a configuration update", "escalated diagnostics", "shared the timeline",
    ),
    "es": (
        "sin caídas", "excelente", "muy rápido", "ágil", "fluido", "mejoró bastante",
        "exacta", "sin cargos extra", "cuadraron correctamente", "precios transparentes",
        "buen valor", "total claridad", "mejoraron notablemente", "agente amable",
        "resolvió rápido", "excelente atención", "sobresaliente", "configuración sencilla",
        "sin fricciones", "diseño limpio", "navegación intuitiva", "cómodo", "ahorran horas",
        "funcionan muy bien", "números exactos", "sin discrepancias", "api estable",
        "impecable", "superaron la revisión", "cubren nuestros requisitos", "gracias",
    ),
    "fr": (
        "parfaitement stable", "aucun plantage", "remarquable", "aucune erreur 500", "très rapide",
        "réactif", "fluide", "quasi instantané", "exacte et claire", "aucune erreur de facture",
        "tarification claire", "bon rapport", "lisibles", "sans mauvaise surprise",
        "nettement accélérés", "conseiller efficace", "compétent", "résolu rapidement",
        "suivi exemplaire", "installation facile", "prise en main rapide", "sans friction",
        "design épuré", "navigation intuitive", "très agréable", "bien structuré",
        "temps précieux", "complets", "données fiables", "aucun écart", "api fiable",
        "fluide et stable", "robustes", "répondent aux exigences", "merci",
    ),
    "de": (
        "absolut stabil", "keine abstürze", "hervorragend", "kein einziges mal eingefroren",
        "schnell", "reaktionsschnell", "spürbar gesunken", "sofort", "vollständig korrekt",
        "ohne doppelbelastung", "problemlos abgleichen", "transparente preisgestaltung",
        "faires preis", "klare tariflimits", "stark verbessert", "hilfsbereiter mitarbeiter",
        "schnell gelöst", "äußerst kompetent", "zuverlässig", "einfaches setup", "mühelos",
        "sehr gut strukturiert", "klares design", "intuitive navigation", "sehr angenehm",
        "übersichtlich", "viel zeit", "präzise daten", "stimmten exakt", "zuverlässige api",
        "reibungslos", "stabil", "erfüllten unsere compliance", "vielen dank",
    ),
}

_NEGATIVE_LEXICON: dict[str, tuple[str, ...]] = {
    "en": (
        "crashed", "error 500", "froze", "unresponsive", "stability drops", "forced our analysts",
        "severe latency", "timeout", "painfully slow", "sluggish", "loading lag", "delayed",
        "double billed", "waiting on a refund", "overcharge", "duplicate charge", "invoice error",
        "mismatch", "surprise fee", "unclear pricing", "hidden fee", "misleading", "waiting days",
        "no reply", "sla breach", "slow support", "unanswered", "ignored ticket", "delayed response",
        "scripted", "failed to resolve", "without verifying", "setup confusing", "steep learning curve",
        "drag out", "lacks clear defaults", "stalls", "cluttered", "hard to find", "confusing interface",
        "buries", "missing feature", "lacks scheduled", "breaks table", "missing in",
        "out of sync", "stale metrics", "stale numbers", "sync lag", "delivery failures",
        "rate limit errors", "broke our", "expired oauth", "dropped nightly", "login loop",
        "overly broad", "compliance concerns", "omit permission", "blocking our security",
        "losing an hour", "right before", "untenable",
    ),
    "es": (
        "se cierra", "error 500", "se cuelga", "bloquea", "demasiado lento", "tiempo de espera",
        "latencia excesiva", "tarde en cargar", "cobro duplicado", "esperando reembolso",
        "cargo extra", "tarifa oculta", "precio poco claro", "nos sorprendió", "sin respuesta",
        "soporte lento", "ticket ignorado", "genéricas", "no resolvieron", "cerraron el caso",
        "configuración confusa", "curva de aprendizaje", "retrasaron", "carecen de guías",
        "recargado", "cuesta encontrar", "poco intuitiva", "falta función", "no permite",
        "se pierden", "desincronizado", "datos desactualizados", "discrepancia", "falla la sincronización",
        "errores de límite", "fallos de webhook", "expira sin renovación", "riesgo de cumplimiento",
        "no detalla",
    ),
    "fr": (
        "planté", "erreur 500", "figé", "inutilisable", "très lent", "dépassent le délai",
        "latence élevée", "pénible", "double prélèvement", "sans remboursement", "surfacturation",
        "erreur de facture", "frais cachés", "tarif flou", "surpris", "manque de clarté",
        "sans réponse", "support lent", "ticket ignoré", "délai contractuel", "superficielles",
        "sans véritable résolution", "clôturé avant", "configuration complexe", "courbe d'apprentissage",
        "freinent", "manque d'instructions", "encombrée", "difficiles à trouver", "manque de cohérence",
        "fonction manquante", "aucun export", "tronque", "désynchronisée", "données obsolètes",
        "écart de chiffres", "pertes de webhook", "limite d'api", "échouent", "erreurs sso",
        "souci de conformité", "n'enregistre pas",
    ),
    "de": (
        "abgestürzt", "fehler 500", "eingefroren", "verloren", "extrem langsam", "timeout",
        "träge ladezeit", "massiv aus", "doppelbelastung", "rückerstattung fehlt", "rechnungsfehler",
        "überhöhte rechnung", "versteckte gebühren", "unklare preise", "ärgerlich", "intransparent",
        "keine antwort", "langsamer support", "verzögerte hilfe", "standardisiert", "lösten die ursache nicht",
        "geschlossen, bevor", "verwirrende einrichtung", "steile lernkurve", "erschweren",
        "kaum verständlich", "unübersichtlich", "versteckt", "zu viele klicks", "fehlende funktion",
        "keinen geplanten", "gehen", "nicht synchron", "veraltete daten", "zahlenabweichung",
        "fehlerhafte datensynchronisierung", "verfälscht", "webhook-ausfälle", "zu enges api-limit",
        "unterbrechen", "stoppen", "sso-anmeldefehler", "gefährden die compliance", "fehlen einträge",
    ),
}

_SARCASM_MARKERS = (
    "oh fantastic",
    "peak engineering",
    "truly love losing",
    "nothing brightens my day like",
    "so thoughtful of",
    "world-class urgency",
    "super productive morning",
    "gives me plenty of time to brew coffee",
    "sits untouched all week, really reassuring",
    "qué maravilla",
    "un lujo total",
    "qué detalle tan amable",
    "rapidez de otro nivel",
    "un vrai bonheur",
    "quelle belle surprise",
    "quelle réactivité",
    "genau mein humor",
    "perfektes geduldstraining",
    "wie aufmerksam",
    "erstklassiges tempo",
)

_AMBIGUOUS_HEDGE_MARKERS = (
    "hard to tell yet",
    "mixed feelings",
    "not fully sure",
    "todavía es pronto",
    "opinión dividida",
    "difficile de se prononcer",
    "avis partagé",
    "schwer zu sagen",
    "geteilter eindruck",
)

# Precompile theme phrase lists for fast scoring across 70,000+ rows
_COMPILED_THEME_KEYWORDS: list[tuple[str, str, dict[str, tuple[str, ...]]]] = [
    (t.theme_id, t.theme_code, t.keywords_by_lang) for t in THEME_TAXONOMY
]


_NEGATED_NEGATIVE_POSITIVES = (
    "zero unexpected shutdowns or error 500 alerts",
    "no error 500",
    "zero crashes",
    "zero duplicate charges",
    "zero discrepancies",
    "sin caídas",
    "sin cargos extra",
    "sin discrepancias",
    "aucun plantage",
    "aucune erreur 500",
    "aucune erreur de facture",
    "aucun écart de chiffres",
    "keine abstürze",
    "ohne doppelbelastung",
    "ohne abweichungen",
)


def _score_clause(clause_lower: str, lang: str) -> tuple[float, int, int]:
    """Score positive vs negative lexicon matches in a single clause."""
    pos_terms = _POSITIVE_LEXICON.get(lang, _POSITIVE_LEXICON["en"])
    neg_terms = _NEGATIVE_LEXICON.get(lang, _NEGATIVE_LEXICON["en"])

    pos_hits = sum(1 for kw in pos_terms if kw in clause_lower)

    # Mask explicit positive negated-negative idioms before negative lexicon matching
    masked_for_neg = clause_lower
    for phrase in _NEGATED_NEGATIVE_POSITIVES:
        if phrase in masked_for_neg:
            masked_for_neg = masked_for_neg.replace(phrase, " ")
            pos_hits += 1

    neg_hits = sum(1 for kw in neg_terms if kw in masked_for_neg)
    raw = (pos_hits - neg_hits) / max(1, pos_hits + neg_hits)
    return raw, pos_hits, neg_hits


def classify_sentiment(
    text: str,
    language: str,
    rating_signal: float | None = None,
) -> tuple[str, float, float, str]:
    """Deterministically predict SentimentPolarity, score [-1,1], confidence [0,1], and rationale."""
    text_lower = text.lower()
    lang_key = language if language in _POSITIVE_LEXICON else "en"

    # 1. Explicit sarcasm cues or severe rating/text incongruence
    sarcasm_hit = any(marker in text_lower for marker in _SARCASM_MARKERS)
    if sarcasm_hit:
        return (
            SentimentPolarity.NEGATIVE.value,
            -0.84,
            0.89,
            "Sarcastic contrast cue detected with negative operational context",
        )

    # 2. Ambiguous / hedged neutrality cues
    if any(h in text_lower for h in _AMBIGUOUS_HEDGE_MARKERS):
        return (
            SentimentPolarity.NEUTRAL.value,
            0.0,
            0.71,
            "Ambiguous or hedged phrasing detected without decisive polarity",
        )

    # 3. Split on contrast connectors to detect MIXED multi-polarity statements
    clauses = [c.strip() for c in _CONTRAST_SPLIT_RE.split(text_lower) if c.strip()]
    if len(clauses) >= 2:
        clause_scores = [_score_clause(c, lang_key) for c in clauses]
        has_pos = any(p > 0 and s > 0.1 for s, p, _n in clause_scores)
        has_neg = any(n > 0 and s < -0.1 for s, _p, n in clause_scores)
        if has_pos and has_neg:
            avg_s = sum(s for s, _p, _n in clause_scores) / len(clause_scores)
            return (
                SentimentPolarity.MIXED.value,
                round(max(-0.35, min(0.35, avg_s)), 4),
                0.86,
                "Contrasting positive and negative clauses linked by discourse connector",
            )

    # 4. Aggregate lexicon signals across full text
    raw_score, pos_hits, neg_hits = _score_clause(text_lower, lang_key)

    # Fallback check against English terms if multilingual text includes English product terms (e.g. SSO/API)
    if pos_hits == 0 and neg_hits == 0 and lang_key != "en":
        raw_score, pos_hits, neg_hits = _score_clause(text_lower, "en")

    if pos_hits > 0 and neg_hits > 0 and abs(pos_hits - neg_hits) <= 1 and len(clauses) > 1:
        return (
            SentimentPolarity.MIXED.value,
            round(raw_score * 0.3, 4),
            0.76,
            "Balanced positive and negative signals detected across clauses",
        )

    # Blend subtle rating prior only when text is sparse/ambiguous (never override strong negative text)
    if pos_hits == 0 and neg_hits == 0:
        if rating_signal is not None:
            if rating_signal >= 0.75:
                return SentimentPolarity.POSITIVE.value, 0.52, 0.64, "Derived from rating signal with neutral text"
            if rating_signal <= 0.25:
                return SentimentPolarity.NEGATIVE.value, -0.52, 0.64, "Derived from rating signal with neutral text"
        return SentimentPolarity.NEUTRAL.value, 0.0, 0.78, "Informational or neutral statement without polarity cues"

    if raw_score >= 0.25:
        score = round(min(0.96, 0.65 + 0.1 * min(pos_hits, 3)), 4)
        conf = round(min(0.97, 0.76 + 0.05 * pos_hits), 4)
        return (
            SentimentPolarity.POSITIVE.value,
            score,
            conf,
            f"Positive lexicon signal ({pos_hits} positive vs {neg_hits} negative cues)",
        )

    if raw_score <= -0.25:
        score = round(max(-0.96, -0.65 - 0.1 * min(neg_hits, 3)), 4)
        conf = round(min(0.97, 0.76 + 0.05 * neg_hits), 4)
        return (
            SentimentPolarity.NEGATIVE.value,
            score,
            conf,
            f"Negative lexicon signal ({neg_hits} negative vs {pos_hits} positive cues)",
        )

    return (
        SentimentPolarity.NEUTRAL.value,
        round(raw_score * 0.2, 4),
        0.72,
        "Balanced lexical score within neutral threshold",
    )


def classify_themes(text: str, language: str, max_themes: int = 2) -> list[tuple[str, str, float]]:
    """Deterministically assign 1..max_themes governed Themes from text keywords."""
    text_lower = text.lower()
    lang_key = language if language in ("en", "es", "fr", "de") else "en"

    scored: list[tuple[float, str, str]] = []
    for theme_id, theme_code, kw_map in _COMPILED_THEME_KEYWORDS:
        kws = kw_map.get(lang_key, kw_map["en"])
        hits = sum(1 for kw in kws if kw in text_lower)
        if hits == 0 and lang_key != "en":
            hits = sum(1 for kw in kw_map["en"] if kw in text_lower)
        if hits > 0:
            rel = round(min(0.99, 0.68 + 0.1 * min(hits, 3)), 4)
            scored.append((rel + hits * 0.05, theme_id, theme_code))

    if not scored:
        # Conservative fallback to general UI/usability or onboarding when text is vague/hedged
        if "onboarding" in text_lower or "setup" in text_lower or "incorporación" in text_lower:
            return [("THEME-000007", "ONBOARDING_COMPLEXITY", 0.55)]
        return [("THEME-000008", "UI_USABILITY_INTUITIVE", 0.52)]

    scored.sort(key=lambda item: (-item[0], item[1]))
    results: list[tuple[str, str, float]] = []
    for score_val, theme_id, theme_code in scored[:max_themes]:
        results.append((theme_id, theme_code, round(min(0.99, score_val), 4)))
    return results


def scan_pii(text: str) -> list[str]:
    """Return list of leaked customer identity pattern names found in text."""
    findings: list[str] = []
    for pii_name, pattern in PII_PATTERNS:
        if pattern.search(text):
            findings.append(pii_name)
    return findings


def scan_model_input_leakage(row: dict[str, Any]) -> list[str]:
    """Detect whether a ModelInputFeature row leaks TEST partition or gold ground-truth labels."""
    leaks: list[str] = []
    if row.get("split_partition") == "TEST":
        leaks.append("TEST_SPLIT_IN_MODEL_INPUT")
    if TEST_LEAK_TOKEN_RE.search(row.get("text_payload", "")):
        leaks.append("GOLD_TOKEN_IN_TEXT_PAYLOAD")
    try:
        extra = json.loads(row.get("extra_features_json", "{}"))
    except json.JSONDecodeError:
        extra = {}
    for key in LEAK_METADATA_KEYS:
        if key in extra:
            leaks.append(f"LEAKED_KEY:{key}")
    return leaks


def build_model_inputs_and_run_nlp(
    feedback_bundle: dict[str, Any],
    channels: list[dict[str, Any]],
) -> dict[str, list[dict[str, Any]]]:
    """Build sanitized ModelInputFeature rows and run deterministic NLP classification."""
    chan_group_by_id = {c["channel_id"]: c["channel_group"] for c in channels}

    model_inputs: list[dict[str, Any]] = []
    sentiment_labels: list[dict[str, Any]] = []
    theme_assignments: list[dict[str, Any]] = []

    inp_seq = 1
    sent_seq = 1
    asn_seq = 1

    # Unified deterministic traversal order: SurveyResponses -> Reviews -> SupportMessages
    def _process_item(
        source_type: str,
        fk_col: str,
        record_id: str,
        product_id: str | None,
        channel_id: str,
        language: str,
        ts: datetime,
        text: str,
        rating_signal: float | None,
        lifecycle_state: str,
        sender_role: str | None = None,
    ) -> None:
        nonlocal inp_seq, sent_seq, asn_seq

        input_id = IDGenerator.model_input_id(inp_seq)
        inp_seq += 1

        extra_meta: dict[str, Any] = {
            "char_length": len(text),
            "word_count": len(text.split()),
            "channel_group": chan_group_by_id[channel_id],
        }
        if sender_role is not None:
            extra_meta["sender_role"] = sender_role

        model_inputs.append(
            {
                "input_id": input_id,
                "source_type": source_type,
                "response_id": record_id if fk_col == "response_id" else None,
                "review_id": record_id if fk_col == "review_id" else None,
                "message_id": record_id if fk_col == "message_id" else None,
                "product_id": product_id,
                "channel_id": channel_id,
                "language": language,
                "event_timestamp": ts,
                "text_payload": text,
                "rating_signal": rating_signal,
                "split_partition": "INFERENCE",
                "extra_features_json": json.dumps(extra_meta, sort_keys=True),
            }
        )

        polarity, score, conf, rationale = classify_sentiment(text, language, rating_signal)
        sentiment_labels.append(
            {
                "label_id": IDGenerator.sentiment_label_id(sent_seq),
                "source_type": source_type,
                "response_id": record_id if fk_col == "response_id" else None,
                "review_id": record_id if fk_col == "review_id" else None,
                "message_id": record_id if fk_col == "message_id" else None,
                "polarity": polarity,
                "sentiment_score": score,
                "confidence": conf,
                "labeling_method": LabelingMethod.AUTOMATED_NLP.value,
                "rationale": rationale,
                "labeled_at": ts,
                "lifecycle_state": lifecycle_state,
            }
        )
        sent_seq += 1

        max_t = 2 if polarity == SentimentPolarity.MIXED.value else 1
        assigned = classify_themes(text, language, max_themes=max_t)
        for theme_id, theme_code, rel_score in assigned:
            theme_assignments.append(
                {
                    "assignment_id": IDGenerator.theme_assignment_id(asn_seq),
                    "source_type": source_type,
                    "response_id": record_id if fk_col == "response_id" else None,
                    "review_id": record_id if fk_col == "review_id" else None,
                    "message_id": record_id if fk_col == "message_id" else None,
                    "theme_id": theme_id,
                    "raw_theme_code": theme_code,
                    "relevance_score": rel_score,
                    "assignment_method": LabelingMethod.AUTOMATED_NLP.value,
                    "assigned_at": ts,
                }
            )
            asn_seq += 1

    for r in feedback_bundle["survey_responses"]:
        _process_item(
            FeedbackSourceType.SURVEY_RESPONSE.value,
            "response_id",
            r["response_id"],
            r["product_id"],
            r["channel_id"],
            r["language"],
            r["submitted_at"],
            r["response_text"],
            r["normalized_score"],
            r["lifecycle_state"],
        )

    for rev in feedback_bundle["reviews"]:
        _process_item(
            FeedbackSourceType.REVIEW.value,
            "review_id",
            rev["review_id"],
            rev["product_id"],
            rev["channel_id"],
            rev["language"],
            rev["published_at"],
            rev["review_text"],
            round((rev["star_rating"] - 1) / 4.0, 4),
            rev["lifecycle_state"],
        )

    for msg in feedback_bundle["support_messages"]:
        _process_item(
            FeedbackSourceType.SUPPORT_MESSAGE.value,
            "message_id",
            msg["message_id"],
            msg["product_id"],
            msg["channel_id"],
            msg["language"],
            msg["sent_at"],
            msg["message_text"],
            None,
            msg["lifecycle_state"],
            sender_role=msg["sender_role"],
        )

    return {
        "model_inputs": model_inputs,
        "sentiment_labels": sentiment_labels,
        "feedback_theme_assignments": theme_assignments,
    }
