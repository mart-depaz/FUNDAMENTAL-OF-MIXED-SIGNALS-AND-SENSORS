#!/usr/bin/env python3
import sys

with open('dashboard/views.py', 'r', encoding='utf-8', errors='replace') as f:
    for i, line in enumerate(f, 1):
        if i >= 10180 and i <= 10190:
            print(f"{i}: {line}", end='')
