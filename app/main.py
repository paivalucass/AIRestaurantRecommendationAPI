# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.recommend import RestaurantRecommender


app = FastAPI(title="Restaurant Recommender GenAI API")
app.mount("/static", StaticFiles(directory="app/static"), name="static")

recommender = RestaurantRecommender()

@app.get("/", response_class=HTMLResponse)
def home():
    with open("app/static/index.html") as f:
        return f.read()

@app.get("/recommend")
def recommend(query: str, user_lat: float, user_lon: float, k: int = 3):
    results = recommender.recommend_restaurants(query, user_lat, user_lon, k)
    return {"results": results}

