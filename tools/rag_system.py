"""
RAG (Retrieval-Augmented Generation) System for Codebase
Implements vector-based code retrieval similar to Cursor AI
"""
import os
import hashlib
import time
from pathlib import Path
from typing import List, Dict, Optional, Any, Tuple
from dataclasses import dataclass
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

try:
    import chromadb
    from chromadb.config import Settings
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False

from openai import OpenAI

from config import Config
from .ast_analyzer import ASTAnalyzer
from .code_graph import CodeGraphBuilder
from .cache import Cache
from .retry import retry_api_call


@dataclass
class CodeChunk:
    """Represents a chunk of code with metadata"""
    content: str
    file_path: str
    language: str
    chunk_type: str  # 'function', 'class', 'method', 'block', 'module'
    start_line: int
    end_line: int
    symbol_name: Optional[str] = None
    parent_symbol: Optional[str] = None
    metadata: Optional[Dict] = None


class RAGSystem:
    """
    RAG System for codebase retrieval and context generation.
    Implements Cursor AI-style retrieval-augmented generation.
    """
    
    def __init__(self, workspace_path: str = ".", api_key: Optional[str] = None,
                 performance_monitor=None):
        self.workspace_path = Path(workspace_path).resolve()
        self.client = OpenAI(api_key=api_key or Config.OPENAI_API_KEY)
        self.ast_analyzer = ASTAnalyzer(workspace_path)
        self.code_graph = None  # Lazy-loaded code graph
        self.performance_monitor = performance_monitor  # Optional performance monitor
        
        # Initialize cache for embeddings and analysis
        self.cache = Cache(cache_dir=str(self.workspace_path / ".cache"))
        
        # Initialize vector database
        self.db_path = self.workspace_path / Config.VECTOR_DB_PATH
        self.db_path.mkdir(exist_ok=True)
        
        if not CHROMADB_AVAILABLE:
            raise ImportError("chromadb is required for RAG. Install with: pip install chromadb")
        
        self.chroma_client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=Settings(anonymized_telemetry=False)
        )
        
        # Get or create collection
        self.collection = self.chroma_client.get_or_create_collection(
            name="codebase",
            metadata={"hnsw:space": "cosine"}
        )
        
        self.is_indexed = False
        self.file_index_map = {}  # Track indexed files
        self._index_lock = Lock()  # Thread-safe indexing
    
    def index_codebase(self, force_reindex: bool = False) -> Dict[str, Any]:
        """
        Index the entire codebase into the vector store.
        
        Args:
            force_reindex: If True, reindex even if already indexed
            
        Returns:
            dict with indexing statistics
        """
        if self.is_indexed and not force_reindex:
            return {"status": "already_indexed", "message": "Codebase already indexed"}
        
        # Start performance monitoring
        if self.performance_monitor:
            self.performance_monitor.start_indexing()
        
        print("[INFO] Scanning codebase...")
        files = self._get_code_files()
        print(f"[INFO] Found {len(files)} code files")
        
        all_chunks = []
        indexed_files = 0
        start_time = time.time()
        
        # Parallel file processing for better performance
        max_workers = min(8, len(files))  # Use up to 8 threads
        chunks_lock = Lock()
        
        # Use progress indicator for better UX
        from rich.console import Console
        from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
        
        console = Console()
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            task = progress.add_task("Indexing files...", total=len(files))
            
            def process_file(file_path: Path):
                """Process a single file and return chunks"""
                try:
                    chunks = self._chunk_file(file_path)
                    with chunks_lock:
                        all_chunks.extend(chunks)
                    return {"success": True, "file": file_path, "chunks": len(chunks)}
                except Exception as e:
                    return {"success": False, "file": file_path, "error": str(e)}
            
            # Process files in parallel
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                future_to_file = {executor.submit(process_file, file_path): file_path 
                                 for file_path in files}
                
                for future in as_completed(future_to_file):
                    result = future.result()
                    if result["success"]:
                        indexed_files += 1
                    else:
                        print(f"   [WARN] Error indexing {result['file']}: {result.get('error', 'Unknown error')}")
                    progress.update(task, advance=1)
        
        elapsed = time.time() - start_time
        print(f"[OK] Indexed {indexed_files} files in {elapsed:.2f}s (parallel processing)")
        
        print(f"[INFO] Generated {len(all_chunks)} code chunks")
        print("[INFO] Generating embeddings...")
        
        # Generate embeddings in batches
        # Reduced batch size to avoid token limit (text-embedding-3-small has 8192 token limit)
        batch_size = 50  # Reduced from 100 to avoid token limit issues
        embeddings = []
        texts = []
        metadatas = []
        ids = []
        
        # First pass: split any chunks that exceed token limit
        processed_chunks = []
        for chunk in all_chunks:
            formatted = self._format_chunk_for_embedding(chunk)
            estimated_tokens = self._estimate_tokens(formatted)
            
            if estimated_tokens > 8000:
                # Split the chunk into smaller pieces
                sub_chunks = self._split_large_chunk(chunk)
                processed_chunks.extend(sub_chunks)
                if len(sub_chunks) > 1:
                    print(f"[INFO] Split large chunk from {chunk.file_path} ({estimated_tokens} tokens) into {len(sub_chunks)} sub-chunks")
            else:
                processed_chunks.append(chunk)
        
        # Update all_chunks with processed chunks
        all_chunks = processed_chunks
        print(f"[INFO] Processed {len(all_chunks)} chunks (after splitting large chunks)")
        
        for i in range(0, len(all_chunks), batch_size):
            batch = all_chunks[i:i + batch_size]
            batch_texts = [self._format_chunk_for_embedding(chunk) for chunk in batch]
            
            # Check total text length and split if needed
            total_chars = sum(len(text) for text in batch_texts)
            # Rough estimate: ~4 chars per token, so 8192 tokens ≈ 32KB
            max_chars_per_batch = 30000  # Conservative limit
            
            if total_chars > max_chars_per_batch:
                # Split batch further if too large
                sub_batches = []
                current_sub_batch = []
                current_chars = 0
                
                for text in batch_texts:
                    if current_chars + len(text) > max_chars_per_batch and current_sub_batch:
                        sub_batches.append(current_sub_batch)
                        current_sub_batch = [text]
                        current_chars = len(text)
                    else:
                        current_sub_batch.append(text)
                        current_chars += len(text)
                
                if current_sub_batch:
                    sub_batches.append(current_sub_batch)
            else:
                sub_batches = [batch_texts]
            
            # Process each sub-batch
            for sub_batch_idx, sub_batch_texts in enumerate(sub_batches):
                # Generate embeddings using OpenAI
                try:
                    response = self.client.embeddings.create(
                        model=Config.EMBEDDING_MODEL,
                        input=sub_batch_texts
                    )
                    
                    batch_embeddings = [item.embedding for item in response.data]
                    embeddings.extend(batch_embeddings)
                    
                    # Map sub-batch texts back to original chunks
                    # Find which chunks correspond to this sub-batch
                    sub_batch_chunks = []
                    for text in sub_batch_texts:
                        # Find the chunk that produced this text
                        for chunk_idx, chunk in enumerate(batch):
                            if self._format_chunk_for_embedding(chunk) == text:
                                sub_batch_chunks.append((chunk, i + chunk_idx))
                                break
                    
                    # Add texts and metadata
                    texts.extend(sub_batch_texts)
                    for chunk, global_idx in sub_batch_chunks:
                        chunk_id = self._generate_chunk_id(chunk, global_idx)
                        ids.append(chunk_id)
                        metadatas.append({
                            "file_path": str(chunk.file_path),
                            "language": chunk.language,
                            "chunk_type": chunk.chunk_type,
                            "start_line": chunk.start_line,
                            "end_line": chunk.end_line,
                            "symbol_name": chunk.symbol_name or "",
                            "parent_symbol": chunk.parent_symbol or ""
                        })
                except Exception as e:
                    print(f"[WARN] Error generating embeddings for batch ({len(sub_batch_texts)} items): {e}")
                    # Skip this batch and continue
                    continue
        
        print("[INFO] Storing in vector database...")
        
        # Clear existing collection if reindexing
        if force_reindex:
            try:
                self.collection.delete()
            except Exception:
                pass  # Collection might not exist
            self.collection = self.chroma_client.get_or_create_collection(
                name="codebase",
                metadata={"hnsw:space": "cosine"}
            )
        
        # Add to vector store in batches if large
        if len(embeddings) > 0:
            try:
                # ChromaDB can handle large batches, but split if very large
                add_batch_size = 1000
                for batch_start in range(0, len(embeddings), add_batch_size):
                    batch_end = min(batch_start + add_batch_size, len(embeddings))
                    self.collection.add(
                        embeddings=embeddings[batch_start:batch_end],
                        documents=texts[batch_start:batch_end],
                        metadatas=metadatas[batch_start:batch_end],
                        ids=ids[batch_start:batch_end]
                    )
                
                self.is_indexed = True
                print(f"[OK] Stored {len(embeddings)} chunks in vector database")
            except Exception as e:
                print(f"[ERROR] Failed to store in vector database: {e}")
                raise
        
        # Record indexing completion
        if self.performance_monitor:
            indexing_stats = self.performance_monitor.end_indexing(
                files_indexed=indexed_files,
                chunks_created=len(all_chunks),
                embeddings_generated=len(embeddings)
            )
        
        return {
            "status": "success",
            "files_indexed": indexed_files,
            "total_files": len(files),
            "chunks_created": len(all_chunks),
            "embeddings_generated": len(embeddings),
            "duration_seconds": elapsed,
            "files_per_second": indexed_files / elapsed if elapsed > 0 else 0
        }
    
    def retrieve(self, query: str, top_k: Optional[int] = None, 
                 file_filter: Optional[str] = None, 
                 use_hybrid: bool = True,
                 use_graph: bool = True) -> List[Dict[str, Any]]:
        """
        Retrieve relevant code chunks for a query using vector similarity.
        Supports hybrid search (semantic + keyword).
        
        Args:
            query: Natural language or code query
            top_k: Number of chunks to retrieve (default from config)
            file_filter: Optional file path to filter results
            use_hybrid: If True, use hybrid search (semantic + keyword)
            
        Returns:
            List of relevant code chunks with metadata
        """
        if not self.is_indexed:
            return []
        
        top_k = top_k or Config.TOP_K_RETRIEVAL
        
        # Get base results
        if use_hybrid:
            results = self._hybrid_retrieve(query, top_k, file_filter)
        else:
            results = self._semantic_retrieve(query, top_k, file_filter)
        
        # Enhance with graph-based retrieval if enabled
        if use_graph:
            # Build code graph if not already built
            if self.code_graph is None:
                try:
                    self.build_code_graph()
                except Exception as e:
                    print(f"[WARN] Code graph build failed: {e}")
            
            if self.code_graph:
                results = self._enhance_with_graph(query, results, top_k)
        
        return results
    
    def _enhance_with_graph(self, query: str, results: List[Dict[str, Any]], 
                           top_k: int) -> List[Dict[str, Any]]:
        """
        Enhance retrieval results using code graph.
        Adds related symbols based on call graphs and dependencies.
        """
        if not self.code_graph:
            return results
        
        # Extract symbol names from query
        import re
        query_words = set(re.findall(r'\b\w+\b', query.lower()))
        
        enhanced_results = list(results)
        added_symbols = set()
        
        # For each result, find related symbols
        for result in results[:top_k // 2]:  # Only enhance top results
            symbol_name = result.get('symbol_name', '')
            if not symbol_name:
                continue
            
            # Find related symbols via graph
            related = self.code_graph.find_related_symbols(
                symbol_name,
                relationship_types=['calls', 'inherits']
            )
            
            for related_node in related[:2]:  # Limit related symbols
                related_id = f"{related_node.file_path}::{related_node.name}"
                if related_id not in added_symbols:
                    # Try to find this symbol in vector store
                    related_chunks = self._semantic_retrieve(
                        related_node.name,
                        top_k=1,
                        file_filter=related_node.file_path
                    )
                    if related_chunks:
                        enhanced_results.append(related_chunks[0])
                        added_symbols.add(related_id)
        
        # Re-rank and return top_k
        return self._rerank_results(enhanced_results, query, top_k)
    
    def _semantic_retrieve(self, query: str, top_k: int, 
                          file_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """Semantic retrieval using embeddings only"""
        # Check cache for query embedding
        cache_key = f"embedding::{Config.EMBEDDING_MODEL}::{hashlib.md5(query.encode()).hexdigest()}"
        query_embedding = self.cache.get(cache_key)
        
        if query_embedding is None:
            # Generate query embedding with retry
            query_embedding = self._get_embedding_with_retry(query)
            # Cache for 24 hours
            self.cache.set(cache_key, query_embedding, ttl=3600 * 24)
        
        # Build where clause for filtering
        where_clause = None
        if file_filter:
            where_clause = {"file_path": {"$eq": file_filter}}
        
        # Query vector store
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k * 2,  # Get more for re-ranking
            where=where_clause
        )
        
        return self._format_results(results, top_k)
    
    @retry_api_call(max_attempts=3)
    def _get_embedding_with_retry(self, text: str):
        """Get embedding with retry logic"""
        response = self.client.embeddings.create(
            model=Config.EMBEDDING_MODEL,
            input=text
        )
        return response.data[0].embedding
    
    @retry_api_call(max_attempts=3)
    def _get_batch_embeddings_with_retry(self, texts: List[str]):
        """Get batch embeddings with retry logic"""
        response = self.client.embeddings.create(
            model=Config.EMBEDDING_MODEL,
            input=texts
        )
        return [item.embedding for item in response.data]
    
    def _hybrid_retrieve(self, query: str, top_k: int, 
                        file_filter: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval: combines semantic search with keyword matching.
        """
        import re
        
        # Get semantic results
        semantic_results = self._semantic_retrieve(query, top_k * 2, file_filter)
        
        # Extract keywords from query
        query_lower = query.lower()
        keywords = set(re.findall(r'\b\w+\b', query_lower))
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'should', 'could', 'may', 'might', 'must', 'can'}
        keywords = keywords - stop_words
        
        if not keywords:
            # Fallback to semantic only
            return self._rerank_results(semantic_results, query, top_k)
        
        # Score chunks by keyword matches
        scored_chunks = []
        for chunk in semantic_results:
            score = chunk.get('distance', 1.0) if chunk.get('distance') else 1.0
            
            # Boost score for keyword matches
            content_lower = chunk['content'].lower()
            symbol_lower = chunk.get('symbol_name', '').lower()
            
            keyword_matches = sum(1 for kw in keywords if kw in content_lower or kw in symbol_lower)
            if keyword_matches > 0:
                # Boost: reduce distance (lower is better)
                score = score * (1.0 - (keyword_matches * 0.1))
            
            chunk['hybrid_score'] = score
            scored_chunks.append(chunk)
        
        # Sort by hybrid score
        scored_chunks.sort(key=lambda x: x.get('hybrid_score', 1.0))
        
        # Re-rank and return top_k
        return self._rerank_results(scored_chunks[:top_k * 2], query, top_k)
    
    def _rerank_results(self, chunks: List[Dict[str, Any]], 
                      query: str, top_k: int) -> List[Dict[str, Any]]:
        """
        Re-rank results using multiple signals:
        - Semantic similarity (distance)
        - Keyword matches
        - Symbol name relevance
        - File path relevance
        """
        import re
        
        query_lower = query.lower()
        query_words = set(re.findall(r'\b\w+\b', query_lower))
        
        for chunk in chunks:
            score = 0.0
            
            # Base score from semantic similarity (invert distance)
            distance = chunk.get('distance', 1.0) or 1.0
            score += (1.0 - min(distance, 1.0)) * 0.4
            
            # Symbol name match boost
            symbol_name = chunk.get('symbol_name', '').lower()
            if symbol_name:
                symbol_words = set(re.findall(r'\b\w+\b', symbol_name))
                symbol_match = len(query_words & symbol_words) / max(len(query_words), 1)
                score += symbol_match * 0.3
            
            # Content keyword match
            content_lower = chunk.get('content', '').lower()
            content_words = set(re.findall(r'\b\w+\b', content_lower))
            content_match = len(query_words & content_words) / max(len(query_words), 1)
            score += content_match * 0.2
            
            # File path relevance (if query mentions file)
            file_path = chunk.get('file_path', '').lower()
            if any(word in file_path for word in query_words):
                score += 0.1
            
            chunk['rerank_score'] = score
        
        # Sort by rerank score
        chunks.sort(key=lambda x: x.get('rerank_score', 0.0), reverse=True)
        
        return chunks[:top_k]
    
    def _format_results(self, results: Dict, top_k: int) -> List[Dict[str, Any]]:
        """Format query results into chunk dictionaries"""
        retrieved_chunks = []
        if results['documents'] and len(results['documents'][0]) > 0:
            for i in range(len(results['documents'][0])):
                chunk_data = {
                    "content": results['documents'][0][i],
                    "file_path": results['metadatas'][0][i]['file_path'],
                    "language": results['metadatas'][0][i]['language'],
                    "chunk_type": results['metadatas'][0][i]['chunk_type'],
                    "start_line": results['metadatas'][0][i]['start_line'],
                    "end_line": results['metadatas'][0][i]['end_line'],
                    "symbol_name": results['metadatas'][0][i].get('symbol_name', ''),
                    "parent_symbol": results['metadatas'][0][i].get('parent_symbol', ''),
                    "distance": results['distances'][0][i] if 'distances' in results else None
                }
                retrieved_chunks.append(chunk_data)
        
        return retrieved_chunks
    
    def get_context_for_query(self, query: str, max_chunks: Optional[int] = None, 
                              use_hybrid: bool = True, use_graph: bool = True) -> str:
        """
        Get formatted context string for LLM prompt.
        Uses hybrid search and re-ranking for better results.
        
        Args:
            query: User query
            max_chunks: Maximum chunks to include
            use_hybrid: If True, use hybrid search
            use_graph: If True, use graph-based enhancement
            
        Returns:
            Formatted context string ready for LLM
        """
        chunks = self.retrieve(query, top_k=max_chunks or Config.TOP_K_RETRIEVAL, 
                              use_hybrid=use_hybrid, use_graph=use_graph)
        
        if not chunks:
            return ""
        
        context_parts = []
        for chunk in chunks:
            file_path = chunk['file_path']
            start_line = chunk['start_line']
            end_line = chunk['end_line']
            symbol_info = ""
            
            if chunk['symbol_name']:
                symbol_info = f" ({chunk['chunk_type']}: {chunk['symbol_name']})"
                if chunk['parent_symbol']:
                    symbol_info += f" in {chunk['parent_symbol']}"
            
            context_parts.append(
                f"<file: {file_path}, lines {start_line}-{end_line}{symbol_info}>\n"
                f"{chunk['content']}\n"
            )
        
        return "\n".join(context_parts)
    
    def _chunk_file(self, file_path: Path) -> List[CodeChunk]:
        """
        Chunk a file using AST-aware chunking.
        Returns semantically meaningful chunks (functions, classes, etc.)
        """
        chunks = []
        extension = file_path.suffix.lower()
        
        if extension == '.py':
            chunks = self._chunk_python_file(file_path)
        elif extension in ['.js', '.jsx', '.ts', '.tsx']:
            chunks = self._chunk_javascript_file(file_path)
        else:
            # Fallback to line-based chunking
            chunks = self._chunk_by_lines(file_path)
        
        return chunks
    
    def _chunk_python_file(self, file_path: Path) -> List[CodeChunk]:
        """Chunk Python file using AST"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            analysis = self.ast_analyzer.analyze_file(str(file_path))
            if "error" in analysis:
                return self._chunk_by_lines(file_path)
            tree = analysis
            
            chunks = []
            lines = content.split('\n')
            
            # Add imports as a chunk
            if tree.get('imports'):
                import_lines = []
                for imp in tree['imports']:
                    import_lines.append(imp.get('line', 0))
                
                if import_lines:
                    start = min(import_lines) - 1
                    end = max(import_lines)
                    import_content = '\n'.join(lines[start:end])
                    chunks.append(CodeChunk(
                        content=import_content,
                        file_path=str(file_path.relative_to(self.workspace_path)),
                        language="python",
                        chunk_type="imports",
                        start_line=start + 1,
                        end_line=end
                    ))
            
            # Add classes as chunks
            for cls in tree.get('classes', []):
                cls_content = '\n'.join(lines[cls['line'] - 1:cls.get('line_end', cls['line'] + 20)])
                chunks.append(CodeChunk(
                    content=cls_content,
                    file_path=str(file_path.relative_to(self.workspace_path)),
                    language="python",
                    chunk_type="class",
                    start_line=cls['line'],
                    end_line=cls.get('line_end', cls['line'] + 20),
                    symbol_name=cls['name']
                ))
            
            # Add functions as chunks
            for func in tree.get('functions', []):
                func_content = '\n'.join(lines[func['line'] - 1:func.get('line_end', func['line'] + 20)])
                chunks.append(CodeChunk(
                    content=func_content,
                    file_path=str(file_path.relative_to(self.workspace_path)),
                    language="python",
                    chunk_type="method" if func.get('parent') else "function",
                    start_line=func['line'],
                    end_line=func.get('line_end', func['line'] + 20),
                    symbol_name=func['name'],
                    parent_symbol=func.get('parent')
                ))
            
            # If no AST chunks, fall back to line-based
            if not chunks:
                return self._chunk_by_lines(file_path)
            
            return chunks
        
        except Exception:
            return self._chunk_by_lines(file_path)
    
    def _chunk_javascript_file(self, file_path: Path) -> List[CodeChunk]:
        """Chunk JavaScript file (simplified)"""
        return self._chunk_by_lines(file_path)
    
    def _chunk_by_lines(self, file_path: Path) -> List[CodeChunk]:
        """Fallback: chunk file by lines"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            chunks = []
            chunk_size = Config.CHUNK_SIZE
            overlap = Config.CHUNK_OVERLAP
            
            for i in range(0, len(lines), chunk_size - overlap):
                chunk_lines = lines[i:i + chunk_size]
                chunk_content = ''.join(chunk_lines)
                
                if chunk_content.strip():
                    chunks.append(CodeChunk(
                        content=chunk_content,
                        file_path=str(file_path.relative_to(self.workspace_path)),
                        language=file_path.suffix[1:] if file_path.suffix else "unknown",
                        chunk_type="block",
                        start_line=i + 1,
                        end_line=min(i + len(chunk_lines), len(lines))
                    ))
            
            return chunks
        
        except Exception:
            return []
    
    def _format_chunk_for_embedding(self, chunk: CodeChunk) -> str:
        """Format chunk content for embedding generation"""
        parts = []
        
        if chunk.symbol_name:
            parts.append(f"{chunk.chunk_type}: {chunk.symbol_name}")
            if chunk.parent_symbol:
                parts.append(f"in {chunk.parent_symbol}")
        
        parts.append(f"file: {chunk.file_path}")
        parts.append(chunk.content)
        
        return "\n".join(parts)
    
    def _estimate_tokens(self, text: str) -> int:
        """Estimate token count for text (rough estimate: ~4 chars per token)"""
        return len(text) // 4
    
    def _split_large_chunk(self, chunk: CodeChunk) -> List[CodeChunk]:
        """
        Split a chunk that exceeds token limit into smaller sub-chunks.
        Tries to split at logical boundaries (function/method boundaries).
        """
        formatted = self._format_chunk_for_embedding(chunk)
        estimated_tokens = self._estimate_tokens(formatted)
        
        # If chunk is within limit, return as-is
        if estimated_tokens <= 8000:
            return [chunk]
        
        # Split the content by lines and try to create logical sub-chunks
        lines = chunk.content.split('\n')
        max_lines_per_chunk = len(lines) // ((estimated_tokens // 8000) + 1)
        max_lines_per_chunk = max(50, max_lines_per_chunk)  # At least 50 lines per chunk
        
        sub_chunks = []
        current_lines = []
        current_start_line = chunk.start_line
        
        for i, line in enumerate(lines):
            current_lines.append(line)
            
            # Check if we've reached the max size for a sub-chunk
            if len(current_lines) >= max_lines_per_chunk:
                # Create a sub-chunk
                sub_content = '\n'.join(current_lines)
                sub_end_line = current_start_line + len(current_lines) - 1
                
                sub_chunk = CodeChunk(
                    content=sub_content,
                    file_path=chunk.file_path,
                    language=chunk.language,
                    chunk_type=chunk.chunk_type,
                    start_line=current_start_line,
                    end_line=sub_end_line,
                    symbol_name=chunk.symbol_name if i == 0 else None,  # Only first chunk keeps symbol name
                    parent_symbol=chunk.parent_symbol,
                    metadata=chunk.metadata
                )
                sub_chunks.append(sub_chunk)
                
                # Reset for next sub-chunk
                current_lines = []
                current_start_line = sub_end_line + 1
        
        # Add remaining lines as final sub-chunk
        if current_lines:
            sub_content = '\n'.join(current_lines)
            sub_end_line = current_start_line + len(current_lines) - 1
            
            sub_chunk = CodeChunk(
                content=sub_content,
                file_path=chunk.file_path,
                language=chunk.language,
                chunk_type=chunk.chunk_type,
                start_line=current_start_line,
                end_line=sub_end_line,
                symbol_name=None,  # Not the first chunk
                parent_symbol=chunk.parent_symbol,
                metadata=chunk.metadata
            )
            sub_chunks.append(sub_chunk)
        
        return sub_chunks if sub_chunks else [chunk]
    
    def _generate_chunk_id(self, chunk: CodeChunk, index: int) -> str:
        """Generate unique ID for a chunk"""
        content = f"{chunk.file_path}:{chunk.start_line}:{chunk.end_line}:{chunk.symbol_name or ''}"
        return hashlib.md5(content.encode()).hexdigest() + f"_{index}"
    
    def _get_code_files(self) -> List[Path]:
        """Get all code files in workspace"""
        code_files = []
        extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', '.rs',
                     '.cpp', '.c', '.h', '.rb', '.php', '.swift', '.kt'}
        
        for root, dirs, files in os.walk(self.workspace_path):
            dirs[:] = [d for d in dirs if d not in {'.git', '__pycache__', 'node_modules', 
                                                     '.venv', 'venv', 'env', '.vector_db'}]
            
            for file in files:
                if any(file.endswith(ext) for ext in extensions):
                    code_files.append(Path(root) / file)
        
        return code_files
    
    def clear_index(self):
        """Clear the vector database"""
        try:
            self.chroma_client.delete_collection("codebase")
            self.collection = self.chroma_client.get_or_create_collection(
                name="codebase",
                metadata={"hnsw:space": "cosine"}
            )
            self.is_indexed = False
        except Exception as e:
            print(f"Error clearing index: {e}")
    
    def index_file(self, file_path: Path, force_reindex: bool = False) -> Dict[str, Any]:
        """
        Index a single file incrementally.
        
        Args:
            file_path: Path to the file to index
            force_reindex: If True, reindex even if already indexed
            
        Returns:
            dict with indexing results
        """
        file_str = str(file_path.relative_to(self.workspace_path))
        
        # Check if already indexed
        if file_str in self.file_index_map and not force_reindex:
            return {"status": "already_indexed", "file": file_str}
        
        try:
            # Remove old chunks for this file if reindexing
            if force_reindex or file_str in self.file_index_map:
                self._remove_file_chunks(file_str)
            
            # Chunk the file
            chunks = self._chunk_file(file_path)
            if not chunks:
                return {"status": "no_chunks", "file": file_str}
            
            # Generate embeddings
            texts = [self._format_chunk_for_embedding(chunk) for chunk in chunks]
            response = self.client.embeddings.create(
                model=Config.EMBEDDING_MODEL,
                input=texts
            )
            
            embeddings = [item.embedding for item in response.data]
            metadatas = []
            ids = []
            
            for i, chunk in enumerate(chunks):
                chunk_id = self._generate_chunk_id(chunk, i)
                ids.append(chunk_id)
                metadatas.append({
                    "file_path": str(chunk.file_path),
                    "language": chunk.language,
                    "chunk_type": chunk.chunk_type,
                    "start_line": chunk.start_line,
                    "end_line": chunk.end_line,
                    "symbol_name": chunk.symbol_name or "",
                    "parent_symbol": chunk.parent_symbol or ""
                })
            
            # Add to vector store
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
                ids=ids
            )
            
            # Update index map
            self.file_index_map[file_str] = len(chunks)
            
            return {
                "status": "success",
                "file": file_str,
                "chunks_created": len(chunks)
            }
        
        except Exception as e:
            return {
                "status": "error",
                "file": file_str,
                "error": str(e)
            }
    
    def remove_file_from_index(self, file_path: Path) -> Dict[str, Any]:
        """
        Remove a file from the index.
        
        Args:
            file_path: Path to the file to remove
            
        Returns:
            dict with removal results
        """
        file_str = str(file_path.relative_to(self.workspace_path))
        return self._remove_file_chunks(file_str)
    
    def _remove_file_chunks(self, file_path: str) -> Dict[str, Any]:
        """Remove all chunks for a specific file"""
        try:
            # Query to find all chunks for this file
            results = self.collection.get(
                where={"file_path": {"$eq": file_path}}
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                if file_path in self.file_index_map:
                    del self.file_index_map[file_path]
                return {
                    "status": "removed",
                    "file": file_path,
                    "chunks_removed": len(results['ids'])
                }
            
            return {"status": "not_found", "file": file_path}
        
        except Exception as e:
            return {"status": "error", "file": file_path, "error": str(e)}
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get statistics about the indexed codebase"""
        if not self.is_indexed:
            return {"indexed": False}
        
        count = self.collection.count()
        return {
            "indexed": True,
            "total_chunks": count,
            "files_indexed": len(self.file_index_map),
            "db_path": str(self.db_path)
        }
