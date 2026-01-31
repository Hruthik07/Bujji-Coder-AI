# Web UI for AI Coding Assistant

Modern web interface for the AI Coding Assistant with real-time chat, code editor, and file management.

## Features

- 🎨 **Modern UI**: VS Code-inspired dark theme
- 💬 **Real-time Chat**: WebSocket-based chat with typing indicators
- 📝 **Code Editor**: Monaco Editor with syntax highlighting
- 📁 **File Tree**: Browse and open files
- 🔍 **Diff Preview**: Visual diff viewer before applying changes
- 📊 **Status Bar**: Real-time system status and statistics

## Architecture

```
web/
├── backend/          # FastAPI server
│   ├── app.py        # Main API server
│   └── requirements.txt
└── frontend/         # React application
    ├── src/
    │   ├── App.js    # Main app component
    │   └── components/
    │       ├── ChatPanel.js
    │       ├── CodeEditor.js
    │       ├── FileTree.js
    │       ├── DiffViewer.js
    │       └── StatusBar.js
    └── package.json
```

## Setup

### Backend Setup

```bash
cd web/backend
pip install -r requirements.txt
python app.py
```

Backend runs on `http://localhost:8000`

### Frontend Setup

```bash
cd web/frontend
npm install
npm start
```

Frontend runs on `http://localhost:3000`

## API Endpoints

### REST API

- `GET /api/status` - Get system status
- `POST /api/chat` - Send chat message (synchronous)
- `GET /api/files` - List files
- `POST /api/files/read` - Read file
- `POST /api/files/write` - Write file
- `POST /api/files/edit` - Edit file
- `POST /api/diff/preview` - Preview diff
- `POST /api/diff/apply` - Apply diff
- `POST /api/search` - Search codebase
- `POST /api/index` - Index codebase
- `GET /api/stats` - Get statistics

### WebSocket

- `ws://localhost:8000/ws/chat` - Real-time chat

## Usage

1. Start backend: `cd web/backend && python app.py`
2. Start frontend: `cd web/frontend && npm start`
3. Open browser: `http://localhost:3000`
4. Start chatting with your AI assistant!

## Environment Variables

Set `WORKSPACE_PATH` environment variable to specify workspace:

```bash
export WORKSPACE_PATH=/path/to/your/code
python app.py
```

## Development

### Backend Development

```bash
cd web/backend
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Development

```bash
cd web/frontend
npm start
```

Hot reload enabled for both!

## Production Build

### Frontend

```bash
cd web/frontend
npm run build
```

Build output in `web/frontend/build/`

### Backend

```bash
cd web/backend
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Features in Detail

### Chat Panel
- Real-time WebSocket communication
- Typing indicators
- Message history
- Automatic diff detection

### Code Editor
- Monaco Editor (VS Code editor)
- Syntax highlighting
- Auto-save
- Multiple language support

### File Tree
- Hierarchical file browser
- File icons by type
- Quick file selection
- Refresh capability

### Diff Viewer
- Visual diff preview
- Side-by-side comparison
- Apply/reject changes
- Syntax highlighting

### Status Bar
- RAG index status
- API usage statistics
- Cost tracking
- System health

## Troubleshooting

### CORS Issues
Backend has CORS enabled for all origins. In production, update `app.py`:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],  # Specific origins
    ...
)
```

### WebSocket Connection Failed
- Check backend is running on port 8000
- Verify WebSocket URL in `ChatPanel.js`
- Check firewall settings

### File Not Loading
- Verify workspace path is correct
- Check file permissions
- Ensure backend has access to files

## Next Steps

- [ ] Add authentication
- [ ] Add file upload
- [ ] Add terminal integration
- [ ] Add code completion
- [ ] Add multi-file editing
- [ ] Add git integration
