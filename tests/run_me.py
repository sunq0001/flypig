#!/usr/bin/env python3
"""Simple test script - used by tests/test_integration.py to verify inline execution."""
import sys

print("=" * 30)
print("Hello from run_me.py!")
print(f"Python: {sys.version.split()[0]}")
print("=" * 30)
print("args:", sys.argv[1:])
sys.exit(0)
