# app/preprocess.py
import pandas as pd
import json
import torch
from sentence_transformers import SentenceTransformer
from app.utils.text_cleaning import clean_text
import faiss
import numpy as np

DATA_PATH = "app/data/restaurants.csv"
PROCESSED_PATH = "app/data/processed.json"
EMB_PATH = "app/data/embeddings.pt"
    
def remove_replacement_chars(text):
    if not isinstance(text, str):
        return text
    return text.replace("\ufffd", "").replace("�", "")

def preprocess():
    model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    print("Loading CSV...")
    df = pd.read_csv(DATA_PATH, encoding="latin1")

    df.columns = df.columns.str.replace("ï»¿", "").str.strip()

    # Clean replacement characters
    df = df.map(remove_replacement_chars)

    print("Selecting required columns...")
    df = df[[
        "Restaurant ID",
        "Restaurant Name",
        "City",
        "Address",
        "Cuisines",
        "Average Cost for two",
        "Price range",
        "Aggregate rating",
        "Rating text",
        "Votes",
        "Latitude",
        "Longitude"
    ]].dropna()

    # Convert latitude/longitude to float
    df["Latitude"] = pd.to_numeric(df["Latitude"], errors="coerce")
    df["Longitude"] = pd.to_numeric(df["Longitude"], errors="coerce")

    df = df.dropna(subset=["Latitude", "Longitude"])

    print("Cleaning text...")
    df["clean_cuisines"] = df["Cuisines"].apply(clean_text)
    df["clean_rating_text"] = df["Rating text"].apply(clean_text)

    print("Building semantic descriptions...")
    df["description"] = df.apply(lambda row: (
        f"{row['Restaurant Name']} in {row['City']}. "
        f"Cuisines: {row['clean_cuisines']}. "
        f"Average cost for two: {row['Average Cost for two']} ({row['Price range']}/5 price level). "
        f"Rating: {row['Aggregate rating']} ({row['clean_rating_text']}) with {row['Votes']} votes. "
        f"Address: {row['Address']}."
    ), axis=1)

    print("Converting to records...")
    records = df.to_dict(orient="records")

    print("Generating embeddings...")
    corpus = [r["description"] for r in records]
    embeddings = model.encode(corpus, convert_to_tensor=True)
    # Convert to numpy float32
    embeddings_np = embeddings.cpu().numpy().astype("float32")

    # Create FAISS index
    dim = embeddings_np.shape[1]
    index = faiss.IndexFlatIP(dim) # cosine similarity (via inner product with normalized vectors)

    # Normalize embeddings for cosine similarity
    faiss.normalize_L2(embeddings_np)

    # Add to index
    index.add(embeddings_np)

    # Save the FAISS index
    faiss.write_index(index, "app/data/faiss.index")

    torch.save(embeddings, EMB_PATH)

    with open(PROCESSED_PATH, "w") as f:
        json.dump(records, f, indent=4)

    print("Preprocessing completed!")

preprocess()
