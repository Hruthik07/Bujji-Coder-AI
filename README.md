# Bujji Coder AI

An intelligent coding assistant that understands your codebase, helps you write better code, and automates tedious development tasks. Think of it as having a senior developer pair-programming with you, but powered by advanced AI models.

## What is This?

Bujji Coder AI is a comprehensive development tool that combines the power of multiple AI models with deep codebase understanding. It's designed to help developers write code faster, catch bugs earlier, and maintain better code quality across projects of any size.

The assistant uses Retrieval-Augmented Generation (RAG) to understand your entire codebase context, making suggestions and changes that actually fit your project's architecture and coding style. Whether you're working on a small script or a large enterprise application, it adapts to your needs.

## Key Features

### Smart Code Understanding
The assistant doesn't just read your code—it understands it. Using AST parsing and vector-based retrieval, it maintains context about your entire codebase. Ask it to refactor a function, and it knows what other parts of your code depend on it.

### Multi-Model Intelligence
Instead of being locked into a single AI model, Bujji Coder AI intelligently routes tasks to the best model for the job:
- **DeepSeek Coder** for code generation and refactoring
- **Claude Sonnet** for complex reasoning and architecture decisions
- **OpenAI GPT** as a reliable fallback

This hybrid approach gives you the best of all worlds: fast, accurate code generation with deep reasoning when you need it.

### Real-Time Code Completion
Get intelligent autocomplete suggestions as you type. The suggestions combine:
- AST analysis of your current file
- Similar patterns from your codebase (via RAG)
- Language-specific keywords and patterns
- Multi-line completions that actually make sense

### Intelligent Debugging
The debug mode goes beyond simple error detection. It:
- Scans your entire codebase for potential issues
- Uses static analysis to catch bugs before runtime
- Generates hypotheses about what might be wrong
- Automatically fixes common issues
- Provides step-by-step debugging guidance

### Git Integration
Full Git support built right in. Stage files, create commits with AI-generated messages, manage branches, and view diffs—all without leaving the interface. The assistant even suggests commit messages based on your changes.

### Modern Web Interface
A clean, responsive web UI built with React and Monaco Editor (the same editor that powers VS Code). Features include:
- Real-time chat with your assistant
- File explorer with Git status indicators
- Side-by-side diff viewer
- Integrated terminal
- Performance monitoring dashboard
- Multi-file editing with the Composer

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

We've documented the important aspects of the system:

- **[Hybrid Model Setup](docs/HYBRID_MODEL_SETUP.md)** - How to configure and use multiple AI models
- **[Memory System](docs/MEMORY_SYSTEM_SUMMARY.md)** - Understanding context management and memory
- **[Gap Analysis](docs/CURSOR_AI_GAP_ANALYSIS.md)** - Feature comparison with similar tools
- **[Improvement Plan](docs/CURSOR_AI_IMPROVEMENT_PLAN.md)** - Development roadmap

Historical test reports and performance analysis are archived in `docs/history/`.

## Contributing

Contributions are welcome! This project is actively developed, and we appreciate any help.

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

**Found a bug?** Please report it with as much detail as possible so we can fix it quickly.

**Have a feature idea?** We'd love to hear it! Open an issue and let's discuss.
