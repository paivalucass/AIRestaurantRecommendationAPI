# app/main.py

from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.osm_recommend import OSMRecommender
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Name of the local Llama model used for generating natural language responses.
MODEL_NAME = "Qwen/Qwen2-1.5B-Instruct"

# Create the FastAPI application.
app = FastAPI(title="Restaurant Recommender GenAI API")

# Expose the "static" directory so the frontend files can be served.
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Load tokenizer for the Llama model.
# The pad token is set to eos to avoid warnings and ensure consistent encoding.
tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
tokenizer.pad_token = tokenizer.eos_token

# Load the Llama model itself.
# The pad token id must match the tokenizer so generation works correctly.
model = AutoModelForCausalLM.from_pretrained(MODEL_NAME)
model.config.pad_token_id = tokenizer.eos_token_id

# Force model to run on CPU. 
# This avoids GPU memory issues and keeps the service stable on machines without a large GPU.
device = "cpu"
model.eval()

# Instantiate the OSM-based restaurant recommender.
recommender = OSMRecommender()


# Serve the index HTML page for the frontend.
@app.get("/", response_class=HTMLResponse)
def home():
    with open("app/static/index.html") as f:
        return f.read()


# Basic recommendation endpoint that only returns ranked restaurants.
@app.get("/recommend")
def recommend(query: str, user_lat: float, user_lon: float, radius: float = 100.0, k: int = 5):
    results = recommender.recommend(query, user_lat, user_lon, radius, k)
    return {"results": results}


# Chat endpoint that sends recommendations through the Llama model.
@app.get("/chat")
def recommend_llm(query: str, user_lat: float, user_lon: float, radius: float = 100.0, k: int = 20):

    results = recommender.recommend(query, user_lat, user_lon, radius, k)
    if not results:
        return {"response": "Sorry, I couldn't find any restaurants nearby."}

    # Build list of restaurants
    restaurant_list = "\n".join([
        f"- {r['name']} ({r['cuisine']}), {r['distance_km']:.1f} km"
        for r in results
    ])

    # Qwen-style structured chat prompt
    prompt = f"""
        <|im_start|>system
        You are a restaurant recommendation assistant.
        Rules:
        - Do not use Markdown.
        - Do not invent information.
        - Use simple natural language.
        - Only use the details given to you.
        - Do not create details that are not given to you.
        <|im_end|>

        <|im_start|>user
        I want food like: '{query}'.

        Here are nearby restaurants:
        {restaurant_list}

        Select the best 3 options and explain why each was chosen.
        Do not add details that are not included above.
        <|im_end|>

        <|im_start|>assistant
        """

    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    outputs = model.generate(
        **inputs,
        max_new_tokens=350,
        temperature=0.3,
        do_sample=True
    )

    response_text = tokenizer.decode(outputs[0], skip_special_tokens=False)

    # Extract only the final assistant response
    if "<|im_start|>assistant" in response_text:
        response_text = response_text.split("<|im_start|>assistant")[-1].strip()

    if "<|im_end|>" in response_text:
        response_text = response_text.split("<|im_end|>")[0].strip()

    return {"response": response_text}
