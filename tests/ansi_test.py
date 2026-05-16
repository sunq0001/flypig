#!/usr/bin/env python3
"""Test script that outputs ANSI sequences - used to verify strip_ansi."""
import sys

# Deliberately print ANSI color codes
GREEN = "\033[32m"
RED = "\033[31m"
BOLD = "\033[1m"
RESET = "\033[0m"

print(f"{BOLD}{GREEN}PASS{RESET}: This line has ANSI colors")
print(f"{RED}ERROR{RESET}: fake error in {BOLD}red{RESET}")
print("plain line without colors")
print(f"\033[1m\033[34mINFO\033[0m: mixed \033[33mwarnings\033[0m here")
sys.exit(0)
