import os
import io
from fastapi import FastAPI, File, UploadFile, WebSocket
from fastapi.responses import HTMLResponse, FileResponse
import uvicorn
from docx import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import OpenAIEmbeddings
from langchain_community.chat_models import ChatOpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.retrievers import MultiQueryRetriever
import json


os.environ["OPENAI_API_KEY"] = "your api key"
app = FastAPI()

embeddings = OpenAIEmbeddings()

vector_store = FAISS.from_texts([""], embeddings)

llm = ChatOpenAI(model="gpt-4o-mini")
qa_chain = ConversationalRetrievalChain.from_llm(llm, vector_store.as_retriever())

chat_history = []

@app.post("/upload/")
async def upload_files(files: list[UploadFile] = File(...)):
    global vector_store, qa_chain
    
    all_chunks = []
    for file in files:
        content = await file.read()
        
        file_like_object = io.BytesIO(content)
        
        doc = Document(file_like_object)
        text = "\n".join([para.text for para in doc.paragraphs])
        
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
        chunks = text_splitter.split_text(text)
        all_chunks.extend(chunks)
    
    vector_store = FAISS.from_texts(all_chunks, embeddings)
    
    retriever = MultiQueryRetriever.from_llm(
        retriever=vector_store.as_retriever(),
        llm=llm
    )
    
    qa_chain = ConversationalRetrievalChain.from_llm(llm, retriever)
    
    return {"message": f"{len(files)} file(s) uploaded and processed successfully"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    while True:
        data = await websocket.receive_text()
        try:
            message = json.loads(data)
            if message['type'] == 'clear_chat':
                chat_history.clear()
                continue
        except json.JSONDecodeError:
            pass
        
        print("data", data)

        response = qa_chain({"question": data, "chat_history": chat_history})
        chat_history.append((data, response['answer']))
        await websocket.send_text(response['answer'])

@app.get("/", response_class=FileResponse)
async def read_root():
    return FileResponse("chat.html")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
