# config.py

DATA_PATH = "data/"
VECTORSTORE_PATH = "vectorstore/faiss_index"
DOCSTORE_PATH = "vectorstore/docstore"
LOG_FILE = "logs/interaction_log.csv"

# Modell-Configuration
EMBEDDING_MODEL = "text-embedding-3-small"
LLM_MODEL = "gpt-4o" #"gpt-4o-mini"

MINIMUM_DWELL_TIME_MODAL = 4  # seconds
MINIMUM_DWELL_TIME_EXPANDER = 1 # second

# RAG-Configuration - Single-scale retrieval 
CHUNK_SIZE = 800  # Characters per chunk (used for both retrieval and generation)
CHUNK_OVERLAP = 50  # Overlap between adjacent chunk
SEARCH_K = 2

# Optional -> Not used
USE_RERANKING = False
USE_MULTI_QUERY = False

LIKERT_LABELS_7 = {
    1: "1 – stimme überhaupt nicht zu",
    2: "2 - stimme nicht zu",
    3: "3 - stimme eher nicht zu",
    4: "4 – neutral",
    5: "5 - stimme eher zu",
    6: "6 - stimme zu",
    7: "7 – stimme voll und ganz zu",
}

LIKERT_LABELS_CONF = {
    1: "1 – Ich bin mir sehr unsicher.",
    2: "2 - Ich bin mir unsicher.",
    3: "3 - Ich bin mir eher unsicher.",
    4: "4 – neutral",
    5: "5 - Ich bin mir eher sicher.",
    6: "6 - Ich bin mir sicher.",
    7: "7 – Ich bin mir sehr sicher.",
}