import pandas as pd

df = pd.read_csv("data/corpus_code_travail.csv")
df["len"] = df["texte"].str.len()

print("Total articles :", len(df))
print("Longueur moyenne :", int(df["len"].mean()))
print("Article le plus long :", df["len"].max())
print()
print("< 500 car   :", (df["len"] < 500).sum())
print("500-1500    :", ((df["len"] >= 500) & (df["len"] < 1500)).sum())
print("> 1500 car  :", (df["len"] >= 1500).sum())