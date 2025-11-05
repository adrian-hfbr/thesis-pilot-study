#create_index.py
import os
import shutil
import re
import config
from langchain_openai import OpenAIEmbeddings
from langchain_community.document_loaders import TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from dotenv import load_dotenv


"""
Purpose: Performs offline document processing for RAG system - loads German tax law documents,
splits them into 800-character chunks, creates embeddings, and saves a persistent FAISS index.

Architecture Note: This implements SINGLE-SCALE retrieval where 800-character chunks are used
for both semantic matching (retrieval) and context provision (generation). Despite earlier
development using ParentDocumentRetriever terminology, the runtime system (rag_pipeline.py)
loads only the FAISS vectorstore and retrieves chunks directly - no parent-child lookup occurs.
"""

# Load environment variables from .env file for the API key
load_dotenv()


def parse_legal_reference(filename):
    """Extract German tax law reference from filename (e.g., 'estg_35a.txt' → 'EStG §35a')."""
    # Extract law name and paragraph
    match = re.search(r'(estg|ustg|abgb)_(\d+[a-z]?)', filename.lower())
    if match:
        law_name = match.group(1).upper()
        paragraph = match.group(2)
        return f"{law_name} §{paragraph}"
    return filename  # Fallback


def extract_paragraph_details(text_content):
    """Extract Absatz (subsection) information from document text (e.g., '(1) Für...' → 'Abs. 1')."""
    # Look for "(1)" or "(2)" at start of text
    abs_match = re.search(r'^\((\d+[a-z]?)\)', text_content.strip())
    if abs_match:
        return f"Abs. {abs_match.group(1)}"
    return None


def load_and_enrich_documents(data_path):
    """Load German tax law documents and enrich with structured metadata including URLs and legal references."""
    print(f"Loading documents from: {data_path}")
    # URL mapping for source attribution to official federal legal database
    source_url_mapping = {
        "estg_6.txt": "https://www.gesetze-im-internet.de/estg/__6.html",
        "estg_9.txt": "https://www.gesetze-im-internet.de/estg/__9.html",
        "estg_20.txt": "https://www.gesetze-im-internet.de/estg/__20.html",
        "estg_35a.txt": "https://www.gesetze-im-internet.de/estg/__35a.html",
    }
    
    all_docs = []
    
    for file_name in os.listdir(data_path):
        file_path = os.path.join(data_path, file_name)
        
        # Skip files without URL mapping
        url = source_url_mapping.get(file_name)
        if not url:
            print(f"Warning: No URL mapping found for {file_name}. Skipping.")
            continue
        
        # Only process .txt files
        if not file_name.endswith('.txt'):
            continue
        
        # Extract legal reference from filename
        legal_ref = parse_legal_reference(file_name)
        
        # Load document content
        loader = TextLoader(file_path, encoding='utf-8')
        docs = loader.load()
        
        # Enrich each document with metadata
        for doc in docs:
            doc.metadata['url'] = url
            doc.metadata['legal_reference'] = legal_ref  # "EStG §35a"
            doc.metadata['source_file'] = file_name
            
            # Extract Absatz detail if present in content
            abs_detail = extract_paragraph_details(doc.page_content)
            if abs_detail:
                doc.metadata['paragraph_detail'] = abs_detail  # "Abs. 2"
                doc.metadata['legal_reference_full'] = f"{legal_ref} {abs_detail}"  # "EStG §35a Abs. 2"
            
        all_docs.extend(docs)
    
    # Validation: ensure documents were found
    if not all_docs:
        print("ERROR: No documents found to index. Check data_path and source_url_mapping.")
        raise SystemExit(1)
    
    print(f"✓ Loaded {len(all_docs)} document(s) with metadata enrichment")
    return all_docs


def chunk_documents(documents):
    """Split documents into 800-character chunks with 50-character overlap using hierarchical separators."""
    print(f"Splitting documents into chunks (size: {config.CHUNK_SIZE} chars, overlap: {config.CHUNK_OVERLAP} chars)...")
    
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=config.CHUNK_SIZE,  # 800 characters
        chunk_overlap=config.CHUNK_OVERLAP,  # 50 characters
        # Hierarchical separators: respect paragraph > sentence > word boundaries
        separators=['\n\n', '\n', '.', '!', '?', ' ', '']
    )
    
    chunked_docs = text_splitter.split_documents(documents)
    
    print(f"✓ Created {len(chunked_docs)} chunks from {len(documents)} source document(s)")
    return chunked_docs


def create_and_save_vectorstore(chunked_documents, vectorstore_path):
    """Generate OpenAI embeddings and persist FAISS IndexFlatL2 vectorstore to disk."""
    print(f"Generating embeddings using {config.EMBEDDING_MODEL}...")
    
    # Initialize OpenAI embeddings
    embeddings = OpenAIEmbeddings(model=config.EMBEDDING_MODEL)
    
    vectorstore = FAISS.from_documents(
        documents=chunked_documents,
        embedding=embeddings
    )
    
    print(f"✓ Built FAISS index with {vectorstore.index.ntotal} embedded chunks")
    
    # Persist to disk for runtime loading
    print(f"Saving vector store to: {vectorstore_path}")
    vectorstore.save_local(vectorstore_path)
    print(f"✓ Vector store persisted at: {vectorstore_path}")
    
    return vectorstore


def build_and_save_index():
    """Orchestrate complete offline indexing pipeline: load, chunk, embed, and persist FAISS index."""
    print("=" * 60)
    print("Starting Index Creation (Single-Scale Retrieval)")
    print("=" * 60)
    
    vectorstore_path = config.VECTORSTORE_PATH
    data_path = config.DATA_PATH
    
    if os.path.exists(vectorstore_path):
        print(f"Removing existing vector store at: {vectorstore_path}")
        shutil.rmtree(vectorstore_path)
    
    all_docs = load_and_enrich_documents(data_path)
    
    chunked_docs = chunk_documents(all_docs)
    
    vectorstore = create_and_save_vectorstore(chunked_docs, vectorstore_path)
    
    # Summary
    print("=" * 60)
    print("Index Creation Complete")
    print(f"Vector store persisted at: {vectorstore_path}")
    print(f"Total chunks indexed: {len(chunked_docs)}")
    print(f"Embedding model: {config.EMBEDDING_MODEL}")
    print(f"Index type: FAISS IndexFlatL2 (exhaustive search)")
    print(f"Architecture: Single-scale retrieval (800-char chunks for both retrieval and generation)")
    print("=" * 60)
    
    return vectorstore


if __name__ == "__main__":
    build_and_save_index()
