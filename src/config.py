# Noms des modeles, centralises a un seul endroit.
EMBEDDING_MODEL = "paraphrase-multilingual-mpnet-base-v2"
LLM_MODEL = "llama-3.3-70b-versatile"
MODERATION_MODEL = "openai/gpt-oss-safeguard-20b"

# Embeddings
MAX_SEQ_LENGTH = 512        # fenetre forcee du modele (128 par defaut, architecture supporte 512)

# Chemins
CSV_PATH = "data/corpus_code_travail.csv"
CHROMA_PATH = "chroma"
COLLECTION_NAME = "code_du_travail"

# Chunking
CHUNK_MAX_CHARS = 1200      # ~380 tokens, sous la limite de 512 du modele
CHUNK_OVERLAP = 150         # chevauchement entre sous-segments (~12%)

# Retrieval
TOP_K = 5                   # nombre de chunks recuperes par question