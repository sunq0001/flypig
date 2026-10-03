#!/bin/bash
export PATH=$HOME/.local/bin:$PATH
cd /mnt/c/Users/mss/WorkBuddy/Flypig-agent/flypig
vulture . --min-confidence 60 2>/dev/null
echo "EXIT: $?"
