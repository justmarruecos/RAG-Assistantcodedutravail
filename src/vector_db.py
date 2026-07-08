import chromadb
from sentence_transformers import SentenceTransformer
from src.config import EMBEDDING_MODEL, CHROMA_PATH, COLLECTION_NAME, MAX_SEQ_LENGTH


def charger_modele(nom):
    """Charge le modele et force sa fenetre a MAX_SEQ_LENGTH tokens.
    (Beaucoup de modeles sentence-transformers sont brides a 128 par defaut
    alors que leur architecture supporte 512.)"""
    modele = SentenceTransformer(nom)
    modele.max_seq_length = MAX_SEQ_LENGTH
    return modele


class VectorDB:
    def __init__(self, chemin=CHROMA_PATH, ids=None, textes=None, metadatas=None):
        self.client = chromadb.PersistentClient(path=chemin)
        base_existe = COLLECTION_NAME in [c.name for c in self.client.list_collections()]

        if base_existe:
            self.collection = self.client.get_collection(COLLECTION_NAME)
            nom_modele = self.collection.metadata["embedding_model"]
            self.model = charger_modele(nom_modele)

        elif textes is not None:
            self.model = charger_modele(EMBEDDING_MODEL)
            self.collection = self.client.create_collection(
                name=COLLECTION_NAME,
                metadata={"embedding_model": EMBEDDING_MODEL, "hnsw:space": "cosine"},
            )
            self._indexer_par_lots(ids, textes, metadatas)

        else:
            raise ValueError(
                "Aucune base trouvee et aucun chunk fourni : impossible de demarrer."
            )

    def _encode(self, textes):
        return self.model.encode(
            textes, normalize_embeddings=True, show_progress_bar=False
        ).tolist()

    def _indexer_par_lots(self, ids, textes, metadatas, taille_lot=500):
        total = len(ids)
        for debut in range(0, total, taille_lot):
            fin = min(debut + taille_lot, total)
            lot_textes = textes[debut:fin]
            vecteurs = self.model.encode(
                lot_textes, normalize_embeddings=True, show_progress_bar=False
            ).tolist()
            self.collection.add(
                ids=ids[debut:fin],
                documents=lot_textes,
                embeddings=vecteurs,
                metadatas=metadatas[debut:fin],
            )
            print(f"  Indexe {fin}/{total} chunks")

    def retrieve(self, question, n=5):
        vecteur = self._encode([question])
        return self.collection.query(query_embeddings=vecteur, n_results=n)