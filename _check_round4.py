"""Round 4 syntax check - ModelRegistry refactoring"""

import ast
import sys

sys.stdout.reconfigure(encoding="utf-8")

files = [
    "flypig/domain/registry.py",
    "flypig/domain/model_ref.py",
    "flypig/bootstrap/app_factory.py",
    "flypig/infrastructure/llm/model_factory.py",
    "flypig/infrastructure/llm/openai_adapter.py",
    "flypig/infrastructure/ollama/service.py",
    "flypig/interface/rest/routes/config_routes.py",
]
errors = 0
for f in files:
    try:
        ast.parse(open(f, encoding="utf-8").read())
        print(f"  PASS  {f}")
    except SyntaxError as e:
        print(f"  FAIL  {f}: {e}")
        errors += 1

sys.exit(errors)
