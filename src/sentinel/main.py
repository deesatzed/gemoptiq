#!/usr/bin/env python3
import argparse
import sys
import os

# Add the parent directory to sys.path to allow running as a script
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sentinel.tui import SentinelTUI

def main():
    parser = argparse.ArgumentParser(description="Cortex Sentinel: Trust HUD for Autonomous Agents")
    parser.add_argument("command", help="The command to run the agent (e.g., 'python agent.py')")
    parser.add_argument("--config", default="sentinel.yaml", help="Path to the sentinel configuration file")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
        
    app = SentinelTUI(args.command, args.config)
    app.run()

if __name__ == "__main__":
    main()
