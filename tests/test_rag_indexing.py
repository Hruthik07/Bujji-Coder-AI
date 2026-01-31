"""Test RAG indexing directly"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from tools.rag_system import RAGSystem
from config import Config

print("Testing RAG Indexing...")
print(f"Workspace: {Path('.').resolve()}")
print(f"RAG Enabled: {Config.ENABLE_RAG}")
print(f"OpenAI API Key: {'SET' if Config.OPENAI_API_KEY else 'NOT SET'}")

if not Config.ENABLE_RAG:
    print("ERROR: RAG is disabled in config")
    sys.exit(1)

if not Config.OPENAI_API_KEY:
    print("ERROR: OpenAI API key not set")
    sys.exit(1)

try:
    rag = RAGSystem(workspace_path=".")
    print(f"RAG System initialized")
    print(f"Current indexed status: {rag.is_indexed}")
    
    # Check for files
    files = rag._get_code_files()
    print(f"Found {len(files)} code files to index")
    
    if len(files) == 0:
        print("WARNING: No code files found to index")
        sys.exit(1)
    
    # Try indexing
    print("\nStarting indexing...")
    result = rag.index_codebase(force_reindex=True)
    print(f"\nIndexing result: {result}")
    print(f"Indexed status after: {rag.is_indexed}")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
