"""比对 flypig/ 文件列表 vs folder-tree.md"""
import os, re, sys

BASE = r"c:\Users\mss\WorkBuddy\Flypig-agent"
FLYPIG = os.path.join(BASE, "flypig")
FOLDER_TREE = os.path.join(BASE, "docs", "docs_refactor", "folder-tree.md")

# 1. 实际文件
actual = set()
for root, dirs, files in os.walk(FLYPIG):
    for f in files:
        rel = os.path.relpath(os.path.join(root, f), FLYPIG).replace("\\", "/")
        actual.add(rel)

print("实际文件数:", len(actual))

# 2. 解析 folder-tree
with open(FOLDER_TREE, "r", encoding="utf-8") as fh:
    lines = fh.readlines()

in_code = False
tree_lines = []
for line in lines:
    s = line.strip()
    if s.startswith("```"):
        if not in_code:
            in_code = True
            continue
        else:
            break
    if in_code:
        tree_lines.append(line)

expected = set()
path_stack = [(-1, "")]
for raw_line in tree_lines:
    line = raw_line.rstrip()
    if not line.strip():
        continue
    stripped = line.lstrip()
    indent = len(line) - len(stripped)
    m = re.match(r'[|\+\\\xa0\s]*[-├└]\s*──\s+(.+)', stripped)
    if not m:
        continue
    entry = m.group(1).strip()
    entry = re.sub(r'\s*[←└├─]\s*[★☆P\d\s]*.*$', '', entry).strip()
    is_dir = entry.endswith('/')
    name = entry.rstrip('/')
    while path_stack and path_stack[-1][0] >= indent:
        path_stack.pop()
    parent = path_stack[-1][1] if path_stack else ""
    if is_dir:
        fp = os.path.join(parent, name).replace("\\", "/")
        path_stack.append((indent, fp))
    else:
        fp = os.path.join(parent, name).replace("\\", "/")
        expected.add(fp)

print("folder-tree.md 解析文件数:", len(expected))

oa = actual - expected
oe = expected - actual

print("\n--- 差异 ---")
print("实际有而 tree 未列出:", len(oa))
print("tree 列出而实际缺失:", len(oe))

if oe:
    print("\n[MISS] folder-tree.md 列出但未创建:")
    for f in sorted(oe):
        print("  -", f)

if oa:
    print("\n[EXTRA] 实际存在但 tree 未列出:")
    for f in sorted(oa):
        print("  +", f)

if not oe and not oa:
    print("\n完美匹配! 没有差异.")
