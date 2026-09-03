# -*- coding: utf-8 -*-
"""git 整理前的项目侦察：git 状态 / 大文件 / 敏感信息扫描"""
import os
import re

root = r'e:\作业\欧莱雅比赛项目\项目3\ColorBoundless'
out = open(r'e:\_git_scan.txt', 'w', encoding='utf-8')

# 1. git 仓库状态
git_dir = os.path.join(root, '.git')
out.write('HAS_GIT: %s\n' % os.path.exists(git_dir))
for f in ('.gitignore', 'README.md', 'requirements.txt', '.env'):
    out.write('%s: %s\n' % (f, os.path.exists(os.path.join(root, f))))

# 2. 目录树（深度2）+ 大文件清单
out.write('\n=== TREE (depth 2) ===\n')
big = []
for dp, dn, fn in os.walk(root):
    rel = os.path.relpath(dp, root)
    depth = rel.count(os.sep)
    if depth >= 2:
        dn[:] = []
        continue
    for skip in ('__pycache__', '.venv', '.git'):
        if skip in dn:
            dn.remove(skip)
    out.write('%s/\n' % rel)
    for f in fn:
        p = os.path.join(dp, f)
        sz = os.path.getsize(p)
        if sz > 500000:
            big.append((sz, os.path.relpath(p, root)))
out.write('\n=== FILES > 500KB ===\n')
for sz, p in sorted(big, reverse=True):
    out.write('%.1f MB  %s\n' % (sz / 1048576, p))

# 3. 敏感信息扫描
out.write('\n=== SECRET SCAN ===\n')
pat = re.compile(r"""api_key\s*=\s*['"][^'"]{8,}|sk-[a-zA-Z0-9]{10,}|Bearer [a-zA-Z0-9]{15,}""")
for dp, dn, fn in os.walk(root):
    dn[:] = [d for d in dn if d not in ('.venv', '__pycache__', '.git', 'models')]
    for f in fn:
        if f.endswith(('.py', '.md', '.json', '.txt')):
            p = os.path.join(dp, f)
            try:
                for i, line in enumerate(open(p, encoding='utf-8', errors='ignore'), 1):
                    if pat.search(line):
                        out.write('%s:%d: %s\n' % (os.path.relpath(p, root), i, line.strip()[:90]))
            except Exception:
                pass
out.close()
print('scan done')
