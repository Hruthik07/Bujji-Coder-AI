# Bujji Coder AI

An intelligent coding assistant that actually understands your codebase. Think of it as having a senior developer pair-programming with you, but powered by advanced AI models that never get tired and remember everything.

## What is This?

I built Bujji Coder AI because I was frustrated with existing AI coding assistants. They either lost context after a few messages, couldn't understand code structure, or were locked into a single expensive model. So I decided to build something better.

This combines multiple AI models with deep codebase understanding using Retrieval-Augmented Generation (RAG). When you ask it to refactor a function, it actually knows what other parts of your code depend on it. It's not just pattern matching—it understands the relationships in your code.

## What Makes This Different?

### Advanced Memory Management
Most AI assistants hit a wall after 20-30 messages. I solved this with:
- **Persistent Memory Database**: SQLite stores conversation summaries and key facts across sessions
- **Progressive Summarization**: Automatically compresses old messages while preserving critical info
- **Facts Extraction**: Extracts structured facts (files created, decisions made) and injects them into future conversations
- **Cross-Session Memory**: Remembers context from previous sessions

### Intelligent Hybrid Model System
Instead of paying premium prices for simple tasks, I built automatic routing:
- **DeepSeek Coder** for code generation (fast, cheap, specialized)
- **Claude Sonnet 3.5** for complex reasoning and architecture decisions
- **OpenAI GPT** as reliable fallback
- Automatically picks the best model for each task

### Multi-Agent Architecture
Specialized agents work together:
- **Retrieval Agent**: Finds relevant code via semantic search
- **Planning Agent**: Breaks down complex tasks into steps
- **Validation Agent**: Verifies changes before applying

### AST-Aware Code Understanding
Unlike text-based assistants, this uses Abstract Syntax Tree parsing to understand code structure, track dependencies, and make refactoring suggestions that respect your architecture.

### Performance Optimized
- Parallel file processing (indexes large codebases in seconds)
- Intelligent caching with LRU eviction
- Batch processing for embeddings
- Real-time performance monitoring

### Advanced Debugging
- Static analysis with AST syntax checking
- Runtime debugging with safe execution
- Auto-fixing common bugs
- Hypothesis generation with confidence scores

### Pre-Apply Validation
Validates code changes before applying:
- Syntax checking
- Linter integration (flake8)
- Type checking
- Pre-apply warnings

### Why This Beats Other Solutions

| Feature | Bujji-Coder-AI | Others |
|---------|----------------|--------|
| Memory Management | ✅ Persistent DB, cross-session | ❌ Conversation window only |
| Model Selection | ✅ Hybrid (DeepSeek + Claude + GPT) | ❌ Single model |
| Code Understanding | ✅ AST-aware | ⚠️ Text-based |
| Context Window | ✅ Up to 150K tokens | ⚠️ 8K-32K |
| Multi-File Editing | ✅ Composer with dependencies | ⚠️ Limited |
| Debugging | ✅ Static + runtime + auto-fix | ⚠️ Basic |
| Validation | ✅ Pre-apply checks | ⚠️ Post-apply |
| Performance | ✅ Parallel + caching | ⚠️ Sequential |
| Cost Tracking | ✅ Real-time monitoring | ❌ Not available |
| Git Integration | ✅ Full support + AI commits | ⚠️ Basic |
| Web Interface | ✅ Modern React + Monaco | ⚠️ CLI/basic |

## Internal Architecture

### System Overview

```
User Interface (Web/CLI) 
    ↓
CodingAssistant (Orchestrator)
    ├── Task Classifier → Routes to best model
    ├── Context Manager → Assembles context intelligently
    ├── RAG System → Codebase understanding
    ├── Multi-Agent System → Specialized agents
    └── Memory System → Persistent storage
```

### Core Components

**CodingAssistant**: Main orchestrator that coordinates everything. When you send a message:
1. Task classification determines the task type
2. Model routing selects the best LLM (DeepSeek/Claude/GPT)
3. Context assembly loads RAG context, facts, and conversation history
4. Multi-agent coordination delegates to specialized agents for complex tasks

**RAG System**: Understands your codebase through:
- **AST Parsing**: Extracts code structure (functions, classes, dependencies)
- **Intelligent Chunking**: Splits code into semantic chunks, not arbitrary text
- **Vector Embeddings**: Uses OpenAI embeddings for semantic search
- **ChromaDB Storage**: Vector database with metadata (file paths, line numbers)
- **Parallel Processing**: ThreadPoolExecutor processes multiple files simultaneously
- **Code Graph**: Tracks function calls, imports, and symbol references

**Memory Management**: Multi-layered system:
- **ContextManager**: Orchestrates context assembly, manages token limits per model, triggers summarization
- **ConversationSummarizer**: Compresses old messages using Claude, preserves key info
- **FactsExtractor**: Extracts structured facts (files created, decisions made)
- **MemoryDB**: SQLite storage for persistent memory across sessions
- **SessionManager**: Manages conversation sessions and cross-session memory

**Multi-Agent System**: Specialized agents:
- **RetrievalAgent**: Semantic search in codebase
- **PlanningAgent**: Breaks down tasks, identifies dependencies
- **ValidationAgent**: Syntax checks, linting, type validation

**LLM Provider Abstraction**: Unified interface for multiple providers with intelligent routing and cost tracking.

**Code Completion Engine**: Combines AST analysis, RAG retrieval, language keywords, and LLM generation, then merges and ranks by relevance.

**Debugging System**: Multi-layer approach with static analysis, runtime debugging, auto-fixing, and interactive step-by-step guidance.

### Data Flow Example

When you ask "Add error handling to the login function":
1. Request received → Task classified → Routed to DeepSeek
2. RAG retrieves login function + related code
3. Context assembled (system prompt + RAG + facts + history)
4. LLM generates diff → Validation (syntax + linter)
5. Diff applied → Memory updated → Response sent

### Technology Stack

**Backend**: FastAPI, ChromaDB, SQLite, GitPython, ThreadPoolExecutor, WebSocket  
**Frontend**: React, Monaco Editor, xterm.js  
**AI/ML**: OpenAI API, Anthropic API, DeepSeek API, Vector embeddings, tiktoken  
**Tools**: AST parsing, Diff-based editing, Rich, Pydantic

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+ (for web interface)
- OpenAI API key (required)
- Anthropic API key (optional, recommended)
- DeepSeek API key (optional, recommended)

### Installation

```bash
# Clone repository
git clone https://github.com/Hruthik07/Bujji-Coder-AI.git
cd Bujji-Coder-AI

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd web/frontend && npm install && cd ../..

# Set up environment
cp .env.example .env
# Edit .env and add your API keys
```

### Running

**CLI:**
```bash
python main.py
```

**Web Interface (Recommended):**
```bash
# Terminal 1: Backend
cd web/backend && python app.py

# Terminal 2: Frontend
cd web/frontend && npm start

# Open http://localhost:3001
```

## Usage

### Basic
```python
from assistant import CodingAssistant

assistant = CodingAssistant(workspace_path=".")
response = assistant.process_message("Add error handling to login function")
print(response)
```

### Web Interface
- Chat with assistant for questions and code changes
- Browse codebase with file tree
- Edit files in Monaco editor
- Use Composer for multi-file editing
- Review diffs before applying
- Git panel for staging and commits

### Debugging
```python
# Debug entire codebase
results = assistant.debug_codebase(auto_fix=True)

# Debug specific file
results = assistant.debug_file("src/auth.py", auto_fix=True)
```

### Project Rules
Create `.cursorrules` in project root for coding standards and architecture preferences.

## Project Structure

```
Bujji-Coder-AI/
├── assistant.py              # Main orchestrator
├── config.py                 # Configuration
├── tools/                    # Core modules
│   ├── rag_system.py         # RAG implementation
│   ├── code_completion.py    # Autocomplete
│   ├── debug_mode.py         # Debugging
│   ├── context_manager.py    # Memory management
│   └── multi_agent.py        # Multi-agent system
└── web/                      # Web interface
    ├── backend/              # FastAPI
    └── frontend/             # React
```

## Configuration

Configure via `.env` file (see `.env.example`):
- Model selection and routing
- Context window sizes
- RAG settings
- Performance tuning
- Memory management

## Documentation

- [Hybrid Model Setup](docs/HYBRID_MODEL_SETUP.md)
- [Memory System](docs/MEMORY_SYSTEM_SUMMARY.md)
- [Gap Analysis](docs/CURSOR_AI_GAP_ANALYSIS.md)
- [Improvement Plan](docs/CURSOR_AI_IMPROVEMENT_PLAN.md)

## Contributing

Contributions welcome! Please:
- Follow PEP 8 for Python
- Ensure tests pass
- Update documentation
- Write clear commit messages

## License

MIT License - see [LICENSE](LICENSE) file.

## Built With

OpenAI, Anthropic, DeepSeek, FastAPI, React, Monaco Editor, ChromaDB

---

**Questions?** Open an issue.  
**Found a bug?** Report it with details.  
**Feature idea?** Let's discuss!
