"""
Verifie que l'ajout incremental fonctionne : un nouvel article ajoute
via ajouter_article() doit etre immediatement retrouvable par recherche,
sans avoir reindexe tout le corpus.

Usage : python -m src.test_ajout_incrementel
"""

from src.vector_db import VectorDB


def main():
    db = VectorDB()

    nouvel_article = {
        "numero_article": "L9999-1",
        "texte": (
            "Le teletravail transfrontalier est autorise sous reserve d'un "
            "accord ecrit entre l'employeur et le salarie, precisant les "
            "modalites de compensation des frais engages."
        ),
        "section": "Test - Article fictif ajoute dynamiquement",
        "source": "Test ajout incremental",
    }

    print("Avant ajout : recherche de l'article fictif...")
    res_avant = db.retrieve("teletravail transfrontalier compensation frais", n=5)
    present_avant = "L9999-1" in [
        m["numero_article"] for m in res_avant["metadatas"][0]
    ]
    print(f"  Trouve avant ajout : {present_avant}")

    print("\nAjout de l'article L9999-1...")
    nb_chunks = db.ajouter_article(nouvel_article)
    print(f"  {nb_chunks} chunk(s) ajoute(s)/mis a jour")

    print("\nApres ajout : recherche de l'article fictif...")
    res_apres = db.retrieve("teletravail transfrontalier compensation frais", n=5)
    numeros_apres = [m["numero_article"] for m in res_apres["metadatas"][0]]
    present_apres = "L9999-1" in numeros_apres
    print(f"  Trouve apres ajout : {present_apres}")
    print(f"  Top-5 : {numeros_apres}")

    assert present_apres, "ECHEC : l'article ajoute n'est pas retrouve."
    print("\n=== SUCCES : ajout incremental fonctionnel, sans reindexation complete ===")


if __name__ == "__main__":
    main()