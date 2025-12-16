#!/usr/bin/env python3
import ast
import sys

try:
    with open('dashboard/views.py', 'rb') as f:
        code = f.read()
    ast.parse(code)
    print("✓ Syntax is valid")
    sys.exit(0)
except SyntaxError as e:
    print(f"✗ Syntax error at line {e.lineno}: {e.msg}")
    if e.text:
        print(f"  {e.text}")
    sys.exit(1)
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")
    sys.exit(1)
