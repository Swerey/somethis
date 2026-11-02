# -*- coding: utf-8 -*-
"""批次B-2：前端静态资源版本号自动注入脚本（替代手工维护）
用法：
  python scripts/bump_version.py [版本号]
不传版本号时使用当天日期（YYYYMMDD）。
扫描 static 下所有 .html/.js/.css，将 ?v=YYYYMMDD 统一替换为新版本号。
"""
import os
import re
import sys
import datetime

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'static'))
PATTERN = re.compile(r'(\?v=)(\d{8})')


def main():
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        new_ver = sys.argv[1]
    else:
        new_ver = datetime.date.today().strftime('%Y%m%d')
    changed = []
    total = 0
    for dirpath, dirs, files in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in ('node_modules', '.git', 'temp')]
        for fn in files:
            if not fn.endswith(('.html', '.js', '.css')):
                continue
            path = os.path.join(dirpath, fn)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    s = f.read()
            except UnicodeDecodeError:
                continue
            matches = PATTERN.findall(s)
            if not matches:
                continue
            old_versions = sorted(set(v for _, v in matches))
            s2 = PATTERN.sub(lambda m: m.group(1) + new_ver, s)
            if s2 != s:
                with open(path, 'w', encoding='utf-8') as f:
                    f.write(s2)
                changed.append((path, old_versions))
                total += len(matches)
    print(f'目标版本: v={new_ver}')
    print(f'替换引用数: {total}')
    for path, olds in changed:
        print(f'  {os.path.relpath(path, ROOT)}  旧版本: {",".join(olds)}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
