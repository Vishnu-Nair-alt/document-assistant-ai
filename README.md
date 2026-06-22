# PDF Intelligence Assistant

An AI-powered **RAG-based PDF intelligence assistant** that transforms uploaded documents into interactive knowledge sources. Users can upload PDF documents, ask questions, and receive instant context-aware answers using a FastAPI backend, vector-based retrieval, and LLM integration.

## Features

* Upload PDF documents
* Extract and process text from PDFs
* Split documents into smaller chunks for better understanding
* Generate embeddings from document chunks
* Store and retrieve relevant chunks using a vector database
* Ask questions based on uploaded PDF content
* Get AI-generated answers using Retrieval-Augmented Generation
* FastAPI-powered backend
* LLM integration for intelligent document understanding

## Tech Stack

### Backend

* **Python**
* **FastAPI**
* **Uvicorn**
* **Pydantic**

### PDF Processing

* **PyMuPDF / pdfplumber**
  Used to extract readable text from uploaded PDF documents.

### RAG Pipeline

* **Text Chunking**
  Splits large PDF content into smaller, meaningful sections.

* **Embeddings**
  Converts text chunks into numerical vector representations.

* **Vector Store / Vector Database**
  Stores document embeddings and retrieves the most relevant chunks based on the user’s question.

* **Semantic Search**
  Finds the most contextually relevant parts of the document instead of relying only on keyword matching.

### AI / LLM Integration

* **Google Gemini / OpenAI API**
  Used to generate final answers based on the retrieved document context.

### Other Tools

* **python-dotenv** for environment variable management
* **CORS Middleware** for frontend-backend communication
* **Git & GitHub** for version control

## How It Works

1. The user uploads a PDF document.
2. The backend extracts text from the PDF.
3. The extracted text is split into smaller chunks.
4. Each chunk is converted into embeddings.
5. The embeddings are stored in a vector database.
6. When the user asks a question, the system performs semantic search to retrieve the most relevant chunks.
7. The retrieved context is sent to the LLM along with the user’s question.
8. The LLM generates a context-aware answer based on the PDF content.

