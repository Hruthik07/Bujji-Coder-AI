# Bujji Coder AI

An intelligent coding assistant that actually understands your codebase. Think of it as having a senior developer pair-programming with you, but powered by advanced AI models that never get tired and remember everything.

## What is This?

I built Bujji Coder AI because I was frustrated with existing AI coding assistants. They either lost context after a few messages, couldn't understand code structure, or were locked into a single expensive model. So I decided to build something better.

This is a comprehensive development tool that combines multiple AI models with deep codebase understanding. It's designed to help developers write code faster, catch bugs earlier, and maintain better code quality—whether you're working on a small script or a massive enterprise application.

The core innovation here is using Retrieval-Augmented Generation (RAG) to understand your entire codebase context. When you ask it to refactor a function, it actually knows what other parts of your code depend on it. It's not just pattern matching—it understands the relationships in your code.

## What Makes This Different?

### The Memory Problem (And How I Solved It)

Most AI coding assistants hit a wall after 20-30 messages. They run out of context window and forget everything. I solved this with a multi-layered approach:

**Persistent Memory Database**: Instead of keeping everything in memory, I built a SQLite-based system that stores conversation summaries and key facts. The assistant remembers important decisions and context across sessions. Close the app, come back a week later, and it still knows your project structure.

**Progressive Summarization**: When approaching token limits, the system automatically summarizes old messages while preserving critical information. It's smart about what to keep verbatim (recent messages, important decisions) and what to compress.

**Facts Extraction**: The system extracts structured facts—files created, functions added, architectural decisions—and injects them into future conversations. This means the assistant maintains context even after hundreds of messages, something most competitors completely fail at.

### Hybrid Model System (Because One Size Doesn't Fit All)

I got tired of paying premium prices for simple code generation tasks. So I built an intelligent routing system that automatically picks the best model for each job:

- **DeepSeek Coder** handles code generation—it's fast, cheap, and specialized for code. Perfect for 90% of tasks.
- **Claude Sonnet 3.5** kicks in for complex reasoning, debugging, and architecture decisions. When you need deep thinking, you get it.
- **OpenAI GPT** serves as a reliable fallback.

The system analyzes each request and routes it intelligently. Simple code generation? DeepSeek. Need to explain why a complex refactoring is needed? Claude. This hybrid approach gives you the speed and cost-effectiveness of specialized models with the reasoning power of advanced models when you actually need it.

### Multi-Agent Architecture

I didn't want a single monolithic system trying to do everything. Instead, I built separate agents that work together:

- **Retrieval Agent**: Finds relevant code patterns and context from your codebase using semantic search
- **Planning Agent**: Breaks down complex tasks into actionable steps, understanding dependencies
- **Validation Agent**: Verifies code changes before applying them, catching issues early

This separation of concerns leads to more accurate results. Each agent is specialized, and they coordinate through a well-defined pipeline. It's like having a team of specialists instead of one generalist.

### AST-Aware Code Understanding

Most AI assistants treat code as plain text. That's fundamentally wrong. Code has structure—functions call other functions, classes inherit from other classes, imports create dependencies. I built AST (Abstract Syntax Tree) parsing into the core system so it actually understands code structure, not just text patterns.

This means the assistant can track dependencies and relationships between functions and classes. When you ask for a refactoring, it respects your code's architecture instead of blindly replacing text.

### Performance That Actually Matters

I optimized this for real-world use. Large codebases? No problem. The system uses parallel file processing with ThreadPoolExecutor to index codebases in seconds, not minutes. Intelligent caching with LRU eviction keeps frequently accessed data fast. Batch processing for embeddings is optimized to handle massive codebases efficiently.

There's also real-time performance monitoring—tracking indexing time, response time, memory usage, and API costs. You can see exactly what's happening under the hood.

### Debugging That Goes Beyond Error Messages

The debug mode isn't just error detection. It's a comprehensive system:
- Static analysis using AST to catch bugs before runtime
- Runtime debugging with safe code execution and instrumentation
- Auto-fixing common bugs using LLM-generated diffs
- Hypothesis generation—it creates multiple theories about what might be wrong with confidence scores
- Interactive step-by-step debugging guidance

### Validation Before You Commit

Before applying any code changes, the system validates them:
- Syntax checking (Python compile-time validation)
- Linter integration (flake8 for style and quality)
- Type checking and structure validation
- Pre-apply warnings so you see potential issues before committing to changes

This prevents the "apply and hope" workflow that other tools force on you.

### Why This Beats Other Solutions

| Feature | Bujji-Coder-AI | Other AI Assistants |
|---------|----------------|---------------------|
| **Memory Management** | ✅ Persistent database, cross-session memory | ❌ Limited to conversation window |
| **Model Selection** | ✅ Hybrid system (DeepSeek + Claude + GPT) | ❌ Single model locked-in |
| **Code Understanding** | ✅ AST-aware, understands structure | ⚠️ Mostly text-based |
| **Context Window** | ✅ Up to 150K tokens (Claude) with smart management | ⚠️ Usually limited to 8K-32K |
| **Multi-File Editing** | ✅ Composer with dependency analysis | ⚠️ Limited or manual |
| **Debugging** | ✅ Static + runtime with auto-fix | ⚠️ Basic error detection |
| **Validation** | ✅ Pre-apply syntax, linting, type checks | ⚠️ Post-apply only |
| **Performance** | ✅ Parallel processing, intelligent caching | ⚠️ Sequential, slower |
| **Cost Tracking** | ✅ Real-time API cost monitoring | ❌ Usually not available |
| **Git Integration** | ✅ Full Git support with AI commits | ⚠️ Basic or external |
| **Web Interface** | ✅ Modern React UI with Monaco Editor | ⚠️ CLI or basic UI |
| **Rules Engine** | ✅ Project-specific `.cursorrules` support | ⚠️ Limited customization |

## Internal Architecture

Understanding how this system works under the hood is important. Here's the architecture I designed:

### System Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interface Layer                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Web UI     │  │  CLI/API     │  │  WebSocket   │      │
│  │  (React)     │  │  (FastAPI)   │  │  (Real-time) │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                  Core Assistant Orchestrator                 │
│                    (CodingAssistant)                         │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Task Classifier → Model Router → Context Manager    │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│ RAG System   │  │ Multi-Agent  │  │ Memory Mgmt  │
│              │  │   System     │  │   System     │
└──────────────┘  └──────────────┘  └──────────────┘
```

### Core Components

#### 1. CodingAssistant (Orchestrator)

This is the main brain. It coordinates everything. When you send a message, here's what happens:

1. **Task Classification**: The `TaskClassifier` analyzes your request and determines what type of task it is (code generation, debugging, explanation, etc.)

2. **Model Routing**: Based on the task type, it routes to the appropriate LLM:
   - Code generation → DeepSeek Coder (fast, cheap)
   - Complex reasoning → Claude Sonnet (powerful, expensive)
   - Fallback → OpenAI GPT

3. **Context Assembly**: The `ContextManager` intelligently assembles context:
   - Loads relevant facts from the memory database
   - Retrieves code context via RAG
   - Manages conversation history with summarization
   - Respects model-specific token limits

4. **Multi-Agent Coordination**: For complex tasks, it delegates to specialized agents:
   - Retrieval Agent finds relevant code
   - Planning Agent breaks down the task
   - Validation Agent checks the result

#### 2. RAG System (Codebase Understanding)

The RAG (Retrieval-Augmented Generation) system is how the assistant understands your codebase:

**Indexing Pipeline**:
```
Code Files → AST Parsing → Chunking → Embedding → Vector Store
```

- **AST Parsing**: Uses Python's `ast` module to parse code structure, extracting functions, classes, imports, and dependencies
- **Intelligent Chunking**: Splits code into semantic chunks (functions, classes, blocks) rather than arbitrary text chunks
- **Embedding Generation**: Uses OpenAI's `text-embedding-3-small` to create vector embeddings
- **Vector Storage**: ChromaDB stores embeddings with metadata (file path, line numbers, symbol names)
- **Parallel Processing**: Uses ThreadPoolExecutor to process multiple files simultaneously

**Retrieval Process**:
When you ask a question, the system:
1. Embeds your query
2. Performs semantic search in the vector store
3. Retrieves top-K most relevant code chunks
4. Ranks by relevance and context
5. Returns code with metadata for the LLM

**Code Graph**: Beyond vector search, the system builds a code graph tracking:
- Function call relationships
- Import dependencies
- Class inheritance
- Symbol references

This graph enables understanding of code relationships, not just similarity.

#### 3. Memory Management System

This is one of the most sophisticated parts. The memory system has multiple layers:

**ContextManager**: Orchestrates context assembly
- Tracks token counts per model (different limits for different models)
- Triggers summarization when approaching limits
- Preserves recent messages verbatim
- Injects relevant facts from database

**ConversationSummarizer**: Compresses old messages
- Uses Claude (better at summarization) to create concise summaries
- Preserves key information (decisions, file changes, important context)
- Incremental updates (merges new messages into existing summaries)

**FactsExtractor**: Extracts structured information
- Identifies facts: "File X was created", "Function Y was added", "Decision Z was made"
- Stores in structured format for fast retrieval
- Updates incrementally as conversation progresses

**MemoryDB**: Persistent storage (SQLite)
- Stores conversation summaries
- Stores extracted facts
- Fast queries for relevant information
- Cross-session memory retrieval

**SessionManager**: Manages conversation sessions
- Tracks session boundaries
- Loads context from previous sessions
- Enables long-term memory across multiple sessions

#### 4. Multi-Agent System

Instead of one model trying to do everything, I built specialized agents:

**RetrievalAgent**:
- Takes user query
- Performs semantic search in RAG system
- Returns relevant code chunks with context
- Uses hybrid search (semantic + keyword) for better results

**PlanningAgent**:
- Analyzes the task complexity
- Breaks down into steps
- Identifies file dependencies
- Creates execution plan
- Uses LLM to understand task requirements

**ValidationAgent**:
- Validates code changes before applying
- Runs syntax checks
- Executes linters
- Performs type checking
- Returns warnings and errors

**Coordination**: The `MultiAgentSystem` orchestrates these agents:
```
User Request
    ↓
Retrieval Agent → Finds relevant code
    ↓
Planning Agent → Creates execution plan
    ↓
Code Generation (via LLM)
    ↓
Validation Agent → Checks result
    ↓
Apply or Reject
```

#### 5. LLM Provider Abstraction

I built a unified interface for multiple LLM providers:

**LLMProvider Interface**:
- Unified `chat_completion()` method
- Handles different API formats (OpenAI, Anthropic, DeepSeek)
- Manages rate limiting and retries
- Tracks costs per provider

**TaskClassifier**:
- Analyzes user message and conversation context
- Classifies task type (code generation, debugging, explanation, etc.)
- Routes to appropriate model
- Can be overridden manually

**Cost Tracking**:
- Real-time cost calculation per API call
- Tracks costs by model and provider
- Provides cost optimization suggestions

#### 6. Code Completion Engine

The autocomplete system combines multiple sources:

**AST Analysis**:
- Parses current file
- Understands context (function scope, class scope)
- Suggests based on code structure

**RAG Retrieval**:
- Finds similar code patterns in codebase
- Suggests completions based on existing code style

**Language Keywords**:
- Standard language completions
- Import suggestions
- Built-in function completions

**LLM Generation**:
- Generates context-aware completions
- Multi-line completions
- Respects code style

**Merging**: All sources are merged and ranked by relevance.

#### 7. Debugging System

The debugging system has multiple layers:

**CodeScanner**: Finds all code files in the workspace

**BugDetector**:
- Static analysis: AST syntax checking, pattern detection
- Import validation: Checks for missing imports
- Runtime checking: Safe code execution to catch runtime errors

**AutoFixer**:
- Uses LLM to generate fixes
- Applies fixes via diff editor
- Validates fixes before applying

**InteractiveDebugMode**:
- Step-by-step debugging
- Hypothesis generation (multiple theories about bugs)
- Code instrumentation for runtime analysis
- Safe execution environment

#### 8. Web Interface Architecture

**Backend (FastAPI)**:
- REST API for file operations, Git, rules management
- WebSocket for real-time chat and terminal
- Async request handling
- CORS middleware for frontend communication

**Frontend (React)**:
- Component-based architecture
- Monaco Editor for code editing
- WebSocket client for real-time updates
- State management for file tree, chat history, etc.

**Real-time Features**:
- WebSocket for chat (bidirectional communication)
- WebSocket for terminal (streaming output)
- Live status updates (RAG indexing, model selection)

### Data Flow Example

Here's what happens when you ask "Add error handling to the login function":

1. **Request Received** (WebSocket/API)
2. **Task Classification** → "Code modification task"
3. **Model Routing** → DeepSeek Coder (code generation)
4. **RAG Retrieval** → Finds login function and related code
5. **Context Assembly**:
   - System prompt
   - RAG context (login function + related code)
   - Relevant facts from memory DB
   - Recent conversation history
6. **LLM Call** → DeepSeek generates diff
7. **Validation** → Syntax check, linter check
8. **Diff Application** → Applies changes to file
9. **Memory Update** → Stores fact: "Error handling added to login function"
10. **Response** → Returns success message with changes

### Performance Optimizations

I spent significant time optimizing performance:

**Parallel Processing**:
- File indexing uses ThreadPoolExecutor (8 workers)
- Batch embedding generation
- Concurrent API calls where possible

**Caching**:
- LRU cache for embeddings (TTL-based eviction)
- AST analysis caching
- Git status caching (8-second TTL)
- Rules file caching (file modification time tracking)

**Batch Operations**:
- Embeddings generated in batches (optimized batch sizes)
- Vector store updates in batches
- Reduced API calls through intelligent batching

**Token Management**:
- Accurate token counting per model
- Aggressive truncation when needed
- Smart summarization to preserve important info

### Technology Stack

**Backend**:
- FastAPI: Modern async Python framework
- ChromaDB: Vector database for embeddings
- SQLite: Persistent memory storage
- GitPython: Git operations
- ThreadPoolExecutor: Parallel processing
- WebSocket: Real-time communication

**Frontend**:
- React: Component-based UI
- Monaco Editor: VS Code editor component
- xterm.js: Terminal emulator
- WebSocket Client: Real-time updates

**AI/ML**:
- OpenAI API: Embeddings and GPT models
- Anthropic API: Claude models
- DeepSeek API: Code generation models
- tiktoken: Token counting
- Vector embeddings: Semantic code search

**Development Tools**:
- AST parsing: Code structure analysis
- Diff-based editing: Precise code changes
- Rich: Beautiful terminal output
- Pydantic: Type-safe validation

## Getting Started

### Prerequisites

You'll need:
- **Python 3.8 or higher** - The backend is built on Python
- **Node.js 16 or higher** - For the web interface (optional, but recommended)
- **OpenAI API key** - Required for core functionality
- **Anthropic API key** - Optional, but recommended for better reasoning capabilities
- **DeepSeek API key** - Optional, but recommended for code generation tasks

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/Hruthik07/Bujji-Coder-AI.git
   cd Bujji-Coder-AI
   ```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install frontend dependencies (for web interface):**
   ```bash
   cd web/frontend
   npm install
   cd ../..
   ```

4. **Set up environment variables:**
   
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   
   Then edit `.env` and add your API keys:
   ```env
   OPENAI_API_KEY=your_key_here
   ANTHROPIC_API_KEY=your_key_here  # Optional but recommended
   DEEPSEEK_API_KEY=your_key_here    # Optional but recommended
   ```
   
   See `.env.example` for all available configuration options.

### Running the Assistant

#### Command Line Interface

For quick tasks and scripts:
```bash
python main.py
```

#### Web Interface (Recommended)

The web interface provides the best experience with real-time features:

1. **Start the backend server:**
   ```bash
   cd web/backend
   python app.py
   ```
   The server will start on `http://localhost:8001`

2. **Start the frontend (in a new terminal):**
   ```bash
   cd web/frontend
   npm start
   ```
   The frontend will open at `http://localhost:3001`

3. **Open your browser** and navigate to `http://localhost:3001`

## How to Use

### Basic Usage

The assistant works through natural language. Just tell it what you want:

```python
from assistant import CodingAssistant

assistant = CodingAssistant(workspace_path=".")
response = assistant.process_message("Add error handling to the login function")
print(response)
```

### Web Interface Workflow

1. **Chat with your assistant** - Ask questions, request code changes, or get explanations
2. **Browse your codebase** - Use the file tree to navigate and open files
3. **Edit files** - Make changes directly in the Monaco editor
4. **Use Composer** - Edit multiple files in a single request
5. **Review changes** - See diffs before applying them
6. **Commit changes** - Use the Git panel to stage and commit with AI-generated messages

### Code Completion

Just start typing. The assistant will suggest completions based on:
- Your current file's context
- Similar code patterns in your codebase
- Language-specific best practices

Press Tab to accept suggestions.

### Debugging

To debug your entire codebase:
```python
results = assistant.debug_codebase(auto_fix=True)
```

Or debug a specific file:
```python
results = assistant.debug_file("src/auth.py", auto_fix=True)
```

The assistant will scan for bugs, suggest fixes, and optionally apply them automatically.

### Project-Specific Rules

Create a `.cursorrules` file in your project root to give the assistant context about your coding standards, architecture decisions, and preferences. The assistant will follow these rules when making suggestions and changes.

## Project Structure

```
Bujji-Coder-AI/
├── assistant.py              # Main assistant orchestrator
├── config.py                 # Configuration management
├── main.py                   # CLI entry point
├── cost_tracker.py           # API usage and cost tracking
├── requirements.txt          # Python dependencies
│
├── tools/                    # Core functionality modules
│   ├── rag_system.py         # Vector-based codebase retrieval
│   ├── code_completion.py    # Autocomplete engine
│   ├── debug_mode.py         # Debugging system
│   ├── git_integration.py    # Git operations
│   ├── context_manager.py    # Memory and context management
│   ├── multi_agent.py        # Multi-agent coordination
│   └── ...                   # Additional tools
│
├── web/                      # Web interface
│   ├── backend/              # FastAPI REST API
│   │   ├── app.py            # Main API server
│   │   └── requirements.txt  # Backend dependencies
│   └── frontend/             # React application
│       ├── src/              # React components
│       └── package.json      # Frontend dependencies
│
└── docs/                     # Documentation
    ├── HYBRID_MODEL_SETUP.md
    ├── MEMORY_SYSTEM_SUMMARY.md
    └── history/              # Test reports and analysis
```

## Configuration

Most configuration is done through environment variables (see `.env.example`). Key settings include:

- **Model selection** - Choose which models to use and when
- **Context window sizes** - Adjust based on your model choices
- **RAG settings** - Control how the codebase is indexed and retrieved
- **Performance tuning** - Cache settings, batch sizes, etc.
- **Memory management** - How conversation history is handled

For advanced configuration, you can modify `config.py` directly.

## Documentation

I've documented the important aspects of the system:

- **[Hybrid Model Setup](docs/HYBRID_MODEL_SETUP.md)** - How to configure and use multiple AI models
- **[Memory System](docs/MEMORY_SYSTEM_SUMMARY.md)** - Understanding context management and memory
- **[Gap Analysis](docs/CURSOR_AI_GAP_ANALYSIS.md)** - Feature comparison with similar tools
- **[Improvement Plan](docs/CURSOR_AI_IMPROVEMENT_PLAN.md)** - Development roadmap

Historical test reports and performance analysis are archived in `docs/history/`.

## Contributing

Contributions are welcome! This project is actively developed, and I appreciate any help.

When contributing:
- Follow PEP 8 style guidelines for Python code
- Ensure all tests pass
- Update documentation for new features
- Write clear commit messages

Feel free to open issues for bugs, feature requests, or questions.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Built With

This project wouldn't be possible without these amazing tools and services:

- **OpenAI** - GPT models and embeddings
- **Anthropic** - Claude models for advanced reasoning
- **DeepSeek** - Specialized code generation models
- **FastAPI** - Modern Python web framework
- **React** - Frontend framework
- **Monaco Editor** - Code editor component
- **ChromaDB** - Vector database for RAG

## Status

This project is production-ready and actively maintained. All core features are implemented and tested. The system has been used successfully on projects ranging from small scripts to large codebases.

---

**Questions?** Open an issue or check the documentation in the `docs/` folder.

**Found a bug?** Please report it with as much detail as possible so I can fix it quickly.

**Have a feature idea?** I'd love to hear it! Open an issue and let's discuss.
