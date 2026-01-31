"""
Incremental indexing system that integrates file watcher with RAG
"""
import threading
from pathlib import Path
from typing import Optional, Callable
from queue import Queue
import time

from .file_watcher import FileWatcher
from .rag_system import RAGSystem


class IncrementalIndexer:
    """
    Manages incremental indexing of codebase changes.
    Integrates file watcher with RAG system for automatic updates.
    """
    
    def __init__(self, rag_system: RAGSystem, workspace_path: str = "."):
        self.rag_system = rag_system
        self.workspace_path = Path(workspace_path).resolve()
        self.file_watcher = None
        self.index_queue = Queue()
        self.index_thread = None
        self.running = False
        self.pending_files = set()
        
        try:
            self.file_watcher = FileWatcher(
                workspace_path=str(self.workspace_path),
                on_change=self._on_file_changed
            )
        except ImportError:
            print("⚠️  File watcher not available. Install watchdog for incremental indexing.")
    
    def start(self):
        """Start incremental indexing"""
        if self.running:
            return
        
        self.running = True
        
        # Start file watcher
        if self.file_watcher:
            self.file_watcher.start()
            print("👀 File watcher started - monitoring codebase changes...")
        
        # Start indexing thread
        self.index_thread = threading.Thread(target=self._index_worker, daemon=True)
        self.index_thread.start()
        print("🔄 Incremental indexer started")
    
    def stop(self):
        """Stop incremental indexing"""
        self.running = False
        
        if self.file_watcher:
            self.file_watcher.stop()
        
        if self.index_thread:
            self.index_thread.join(timeout=2)
        
        print("⏹️  Incremental indexer stopped")
    
    def _on_file_changed(self, file_path: Path):
        """Callback when a file changes"""
        # Add to queue for processing
        file_str = str(file_path.relative_to(self.workspace_path))
        
        # Debounce: add to pending set
        self.pending_files.add(file_str)
        
        # Schedule indexing after a delay
        self.index_queue.put(("index", file_path, time.time() + 2))  # 2 second delay
    
    def _index_worker(self):
        """Worker thread that processes indexing queue"""
        pending_tasks = {}
        
        while self.running:
            try:
                # Process queue
                while not self.index_queue.empty():
                    action, file_path, timestamp = self.index_queue.get_nowait()
                    pending_tasks[file_path] = (action, timestamp)
                
                # Process pending tasks that are ready
                current_time = time.time()
                ready_tasks = [
                    (fp, action) for fp, (action, ts) in pending_tasks.items()
                    if current_time >= ts
                ]
                
                for file_path, action in ready_tasks:
                    if action == "index":
                        self._index_file_safe(file_path)
                    elif action == "remove":
                        self._remove_file_safe(file_path)
                    
                    del pending_tasks[file_path]
                
                # Small sleep to prevent busy waiting
                time.sleep(0.5)
            
            except Exception as e:
                print(f"⚠️  Error in index worker: {e}")
                time.sleep(1)
    
    def _index_file_safe(self, file_path: Path):
        """Safely index a file with error handling"""
        try:
            if not file_path.exists():
                # File was deleted, remove from index
                self.rag_system.remove_file_from_index(file_path)
                return
            
            result = self.rag_system.index_file(file_path, force_reindex=True)
            if result.get("status") == "success":
                print(f"✅ Incrementally indexed: {file_path.name} ({result.get('chunks_created', 0)} chunks)")
            elif result.get("status") == "error":
                print(f"⚠️  Error indexing {file_path.name}: {result.get('error')}")
        except Exception as e:
            print(f"⚠️  Exception indexing {file_path}: {e}")
    
    def _remove_file_safe(self, file_path: Path):
        """Safely remove a file from index"""
        try:
            result = self.rag_system.remove_file_from_index(file_path)
            if result.get("status") == "removed":
                print(f"🗑️  Removed from index: {file_path.name}")
        except Exception as e:
            print(f"⚠️  Error removing {file_path}: {e}")
    
    def index_file_now(self, file_path: Path):
        """Immediately index a file (bypass queue)"""
        self._index_file_safe(file_path)
    
    def get_status(self) -> dict:
        """Get status of incremental indexer"""
        return {
            "running": self.running,
            "queue_size": self.index_queue.qsize(),
            "pending_files": len(self.pending_files),
            "watcher_active": self.file_watcher is not None and (
                self.file_watcher.observer is not None and 
                self.file_watcher.observer.is_alive()
            ) if self.file_watcher else False
        }
