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
    build-index.py <.packageinfo> <编译后的.config> <源配置文件> <分支> <标签> <输出.json> [附加包]

末位的「附加包」是本次构建经 extra_packages 临时加进去的包名（空格分隔），
不传则取环境变量 EXTRA_ADD。这些包只在这一次编译里存在，不能算进"已含"。

除主索引外还会在同目录写一份依赖表，文件名把 packages- 换成 deps-。
拆成两个文件是有意的：主索引一万三千个包已经一兆多，而绝大多数人只是
搜个包名勾上就走，不看依赖，没道理让所有人先把依赖表也下载下来。
"""
import io
import json
import os
import re
import sys


def parse_depends(val):
    """把一行 Depends 拆成 (无条件依赖, 条件依赖) 两份。

    条目形如：
        +libc              自动选中的依赖
        libc               依赖但不自动选中
        +USE_GLIBC:librt   条件依赖，USE_GLIBC 打开时才要
        +!SSP_SUPPORT:foo  条件取反
        @USE_GLIBC         纯编译条件，不是依赖，丢弃
    """
    plain, cond = [], []
    for tok in val.split():
        t = tok.lstrip('+')
        if t.startswith('@'):
            continue                      # 编译条件，不构成依赖
        if ':' in t:
            c, _, name = t.partition(':')
            if name:
                cond.append((c, name))
        elif t:
            plain.append(t)
    return plain, cond


def parse_packageinfo(path):
    """返回 {名字: {n, t, c, s, _dep, _cond, _prov}}，同名包保留首次出现的定义。"""
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
                cur = {'n': val, 't': '', 'c': '', 's': '',
                       '_dep': [], '_cond': [], '_prov': []}
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
            elif key == 'Depends' and not cur['_dep'] and not cur['_cond']:
                cur['_dep'], cur['_cond'] = parse_depends(val)
            elif key == 'Provides' and not cur['_prov']:
                cur['_prov'] = val.split()
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


def write_deps(out, branch, tag, ordered):
    """写依赖表，文件名把主索引的 packages- 换成 deps-，返回路径。

    依赖用「在 ordered 里的下标」而不是包名来存：包名在依赖关系里重复度
    极高，存下标能省掉一大半体积，前端算反向依赖也只要遍历一遍。解析不
    到对应包的（虚拟包、内核符号等）原样存字符串，前端按类型区分即可。

    d[i] 是第 i 个包的无条件依赖，k[i] 是条件依赖，每项为 [条件, 目标]。
    两个数组与主索引的 packages 数组按下标一一对应。
    """
    idx = {p['n']: i for i, p in enumerate(ordered)}
    # Provides 声明的虚拟名也能当依赖目标，指向第一个提供者
    for i, p in enumerate(ordered):
        for v in p['_prov']:
            idx.setdefault(v, i)

    def ref(name):
        return idx[name] if name in idx else name

    d = [[ref(x) for x in p['_dep']] for p in ordered]
    k = [[[c, ref(x)] for c, x in p['_cond']] for p in ordered]

    base = os.path.basename(out)
    dep_out = os.path.join(os.path.dirname(out) or '.',
                           ('deps-' + base[len('packages-'):])
                           if base.startswith('packages-') else 'deps-' + base)
    os.makedirs(os.path.dirname(dep_out) or '.', exist_ok=True)
    with io.open(dep_out, 'w', encoding='utf-8') as f:
        json.dump({'branch': branch, 'tag': tag, 'count': len(ordered),
                   'd': d, 'k': k},
                  f, ensure_ascii=False, separators=(',', ':'))
    nd = sum(len(x) for x in d)
    nk = sum(len(x) for x in k)
    unresolved = len({x for row in d for x in row if isinstance(x, str)})
    print('依赖表：无条件 %d 条，条件 %d 条，未解析目标 %d 个'
          % (nd, nk, unresolved))
    return dep_out


def main():
    if len(sys.argv) not in (7, 8):
        sys.stderr.write(__doc__)
        return 2
    pkginfo, final_cfg, src_cfg, branch, tag, out = sys.argv[1:7]
    extra = set((sys.argv[7] if len(sys.argv) == 8
                 else os.environ.get('EXTRA_ADD', '')).split())

    pkgs = parse_packageinfo(pkginfo)
    if not pkgs:
        sys.stderr.write('::error::%s 里没解析出任何软件包\n' % pkginfo)
        return 1

    explicit = selected_packages(src_cfg)   # 配置文件里显式勾选的
    built = selected_packages(final_cfg)    # defconfig 补全依赖后实际编入的
    # 本次经 extra_packages 临时加进来的包，下次不带参数重编就没有了。
    # 不剔掉的话它们会被标成"依赖已含"，页面上看着像固件本来就带，是假的。
    built -= extra
    if extra:
        print('已排除本次临时附加的 %d 个包：%s' % (len(extra), ' '.join(sorted(extra))))

    for name, p in pkgs.items():
        if name in explicit:
            p['sel'] = 2        # 显式选择，页面上默认勾选，可取消
        elif name in built:
            p['sel'] = 1        # 被依赖带入，页面上标注但不可操作
    # 显式勾选里可能有 .packageinfo 没有的符号（如 CONFIG_PACKAGE_DEFAULT_*
    # 之类的虚拟项），不补进列表，避免页面生成出编不出来的包名

    ordered = sorted(pkgs.values(), key=lambda p: p['n'])
    dep_out = write_deps(out, branch, tag, ordered)

    data = {
        'branch': branch,
        'tag': tag,
        'count': len(ordered),
        'packages': [{k: v for k, v in p.items() if not k.startswith('_')}
                     for p in ordered],
    }
    os.makedirs(os.path.dirname(out) or '.', exist_ok=True)
    with io.open(out, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, separators=(',', ':'))

    n2 = sum(1 for p in ordered if p.get('sel') == 2)
    n1 = sum(1 for p in ordered if p.get('sel') == 1)
    print('%s: %d 个包，显式勾选 %d，依赖带入 %d' % (branch, len(ordered), n2, n1))
    for f in (out, dep_out):
        print('  写入 %s (%.0f KB)' % (f, os.path.getsize(f) / 1024.0))
    return 0


if __name__ == '__main__':
    sys.exit(main())
