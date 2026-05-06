import os
import shutil # Added to help clear the old database
from dotenv import load_dotenv
from langchain_community.document_loaders import PyPDFDirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma # 2026 Updated Import
from langchain_openai import OpenAIEmbeddings

# 1. Load Keys
load_dotenv()

embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

# --- STEP 1: CLEAR OLD DATA ---

if os.path.exists("./my_vector_db"):
    shutil.rmtree("./my_vector_db")
    print("Cleaned up old database.")

# 2. Load documents
loader = PyPDFDirectoryLoader("C:\\Users\\viq021\\repositories\\Robot_Detective\\Detective_Data\\Mysterie 1 Trudy")
docs = loader.load()

if not docs:
    print("Warning: No PDFs found in ../data folder!")

# 3. Split
text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
chunks = text_splitter.split_documents(docs)

# 4. Use OpenAI Embeddings (2026 Standard)
embeddings = OpenAIEmbeddings(model="text-embedding-3-large")

# 5. Create and SAVE (Note: we use .from_documents here)
vector_store = Chroma.from_documents(
    documents=chunks,
    embedding=embeddings,
    persist_directory="./Episode_1_Vector_DB"
)

print(f"Success! Vector database created with {len(chunks)} chunks.")