from src.config import CHUNK_MAX_CHARS, CHUNK_OVERLAP
import pandas as pd
from src.chunking import construire_chunks

df = pd.read_csv("data/corpus_code_travail.csv")
articles = df.to_dict("records")
ids, textes, metadatas = construire_chunks(articles)

print(f"Total articles : {len(articles)}")
print(f"Total chunks   : {len(ids)}")
print()

# 1. Statistiques de longueur des chunks
longueurs = [len(t) for t in textes]
print("=== Longueurs des chunks ===")
print(f"  Min : {min(longueurs)} car")
print(f"  Max : {max(longueurs)} car")
print(f"  Moy : {sum(longueurs)//len(longueurs)} car")
print()

# 2. Combien d'articles ont ete decoupes en plusieurs chunks ?
multi = [m for m in metadatas if m["nb_segments"] > 1]
articles_decoupes = len(set(m["numero_article"] for m in multi))
print(f"Articles decoupes en plusieurs chunks : {articles_decoupes}")
print(f"Chunks issus d'un decoupage : {len(multi)}")
print()

# 3. Verifier les coupures : un segment non-final doit finir proprement
print("=== Verification des coupures (articles longs) ===")
coupures_brutales = 0
for i, (t, m) in enumerate(zip(textes, metadatas)):
    if m["nb_segments"] > 1 and m["segment"] < m["nb_segments"] - 1:
        # ce n'est pas le dernier segment : comment finit-il ?
        fin = t.rstrip()[-1]
        if fin not in ".;:,)":   # fin acceptable
            coupures_brutales += 1
print(f"  Segments finissant en plein mot/phrase abrupte : {coupures_brutales}")
print()

# 4. Lire 5 chunks courts au hasard (articles entiers)
print("=== 5 chunks COURTS au hasard (articles entiers) ===")
import random
random.seed(1)
courts = [i for i, m in enumerate(metadatas) if m["nb_segments"] == 1]
for i in random.sample(courts, 5):
    print(f"\n[{ids[i]}]")
    print(textes[i][:400])

# 5. Lire un article decoupé en entier (voir les jointures)
print("\n\n=== Un article LONG et ses segments (verifier l'overlap) ===")
longs = [m["numero_article"] for m in metadatas if m["nb_segments"] > 3]
if longs:
    num = longs[0]
    for i, m in enumerate(metadatas):
        if m["numero_article"] == num:
            print(f"\n--- segment {m['segment']+1}/{m['nb_segments']} [{ids[i]}] ---")
            print("DEBUT:", textes[i][:120])
            print("FIN  :", textes[i][-120:])