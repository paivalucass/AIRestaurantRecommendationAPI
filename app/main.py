# app/main.py

from fastapi import FastAPI, APIRouter
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from app.osm_recommend import OSMRecommender
from transformers import AutoTokenizer, AutoModelForCausalLM
import torch

# Name of the local Llama model used for generating natural language responses.
MODEL_NAME = "meta-llama/Llama-3.2-1B-Instruct"

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

    # Retrieve restaurants from Overpass + embedding ranking.
    results = recommender.recommend(query, user_lat, user_lon, radius, k)
    if not results:
        return {"response": "Sorry, I couldn't find any restaurants nearby."}

    # Construct the message format expected by Llama 3's chat template.
    # The system message instructs the model to respond clearly and without Markdown.
    # The user message includes the query and the list of nearby restaurants.
    messages = [
        {
            "role": "system",
            "content": (
                "You are a restaurant recommendation assistant.\n"
                "Rules:\n"
                "- Do not use Markdown.\n"
                "- Use simple, natural phrasing.\n"
                "- Output plain text only."
            )
        },
        {
            "role": "user",
            "content": (
                f"I want food like: '{query}'.\n\n"
                "Here are nearby restaurants:\n" +
                "\n".join([
                    f"- {r['name']} ({r['cuisine']}), {r['distance_km']:.1f} km"
                    for r in results
                ]) +
                "\n\nSelect the best 5 options and explain the reason for each choice. "
                "Do not invent information."
            )
        }
    ]

    # Convert the messages to model-ready tensors using Llama's chat template.
    encoded = tokenizer.apply_chat_template(
        messages,
        return_tensors="pt",
        add_generation_prompt=True,
        padding=True
    )

    input_ids = encoded.to(device)
    attention_mask = (input_ids != tokenizer.pad_token_id).long().to(device)

    # Generate the assistant's response.
    outputs = model.generate(
        input_ids=input_ids,
        attention_mask=attention_mask,
        max_new_tokens=200,
        temperature=0.7,
        do_sample=True,
    )

    # Decode the raw text returned by the model.
    response_text = tokenizer.decode(outputs[0], skip_special_tokens=False)

    # The generated text includes the model's internal chat headers.
    # This extracts only the final assistant message.
    assistant_tag = "<|start_header_id|>assistant<|end_header_id|>"
    start = response_text.rfind(assistant_tag)

    if start != -1:
        # Keep only the section after the assistant header.
        answer = response_text[start + len(assistant_tag):].strip()
    else:
        # Fallback: strip special tokens.
        answer = tokenizer.decode(outputs[0], skip_special_tokens=True)

    # Remove the end-of-turn token if present.
    answer = answer.replace("<|eot_id|>", "").strip()

    return {"response": answer}
