# Auto - AI Coding Assistant

A powerful AI coding assistant with advanced features including RAG (Retrieval-Augmented Generation), multi-model support, code completion, debugging, and a modern web interface.

## 🚀 Features

### Core Capabilities
- **RAG System**: Vector-based codebase retrieval with AST-aware chunking
- **Multi-Model Support**: Hybrid LLM approach (OpenAI, Anthropic Claude, DeepSeek)
- **Code Completion**: Real-time inline autocomplete with context awareness
- **Diff-Based Editing**: Precise code changes using unified diff format
- **Debug Mode**: Comprehensive debugging with static analysis and runtime debugging
- **Git Integration**: Full Git support with AI-powered commit messages
- **Terminal Integration**: Built-in terminal for command execution
- **Rules Engine**: Project-specific instructions via `.cursorrules` files

### Web Interface
- **Modern UI**: React-based web interface with Monaco Editor
- **Real-time Chat**: WebSocket-powered chat with model selection
- **File Explorer**: Visual file tree with Git status indicators
- **Diff Viewer**: Side-by-side diff visualization with validation
- **Performance Dashboard**: Real-time metrics and monitoring
- **Composer**: Multi-file editing interface

## 📋 Requirements

- Python 3.8+
- Node.js 16+ (for web interface)
- OpenAI API key (required)
- Anthropic API key (optional, for Claude)
- DeepSeek API key (optional, for DeepSeek Coder)

## 🛠️ Installation

### 1. Clone the Repository
```bash
git clone <repository-url>
cd Bujji_Coder_AI
```

### 2. Install Python Dependencies
```bash
pip install -r requirements.txt
```

### 3. Install Frontend Dependencies
```bash
cd web/frontend
npm install
cd ../..
```

### 4. Configure Environment Variables

Copy the example environment file and fill in your API keys:

```bash
cp .env.example .env
```

Then edit `.env` and add your API keys:

```env
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional - for hybrid model support
ANTHROPIC_API_KEY=your_anthropic_api_key_here
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Optional - workspace path
WORKSPACE_PATH=.

# Optional - server port
PORT=8001
```

See `.env.example` for all available configuration options.

## 🚀 Quick Start

### Command Line Interface

```bash
python main.py
```

### Web Interface

1. **Start Backend Server:**
```bash
cd web/backend
python app.py
```

2. **Start Frontend Server:**
```bash
cd web/frontend
npm start
```

3. **Open Browser:**
Navigate to `http://localhost:3001` (or the port shown in terminal)

## 📖 Usage

### Interactive Chat

Start the assistant and interact via natural language:

```python
from assistant import CodingAssistant

assistant = CodingAssistant(workspace_path=".")
response = assistant.process_message("Add error handling to my code")
print(response)
```

### Web Interface

1. Open the web interface in your browser
2. Use the chat panel to ask questions or request code changes
3. Select files from the file tree to view/edit
4. Use Composer for multi-file editing
5. Access Git panel for version control
6. Use Terminal for command execution

### Code Completion

The assistant provides real-time code completion:
- AST-based suggestions
- RAG-powered context
- Language keyword completion
- Multi-source merging

### Debug Mode

Automatically detect and fix bugs:

```python
# Debug entire codebase
results = assistant.debug_codebase(auto_fix=True)

# Debug specific file
results = assistant.debug_file("path/to/file.py", auto_fix=True)
```

## 🏗️ Project Structure

```
Bujji_Coder_AI/
├── assistant.py              # Main assistant class
├── config.py                 # Configuration settings
├── main.py                   # CLI entry point
├── cost_tracker.py           # API cost tracking
├── requirements.txt          # Python dependencies
├── tools/                    # Core tools and utilities
│   ├── rag_system.py         # RAG implementation
│   ├── code_completion.py    # Autocomplete engine
│   ├── debug_mode.py         # Debugging system
│   ├── git_integration.py    # Git operations
│   └── ...                   # Other tools
├── web/                      # Web interface
│   ├── backend/              # FastAPI backend
│   │   ├── app.py            # API server
│   │   └── requirements.txt  # Backend dependencies
│   └── frontend/             # React frontend
│       ├── src/              # Source code
│       └── package.json      # Frontend dependencies
└── docs/                     # Documentation
```

## 🔧 Configuration

Edit `config.py` to customize:

- Model selection and hybrid mode
- Context window sizes
- RAG settings
- Performance monitoring
- Memory management

## 📚 Documentation

Additional documentation available in the `docs/` folder:
- `HYBRID_MODEL_SETUP.md` - Multi-model configuration guide
- `MEMORY_SYSTEM_SUMMARY.md` - Context memory management
- `CURSOR_AI_GAP_ANALYSIS.md` - Feature comparison
- `CURSOR_AI_IMPROVEMENT_PLAN.md` - Development roadmap

Historical test reports and performance analysis are available in `docs/history/`.

## 🤝 Contributing

Contributions are welcome! Please ensure:
- Code follows PEP 8 style guidelines
- All tests pass
- Documentation is updated

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with:
- OpenAI API
- Anthropic Claude API
- DeepSeek API
- FastAPI
- React
- Monaco Editor
- ChromaDB

---

**Status**: Production Ready ✅
