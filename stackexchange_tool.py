import os
from typing import Any

import requests
from dotenv import load_dotenv
from logging_config import get_logger

load_dotenv(".env")
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


def fetch_stackoverflow_results(query: str, pagesize: int = 3) -> list[dict[str, Any]]:
    logger.info("StackOverflow enrichment request | query_len=%s pagesize=%s", len(query), pagesize)
    params: dict[str, Any] = {
        "site": "stackoverflow",
        "q": query,
        "sort": "relevance",
        "order": "desc",
        "pagesize": max(1, min(pagesize, 10)),
        "filter": "default",
    }
    key = _get_stackexchange_key()
    if key:
        params["key"] = key
    else:
        logger.info("StackExchange API key not set; using anonymous quota")

    verify = _get_stackexchange_verify()
    if verify is False:
        logger.warning("StackExchange SSL verification is disabled")

    response = requests.get(
        STACKEXCHANGE_API_URL, params=params, timeout=10, verify=verify
    )
    response.raise_for_status()
    payload = response.json()
    logger.info(
        "StackOverflow enrichment response | items=%s quota_remaining=%s",
        len(payload.get("items", [])),
        payload.get("quota_remaining", "unknown"),
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
