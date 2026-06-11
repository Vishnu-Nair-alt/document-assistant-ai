from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pypdf import PdfReader
from google import genai
from dotenv import load_dotenv
import os
import shutil

# Load .env file
load_dotenv()

app = FastAPI()

# Gemini setup
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

client = genai.Client(api_key=GEMINI_API_KEY)

# Allow future React frontend to talk to this backend
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


class AskRequest(BaseModel):
    question: str


@app.get("/")
def home():
    return {
        "message": "Document Assistant AI backend is running with Gemini"
    }


@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):
    global document_text, uploaded_filename

    if not file.filename.lower().endswith(".pdf"):
        return {
            "error": "Only PDF files are allowed."
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
        return {
            "filename": file.filename,
            "message": "PDF uploaded, but no readable text was found. This may be a scanned PDF.",
            "total_characters": 0,
            "text_preview": ""
        }

    return {
        "filename": file.filename,
        "message": "PDF uploaded and text extracted successfully",
        "total_characters": len(document_text),
        "text_preview": document_text[:1000]
    }


@app.post("/ask")
async def ask_question(request: AskRequest):
    global document_text, uploaded_filename

    if not document_text.strip():
        return {
            "answer": "No readable PDF text found. Please upload a text-based PDF first."
        }

    if not GEMINI_API_KEY:
        return {
            "answer": "GEMINI_API_KEY is missing. Add it to your .env file."
        }

    # Simple Version 1 limitation:
    # We are not doing RAG yet.
    # So we send only the first part of the document to Gemini.
    max_context_chars = 12000
    limited_document_text = document_text[:max_context_chars]

    prompt = f"""
You are a helpful document assistant.

Your job:
- Answer the user's question using ONLY the uploaded document text.
- If the answer is not present in the document, say:
  "I could not find this information in the uploaded document."
- Keep the answer clear and beginner-friendly.
- If useful, answer in bullet points.

Uploaded file name:
{uploaded_filename}

Document text:
{limited_document_text}

User question:
{request.question}
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt
        )

        return {
            "question": request.question,
            "answer": response.text,
            "filename": uploaded_filename
        }

    except Exception as e:
        return {
            "answer": "Something went wrong while contacting Gemini.",
            "error": str(e)
        }


@app.get("/document-status")
def document_status():
    global document_text, uploaded_filename

    return {
        "has_document": bool(document_text.strip()),
        "filename": uploaded_filename,
        "total_characters": len(document_text)
    }