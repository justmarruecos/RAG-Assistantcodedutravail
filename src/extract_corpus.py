import json
import pandas as pd


def parcourir(noeud, chemin, articles):
    """Parcourt l'arbre du JSON recursivement.
    - chemin : titres des sections au-dessus de l'article (la hierarchie)
    - articles : liste qui accumule les articles trouves
    """
    ntype = noeud.get("type")
    d = noeud.get("data", {})

    if ntype == "article":
        # On ne garde que les articles en vigueur
        if d.get("etat") == "VIGUEUR":
            texte = (d.get("texte") or "").strip()
            if texte:
                articles.append({
                    "id": d.get("num"),
                    "numero_article": d.get("num"),
                    "texte": texte,
                    "section": " > ".join(chemin),
                    "source": "Code du travail",
                })
        return

    # Sinon c'est une section : on ajoute son titre au chemin et on descend
    titre = d.get("title", "")
    nouveau_chemin = chemin + [titre] if titre else chemin
    for enfant in noeud.get("children", []):
        parcourir(enfant, nouveau_chemin, articles)


def main():
    with open("data/code_travail.json", encoding="utf-8") as f:
        data = json.load(f)

    articles = []
    parcourir(data, [], articles)

    corpus = pd.DataFrame(articles)
    corpus = corpus.drop_duplicates(subset="numero_article").reset_index(drop=True)

    # Retirer les numeros atypiques (annexes, vides) : on garde L, R, D
    corpus = corpus[corpus["numero_article"].str[0].isin(["L", "R", "D"])].reset_index(drop=True)

    sortie = "data/corpus_code_travail.csv"
    corpus.to_csv(sortie, index=False, encoding="utf-8")

    print(f"Corpus ecrit : {sortie}")
    print(f"Nombre d'articles en vigueur : {len(corpus)}")
    print("\nExemple de hierarchie :")
    print(corpus.iloc[0]["numero_article"], "->", corpus.iloc[0]["section"])
    print("\nRepartition L / R / D :")
    print(corpus["numero_article"].str[0].value_counts())


if __name__ == "__main__":
    main()