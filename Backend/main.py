from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
from google import genai
from dotenv import load_dotenv
import os
import shutil
import math

# Load .env file
load_dotenv()

app = FastAPI()

# Gemini setup
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-2")

client = genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None

# Allow React frontend to talk to this backend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Temporary storage for one uploaded PDF
document_text = ""
uploaded_filename = ""

# RAG storage
document_chunks = []


class AskRequest(BaseModel):
    question: str


@app.get("/")
def home():
    return {
        "message": "Document Assistant AI backend is running with Gemini RAG"
    }


def chunk_text(text: str, chunk_size: int = 2500, overlap: int = 300):
    """
    Splits long document text into smaller overlapping chunks.

    Example:
    chunk 1: chars 0 - 2500
    chunk 2: chars 2200 - 4700
    chunk 3: chars 4400 - 6900

    The overlap helps avoid losing meaning between chunk boundaries.
    """
    chunks = []

    start = 0
    chunk_number = 1

    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end].strip()

        if chunk:
            chunks.append({
                "chunk_number": chunk_number,
                "text": chunk,
                "embedding": None
            })

        chunk_number += 1
        start += chunk_size - overlap

    return chunks


def prepare_document_for_embedding(content: str, title: str = "uploaded pdf"):
    """
    Gemini embedding 2 recommends using a structured format for retrieval documents.
    """
    return f"title: {title} | text: {content}"


def prepare_query_for_embedding(query: str):
    """
    Gemini embedding 2 recommends using a task prefix for retrieval/search queries.
    """
    return f"task: question answering | query: {query}"


def get_embedding(text: str):
    """
    Converts text into a numerical vector using Gemini embeddings.
    """
    result = client.models.embed_content(
        model=EMBEDDING_MODEL,
        contents=text
    )

    return result.embeddings[0].values


def cosine_similarity(vector_a, vector_b):
    """
    Measures how similar two embedding vectors are.

    Higher score = more similar.
    """
    dot_product = sum(a * b for a, b in zip(vector_a, vector_b))

    magnitude_a = math.sqrt(sum(a * a for a in vector_a))
    magnitude_b = math.sqrt(sum(b * b for b in vector_b))

    if magnitude_a == 0 or magnitude_b == 0:
        return 0

    return dot_product / (magnitude_a * magnitude_b)


def build_rag_index(chunks):
    """
    Creates embeddings for all document chunks.
    This is the indexing step.
    """
    for chunk in chunks:
        embedding_input = prepare_document_for_embedding(
            content=chunk["text"],
            title=uploaded_filename
        )

        chunk["embedding"] = get_embedding(embedding_input)

    return chunks


def retrieve_relevant_chunks(question: str, top_k: int = 4):
    """
    Finds the most relevant document chunks for the user's question.
    """
    query_input = prepare_query_for_embedding(question)
    question_embedding = get_embedding(query_input)

    scored_chunks = []

    for chunk in document_chunks:
        score = cosine_similarity(question_embedding, chunk["embedding"])

        scored_chunks.append({
            "chunk_number": chunk["chunk_number"],
            "text": chunk["text"],
            "score": score
        })

    scored_chunks.sort(key=lambda item: item["score"], reverse=True)

    return scored_chunks[:top_k]


@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    global document_text, uploaded_filename, document_chunks

    if not file.filename.lower().endswith(".pdf"):
        return {
            "error": "Only PDF files are allowed."
        }

    if not GEMINI_API_KEY or client is None:
        return {
            "error": "GEMINI_API_KEY is missing. Add it to your .env file."
        }

    file_path = os.path.join(UPLOAD_FOLDER, file.filename)

    # Save uploaded PDF
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Extract text from PDF
    reader = PdfReader(file_path)
    extracted_text = ""

    for page_number, page in enumerate(reader.pages, start=1):
        page_text = page.extract_text()

        if page_text:
            extracted_text += f"\n--- Page {page_number} ---\n"
            extracted_text += page_text + "\n"

    document_text = extracted_text
    uploaded_filename = file.filename

    print("Uploaded filename:", uploaded_filename)
    print("Extracted characters:", len(document_text))
    print("Text preview:", document_text[:500])

    if not document_text.strip():
        document_chunks = []

        return {
            "filename": file.filename,
            "message": "PDF uploaded, but no readable text was found. This may be a scanned PDF.",
            "total_characters": 0,
            "total_chunks": 0,
            "text_preview": ""
        }

    # RAG step 1: split document into chunks
    chunks = chunk_text(document_text)

    # RAG step 2: create embeddings for every chunk
    document_chunks = build_rag_index(chunks)

    return {
        "filename": file.filename,
        "message": "PDF uploaded, text extracted, chunks created, and RAG index built successfully.",
        "total_characters": len(document_text),
        "total_chunks": len(document_chunks),
        "text_preview": document_text[:1000]
    }


@app.post("/ask")
async def ask_question(request: AskRequest):
    global document_text, uploaded_filename, document_chunks

    if not document_text.strip():
        return {
            "answer": "No readable PDF text found. Please upload a text-based PDF first."
        }

    if not document_chunks:
        return {
            "answer": "No RAG chunks found. Please upload the PDF again."
        }

    if not GEMINI_API_KEY or client is None:
        return {
            "answer": "GEMINI_API_KEY is missing. Add it to your .env file."
        }

    try:
        # RAG step 3: retrieve only the most relevant chunks
        relevant_chunks = retrieve_relevant_chunks(
            question=request.question,
            top_k=4
        )

        context_text = ""

        for chunk in relevant_chunks:
            context_text += f"\n--- Chunk {chunk['chunk_number']} | Score: {chunk['score']:.4f} ---\n"
            context_text += chunk["text"] + "\n"

        prompt = f"""
You are a helpful document assistant.

Your job:
- Answer the user's question using ONLY the retrieved document chunks.
- If the answer is not present in the chunks, say:
  "I could not find this information in the uploaded document."
- Keep the answer clear and beginner-friendly.
- If useful, answer in bullet points.
- Do not make up information outside the document.

Uploaded file name:
{uploaded_filename}

Retrieved document chunks:
{context_text}

User question:
{request.question}
"""

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        return {
            "question": request.question,
            "answer": response.text,
            "filename": uploaded_filename,
            "retrieved_chunks": [
                {
                    "chunk_number": chunk["chunk_number"],
                    "score": round(chunk["score"], 4)
                }
                for chunk in relevant_chunks
            ]
        }

    except Exception as e:
        return {
            "answer": "Something went wrong while running RAG with Gemini.",
            "error": str(e)
        }


@app.get("/document-status")
def document_status():
    global document_text, uploaded_filename, document_chunks

    return {
        "has_document": bool(document_text.strip()),
        "filename": uploaded_filename,
        "total_characters": len(document_text),
        "total_chunks": len(document_chunks)
    }