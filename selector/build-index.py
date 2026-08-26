#!/usr/bin/env python3
"""从 buildroot 的 tmp/.packageinfo 导出选包页用的软件包索引。

.packageinfo 是 include/scan.mk 扫描全部 feeds 后生成的元数据缓存，
在 make defconfig 时产生，内容形如：

    Source-Makefile: package/network/services/dnsmasq/Makefile
    Package: dnsmasq
    Submenu: IP Addresses and Names
    Category: Base system
    Section: net
    Title: DNS and DHCP server
    Description: ...
    @@

用它而不是官方 apk 索引，是因为只有它反映"这条源码分支实际能编出哪些包"，
自建的 luci-app-airoha-npu 之类也在里面。

用法：
    build-index.py <.packageinfo> <编译后的.config> <源配置文件> <分支> <标签> <输出.json>
"""
import io
import json
import os
import re
import sys


def parse_packageinfo(path):
    """返回 [{n, t, c, s}, ...]，按包名去重后保留首次出现的定义。"""
    pkgs = {}
    cur = None
    with io.open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n')
            if line == '@@':
                cur = None
                continue
            m = re.match(r'^([A-Za-z][A-Za-z0-9-]*): ?(.*)$', line)
            if not m:
                continue
            key, val = m.group(1), m.group(2).strip()
            if key == 'Package':
                cur = {'n': val, 't': '', 'c': '', 's': ''}
                # 同名包可能被多个 Makefile 定义（如不同 feed），以先扫到的为准
                pkgs.setdefault(val, cur)
                cur = pkgs[val]
            elif cur is None:
                continue
            elif key == 'Title' and not cur['t']:
                cur['t'] = val
            elif key == 'Category' and not cur['c']:
                cur['c'] = val
            elif key == 'Submenu' and not cur['s']:
                cur['s'] = val
    return pkgs


def selected_packages(path):
    """读取 kconfig 风格配置，返回其中 =y/=m 的软件包名集合。

    源配置文件里的行常带行尾注释（CONFIG_PACKAGE_x=y # 说明），要一并认出来。
    """
    sel = set()
    if not os.path.exists(path):
        return sel
    with io.open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            m = re.match(r'^CONFIG_PACKAGE_(\S+?)=[ym]\s*(?:#.*)?$', line.rstrip('\n'))
            if m:
                sel.add(m.group(1))
    return sel


def main():
    if len(sys.argv) != 7:
        sys.stderr.write(__doc__)
        return 2
    pkginfo, final_cfg, src_cfg, branch, tag, out = sys.argv[1:]

    pkgs = parse_packageinfo(pkginfo)
    if not pkgs:
        sys.stderr.write('::error::%s 里没解析出任何软件包\n' % pkginfo)
        return 1

    explicit = selected_packages(src_cfg)   # 配置文件里显式勾选的
    built = selected_packages(final_cfg)    # defconfig 补全依赖后实际编入的

    for name, p in pkgs.items():
        if name in explicit:
            p['sel'] = 2        # 显式选择，页面上默认勾选，可取消
        elif name in built:
            p['sel'] = 1        # 被依赖带入，页面上标注但不可操作
    # 显式勾选里可能有 .packageinfo 没有的符号（如 CONFIG_PACKAGE_DEFAULT_*
    # 之类的虚拟项），不补进列表，避免页面生成出编不出来的包名

    data = {
        'branch': branch,
        'tag': tag,
        'count': len(pkgs),
        'packages': sorted(pkgs.values(), key=lambda p: p['n']),
    }
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    with io.open(out, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    n2 = sum(1 for p in pkgs.values() if p.get('sel') == 2)
    n1 = sum(1 for p in pkgs.values() if p.get('sel') == 1)
    print('%s: %d 个包，显式勾选 %d，依赖带入 %d，写入 %s (%.0f KB)'
          % (branch, len(pkgs), n2, n1, out, os.path.getsize(out) / 1024.0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
