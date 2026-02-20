import os

import httpx
from dotenv import load_dotenv
from logging_config import get_logger

# Force tiktoken to use a local cache bundle to avoid runtime downloads.
_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
_TIKTOKEN_CACHE_DIR = os.path.join(_PROJECT_DIR, "tiktoken_cache")
_TIKTOKEN_REQUIRED_FILE = "9b5ad71b2ce5302211f9c61530b329a4922fc6a4"

os.environ["TIKTOKEN_CACHE_DIR"] = _TIKTOKEN_CACHE_DIR
if not os.path.exists(os.path.join(_TIKTOKEN_CACHE_DIR, _TIKTOKEN_REQUIRED_FILE)):
    raise FileNotFoundError(
        f"tiktoken cache not found at {_TIKTOKEN_CACHE_DIR}\\{_TIKTOKEN_REQUIRED_FILE}"
    )
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings

load_dotenv(os.path.join(_PROJECT_DIR, ".env"))
logger = get_logger(__name__)

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-01")
AZURE_OPENAI_CHAT_DEPLOYMENT = os.getenv("AZURE_OPENAI_CHAT_DEPLOYMENT")
AZURE_OPENAI_EMBEDDING_DEPLOYMENT = os.getenv("AZURE_OPENAI_EMBEDDING_DEPLOYMENT")
AZURE_OPENAI_CHAT_MODEL = os.getenv(
    "AZURE_OPENAI_CHAT_MODEL", "azure/genailab-maas-gpt-4o"
)
AZURE_OPENAI_EMBEDDING_MODEL = os.getenv(
    "AZURE_OPENAI_EMBEDDING_MODEL", "azure/genailab-maas-text-embedding-3-large"
)
AZURE_OPENAI_CA_BUNDLE = os.getenv("AZURE_OPENAI_CA_BUNDLE")
AZURE_OPENAI_SSL_VERIFY = os.getenv("AZURE_OPENAI_SSL_VERIFY", "false")


def _require_env(var_name: str, value: str | None) -> str:
    if not value:
        raise ValueError(f"Missing required environment variable: {var_name}")
    return value


def _to_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _get_http_client() -> httpx.Client:
    verify: bool | str = _to_bool(AZURE_OPENAI_SSL_VERIFY)

    if AZURE_OPENAI_CA_BUNDLE:
        if not os.path.exists(AZURE_OPENAI_CA_BUNDLE):
            raise FileNotFoundError(
                f"AZURE_OPENAI_CA_BUNDLE does not exist: {AZURE_OPENAI_CA_BUNDLE}"
            )
        # Keep common TLS env vars aligned for other SDK internals.
        os.environ["SSL_CERT_FILE"] = AZURE_OPENAI_CA_BUNDLE
        os.environ["REQUESTS_CA_BUNDLE"] = AZURE_OPENAI_CA_BUNDLE
        verify = AZURE_OPENAI_CA_BUNDLE

    logger.info("Initializing HTTP client | ssl_verify=%s", verify)
    return httpx.Client(verify=verify, timeout=60.0)


_HTTP_CLIENT = _get_http_client()


def get_embeddings() -> AzureOpenAIEmbeddings:
    endpoint = _require_env("AZURE_OPENAI_ENDPOINT", AZURE_OPENAI_ENDPOINT)
    api_key = _require_env("AZURE_OPENAI_API_KEY", AZURE_OPENAI_API_KEY)

    common_kwargs = {
        "azure_endpoint": endpoint,
        "api_key": api_key,
        "api_version": AZURE_OPENAI_API_VERSION,
        "http_client": _HTTP_CLIENT,
    }
    if AZURE_OPENAI_EMBEDDING_DEPLOYMENT:
        logger.info(
            "Using embedding deployment | deployment=%s",
            AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
        )
        return AzureOpenAIEmbeddings(
            azure_deployment=AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            **common_kwargs,
        )
    logger.info("Using embedding model | model=%s", AZURE_OPENAI_EMBEDDING_MODEL)
    return AzureOpenAIEmbeddings(
        model=AZURE_OPENAI_EMBEDDING_MODEL,
        **common_kwargs,
    )


def get_chat_llm() -> AzureChatOpenAI:
    endpoint = _require_env("AZURE_OPENAI_ENDPOINT", AZURE_OPENAI_ENDPOINT)
    api_key = _require_env("AZURE_OPENAI_API_KEY", AZURE_OPENAI_API_KEY)

    common_kwargs = {
        "azure_endpoint": endpoint,
        "api_key": api_key,
        "api_version": AZURE_OPENAI_API_VERSION,
        "temperature": 0.2,
        "http_client": _HTTP_CLIENT,
    }
    if AZURE_OPENAI_CHAT_DEPLOYMENT:
        logger.info(
            "Using chat deployment | deployment=%s",
            AZURE_OPENAI_CHAT_DEPLOYMENT,
        )
        return AzureChatOpenAI(
            azure_deployment=AZURE_OPENAI_CHAT_DEPLOYMENT,
            **common_kwargs,
        )
    if not AZURE_OPENAI_CHAT_MODEL:
        raise ValueError(
            "Missing chat model config. Set AZURE_OPENAI_CHAT_DEPLOYMENT or "
            "AZURE_OPENAI_CHAT_MODEL in .env."
        )
    logger.info("Using chat model | model=%s", AZURE_OPENAI_CHAT_MODEL)
    return AzureChatOpenAI(
        model=AZURE_OPENAI_CHAT_MODEL,
        **common_kwargs,
    )
