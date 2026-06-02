#!/bin/bash
# Open the session brain in Obsidian
cd "$(dirname "$0")"
nohup obsidian "obsidian://open?vault=$(pwd)" > /dev/null 2>&1 &
echo "Brain vault opened in Obsidian. INDEX.md is your starting point."
