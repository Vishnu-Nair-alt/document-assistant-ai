import { useEffect, useState } from "react";
import "./App.css";

const API_BASE_URL = "http://127.0.0.1:8000";

function App() {
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem("docubot-theme") || "light";
  });
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadedFileName, setUploadedFileName] = useState("");
  const [uploadStatus, setUploadStatus] = useState("");
  const [question, setQuestion] = useState("");
  const [messages, setMessages] = useState([
    {
      sender: "bot",
      text: "Hey! Upload a PDF first, then ask me questions from it.",
    },
  ]);
  const [isUploading, setIsUploading] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const hasDocument = Boolean(uploadedFileName);

  useEffect(() => {
    localStorage.setItem("docubot-theme", theme);
  }, [theme]);

  const handleFileChange = (event) => {
    const file = event.target.files[0];

    if (!file) return;

    if (file.type !== "application/pdf") {
      setUploadStatus("Please select a PDF file only.");
      setSelectedFile(null);
      return;
    }

    setSelectedFile(file);
    setUploadStatus("");
  };

  const handleUpload = async () => {
    if (!selectedFile) {
      setUploadStatus("Choose a PDF first.");
      return;
    }

    setIsUploading(true);
    setUploadStatus("Uploading and extracting text...");

    const formData = new FormData();
    formData.append("file", selectedFile);

    try {
      const response = await fetch(`${API_BASE_URL}/upload-pdf`, {
        method: "POST",
        body: formData,
      });

      const data = await response.json();

      if (data.error) {
        setUploadStatus(data.error);
        return;
      }

      setUploadedFileName(data.filename);
      setUploadStatus(
        `Uploaded: ${data.filename} (${data.total_characters} characters extracted)`
      );

      setMessages((prevMessages) => [
        ...prevMessages,
        {
          sender: "bot",
          text: `PDF uploaded successfully: ${data.filename}. Now ask me something from it.`,
        },
      ]);
    } catch (error) {
      console.error(error);
      setUploadStatus("Upload failed. Make sure the backend is running.");
    } finally {
      setIsUploading(false);
    }
  };

  const handleAskQuestion = async (event) => {
    event.preventDefault();

    const trimmedQuestion = question.trim();

    if (!trimmedQuestion) return;

    const userMessage = {
      sender: "user",
      text: trimmedQuestion,
    };

    setMessages((prevMessages) => [...prevMessages, userMessage]);
    setQuestion("");
    setIsAsking(true);

    try {
      const response = await fetch(`${API_BASE_URL}/ask`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          question: trimmedQuestion,
        }),
      });

      const data = await response.json();

      const botMessage = {
        sender: "bot",
        text: data.answer || "No answer received.",
      };

      setMessages((prevMessages) => [...prevMessages, botMessage]);
    } catch (error) {
      console.error(error);

      const errorMessage = {
        sender: "bot",
        text: "Something went wrong. Check if the backend is running.",
      };

      setMessages((prevMessages) => [...prevMessages, errorMessage]);
    } finally {
      setIsAsking(false);
    }
  };

  return (
    <div className={`app theme-${theme}`}>
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark" aria-hidden="true">
            D
          </div>
          <div>
            <h1>DocuBot</h1>
            <p className="subtitle">Ask questions from your PDF</p>
          </div>
        </div>

        <div className="theme-switch" aria-label="Theme selector">
          <button
            type="button"
            className={theme === "light" ? "active" : ""}
            onClick={() => setTheme("light")}
          >
            Light
          </button>
          <button
            type="button"
            className={theme === "dark" ? "active" : ""}
            onClick={() => setTheme("dark")}
          >
            Dark
          </button>
        </div>

        <section className="upload-card" aria-labelledby="upload-title">
          <div className="section-heading">
            <p className="eyebrow">Workspace</p>
            <h2 id="upload-title">Upload PDF</h2>
          </div>

          <label className="file-drop">
            <span className="file-icon" aria-hidden="true">
              PDF
            </span>
            <span className="file-copy">
              <strong>{selectedFile ? selectedFile.name : "Choose a PDF"}</strong>
              <small>
                {selectedFile
                  ? "Ready to upload"
                  : "Drop in a document to start a chat"}
              </small>
            </span>
            <input
              type="file"
              accept="application/pdf"
              onChange={handleFileChange}
            />
          </label>

          {selectedFile && (
            <p className="file-name">Selected: {selectedFile.name}</p>
          )}

          <button onClick={handleUpload} disabled={isUploading}>
            {isUploading ? "Uploading..." : "Upload PDF"}
          </button>

          {uploadStatus && <p className="upload-status">{uploadStatus}</p>}
        </section>

        <section className="info-card" aria-labelledby="document-title">
          <div className="section-heading">
            <p className="eyebrow">Active file</p>
            <h2 id="document-title">Current Document</h2>
          </div>
          <div className={`document-status ${hasDocument ? "ready" : ""}`}>
            <span aria-hidden="true" />
            <p>{uploadedFileName || "No PDF uploaded yet."}</p>
          </div>
        </section>
      </aside>

      <main className="chat-section">
        <div className="chat-header">
          <div>
            <h2>Document Chat</h2>
            <p>
              {hasDocument
                ? `Ready to answer from ${uploadedFileName}`
                : "Upload a PDF to unlock document-aware answers"}
            </p>
          </div>
          <div className={`status-pill ${hasDocument ? "online" : ""}`}>
            <span aria-hidden="true" />
            {hasDocument ? "Document loaded" : "Waiting for PDF"}
          </div>
        </div>

        <div className="messages">
          {messages.map((message, index) => (
            <div
              key={index}
              className={`message-row ${
                message.sender === "user" ? "user-row" : "bot-row"
              }`}
            >
              <div
                className={`message-bubble ${
                  message.sender === "user" ? "user-bubble" : "bot-bubble"
                }`}
              >
                {message.text}
              </div>
            </div>
          ))}

          {isAsking && (
            <div className="message-row bot-row">
              <div className="message-bubble bot-bubble typing">
                Thinking...
              </div>
            </div>
          )}
        </div>

        <form className="question-form" onSubmit={handleAskQuestion}>
          <input
            type="text"
            placeholder="Ask something from the uploaded PDF..."
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
          />

          <button type="submit" disabled={isAsking}>
            {isAsking ? "Asking..." : "Send"}
          </button>
        </form>
      </main>
    </div>
  );
}

export default App;
