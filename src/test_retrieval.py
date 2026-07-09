from src.vector_db import VectorDB
from src.config import TOP_K

# Jeu d'evaluation : question realiste -> article(s) valide(s)
# Plusieurs articles acceptes quand le sujet s'etale sur plusieurs.
TESTS = [
    ("Quelle est la duree legale du travail hebdomadaire ?", ["L3121-27"]),
    ("Comment sont acquis les conges payes ?", ["L3141-3"]),
    ("Qu'est-ce que le harcelement moral au travail ?", ["L1152-1", "L1152-2"]),
    ("Qu'est-ce que le harcelement sexuel ?", ["L1153-1", "L1153-2"]),
    ("Quelle est la duree de la periode d'essai d'un CDI ?", ["L1221-19", "L1221-20", "L1221-21"]),
    ("Qu'est-ce qu'une discrimination au travail ?", ["L1132-1"]),
    ("Comment fonctionne la rupture conventionnelle ?", ["L1237-11", "L1237-12", "L1237-13"]),
    ("Qu'est-ce qu'un licenciement pour motif economique ?", ["L1233-3", "L1233-2"]),
]


def main():
    db = VectorDB()

    reussis = 0
    for question, attendus in TESTS:
        res = db.retrieve(question, n=TOP_K)
        numeros = [m["numero_article"] for m in res["metadatas"][0]]
        trouve = any(a in numeros for a in attendus)
        if trouve:
            reussis += 1
        statut = "OK  " if trouve else "RATE"
        print(f"[{statut}] {question}")
        print(f"       attendu(s): {attendus}")
        print(f"       top-{TOP_K}: {numeros}")
        print()

    print(f"=== {reussis}/{len(TESTS)} questions trouvent un article valide dans le top-{TOP_K} ===")


if __name__ == "__main__":
    main()