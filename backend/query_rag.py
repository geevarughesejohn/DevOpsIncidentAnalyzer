import json
import os
import re

from langchain_community.vectorstores import FAISS
from langchain.prompts import ChatPromptTemplate
from langchain.chains import RetrievalQA
from langchain.schema.output_parser import StrOutputParser
from logging_config import get_logger
from model_config import get_chat_llm, get_embeddings
from prompts import INCIDENT_ANALYSIS_PROMPT
from stackexchange_tool import fetch_stackoverflow_results

# ==========================
# CONFIG
# ==========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FAISS_INDEX_PATH = os.path.join(BASE_DIR, "faiss_index")
ENABLE_WEB_ENRICHMENT = os.getenv("ENABLE_WEB_ENRICHMENT", "true").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
WEB_RESULTS_K = int(os.getenv("WEB_RESULTS_K", "3"))
logger = get_logger(__name__)

embeddings = get_embeddings()

vectorstore = FAISS.load_local(
    FAISS_INDEX_PATH,
    embeddings,
    allow_dangerous_deserialization=True
)

retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

# ==========================
# LLM (Allowed Model)
# ==========================

llm = get_chat_llm()

# ==========================
# PROMPT
# ==========================

prompt = ChatPromptTemplate.from_template(INCIDENT_ANALYSIS_PROMPT)

# ==========================
# CHAIN
# ==========================

qa_chain = RetrievalQA.from_chain_type(
    llm=llm,
    retriever=retriever,
    chain_type="stuff",
)


def _sanitize_blocked_keywords(text: str) -> str:
    replacements = {
        "symptoms": "indicators",
        "Symptoms": "Indicators",
    }
    for source, target in replacements.items():
        text = text.replace(source, target)
    return text


def _is_meaningful_incident_text(text: str) -> tuple[bool, str]:
    cleaned = text.strip()
    if len(cleaned) < 20:
        return False, "Input is too short."
    words = re.findall(r"\w+", cleaned)
    if len(words) < 4:
        return False, "Input must contain at least 4 words."

    technical_keywords = {
        "error", "errors", "incident", "failure", "failed", "timeout", "latency",
        "cpu", "memory", "oom", "pod", "service", "api", "http", "5xx", "4xx",
        "database", "db", "crash", "restart", "unavailable", "exception", "alert",
        "degraded", "slow", "spike", "connection", "kafka", "queue",
    }
    lowered = cleaned.lower()
    has_keyword = any(keyword in lowered for keyword in technical_keywords)
    has_number = bool(re.search(r"\d", cleaned))
    if not has_keyword and not has_number:
        return False, "Input has insufficient technical signal."
    return True, ""


def _insufficient_input_response(reason: str) -> str:
    payload = {
        "executive_summary": "Insufficient incident details to analyze.",
        "root_cause": "unknown",
        "impacted_services": [],
        "indicators_detected": [],
        "severity": "Low",
        "resolution_steps": [
            "Provide clear incident details (error type, service, timeframe, and observed indicators)."
        ],
        "preventive_actions": [
            "Use a structured incident template with symptoms, logs, metrics, and impact."
        ],
        "confidence_score": 0.0,
        "input_validation_note": reason,
    }
    return json.dumps(payload)


def _build_external_context(incident_text: str, trace_id: str) -> str:
    if not ENABLE_WEB_ENRICHMENT:
        logger.info("Web enrichment disabled | trace_id=%s", trace_id)
        return ""

    try:
        results = fetch_stackoverflow_results(incident_text, pagesize=WEB_RESULTS_K)
    except Exception as exc:
        logger.warning("Web enrichment failed | trace_id=%s error=%s", trace_id, exc)
        return ""

    if not results:
        logger.info("Web enrichment returned no results | trace_id=%s", trace_id)
        return ""

    lines = []
    for idx, item in enumerate(results, start=1):
        lines.append(
            (
                f"[StackOverflow {idx}] "
                f"Title: {item.get('title', '')}; "
                f"Answered: {item.get('is_answered', False)}; "
                f"Score: {item.get('score', 0)}; "
                f"Tags: {', '.join(item.get('tags', []))}; "
                f"Link: {item.get('link', '')}"
            )
        )
    logger.info("Web enrichment results added | trace_id=%s count=%s", trace_id, len(results))
    return "\n".join(lines)


def analyze_incident(incident_text: str, trace_id: str = "script") -> str:
    logger.info("Analyze incident started | trace_id=%s input_len=%s", trace_id, len(incident_text))
    is_valid, reason = _is_meaningful_incident_text(incident_text)
    if not is_valid:
        logger.info("Input rejected by validator | trace_id=%s reason=%s", trace_id, reason)
        return _insufficient_input_response(reason)

    docs = retriever.invoke(incident_text)
    logger.info("Retriever completed | trace_id=%s docs=%s", trace_id, len(docs))

    context = "\n\n".join([doc.page_content for doc in docs])
    external_context = _build_external_context(incident_text, trace_id=trace_id)
    if external_context:
        context = f"{context}\n\nExternal Context:\n{external_context}"
    context = _sanitize_blocked_keywords(context)
    incident_text = _sanitize_blocked_keywords(incident_text)

    final_prompt = prompt.format(
        context=context,
        question=incident_text
    )
    logger.info(
        "Prompt prepared | trace_id=%s context_chars=%s question_chars=%s",
        trace_id,
        len(context),
        len(incident_text),
    )

    response = llm.invoke(final_prompt)
    logger.info("LLM response received | trace_id=%s output_len=%s", trace_id, len(response.content))
    return response.content


# ==========================
# TEST
# ==========================

if __name__ == "__main__":
    sample_incident = """
    Users experiencing HTTP 503 errors.
    Logs show database connection timeout.
    Connection pool usage at 97%.
    Pods restarting repeatedly.
    """

    result = analyze_incident(sample_incident)
    print(result)
