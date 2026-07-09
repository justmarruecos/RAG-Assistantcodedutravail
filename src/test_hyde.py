"""
Compare le retrieval standard (question brute) au retrieval avec HyDE
(Hypothetical Document Embedding) : le LLM genere un extrait fictif
d'article qui repondrait a la question, et c'est cet extrait qui est
embedde pour la recherche, plutot que la question elle-meme.

Usage : python -m src.test_hyde
"""

from src.vector_db import VectorDB
from src.test_retrieval import TESTS
from src.generation import generer_hyde


def position_dans_resultats(db, texte_recherche, attendus, n=15):
    """Retourne la position (1-indexee) du premier article attendu trouve,
    ou None si aucun des articles attendus n'apparait dans le top-n."""
    res = db.retrieve(texte_recherche, n=n)
    numeros = [m["numero_article"] for m in res["metadatas"][0]]
    for i, num in enumerate(numeros):
        if num in attendus:
            return i + 1, numeros[:5]
    return None, numeros[:5]


def main():
    db = VectorDB()

    print(f"{'Question':<55} {'Sans HyDE':<12} {'Avec HyDE':<12}")
    print("-" * 80)

    for question, attendus in TESTS:
        pos_brute, _ = position_dans_resultats(db, question, attendus)

        texte_hyde = generer_hyde(question)
        pos_hyde, top5_hyde = position_dans_resultats(db, texte_hyde, attendus)

        val_brute = pos_brute if pos_brute else "absent"
        val_hyde = pos_hyde if pos_hyde else "absent"

        print(f"{question:<55} {str(val_brute):<12} {str(val_hyde):<12}")

    print()
    print("Rappel : le texte HyDE est genere par LLM et peut contenir des")
    print("erreurs factuelles (numeros d'articles inventes, etc.). Il n'est")
    print("jamais montre a l'utilisateur, seulement utilise pour la recherche.")


if __name__ == "__main__":
    main()