"""
File watcher for continuous codebase indexing
Monitors file changes and updates the RAG index
"""
import time
from pathlib import Path
from typing import Optional, Callable

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    # Dummy classes for type hints when watchdog not available
    class FileSystemEventHandler:
        pass
    class FileSystemEvent:
        pass


class CodeChangeHandler(FileSystemEventHandler):
    """Handles file system events for code files"""
    
    def __init__(self, on_change: Callable[[Path], None]):
        self.on_change = on_change
        self.code_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.java', '.go', 
                              '.rs', '.cpp', '.c', '.h', '.rb', '.php', '.swift', '.kt'}
    
    def on_modified(self, event):
        if not event.is_directory:
            self._handle_file_event(event.src_path)
    
    def on_created(self, event):
        if not event.is_directory:
            self._handle_file_event(event.src_path)
    
    def on_deleted(self, event):
        if not event.is_directory:
            self._handle_file_event(event.src_path)
    
    def _handle_file_event(self, file_path: str):
        path = Path(file_path)
        if path.suffix in self.code_extensions:
            # Debounce: wait a bit before processing
            time.sleep(0.5)
            self.on_change(path)


class FileWatcher:
    """Watches codebase for changes and triggers reindexing"""
    
    def __init__(self, workspace_path: str, on_change: Optional[Callable[[Path], None]] = None):
        if not WATCHDOG_AVAILABLE:
            raise ImportError("watchdog is required. Install with: pip install watchdog")
        
        self.workspace_path = Path(workspace_path).resolve()
        self.on_change = on_change
        self.observer = None
        self.handler = None
    
    def start(self):
        """Start watching for file changes"""
        if self.observer and self.observer.is_alive():
            return
        
        self.handler = CodeChangeHandler(self._handle_change)
        self.observer = Observer()
        self.observer.schedule(
            self.handler,
            str(self.workspace_path),
            recursive=True
        )
        self.observer.start()
    
    def stop(self):
        """Stop watching for file changes"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
    
    def _handle_change(self, file_path: Path):
        """Handle file change event"""
        if self.on_change:
            self.on_change(file_path)

