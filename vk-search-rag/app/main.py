from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from common.config import settings
from common.embedder import embed_query
from common.llm import get_llm_answer
from common.opensearch_client import get_client, hybrid_search
from app.schemas import AskRequest, AskResponse, SearchRequest, SearchResponse

app = FastAPI(title="VK Search & RAG", version="1.0.0")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def index():
    return FileResponse("static/index.html")

_client = None


def client():
    global _client
    if _client is None:
        _client = get_client()
    return _client


@app.get("/health")
def health():
    try:
        info = client().info()
        return {"status": "ok", "opensearch_cluster": info.get("cluster_name")}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"OpenSearch недоступен: {e}")


@app.post("/search", response_model=SearchResponse)
def search(req: SearchRequest):
    query_vector = embed_query(req.query)
    results = hybrid_search(client(), req.query, query_vector, req.top_n)
    return SearchResponse(query=req.query, results=results)


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    query_vector = embed_query(req.query)
    top_chunks = hybrid_search(client(), req.query, query_vector, req.context_docs)
    answer = get_llm_answer(req.query, top_chunks)
    return AskResponse(query=req.query, answer=answer, sources=top_chunks)
