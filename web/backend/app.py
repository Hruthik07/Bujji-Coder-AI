"""
FastAPI backend for AI Coding Assistant Web UI
Provides REST API and WebSocket for real-time communication
"""
import os
import sys
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import json
import json as json_lib  # For debug logging
import asyncio
import time
from contextlib import asynccontextmanager

# Add parent directory to path to import assistant
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from assistant import CodingAssistant
from tools.code_completion import CodeCompletionEngine
from tools.git_integration import GitService
from config import Config

# Global assistant instance
assistant: Optional[CodingAssistant] = None
completion_engine: Optional[CodeCompletionEngine] = None
git_service: Optional[GitService] = None
active_connections: List[WebSocket] = []


def safe_debug_log(location: str, message: str, data: Optional[Dict] = None):
    """Safely write debug log without failing if directory doesn't exist"""
    try:
        log_dir = Path(__file__).parent.parent.parent / ".cursor"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = log_dir / "debug.log"
        
        log_entry = {
            "sessionId": "debug-session",
            "runId": "run1",
            "hypothesisId": "B",
            "location": location,
            "message": message,
            "data": data or {},
            "timestamp": int(time.time() * 1000)
        }
        
        with open(log_file_path, "a", encoding="utf-8") as log_file:
            log_file.write(json_lib.dumps(log_entry) + "\n")
    except Exception:
        # Silently fail - don't break the app if logging fails
        pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize and cleanup"""
    global assistant, completion_engine, git_service
    # Initialize assistant
    workspace_path = os.getenv("WORKSPACE_PATH", ".")
    print("[INFO] Initializing assistant...")
    try:
        assistant = CodingAssistant(workspace_path=workspace_path)
        print("[OK] Assistant initialization started")
    except Exception as e:
        print(f"[ERROR] Assistant initialization failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    
    # Auto-index RAG if not already indexed
    if assistant.rag_system:
        try:
            rag_stats = assistant.rag_system.get_index_stats()
            if not rag_stats.get("indexed", False):
                print("[INFO] RAG not indexed. Starting automatic indexing...")
                # Start indexing in background (non-blocking)
                import threading
                def index_background():
                    try:
                        assistant.rag_system.index_codebase(force_reindex=False)
                        print("[OK] RAG indexing completed")
                    except Exception as e:
                        print(f"[WARN] RAG indexing failed: {e}")
                
                index_thread = threading.Thread(target=index_background, daemon=True)
                index_thread.start()
        except Exception as e:
            print(f"[WARN] Could not check RAG status: {e}")
    
    # Initialize completion engine
    try:
        completion_engine = CodeCompletionEngine(
            rag_system=assistant.rag_system,
            workspace_path=workspace_path
        )
        print(f"[OK] Completion engine initialized")
    except Exception as e:
        print(f"[WARN] Completion engine initialization failed: {e}")
        completion_engine = None
    
    # Initialize git service
    try:
        git_service = GitService(workspace_path=workspace_path)
        if git_service.is_repo:
            print(f"[OK] Git service initialized (repo: {git_service.get_current_branch()})")
        else:
            print(f"[WARN] Git service initialized (not a git repository)")
    except Exception as e:
        print(f"[WARN] Git service initialization failed: {e}")
        git_service = None
    
    print(f"[OK] Assistant initialized for workspace: {workspace_path}")
    yield
    # Cleanup
    assistant = None
    completion_engine = None
    git_service = None


app = FastAPI(
    title="AI Coding Assistant API",
    description="Web API for AI Coding Assistant",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Pydantic models
class ChatMessage(BaseModel):
    message: str
    conversation_id: Optional[str] = None


class FileReadRequest(BaseModel):
    file_path: str
    offset: Optional[int] = None
    limit: Optional[int] = None


class FileWriteRequest(BaseModel):
    file_path: str
    contents: str


class FileEditRequest(BaseModel):
    file_path: str
    old_string: str
    new_string: str
    replace_all: bool = False


class DiffRequest(BaseModel):
    diff_text: str
    dry_run: bool = False


class ValidateDiffRequest(BaseModel):
    diff_text: str
    file_path: Optional[str] = None


class CompletionRequest(BaseModel):
    file_path: str
    file_content: str
    cursor_line: int
    cursor_column: int
    language: str = "python"


class ComposerRequest(BaseModel):
    """Request for multi-file editing via Composer"""
    query: str
    files: Optional[List[str]] = None  # Specific files to edit, None = all relevant
    context: Optional[str] = None  # Additional context
    model: Optional[str] = None  # Model override


class GitStageRequest(BaseModel):
    files: List[str]


class GitUnstageRequest(BaseModel):
    files: List[str]


class GitCommitRequest(BaseModel):
    message: str
    files: Optional[List[str]] = None
    generate_message: bool = False


class GitBranchRequest(BaseModel):
    branch: str
    create: bool = False


class RulesSaveRequest(BaseModel):
    content: str


# REST API Endpoints

@app.get("/")
async def root():
    """Health check"""
    return {
        "status": "ok",
        "service": "AI Coding Assistant API",
        "version": "1.0.0"
    }


@app.get("/api/health")
async def get_health():
    """Quick health check endpoint that responds immediately"""
    try:
        # Check if assistant is initialized
        assistant_ready = assistant is not None
        
        # Check RAG status
        rag_status = "not_indexed"
        if assistant and assistant.rag_system:
            try:
                rag_stats = assistant.rag_system.get_index_stats()
                if rag_stats.get("indexed", False):
                    rag_status = "indexed"
                elif hasattr(assistant.rag_system, '_index_lock') and assistant.rag_system._index_lock.locked():
                    rag_status = "indexing"
            except Exception:
                pass
        
        # Check service availability
        services = {
            "git": git_service is not None and (git_service.is_repo if git_service else False),
            "rules": assistant is not None and hasattr(assistant, 'rules_engine') and assistant.rules_engine is not None,
            "performance": assistant is not None and hasattr(assistant, 'performance_monitor') and assistant.performance_monitor is not None
        }
        
        return {
            "status": "ready" if assistant_ready else "initializing",
            "assistant_ready": assistant_ready,
            "rag_status": rag_status,
            "services": services,
            "timestamp": time.time()
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        }


@app.get("/api/status")
async def get_status():
    """Get system status"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    # Determine active model based on configuration
    if Config.USE_HYBRID_MODELS:
        # Hybrid mode - show available models
        available_models = []
        if assistant.deepseek_provider:
            available_models.append(Config.DEEPSEEK_MODEL)
        if assistant.anthropic_provider:
            available_models.append(Config.ANTHROPIC_MODEL)
        if assistant.openai_provider:
            available_models.append(Config.OPENAI_MODEL)
        
        model_info = f"Hybrid Mode: {', '.join(available_models) if available_models else 'None configured'}"
        default_model = Config.DEEPSEEK_MODEL if assistant.deepseek_provider else (Config.ANTHROPIC_MODEL if assistant.anthropic_provider else Config.OPENAI_MODEL)
    else:
        # Single model mode
        if Config.DEFAULT_PROVIDER == "deepseek" and assistant.deepseek_provider:
            default_model = Config.DEEPSEEK_MODEL
        elif Config.DEFAULT_PROVIDER == "anthropic" and assistant.anthropic_provider:
            default_model = Config.ANTHROPIC_MODEL
        else:
            default_model = Config.OPENAI_MODEL
        model_info = default_model
    
    stats = {
        "assistant_ready": assistant is not None,
        "rag_enabled": assistant.rag_system is not None if assistant else False,
        "rag_indexed": False,
        "model": default_model,
        "model_info": model_info,
        "hybrid_mode": Config.USE_HYBRID_MODELS,
        "available_providers": {
            "deepseek": assistant.deepseek_provider is not None,
            "anthropic": assistant.anthropic_provider is not None,
            "openai": assistant.openai_provider is not None
        }
    }
    
    if assistant and assistant.rag_system:
        try:
            rag_stats = assistant.rag_system.get_index_stats()
            stats["rag_indexed"] = rag_stats.get("indexed", False)
            stats["rag_chunks"] = rag_stats.get("total_chunks", 0)
        except Exception as e:
            safe_debug_log("app.py:get_status", "Silent exception in get_status", {
                "error_type": type(e).__name__,
                "error_message": str(e)
            })
            pass
    
    return stats


@app.post("/api/chat")
async def chat(message: ChatMessage):
    """Process chat message (synchronous)"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        response = assistant.process_message(message.message)
        return {
            "response": response,
            "success": True
        }
    except Exception as e:
        return {
            "response": f"Error: {str(e)}",
            "success": False,
            "error": str(e)
        }


@app.get("/api/files")
async def list_files(directory: str = "."):
    """List files in directory"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        result = assistant.file_ops.list_directory(directory)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/read")
async def read_file(request: FileReadRequest):
    """Read a file"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        result = assistant.file_ops.read_file(
            request.file_path,
            offset=request.offset,
            limit=request.limit
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/write")
async def write_file(request: FileWriteRequest):
    """Write a file"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        result = assistant.file_ops.write_file(request.file_path, request.contents)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/files/edit")
async def edit_file(request: FileEditRequest):
    """Edit a file"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        result = assistant.file_ops.search_replace(
            request.file_path,
            request.old_string,
            request.new_string,
            replace_all=request.replace_all
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/diff/preview")
async def preview_diff(request: DiffRequest):
    """Preview a diff"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        result = assistant.diff_editor.preview_diff(request.diff_text)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/diff/apply")
async def apply_diff(request: DiffRequest):
    """Apply a diff"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        # Parse diff text into FileDiff objects
        file_diffs = assistant.diff_editor.parse_diff(request.diff_text)
        # Apply the parsed diffs
        result = assistant.diff_editor.apply_diffs(file_diffs, dry_run=request.dry_run)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/diff/validate")
async def validate_diff(request: ValidateDiffRequest):
    """Validate a diff before applying"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        is_valid, error_message, validation_results = assistant.diff_editor.validate_diff(
            request.diff_text,
            use_validation_service=True
        )
        
        return {
            "is_valid": is_valid,
            "error_message": error_message,
            "validation_results": validation_results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/debug")
async def debug_codebase(
    auto_fix: bool = True,
    file_pattern: Optional[str] = None,
    max_files: Optional[int] = None
):
    """
    Debug entire codebase - scan, detect bugs, and optionally auto-fix
    
    Args:
        auto_fix: If True, automatically fix detected bugs
        file_pattern: Optional pattern to filter files (e.g., "*.py")
        max_files: Maximum number of files to analyze
        
    Returns:
        Dict with scan results, bugs found, and fixes applied
    """
    if not assistant or not assistant.debug_mode:
        raise HTTPException(status_code=503, detail="Debug mode not available")
    
    try:
        results = assistant.debug_mode.debug_codebase(
            auto_fix=auto_fix,
            file_pattern=file_pattern,
            max_files=max_files
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/debug/file")
async def debug_file(
    file_path: str,
    auto_fix: bool = True
):
    """
    Debug a single file
    
    Args:
        file_path: Path to file to debug
        auto_fix: If True, automatically fix bugs
        
    Returns:
        Dict with bugs found and fixes applied
    """
    if not assistant or not assistant.debug_mode:
        raise HTTPException(status_code=503, detail="Debug mode not available")
    
    try:
        results = assistant.debug_mode.debug_file(file_path, auto_fix=auto_fix)
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class InteractiveDebugRequest(BaseModel):
    """Request for interactive debugging"""
    bug_description: str
    error_text: Optional[str] = None
    file_path: Optional[str] = None


@app.post("/api/debug/interactive")
async def interactive_debug(request: InteractiveDebugRequest):
    """
    Start interactive debugging session (Cursor AI-style)
    Generates hypotheses, instruments code, and collects runtime data
    
    Args:
        bug_description: User's description of the bug
        error_text: Optional error message/stack trace
        file_path: Optional file where bug occurs
        
    Returns:
        Dict with session info and hypotheses
    """
    if not assistant or not assistant.debug_mode:
        raise HTTPException(status_code=503, detail="Debug mode not available")
    
    try:
        results = assistant.interactive_debug(
            bug_description=request.bug_description,
            error_text=request.error_text,
            file_path=request.file_path
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/composer")
async def composer_edit(request: ComposerRequest):
    """
    Multi-file editing via Composer.
    Processes a query and generates diffs for multiple files.
    """
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        # Build query with context
        full_query = request.query
        if request.context:
            full_query = f"{request.query}\n\nContext: {request.context}"
        
        if request.files:
            full_query += f"\n\nFiles to edit: {', '.join(request.files)}"
        
        # Process the query through assistant
        conversation_history = []  # Could be enhanced with session management
        
        # Get RAG context if available
        rag_context = ""
        if assistant.rag_system and assistant.rag_system.is_indexed:
            try:
                rag_context = assistant.rag_system.get_context_for_query(
                    request.query,
                    use_hybrid=True
                )
            except Exception as e:
                print(f"[WARN] RAG retrieval error: {e}")
        
        # Determine which LLM provider to use
        provider = assistant.openai_provider
        model_name = Config.OPENAI_MODEL
        
        if Config.USE_HYBRID_MODELS:
            task_info = assistant.task_classifier.classify(full_query, conversation_history)
            provider_name = task_info["provider"]
            model_name = task_info["model"]
            
            if provider_name == "deepseek" and assistant.deepseek_provider:
                provider = assistant.deepseek_provider
            elif provider_name == "anthropic" and assistant.anthropic_provider:
                provider = assistant.anthropic_provider
        
        # Build system prompt for multi-file editing
        system_prompt = assistant.system_prompt + """
        
You are now in Composer mode for multi-file editing. When the user requests changes across multiple files:
1. Generate unified diffs for ALL affected files
2. Use the format: ```diff\n<unified diff>\n```
3. Include file headers (--- a/path, +++ b/path) for each file
4. Be comprehensive - show all changes needed
5. Do NOT ask for confirmation - just generate the diffs
"""
        
        if rag_context:
            system_prompt += f"\n\n<codebase_context>\n{rag_context}\n</codebase_context>"
        
        # Use context manager
        session_id = getattr(assistant, '_session_id', None)
        context_result = assistant.context_manager.assemble_context(
            user_message=full_query,
            conversation_history=conversation_history,
            rag_context=rag_context,
            system_prompt=system_prompt,
            model=model_name,
            session_id=session_id
        )
        
        messages = context_result["messages"]
        
        # Call LLM
        response = provider.chat_completion(
            messages=messages,
            model=model_name,
            temperature=Config.OPENAI_TEMPERATURE,
            max_tokens=Config.MAX_TOKENS * 2  # More tokens for multi-file edits
        )
        
        assistant_message = response.content
        
        # Extract diffs from response
        diffs = assistant.diff_extractor.extract_diffs(assistant_message)
        
        if not diffs:
            return {
                "success": False,
                "error": "No diffs found in response",
                "response": assistant_message
            }
        
        # Parse diffs to get file list
        file_diffs = []
        for diff_text in diffs:
            parsed = assistant.diff_editor.parse_diff(diff_text)
            file_diffs.extend(parsed)
        
        # Preview diffs (dry run)
        preview_results = []
        for file_diff in file_diffs:
            preview = assistant.diff_editor.apply_diff(file_diff, dry_run=True)
            preview_results.append({
                "file": file_diff.new_path,
                "old_path": file_diff.old_path,
                "hunks": len(file_diff.hunks),
                "preview": preview
            })
        
        return {
            "success": True,
            "diffs": diffs,
            "files": [fd.new_path for fd in file_diffs],
            "file_diffs": [
                {
                    "file": fd.new_path,
                    "old_path": fd.old_path,
                    "hunks": len(fd.hunks)
                }
                for fd in file_diffs
            ],
            "preview": preview_results,
            "response": assistant_message
        }
    
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


@app.post("/api/search")
async def search(query: str, search_type: str = "semantic"):
    """Search codebase"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        if search_type == "semantic":
            result = assistant.codebase_search.semantic_search(query)
        elif search_type == "grep":
            result = assistant.codebase_search.grep(query)
        else:
            result = assistant.codebase_search.semantic_search(query)
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/index")
async def index_codebase(force: bool = False):
    """Index codebase for RAG (non-blocking)"""
    if not assistant or not assistant.rag_system:
        raise HTTPException(status_code=503, detail="RAG system not available")
    
    try:
        # Check if already indexing
        if hasattr(assistant.rag_system, '_index_lock'):
            if assistant.rag_system._index_lock.locked():
                return {
                    "status": "already_indexing",
                    "message": "Indexing is already in progress"
                }
        
        # Run indexing in background thread (non-blocking)
        import threading
        def index_background():
            try:
                assistant.rag_system.index_codebase(force_reindex=force)
                print("[OK] RAG indexing completed")
            except Exception as e:
                print(f"[WARN] Background indexing failed: {e}")
        
        index_thread = threading.Thread(target=index_background, daemon=True)
        index_thread.start()
        
        # Return immediately
        return {
            "status": "started",
            "message": "Indexing started in background"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/stats")
async def get_stats():
    """Get usage statistics"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    stats = {
        "cost": assistant.cost_tracker.get_stats(),
        "rag": {},
        "performance": {}
    }
    
    if assistant.rag_system:
        try:
            rag_stats = assistant.rag_system.get_index_stats()
            stats["rag"] = rag_stats
        except Exception as e:
            safe_debug_log("app.py:get_stats", "Silent exception in get_stats", {
                "error_type": type(e).__name__,
                "error_message": str(e)
            })
            pass
    
    if assistant.performance_monitor:
        try:
            stats["performance"] = assistant.performance_monitor.get_current_stats()
        except Exception as e:
            print(f"[WARN] Error getting performance stats: {e}")
    
    return stats


# Git API Endpoints

@app.get("/api/git/status")
async def get_git_status():
    """Get repository status"""
    if not git_service:
        raise HTTPException(status_code=503, detail="Git service not initialized")
    
    try:
        # Use asyncio timeout to prevent hanging
        status = await asyncio.wait_for(
            asyncio.to_thread(git_service.get_status),
            timeout=5.0
        )
        return status
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Git status retrieval timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/git/stage")
async def stage_files(request: GitStageRequest):
    """Stage files"""
    if not git_service:
        raise HTTPException(status_code=503, detail="Git service not initialized")
    
    try:
        result = git_service.stage_files(request.files)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/git/unstage")
async def unstage_files(request: GitUnstageRequest):
    """Unstage files"""
    if not git_service:
        raise HTTPException(status_code=503, detail="Git service not initialized")
    
    try:
        result = git_service.unstage_files(request.files)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/git/commit")
async def create_commit(request: GitCommitRequest):
    """Create commit"""
    if not git_service:
        raise HTTPException(status_code=503, detail="Git service not initialized")
    
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        commit_message = request.message
        
        # Generate commit message if requested
        if request.generate_message:
            staged_status = git_service.get_status()
            staged_files = [f["path"] for f in staged_status.get("staged", [])]
            
            if staged_files:
                generated_message = assistant.generate_commit_message(staged_files)
                if generated_message:
                    commit_message = generated_message
        
        result = git_service.commit(commit_message, request.files)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/git/branches")
async def get_branches():
    """Get all branches"""
    if not git_service:
        raise HTTPException(status_code=503, detail="Git service not initialized")
    
    try:
        branches = git_service.get_branches()
        return branches
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/git/branch")
async def switch_branch(request: GitBranchRequest):
    """Switch or create branch"""
    if not git_service:
        raise HTTPException(status_code=503, detail="Git service not initialized")
    
    try:
        if request.create:
            result = git_service.create_branch(request.branch)
        else:
            result = git_service.switch_branch(request.branch)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/git/diff")
async def get_git_diff(file_path: Optional[str] = None, staged: bool = False):
    """Get diff for file or all changes"""
    if not git_service:
        raise HTTPException(status_code=503, detail="Git service not initialized")
    
    try:
        result = git_service.get_diff(file_path, staged)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/git/history")
async def get_commit_history(limit: int = 10):
    """Get recent commit history"""
    if not git_service:
        raise HTTPException(status_code=503, detail="Git service not initialized")
    
    try:
        history = git_service.get_commit_history(limit)
        return {"commits": history}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Rules API Endpoints

@app.get("/api/rules")
async def get_rules():
    """Get current rules content"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        if not hasattr(assistant, 'rules_engine') or not assistant.rules_engine:
            return {"exists": False, "content": "", "info": {}}
        
        rules_engine = assistant.rules_engine
        
        # Use asyncio timeout to prevent hanging
        def get_rules_data():
            content = rules_engine.get_rules()
            info = rules_engine.get_rules_info()
            return content, info
        
        content, info = await asyncio.wait_for(
            asyncio.to_thread(get_rules_data),
            timeout=3.0
        )
        
        return {
            "exists": info["exists"],
            "content": content or "",
            "info": info
        }
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Rules retrieval timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rules")
async def save_rules(request: RulesSaveRequest):
    """Save rules to .cursorrules file"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        if not hasattr(assistant, 'rules_engine') or not assistant.rules_engine:
            raise HTTPException(status_code=503, detail="Rules engine not initialized")
        
        result = assistant.rules_engine.save_rules(request.content)
        
        # Reload system prompt with new rules
        if hasattr(assistant, '_get_system_prompt'):
            assistant.system_prompt = assistant._get_system_prompt()
        
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/rules/validate")
async def validate_rules(request: RulesSaveRequest):
    """Validate rules content"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        if not hasattr(assistant, 'rules_engine') or not assistant.rules_engine:
            raise HTTPException(status_code=503, detail="Rules engine not initialized")
        
        validation = assistant.rules_engine.validate_rules(request.content)
        return validation
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/rules/preview")
async def preview_rules():
    """Get preview of merged prompt with rules"""
    if not assistant:
        raise HTTPException(status_code=503, detail="Assistant not initialized")
    
    try:
        # Get base prompt without rules
        if hasattr(assistant, '_get_system_prompt'):
            base_prompt = assistant._get_system_prompt()
        else:
            base_prompt = assistant.system_prompt
        
        # If rules exist, show merged version
        if hasattr(assistant, 'rules_engine') and assistant.rules_engine and assistant.rules_engine.rules_loaded:
            merged_prompt = assistant.rules_engine.inject_into_prompt(base_prompt)
            return {
                "base_prompt": base_prompt,
                "merged_prompt": merged_prompt,
                "has_rules": True
            }
        else:
            return {
                "base_prompt": base_prompt,
                "merged_prompt": base_prompt,
                "has_rules": False
            }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/performance")
async def get_performance():
    """Get detailed performance metrics"""
    if not assistant or not assistant.performance_monitor:
        raise HTTPException(status_code=503, detail="Performance monitor not available")
    
    try:
        # Use asyncio timeout to prevent hanging
        summary = await asyncio.wait_for(
            asyncio.to_thread(assistant.performance_monitor.get_summary),
            timeout=5.0
        )
        return summary
    except asyncio.TimeoutError:
        raise HTTPException(status_code=504, detail="Performance data retrieval timed out")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/performance/history")
async def get_performance_history(metric_type: Optional[str] = None, hours: int = 24):
    """Get historical performance metrics"""
    if not assistant or not assistant.performance_monitor:
        raise HTTPException(status_code=503, detail="Performance monitor not available")
    
    try:
        return assistant.performance_monitor.get_historical_stats(
            metric_type=metric_type,
            hours=hours
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/performance/indexing")
async def get_indexing_history():
    """Get indexing performance history"""
    if not assistant or not assistant.performance_monitor:
        raise HTTPException(status_code=503, detail="Performance monitor not available")
    
    try:
        return assistant.performance_monitor.get_indexing_history()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/completion")
async def get_completions(request: CompletionRequest):
    """Get code completions for cursor position"""
    if not completion_engine:
        raise HTTPException(status_code=503, detail="Completion engine not initialized")
    
    try:
        completions = completion_engine.get_completions(
            file_path=request.file_path,
            file_content=request.file_content,
            cursor_line=request.cursor_line,
            cursor_column=request.cursor_column,
            language=request.language,
            max_completions=10
        )
        
        # Convert to API format
        result = []
        for comp in completions:
            result.append({
                "label": comp.label,
                "kind": comp.kind,
                "detail": comp.detail,
                "documentation": comp.documentation,
                "insertText": comp.insert_text or comp.text,
                "score": comp.score
            })
        
        return {
            "completions": result,
            "success": True
        }
    except Exception as e:
        return {
            "completions": [],
            "success": False,
            "error": str(e)
        }


# WebSocket for real-time chat
@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """WebSocket endpoint for real-time chat"""
    # #region agent log
    safe_debug_log("app.py:websocket_chat", "WebSocket connection accepted", {
        "has_assistant": assistant is not None
    })
    # #endregion
    await websocket.accept()
    active_connections.append(websocket)
    
    # Generate session ID for memory management
    import uuid
    session_id = str(uuid.uuid4())
    
    # Set session ID on assistant for memory management
    if assistant:
        assistant.set_session_id(session_id)
    
    # Maintain conversation history per WebSocket connection
    conversation_history = []
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
            except json.JSONDecodeError as e:
                await websocket.send_json({
                    "type": "error",
                    "message": f"Invalid JSON: {str(e)}"
                })
                continue
            
            user_message = message_data.get("message", "")
            model_override = message_data.get("model")  # Get model selection from client
            
            if not assistant:
                await websocket.send_json({
                    "type": "error",
                    "message": "Assistant not initialized"
                })
                continue
            
            # Send typing indicator
            await websocket.send_json({
                "type": "typing",
                "status": True
            })
            
            try:
                # Process message with conversation history and optional model override
                response = assistant.process_message(
                    user_message, 
                    conversation_history=conversation_history,
                    model_override=model_override
                )
                
                # Determine which model was actually used
                used_model = model_override if model_override else 'auto'
                
                # Update conversation history (context manager will handle truncation/summarization)
                conversation_history.append({"role": "user", "content": user_message})
                conversation_history.append({"role": "assistant", "content": response})
                # Note: Context manager handles token limits and summarization automatically
                
                # Send response with model info
                await websocket.send_json({
                    "type": "message",
                    "response": response,
                    "model": used_model,
                    "success": True
                })
            except Exception as e:
                safe_debug_log("app.py:process_message", "Exception in process_message", {
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                })
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "success": False
                })
            finally:
                # Stop typing indicator
                await websocket.send_json({
                    "type": "typing",
                    "status": False
                })
    
    except WebSocketDisconnect:
        safe_debug_log("app.py:websocket_chat", "WebSocket disconnected", {})
        active_connections.remove(websocket)
    except Exception as e:
        safe_debug_log("app.py:websocket_chat", "WebSocket exception", {
            "error_type": type(e).__name__,
            "error_message": str(e)
        })
        if websocket in active_connections:
            active_connections.remove(websocket)
        print(f"WebSocket error: {e}")


# WebSocket for real-time completions
@app.websocket("/ws/completion")
async def websocket_completion(websocket: WebSocket):
    """WebSocket endpoint for real-time code completions"""
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message_data = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
                continue
            
            if not completion_engine:
                await websocket.send_json({
                    "type": "error",
                    "message": "Completion engine not initialized"
                })
                continue
            
            # Extract request data
            file_path = message_data.get("file_path", "")
            file_content = message_data.get("file_content", "")
            cursor_line = message_data.get("cursor_line", 0)
            cursor_column = message_data.get("cursor_column", 0)
            language = message_data.get("language", "python")
            
            try:
                # Get completions
                completions = completion_engine.get_completions(
                    file_path=file_path,
                    file_content=file_content,
                    cursor_line=cursor_line,
                    cursor_column=cursor_column,
                    language=language,
                    max_completions=10
                )
                
                # Convert to API format
                result = []
                for comp in completions:
                    result.append({
                        "label": comp.label,
                        "kind": comp.kind,
                        "detail": comp.detail,
                        "documentation": comp.documentation,
                        "insertText": comp.insert_text or comp.text,
                        "score": comp.score
                    })
                
                await websocket.send_json({
                    "type": "completions",
                    "completions": result,
                    "success": True
                })
            except Exception as e:
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                    "success": False
                })
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Completion WebSocket error: {e}")


# WebSocket for terminal
@app.websocket("/ws/terminal")
async def websocket_terminal(websocket: WebSocket):
    """WebSocket endpoint for terminal"""
    await websocket.accept()
    
    import uuid
    session_id = None
    workspace_path = os.getenv("WORKSPACE_PATH", ".")
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON"
                })
                continue
            
            if message.get("type") == "init":
                session_id = message.get("session_id", str(uuid.uuid4()))
                workspace_path = message.get("workspace_path", workspace_path)
                await websocket.send_json({
                    "type": "ready",
                    "session_id": session_id
                })
            
            elif message.get("type") == "command":
                command = message.get("command", "").strip()
                if not command:
                    # Empty command, just send prompt
                    await websocket.send_json({
                        "type": "output",
                        "data": "\r\n$ "
                    })
                    continue
                
                # Execute command
                try:
                    from tools.terminal import Terminal
                    terminal = Terminal(workspace_path=workspace_path)
                    
                    # Execute and get output
                    result = terminal.execute(command, is_background=False)
                    
                    # Send output (stdout and stderr combined)
                    output = ""
                    if result.get("stdout"):
                        output += result["stdout"]
                    if result.get("stderr"):
                        output += result["stderr"]
                    
                    if output:
                        await websocket.send_json({
                            "type": "output",
                            "data": output
                        })
                    
                    # Send exit code
                    await websocket.send_json({
                        "type": "exit",
                        "code": result.get("returncode", 0)
                    })
                    
                    # Send prompt for next command
                    await websocket.send_json({
                        "type": "output",
                        "data": "\r\n$ "
                    })
                    
                except Exception as e:
                    await websocket.send_json({
                        "type": "error",
                        "message": str(e)
                    })
                    await websocket.send_json({
                        "type": "output",
                        "data": "\r\n$ "
                    })
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"Terminal WebSocket error: {e}")


if __name__ == "__main__":
    import uvicorn
    import os
    # Use port from environment or default to 8001
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)
