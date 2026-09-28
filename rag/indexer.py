import json
import os
import shutil

import chromadb
from sentence_transformers import SentenceTransformer

_base         = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRODUCTS_PATH = os.path.join(_base, "rag/knowledge_base/products.json")
DB_PATH       = os.path.join(_base, "rag/chroma_db")


def build_index():
    print("Loading products...")
    with open(PRODUCTS_PATH, "r") as f:
        products = json.load(f)

    if os.path.exists(DB_PATH):
        shutil.rmtree(DB_PATH)
        print("Wiped existing chroma_db.")

    client     = chromadb.PersistentClient(path=DB_PATH)
    collection = client.get_or_create_collection("products")
    model      = SentenceTransformer("all-MiniLM-L6-v2")

    documents = []
    ids       = []
    metadatas = []

    for p in products:
        text = (
            f"{p['name']} {p['category']} {p['wood']} {p['description']} "
            f"tier {p.get('pricing_tier', 'Luxury')}"
        )
        documents.append(text)
        ids.append(p["id"])
        metadatas.append({
            "name":         p["name"],
            "pricing_tier": p.get("pricing_tier", "Luxury"),
            "category":     p["category"],
        })

    embeddings = model.encode(documents).tolist()
    collection.add(documents=documents, embeddings=embeddings, ids=ids, metadatas=metadatas)
    print(f"Indexed {len(products)} products successfully.")


if __name__ == "__main__":
    build_index()
