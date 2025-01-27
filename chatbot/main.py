import os
from fastapi import FastAPI, HTTPException, Request, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.messages import HumanMessage, AIMessage
from pydantic import BaseModel
from typing import List
import openai

app = FastAPI()

# CORS Middleware (optional for frontend compatibility)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Update to specific origins for security
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for chat history
chat_history = []

# Configure OpenAI API Key
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    raise RuntimeError("OpenAI API key is missing. Set the 'OPENAI_API_KEY' environment variable.")

# Update NO_PROXY only if necessary
if "api.openai.com" not in os.getenv("NO_PROXY", ""):
    os.environ["NO_PROXY"] = os.getenv("NO_PROXY", "") + ",api.openai.com"
if "api.openai.com" not in os.getenv("no_proxy", ""):
    os.environ["no_proxy"] = os.getenv("no_proxy", "") + ",api.openai.com"

from langchain_openai import ChatOpenAI

model = ChatOpenAI()

class ChatMessage(BaseModel):
    message: str

class ChatResponse(BaseModel):
    user: str
    bot: str


# Endpoint to upload and process a document
@app.post('/upload_document')
async def upload_document(file: UploadFile = File(...)):
    """Endpoint to upload a document and return its content."""
    if not file.filename.endswith(('.txt', '.pdf', '.docx')):
        raise HTTPException(status_code=400, detail="Unsupported file format. Please upload a .txt, .pdf, or .docx file.")

    try:
        # Read the content of the file
        content = await file.read()

        # Process the content based on the file type
        if file.filename.endswith('.txt'):
            text_content = content.decode('utf-8')
        elif file.filename.endswith('.pdf'):
            import PyPDF2
            from io import BytesIO
            pdf_reader = PyPDF2.PdfReader(BytesIO(content))
            text_content = ''.join([page.extract_text() for page in pdf_reader.pages])
        elif file.filename.endswith('.docx'):
            from docx import Document
            from io import BytesIO
            document = Document(BytesIO(content))
            text_content = '\n'.join([para.text for para in document.paragraphs])
        else:
            raise HTTPException(status_code=400, detail="Unsupported file format.")

        # Save the text content for querying
        global document_content
        document_content = text_content

        return {"message": "Document uploaded successfully.", "content_preview": text_content[:500]}  # Preview first 500 characters
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")


# Define the request model for the query
class QueryDocumentRequest(BaseModel):
    query: str

@app.post('/query_document')
async def query_document(query_request: QueryDocumentRequest):
    """Endpoint to query the uploaded document."""
    global document_content
    if not document_content:
        raise HTTPException(status_code=400, detail="No document uploaded. Please upload a document first.")

    # Extract the query from the request body
    query = query_request.query

    # Integrate with ChatGPT to query the document
    try:
        from langchain_core.messages import HumanMessage
        from langchain_openai import ChatOpenAI
        model = ChatOpenAI()

        response = model.invoke([
            HumanMessage(content=f"Use the following document to answer the question:\n\n{document_content[:4000]}\n\nQuestion: {query}")
        ])

        return {"response": response.content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error querying the document: {str(e)}")


@app.post('/chat', response_model=ChatResponse)
async def chat(chat_message: ChatMessage):
    """Endpoint to handle user input and generate chatbot response."""
    user_input = chat_message.message

    if not user_input:
        raise HTTPException(status_code=400, detail="Message is required.")

    try:
        # Call to ChatGPT model using the latest API
        response: AIMessage = model.invoke([HumanMessage(content=user_input)])
        bot_response = response.content
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error communicating with ChatGPT: {str(e)}")

    # Append to chat history
    chat_entry = ChatResponse(user=user_input, bot=bot_response)
    chat_history.append(chat_entry)

    return chat_entry

@app.get('/history', response_model=List[ChatResponse])
async def history():
    """Endpoint to retrieve chat history."""
    return chat_history

@app.post('/clear_history')
async def clear_history():
    """Endpoint to clear chat history."""
    chat_history.clear()
    return {"message": "Chat history cleared."}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
