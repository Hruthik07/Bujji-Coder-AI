# Application Testing Guide

## 🚀 Quick Start Testing

### 1. Start Backend Server

```bash
cd web/backend
python app.py
```

**Expected Output:**
```
[OK] Completion engine initialized
[OK] Git service initialized (repo: main) or (not a git repository)
[INFO] RAG not indexed. Starting automatic indexing...
[OK] Assistant initialized for workspace: .
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8001
```

**Note:** If RAG indexing is running, wait for it to complete (may take 1-2 minutes for large codebases).

### 2. Start Frontend Server

In a **new terminal**:

```bash
cd web/frontend
npm start
```

**Expected Output:**
```
Compiled successfully!
You can now view the app in the browser.
  Local:            http://localhost:3001
```

### 3. Open Browser

Navigate to: **http://localhost:3001**

---

## ✅ Manual Testing Checklist

### Backend API Tests

#### Test 1: Status Endpoint
```bash
curl http://localhost:8001/api/status
```

**Expected:** JSON response with:
- `assistant_ready: true`
- `rag_enabled: true`
- `rag_indexed: true/false`
- `model: "gpt-3.5-turbo"` or hybrid model info

#### Test 2: File Listing
```bash
curl http://localhost:8001/api/files?directory=.
```

**Expected:** JSON with file list

#### Test 3: Stats Endpoint
```bash
curl http://localhost:8001/api/stats
```

**Expected:** JSON with cost and performance stats

---

### Web Interface Tests

#### Test 1: UI Loads
- [ ] Open `http://localhost:3001`
- [ ] Verify page loads without errors
- [ ] Check browser console for errors (F12)

#### Test 2: File Tree
- [ ] Left panel shows file tree
- [ ] Can expand/collapse folders
- [ ] Can click files to open them
- [ ] Git status indicators show (if in git repo)

#### Test 3: Code Editor
- [ ] Center panel shows code editor
- [ ] Can edit code
- [ ] Syntax highlighting works
- [ ] Can save files

#### Test 4: Chat Panel
- [ ] Right panel shows chat interface
- [ ] Model selector dropdown is visible
- [ ] Can type messages
- [ ] Can send messages
- [ ] Receives responses

#### Test 5: Model Selection
- [ ] Click model dropdown
- [ ] See options: Auto, DeepSeek, Claude, OpenAI
- [ ] Select different model
- [ ] Send message and verify model is used

#### Test 6: Terminal
- [ ] Click "Terminal" button
- [ ] Terminal panel opens
- [ ] Can type commands
- [ ] Commands execute
- [ ] Output displays correctly

#### Test 7: Git Integration
- [ ] Click "Git" button
- [ ] Git panel opens
- [ ] Shows repository status
- [ ] Can stage/unstage files
- [ ] Can create commits

#### Test 8: Rules Editor
- [ ] Click "Rules" button
- [ ] Rules editor opens
- [ ] Can edit .cursorrules file
- [ ] Can save rules

#### Test 9: Performance Dashboard
- [ ] Click "Performance" button
- [ ] Dashboard opens
- [ ] Shows metrics and charts

#### Test 10: Composer
- [ ] Click "Composer" button
- [ ] Composer panel opens
- [ ] Can request multi-file edits
- [ ] Diff viewer shows changes

---

### Feature-Specific Tests

#### RAG System
1. **Check Status Bar:**
   - Bottom of UI shows "RAG: ✓ Indexed" or "RAG: ○ Not Indexed"
   - If not indexed, click "Index Codebase" button

2. **Test RAG Retrieval:**
   - Ask: "What files are in this directory?"
   - Ask: "Show me the structure of assistant.py"
   - Verify responses include codebase context

#### Code Completion
1. Open a Python file in editor
2. Start typing code
3. Verify autocomplete suggestions appear
4. Suggestions should be context-aware

#### Validation Service
1. Request a code change with syntax error
2. View the diff
3. Verify validation panel shows errors
4. Verify "Apply Changes" button is disabled

#### Debug Mode
1. In chat, type: "debug the codebase"
2. Verify debug scan runs
3. Check for bug reports
4. Verify auto-fix works (if enabled)

---

## 🐛 Troubleshooting

### Backend Not Responding

**Symptoms:** Timeout errors, connection refused

**Solutions:**
1. Check if backend is running: `netstat -ano | findstr ":8001"`
2. Restart backend: Stop (Ctrl+C) and restart
3. Check backend console for errors
4. Verify port 8001 is not blocked by firewall

### Frontend Not Loading

**Symptoms:** Blank page, connection errors

**Solutions:**
1. Check if frontend is running: `netstat -ano | findstr ":3001"`
2. Check browser console (F12) for errors
3. Verify proxy in `package.json` points to `http://localhost:8001`
4. Clear browser cache and reload

### RAG Not Indexing

**Symptoms:** Status shows "Not Indexed"

**Solutions:**
1. Click "Index Codebase" button in UI
2. Or use API: `curl -X POST http://localhost:8001/api/index`
3. Check backend console for indexing progress
4. Wait for indexing to complete (may take time)

### WebSocket Errors

**Symptoms:** Chat not working, terminal not connecting

**Solutions:**
1. Check WebSocket URL in browser console
2. Verify backend WebSocket endpoints are accessible
3. Check CORS configuration in backend
4. Restart both frontend and backend

---

## 📊 Test Results Template

```
Date: ___________
Tester: ___________

Backend Tests:
[ ] Status endpoint works
[ ] File listing works
[ ] Stats endpoint works
[ ] Validation endpoint works

Frontend Tests:
[ ] UI loads correctly
[ ] File tree works
[ ] Code editor works
[ ] Chat works
[ ] Model selection works
[ ] Terminal works
[ ] Git integration works
[ ] Rules editor works
[ ] Performance dashboard works
[ ] Composer works

Feature Tests:
[ ] RAG indexing works
[ ] Code completion works
[ ] Validation works
[ ] Debug mode works

Issues Found:
1. 
2. 
3. 

Overall Status: [ ] Pass [ ] Fail [ ] Needs Work
```

---

## 🎯 Success Criteria

Application is working correctly if:
- ✅ All backend endpoints respond
- ✅ Frontend loads without errors
- ✅ Chat can send/receive messages
- ✅ File operations work
- ✅ All UI panels open correctly
- ✅ No critical errors in console

---

**Happy Testing!** 🚀
