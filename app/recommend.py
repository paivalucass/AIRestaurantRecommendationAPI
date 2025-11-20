# app/recommend.py
import json
import faiss
import numpy as np
from math import radians, cos, sin, asin, sqrt
from sentence_transformers import SentenceTransformer

PROCESSED_PATH = "app/data/processed.json"
FAISS_INDEX = faiss.read_index("app/data/faiss.index")


class RestaurantRecommender:
    def __init__(self):
        print("Loading model...")
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

        print("Loading processed dataset...")
        with open(PROCESSED_PATH) as f:
            self.db = json.load(f)

    def recommend_restaurants(self, query, user_lat, user_lon, k=3):        
        # Encode user query
        query_emb = self.model.encode(query, convert_to_numpy=True).astype("float32")

        # Normalize for cosine similarity
        faiss.normalize_L2(query_emb.reshape(1, -1))

        # FAISS search
        distances, indices = FAISS_INDEX.search(query_emb.reshape(1, -1), k)

        results = []
        for i, sim in zip(indices[0], distances[0]):
            r = self.db[i]

            # Get restaurant location (safe)
            lat = float(r.get("Latitude", 999))
            lon = float(r.get("Longitude", 999))

            if lat == 999 or lon == 999:
                distance_km = 9999
            else:
                distance_km = self.__haversine(user_lat, user_lon, lat, lon)

            # Normalize distance: 0–100 km range
            max_dist = 100
            distance_score = max(0, 1 - (distance_km / max_dist))

            # Rating score
            rating = float(r.get("Aggregate rating", 0))
            rating_score = rating / 5.0

            # Weighted final score
            final_score = (
                0.4 * float(sim) +
                0.25 * rating_score +
                0.35 * distance_score
            )

            r_out = r.copy()
            r_out["similarity"] = float(sim)
            r_out["distance_km"] = float(distance_km)
            r_out["rating_score"] = rating_score
            r_out["distance_score"] = distance_score
            r_out["final_score"] = float(final_score)

            results.append(r_out)

        # Final ranking
        results = sorted(results, key=lambda x: x["final_score"], reverse=True)

        return results[:k]
    
    def __haversine(self, lat1, lon1, lat2, lon2):
        R = 6371 
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)

        a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
        c = 2 * asin(sqrt(a))
        return R * c
