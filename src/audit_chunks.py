import pandas as pd
from collections import Counter
from src.chunking import construire_chunks
from src.config import MAX_SEQ_LENGTH

df = pd.read_csv("data/corpus_code_travail.csv")
articles = df.to_dict("records")
ids, textes, metadatas = construire_chunks(articles)

print(f"Total chunks : {len(ids)}")
print()

# 1. IDs uniques ?
doublons = [k for k, v in Counter(ids).items() if v > 1]
print(f"1. IDs en double : {len(doublons)}")
if doublons[:5]:
    print("   exemples :", doublons[:5])

# 2. Chunks vides ou trop courts ?
vides = [i for i, t in enumerate(textes) if len(t.strip()) < 20]
print(f"2. Chunks quasi-vides (<20 car) : {len(vides)}")

# 3. Chunks trop longs pour le modele ?
#    approximation : 1 token ~ 3.5 car en francais. 512 tokens ~ 1790 car.
seuil_car = int(MAX_SEQ_LENGTH * 3.5)
trop_longs = [i for i, t in enumerate(textes) if len(t) > seuil_car]
print(f"3. Chunks depassant ~{seuil_car} car (risque de troncature) : {len(trop_longs)}")
print(f"   soit {len(trop_longs)/len(textes)*100:.1f}% des chunks")

# 4. Tous les chunks ont-ils un numero d'article en metadata ?
sans_num = [i for i, m in enumerate(metadatas) if not m.get("numero_article")]
print(f"4. Chunks sans numero d'article : {len(sans_num)}")

# 5. Distribution des longueurs
longueurs = [len(t) for t in textes]
print(f"\n5. Longueurs : min={min(longueurs)}, moy={sum(longueurs)//len(longueurs)}, max={max(longueurs)}")
sous_seuil = sum(1 for l in longueurs if l <= seuil_car)
print(f"   Chunks OK (<= {seuil_car} car) : {sous_seuil}/{len(longueurs)} = {sous_seuil/len(longueurs)*100:.1f}%")