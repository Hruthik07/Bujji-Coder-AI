"""
Main entry point for the AI Coding Assistant
"""
import sys
import os
from assistant import CodingAssistant, AssistantTools
from config import Config


def main():
    """Main entry point"""
    if len(sys.argv) > 1:
        mode = sys.argv[1]
        
        if mode == "chat":
            # Interactive chat mode
            workspace = sys.argv[2] if len(sys.argv) > 2 else "."
            assistant = CodingAssistant(workspace_path=workspace)
            assistant.chat()
        
        elif mode == "tools":
            # Direct tool access mode (for testing/scripting)
            workspace = sys.argv[2] if len(sys.argv) > 2 else "."
            tools = AssistantTools(workspace_path=workspace)
            
            # Example usage
            print("Assistant Tools - Direct Access Mode")
            print("Use this mode for programmatic access to tools")
            
            # Example: list directory
            result = tools.list_directory(".")
            print(f"\nDirectory listing: {result}")
        
        else:
            print(f"Unknown mode: {mode}")
            print("Usage: python main.py [chat|tools] [workspace_path]")
    else:
        # Default: interactive chat
        workspace = os.getcwd()
        assistant = CodingAssistant(workspace_path=workspace)
        assistant.chat()


if __name__ == "__main__":
    main()

