"""
Tools package for the AI Coding Assistant
"""
from .file_operations import FileOperations
from .codebase_search import CodebaseSearch
from .terminal import Terminal
from .ast_analyzer import ASTAnalyzer
from .diff_editor import DiffEditor
from .diff_extractor import DiffExtractor
from .code_graph import CodeGraphBuilder
from .error_parser import ErrorParser
from .error_debugger import ErrorDebugger
from .multi_agent import MultiAgentSystem

try:
    from .rag_system import RAGSystem
    from .incremental_indexer import IncrementalIndexer
    from .cache import Cache
    from .logger import Logger, get_logger
    from .retry import retry, retry_api_call
    from .llm_provider import LLMProvider, get_provider, OpenAIProvider, DeepSeekProvider, AnthropicProvider
    from .task_classifier import TaskClassifier
    from .context_manager import ContextManager
    from .token_counter import TokenCounter
    from .conversation_summarizer import ConversationSummarizer
    from .facts_extractor import FactsExtractor, Fact
    from .memory_db import MemoryDB
    from .code_completion import CodeCompletionEngine, CompletionCandidate
    from .code_scanner import CodeScanner
    from .bug_detector import BugDetector, Bug
    from .auto_fixer import AutoFixer
    from .debug_mode import DebugMode
    from .code_instrumentation import CodeInstrumentation
    from .hypothesis_generator import HypothesisGenerator, Hypothesis
    from .runtime_debugger import RuntimeDebugger
    from .interactive_debug_mode import InteractiveDebugMode
    from .performance_monitor import PerformanceMonitor, PerformanceMetric, IndexingStats, ResponseStats
    from .rules_engine import RulesEngine
    from .git_integration import GitService
    from .validation_service import ValidationService, ValidationResult, ValidationIssue, ValidationSeverity
    __all__ = ['FileOperations', 'CodebaseSearch', 'Terminal', 'ASTAnalyzer', 'RAGSystem', 
               'DiffEditor', 'DiffExtractor', 'IncrementalIndexer', 'CodeGraphBuilder',
               'ErrorParser', 'ErrorDebugger', 'MultiAgentSystem', 'Cache', 'Logger', 
               'get_logger', 'retry', 'retry_api_call', 'LLMProvider', 'get_provider',
               'OpenAIProvider', 'DeepSeekProvider', 'AnthropicProvider', 'TaskClassifier',
               'ContextManager', 'TokenCounter', 'ConversationSummarizer', 'FactsExtractor',
               'Fact', 'MemoryDB', 'CodeCompletionEngine', 'CompletionCandidate',
               'CodeScanner', 'BugDetector', 'Bug', 'AutoFixer', 'DebugMode',
               'CodeInstrumentation', 'HypothesisGenerator', 'Hypothesis', 'RuntimeDebugger',
               'InteractiveDebugMode', 'PerformanceMonitor', 'PerformanceMetric', 'IndexingStats', 'ResponseStats',
               'RulesEngine', 'GitService', 'ValidationService', 'ValidationResult', 'ValidationIssue', 'ValidationSeverity']
except ImportError:
    try:
        from .cache import Cache
        from .logger import Logger, get_logger
        from .retry import retry, retry_api_call
    except ImportError:
        Cache = None
        Logger = None
        get_logger = None
        retry = None
        retry_api_call = None
    
    __all__ = ['FileOperations', 'CodebaseSearch', 'Terminal', 'ASTAnalyzer', 
               'DiffEditor', 'DiffExtractor', 'CodeGraphBuilder', 'ErrorParser', 
               'ErrorDebugger', 'MultiAgentSystem']
    if Cache:
        __all__.extend(['Cache', 'Logger', 'get_logger', 'retry', 'retry_api_call'])
