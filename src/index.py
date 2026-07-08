import pandas as pd
from src.chunking import construire_chunks
from src.vector_db import VectorDB
from src.config import CSV_PATH


def main():
    print("Chargement du corpus...")
    df = pd.read_csv(CSV_PATH)
    articles = df.to_dict("records")
    print(f"  {len(articles)} articles charges.")

    print("Decoupage en chunks...")
    ids, textes, metadatas = construire_chunks(articles)
    print(f"  {len(ids)} chunks generes.")

    print("Indexation dans ChromaDB (cela peut prendre plusieurs minutes)...")
    VectorDB(ids=ids, textes=textes, metadatas=metadatas)
    print("Base vectorielle construite et persistee.")


if __name__ == "__main__":
    main()