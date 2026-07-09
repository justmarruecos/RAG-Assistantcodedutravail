import chromadb
from sentence_transformers import SentenceTransformer
from src.config import EMBEDDING_MODEL, CHROMA_PATH, COLLECTION_NAME, MAX_SEQ_LENGTH
from src.chunking import construire_chunks
import json

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

                    # On recupere la fraicheur du corpus si le fichier existe
                    date_maj_corpus = None
                    try:
                        with open("data/corpus_meta.json", encoding="utf-8") as f:
                            meta_corpus = json.load(f)
                            date_maj_corpus = meta_corpus.get("date_maj_corpus")
                    except FileNotFoundError:
                        pass  # pas bloquant : la base se construit quand meme

                    self.collection = self.client.create_collection(
                        name=COLLECTION_NAME,
                        metadata={
                            "embedding_model": EMBEDDING_MODEL,
                            "hnsw:space": "cosine",
                            "date_maj_corpus": date_maj_corpus or "inconnue",
                        },
                    )
                    self._indexer_par_lots(ids, textes, metadatas)

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

    def rechercher_par_numero(self, numero_article, n=5):
        """Recherche EXACTE par numero d'article via les metadonnees,
        sans passer par la similarite vectorielle. Utile pour les
        questions du type 'Que dit l'article L3121-27 ?', ou la
        recherche semantique echoue car un numero d'article n'a pas de
        sens semantique en soi.

        Retourne le meme format que retrieve() pour rester compatible
        avec generation.py."""
        resultats = self.collection.get(
            where={"numero_article": numero_article},
            include=["documents", "metadatas"],
        )
        docs = resultats["documents"][:n]
        metas = resultats["metadatas"][:n]
        dists = [float(i) for i in range(len(docs))]

        return {
            "ids": [resultats["ids"][:n]],
            "documents": [docs],
            "metadatas": [metas],
            "distances": [dists],
        }
        
    def date_fraicheur(self):
        """Retourne la date de mise a jour officielle du corpus (DILA),
        telle que stockee dans les metadonnees de la collection."""
        return self.collection.metadata.get("date_maj_corpus", "inconnue")

    def avertissement_fraicheur(self, seuil_jours=90):
        """Retourne un message d'avertissement si le corpus commence a
        dater, ou None si la fraicheur est encore raisonnable.
        seuil_jours=90 : au-dela de 3 mois, le droit du travail a pu
        evoluer (lois, ordonnances) sans que la base soit mise a jour."""
        import datetime

        date_str = self.date_fraicheur()
        if date_str == "inconnue":
            return "Date de mise a jour du corpus inconnue : fraicheur non garantie."

        date_maj = datetime.date.fromisoformat(date_str)
        aujourdhui = datetime.date.today()
        age_jours = (aujourdhui - date_maj).days

        if age_jours > seuil_jours:
            return (
                f"Attention : ce corpus date du {date_maj.strftime('%d/%m/%Y')} "
                f"({age_jours} jours). Des evolutions legislatives recentes "
                f"pourraient ne pas etre prises en compte."
            )
        return None

    def ajouter_article(self, article):
            """Ajoute ou met a jour un seul article dans la base existante,
            SANS reindexer l'ensemble du corpus.

            Usage : nouvelle loi votee, ou modification d'un article existant.
            article doit etre un dict avec les memes cles que le corpus CSV :
            {"numero_article": ..., "texte": ..., "section": ..., "source": ...}

            Si l'article existe deja (meme numero_article), ses chunks sont
            REMPLACES (upsert), pas dupliques : utile pour une loi amendee.
            """
            ids, textes, metadatas = construire_chunks([article])

            # On supprime d'abord d'anciens chunks de cet article s'ils existent,
            # au cas ou le nouveau texte se decoupe en MOINS de chunks que l'ancien
            # (upsert seul ne supprimerait pas un chunk devenu superflu, ex:
            # __2 qui existait avant mais n'existe plus apres modification).
            anciens = self.collection.get(
                where={"numero_article": article["numero_article"]}
            )
            if anciens["ids"]:
                self.collection.delete(ids=anciens["ids"])

            vecteurs = self._encode(textes)
            self.collection.upsert(
                ids=ids,
                documents=textes,
                embeddings=vecteurs,
                metadatas=metadatas,
            )
            return len(ids)