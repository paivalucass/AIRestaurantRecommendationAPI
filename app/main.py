# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.osm_recommend import OSMRecommender


app = FastAPI(title="Restaurant Recommender GenAI API")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

recommender = OSMRecommender()

@app.get("/", response_class=HTMLResponse)
def home():
    with open("app/static/index.html") as f:
        return f.read()

@app.get("/recommend")
def recommend(query: str, user_lat: float, user_lon: float, radius: float = 100.0,  k: int = 5):
    results = recommender.recommend(query, user_lat, user_lon, radius, k)
    return {"results": results}

