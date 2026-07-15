#!/bin/bash
export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
cd /mnt/c/Users/mss/WorkBuddy/Flypig-agent
unset http_proxy https_proxy HTTP_PROXY HTTPS_PROXY no_proxy NO_PROXY
tmux kill-session -t flypig 2>/dev/null
sleep 1
tmux new-session -d -s flypig "python3 /mnt/c/Users/mss/WorkBuddy/Flypig-agent/dev.py > /tmp/devpy.log 2>&1"
echo "TMUX_DONE:$?"
