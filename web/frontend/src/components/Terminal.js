import React, { useEffect, useRef, useState } from 'react';
import { Terminal as XTerm } from 'xterm';
import { FitAddon } from 'xterm-addon-fit';
import 'xterm/css/xterm.css';
import './Terminal.css';

// Note: xterm packages are deprecated but still functional
// Consider migrating to @xterm/xterm and @xterm/addon-fit in future

function Terminal({ workspacePath = '.' }) {
  const terminalRef = useRef(null);
  const xtermRef = useRef(null);
  const fitAddonRef = useRef(null);
  const wsRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const [sessionId, setSessionId] = useState(null);
  const [commandHistory, setCommandHistory] = useState([]);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const currentCommandRef = useRef('');

  useEffect(() => {
    // Initialize xterm
    const xterm = new XTerm({
      theme: {
        background: '#1e1e1e',
        foreground: '#cccccc',
        cursor: '#cccccc',
        selection: '#264f78',
        black: '#000000',
        red: '#cd3131',
        green: '#0dbc79',
        yellow: '#e5e510',
        blue: '#2472c8',
        magenta: '#bc3fbc',
        cyan: '#11a8cd',
        white: '#e5e5e5',
        brightBlack: '#666666',
        brightRed: '#f14c4c',
        brightGreen: '#23d18b',
        brightYellow: '#f5f543',
        brightBlue: '#3b8eea',
        brightMagenta: '#d670d6',
        brightCyan: '#29b8db',
        brightWhite: '#e5e5e5'
      },
      fontSize: 13,
      fontFamily: 'Consolas, "Courier New", monospace',
      cursorBlink: true,
      cursorStyle: 'block',
      allowTransparency: true
    });

    const fitAddon = new FitAddon();
    xterm.loadAddon(fitAddon);
    
    xtermRef.current = xterm;
    fitAddonRef.current = fitAddon;

    if (terminalRef.current) {
      xterm.open(terminalRef.current);
      fitAddon.fit();
    }

    // Connect to WebSocket
    const ws = new WebSocket(`ws://${window.location.hostname}:8010/ws/terminal`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      // Generate session ID
      const id = `term-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
      setSessionId(id);
      
      // Send session ID
      ws.send(JSON.stringify({
        type: 'init',
        session_id: id,
        workspace_path: workspacePath
      }));

      // Show prompt
      xterm.writeln('Terminal connected. Type commands below.');
      xterm.write('\r\n$ ');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      
      if (data.type === 'output') {
        xterm.write(data.data);
      } else if (data.type === 'error') {
        xterm.write(`\r\nError: ${data.message}\r\n`);
      } else if (data.type === 'exit') {
        // Exit code is handled, prompt will be sent by server
        // Only show exit code if non-zero
        if (data.code !== 0) {
          xterm.write(`\r\n[Process exited with code ${data.code}]\r\n`);
        }
      } else if (data.type === 'ready') {
        // Session ready
        xterm.write('\r\nTerminal ready.\r\n$ ');
      }
    };

    ws.onerror = (error) => {
      console.error('Terminal WebSocket error:', error);
      xterm.write('\r\nConnection error. Reconnecting...\r\n');
    };

    ws.onclose = () => {
      setConnected(false);
      xterm.write('\r\nTerminal disconnected.\r\n');
    };

    // Handle input
    let currentLine = '';
    xterm.onData((data) => {
      if (data === '\r') {
        // Enter pressed
        xterm.write('\r\n');
        
        if (currentLine.trim()) {
          // Add to history
          const newHistory = [...commandHistory, currentLine];
          setCommandHistory(newHistory);
          setHistoryIndex(-1);
          currentCommandRef.current = '';
          
          // Send command
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
              type: 'command',
              session_id: sessionId,
              command: currentLine
            }));
          }
        } else {
          // Empty line, send empty command to get prompt from server
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
              type: 'command',
              session_id: sessionId,
              command: ''
            }));
          }
        }
        
        currentLine = '';
      } else if (data === '\x7f') {
        // Backspace
        if (currentLine.length > 0) {
          currentLine = currentLine.slice(0, -1);
          xterm.write('\b \b');
        }
      } else if (data === '\x1b[A') {
        // Up arrow - history
        if (commandHistory.length > 0) {
          const newIndex = historyIndex === -1 
            ? commandHistory.length - 1 
            : Math.max(0, historyIndex - 1);
          setHistoryIndex(newIndex);
          
          // Clear current line
          xterm.write('\r$ ');
          for (let i = 0; i < currentLine.length; i++) {
            xterm.write(' ');
          }
          xterm.write('\r$ ');
          
          // Write history command
          currentLine = commandHistory[newIndex];
          currentCommandRef.current = currentLine;
          xterm.write(currentLine);
        }
      } else if (data === '\x1b[B') {
        // Down arrow - history
        if (historyIndex >= 0) {
          const newIndex = historyIndex < commandHistory.length - 1
            ? historyIndex + 1
            : -1;
          setHistoryIndex(newIndex);
          
          // Clear current line
          xterm.write('\r$ ');
          for (let i = 0; i < currentLine.length; i++) {
            xterm.write(' ');
          }
          xterm.write('\r$ ');
          
          // Write history command or clear
          if (newIndex >= 0) {
            currentLine = commandHistory[newIndex];
            currentCommandRef.current = currentLine;
            xterm.write(currentLine);
          } else {
            currentLine = '';
            currentCommandRef.current = '';
          }
        }
      } else if (data.charCodeAt(0) >= 32) {
        // Printable character
        currentLine += data;
        currentCommandRef.current = currentLine;
        xterm.write(data);
      }
    });

    // Handle window resize
    const handleResize = () => {
      if (fitAddonRef.current) {
        fitAddonRef.current.fit();
      }
    };
    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (xtermRef.current) {
        xtermRef.current.dispose();
      }
    };
  }, [workspacePath]);

  return (
    <div className="terminal-container">
      <div className="terminal-header">
        <span className="terminal-title">Terminal</span>
        <span className={`terminal-status ${connected ? 'connected' : 'disconnected'}`}>
          {connected ? '● Connected' : '○ Disconnected'}
        </span>
      </div>
      <div ref={terminalRef} className="terminal-content" />
    </div>
  );
}

export default Terminal;
