import os
import re
from typing import Any

import requests
from dotenv import load_dotenv
from logging_config import get_logger

_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(_PROJECT_DIR, ".env"))
logger = get_logger(__name__)

STACKEXCHANGE_API_URL = "https://api.stackexchange.com/2.3/search/advanced"


def _get_stackexchange_key() -> str | None:
    # Support both explicit and existing key naming from .env
    return os.getenv("STACKEXCHANGE_API_KEY") or os.getenv("stackapps_key")


def _to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_stackexchange_verify() -> bool | str:
    verify_env = os.getenv("STACKEXCHANGE_SSL_VERIFY", "true")
    verify = _to_bool(verify_env)

    ca_bundle = os.getenv("STACKEXCHANGE_CA_BUNDLE", "").strip()
    if ca_bundle:
        if not os.path.exists(ca_bundle):
            logger.warning(
                "STACKEXCHANGE_CA_BUNDLE not found, falling back to STACKEXCHANGE_SSL_VERIFY | path=%s",
                ca_bundle,
            )
            return verify
        return ca_bundle
    return verify


def _normalize_queries(query: str) -> list[str]:
    q = query.lower()
    tokens = re.findall(r"[a-z0-9\-\+]+", q)
    allow = {
        "http",
        "https",
        "503",
        "502",
        "504",
        "500",
        "timeout",
        "latency",
        "database",
        "db",
        "connection",
        "pool",
        "pod",
        "kubernetes",
        "kafka",
        "consumer",
        "cpu",
        "memory",
        "oom",
        "crashloopbackoff",
        "redis",
        "mysql",
        "postgres",
        "nginx",
        "api",
    }
    filtered = [token for token in tokens if token in allow]
    compact = " ".join(dict.fromkeys(filtered))
    queries = [query]
    if compact and compact != query:
        queries.append(compact)
    queries.append("http 503 timeout database connection pool")
    return list(dict.fromkeys(queries))


def _request_search(
    query: str, pagesize: int, verify: bool | str, key: str | None
) -> dict[str, Any]:
    params: dict[str, Any] = {
        "site": "stackoverflow",
        "q": query,
        "sort": "relevance",
        "order": "desc",
        "pagesize": max(1, min(pagesize, 10)),
        "filter": "default",
    }
    if key:
        params["key"] = key
    response = requests.get(
        STACKEXCHANGE_API_URL, params=params, timeout=10, verify=verify
    )
    response.raise_for_status()
    return response.json()


def fetch_stackoverflow_results(query: str, pagesize: int = 3) -> list[dict[str, Any]]:
    logger.info(
        "StackOverflow enrichment request | query_len=%s pagesize=%s",
        len(query),
        pagesize,
    )
    key = _get_stackexchange_key()
    if key:
        logger.info("StackExchange API key configured")
    else:
        logger.info("StackExchange API key not set; using anonymous quota")

    verify = _get_stackexchange_verify()
    if verify is False:
        logger.warning("StackExchange SSL verification is disabled")

    payload: dict[str, Any] = {"items": []}
    query_attempts = _normalize_queries(query)
    for attempt_no, candidate in enumerate(query_attempts, start=1):
        logger.info(
            "StackOverflow query attempt | attempt=%s query=%s",
            attempt_no,
            candidate,
        )
        payload = _request_search(
            query=candidate, pagesize=pagesize, verify=verify, key=key
        )
        if payload.get("items"):
            break

    logger.info(
        "StackOverflow enrichment response | items=%s quota_remaining=%s attempts=%s",
        len(payload.get("items", [])),
        payload.get("quota_remaining", "unknown"),
        len(query_attempts),
    )

    items = payload.get("items", [])
    results: list[dict[str, Any]] = []
    for item in items:
        results.append(
            {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "tags": item.get("tags", []),
                "is_answered": item.get("is_answered", False),
                "score": item.get("score", 0),
            }
        )
    return results
