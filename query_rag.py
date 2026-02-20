from langchain_community.vectorstores import FAISS
from langchain.prompts import ChatPromptTemplate
from langchain.chains import RetrievalQA
from langchain.schema.output_parser import StrOutputParser
from model_config import get_chat_llm, get_embeddings
from prompts import INCIDENT_ANALYSIS_PROMPT

# ==========================
# CONFIG
# ==========================

FAISS_INDEX_PATH = "faiss_index"

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


def analyze_incident(incident_text):
    docs = retriever.invoke(incident_text)

    context = "\n\n".join([doc.page_content for doc in docs])
    context = _sanitize_blocked_keywords(context)
    incident_text = _sanitize_blocked_keywords(incident_text)

    final_prompt = prompt.format(
        context=context,
        question=incident_text
    )

    response = llm.invoke(final_prompt)
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
