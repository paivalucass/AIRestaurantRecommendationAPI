# AI Restaurant Recommendation Chatbot using RAG (Qwen2-1.5B-Instruct) 🍜

## [[Check out this project on Hugging Face 🤗]](https://huggingface.co/spaces/paivalucass/ai-restaurant-recommend)

This project implements an intelligent restaurant recommendation system using OpenStreetMap, sentence-transformer embeddings, FAISS vector search, and an LLM assistant (Qwen2-1.5B-Instruct).


It provides two main features:

1. **Embedding-based restaurant recommendations**

2. **A conversational AI assistant that explains and selects the best restaurants based on the retrieved data.**

The system is built with FastAPI, Sentence Transformers, FAISS, PyTorch, Transformers, and Docker.

## 1. System Architecture

### Pipeline Overview

1. User provides a query + location (lat/lon).

2. API calls Overpass API to fetch real nearby restaurants from OSM.

3. Each restaurant is converted into a dense textual description containing:

   - Name

   - Cuisine

   - Opening hours

   - Coordinates

   - City
 
   - Street

   - Neighborhood

   - Amenity type

4. These descriptions are encoded into embeddings using:
sentence-transformers/all-MiniLM-L6-v2

5. Embeddings are indexed using FAISS (Inner Product search with L2 normalization).

6. User query is embedded and compared to all restaurants (RAG).

7. Results are ranked using a blended score:

    ```
    final_score = 0.6 * semantic_similarity + 0.4 * distance_score
    ```

8. The top-k results are sent to the user.

9. For chat requests:

   - The selected restaurants are fed into an LLM prompt.

   - Qwen2-1.5B-Instruct generates a human-friendly explanation.

## 2. Technologies Used
#### **Core**

   - **FastAPI** — API framework

   - **Uvicorn** — ASGI server

   - **Sentence Transformers** — embedding model

   - **FAISS** — similarity search engine

   - **Transformers (HuggingFace)** — LLM inference

   - **PyTorch** — used by both LLM and embedding model

   - **OSM Overpass API** — live restaurant data

#### **Frontend**

- Vanilla **HTML, CSS, JavaScript**

- Chat-style UI with:

  - User messages

  - AI messages

  - Loading animation

  - Location input + auto-detect

#### **Deployment**

  - **Docker** — fully containerized backend

  - Runs with a single command

## 3. Endpoints

#### **GET /chat**

Returns an AI-generated explanation from the LLM.

The endpoint:

1. Runs the same FAISS recommendation pipeline.

2. Creates a structured chat template.

3. Uses Qwen2-1.5B-Instruct.

4. Returns a natural-language text response recommending the top 4 best restaurant for the user's query.

## 4. Embeddings and Models

### Embedding Model

- **sentence-transformers/all-MiniLM-L6-v2**

- 384-dimensional embeddings

### Similarity Search

- FAISS **IndexFlatIP** with L2 normalized vectors

### LLM Model

- **Qwen/Qwen2-1.5B-Instruct**

- Runs on CPU in this project

- Used only for final natural-language reasoning

## 5. How to Run Locally

### Install dependencies

In a .venv environment, run:
```
pip install -r requirements.txt
```

### Start the server
```
uvicorn app.main:app --reload
```

Then open:
```
http://localhost:7860
```

## 6. Docker Deployment
### Build the Docker image
```
docker build -t restaurant-ai .
```
### Run the container
```
docker run -p 7860:7860 restaurant-ai
```

Your API and frontend will be available at:
```
http://localhost:7860
```

## 7. Project Structure
```
app/
  ├── main.py                 # FastAPI app + LLM chat endpoint
  ├── osm_recommend.py        # OSM + embeddings + FAISS pipeline
  ├── static/
       ├── index.html         # UI
       ├── style.css
       └── script.js
requirements.txt
Dockerfile
README.md
```
