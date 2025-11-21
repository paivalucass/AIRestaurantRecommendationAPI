# app/osm_recommend.py

import requests
import faiss
import numpy as np
from math import radians, cos, sin, asin, sqrt
from sentence_transformers import SentenceTransformer

# URL for Overpass API. This is the service used to query OpenStreetMap data.
OVERPASS_URL = "http://overpass-api.de/api/interpreter"

# Overpass template query. It looks for several food-related amenities within a radius.
# The template variables (radius, lat, lon) are replaced before sending the request.
OVERPASS_QUERY = """
[out:json][timeout:20];
(
  node["amenity"="restaurant"](around:{radius},{lat},{lon});
  node["amenity"="fast_food"](around:{radius},{lat},{lon});
  node["amenity"="cafe"](around:{radius},{lat},{lon});
  node["amenity"="bar"](around:{radius},{lat},{lon});
  node["amenity"="pub"](around:{radius},{lat},{lon});
);
out center;
"""


class OSMRecommender:
    def __init__(self):
        # Load the embedding model used to convert restaurant descriptions into vectors.
        # This model is small and fast, suitable for CPU inference.
        print("Loading embedding model...")
        self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    def __fetch_osm_restaurants(self, lat, lon, radius=1000):
        """
        Calls the Overpass API and retrieves food-related amenities near a location.
        Returns a list of normalized restaurant dictionaries.
        """
        query = OVERPASS_QUERY.format(radius=radius, lat=lat, lon=lon)

        try:
            # Overpass only accepts POST requests for large queries.
            response = requests.post(url=OVERPASS_URL, data=query, timeout=25)

            # The API should return HTTP 200. Anything else is an error.
            if response.status_code != 200:
                print("Overpass error:", response.status_code, response.text[:200])
                return []

            try:
                data = response.json()
            except Exception:
                # Overpass sometimes responds with XML or HTML when under load.
                print("Overpass returned invalid JSON:")
                print(response.text[:300])
                return []

            # The JSON must contain the "elements" field holding objects.
            if "elements" not in data:
                print("No 'elements' in Overpass response:", data)
                return []

            # Normalize all returned nodes/ways into a consistent representation.
            restaurants = [self.__normalize_osm(r) for r in data["elements"]]
            return [r for r in restaurants if r is not None]

        except requests.exceptions.Timeout:
            print("Overpass API timeout")
            return []

        except Exception as e:
            print("Unexpected Overpass error:", e)
            return []

    def __normalize_osm(self, node):
        """
        Converts raw OSM node/way data into a clean, predictable dictionary.
        Only entries with a name are kept, since the model needs textual identifiers.
        """
        tags = node.get("tags", {})

        if "name" not in tags:
            return None

        return {
            "id": node.get("id"),
            "name": tags.get("name", "Unknown"),
            "cuisine": tags.get("cuisine", "unknown"),
            "opening_hours": tags.get("opening_hours", "unknown"),
            "lat": node.get("lat"),
            "lon": node.get("lon"),
            "city": tags.get("addr:city", "unknown"),
            "street": tags.get("addr:street", "unknown"),
            "neighborhood": tags.get("addr:suburb", "unknown"),
            "number": tags.get("addr:housenumber", "unknown"),
            "amenity": tags.get("amenity", "unknown")
        }

    def __build_description(self, r):
        """
        Builds a natural-language description of a restaurant.
        The description is embedded into a semantic vector using MiniLM.
        """
        return (
            f"{r['name']}. "
            f"Cuisine: {r['cuisine']}. "
            f"Opening hours: {r['opening_hours']}. "
            f"Located at coordinates {r['lat']}, {r['lon']}."
            f"City: {r['city']}."
            f"Street: {r['street']}"
            f"Neighborhood: {r['neighborhood']}"
            f"Amenity: {r['amenity']}"
        )

    def __haversine(self, lat1, lon1, lat2, lon2):
        """
        Computes the distance between two coordinates using the Haversine formula.
        Returns distance in kilometers.
        """
        R = 6371  # Earth radius in km
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)

        a = (
            sin(dlat / 2) ** 2
            + cos(radians(lat1))
            * cos(radians(lat2))
            * sin(dlon / 2) ** 2
        )
        c = 2 * asin(sqrt(a))
        return R * c

    def recommend(self, user_query, user_lat, user_lon, radius=1000, k=20):
        """
        End-to-end pipeline:
        1. Query OSM for nearby restaurants.
        2. Convert each restaurant into an embedding.
        3. Embed the user query.
        4. Compute similarity using FAISS.
        5. Combine similarity and physical distance into a final score.
        6. Return the top-k results.
        """
        restaurants = self.__fetch_osm_restaurants(user_lat, user_lon, radius)
        if not restaurants:
            return []

        # Build text descriptions for embedding.
        descriptions = [self.__build_description(r) for r in restaurants]

        # Encode descriptions into vectors.
        embeddings = self.model.encode(descriptions, convert_to_tensor=False)
        embeddings = np.array(embeddings).astype("float32")

        # Normalize vectors to unit length for dot-product similarity.
        faiss.normalize_L2(embeddings)

        # Create FAISS index for inner-product search.
        index = faiss.IndexFlatIP(embeddings.shape[1])
        index.add(embeddings)

        # Encode the user query.
        query_emb = self.model.encode(user_query, convert_to_tensor=False)
        query_emb = np.array(query_emb).astype("float32")
        faiss.normalize_L2(query_emb.reshape(1, -1))

        # Perform similarity search.
        distances, indices = index.search(query_emb.reshape(1, -1), k)

        ranked = []
        for idx, sim in zip(indices[0], distances[0]):
            r = restaurants[idx]

            # Compute real-world distance from user.
            dist_km = self.__haversine(user_lat, user_lon, r["lat"], r["lon"])

            # Convert radius from meters to kilometers when scoring.
            dist_score = max(0, 1 - dist_km / (radius / 1000))

            # Weighted combination of semantic similarity and physical closeness.
            final_score = (0.6 * float(sim)) + (0.4 * dist_score)

            r_out = r.copy()
            r_out["similarity"] = float(sim)
            r_out["distance_km"] = dist_km
            r_out["final_score"] = final_score

            ranked.append(r_out)

        # Sort by combined score descending.
        ranked.sort(key=lambda x: x["final_score"], reverse=True)

        return ranked[:k]
