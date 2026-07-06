import sys
with open('docs/WORKSTREAMS.md', 'r') as f:
    for i, line in enumerate(f):
        print(f"{i+1:03d} {line}", end='')
