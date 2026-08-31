#!/usr/bin/env python3
"""在默认 SSH banner 与 LuCI 概览「固件版本」后面追加作者信息。

全量编译不读 make FILES=（那是 ImageBuilder 的接口，还会和 kmod 的 FILES
变量撞名）。这里直接改 immortalwrt 源码树里的模板：banner 仍走 %D %V %C
替换。

LuCI 概览的「固件版本」来自 ubus system.board 的 release.description，
也就是 /etc/openwrt_release 的 DISTRIB_DESCRIPTION。base-files 打包时
从 package/base-files/files/ 现拷现替换，和 SSH banner 同一条路。

不要改 luci-mod-status 的 10_system.js：那份源码会在编包时 minify 进
build_dir，工具链缓存命中后不会重编，补丁进不了固件。

幂等：已含仓库 URL 则跳过。feeds 更新 / git reset 之后再跑一次即可。
"""
from __future__ import annotations

import sys
from pathlib import Path

# LuCI 固件版本本来就用 / 分隔，追加时带斜杠；SSH banner 是新起一行，不要斜杠。
BANNER_LINE = " Loong · https://github.com/Loong1996/ImmortalWrt-XG-040G-MD"
RELEASE_SUFFIX = " / Loong · https://github.com/Loong1996/ImmortalWrt-XG-040G-MD"
MARKER = "github.com/Loong1996/ImmortalWrt-XG-040G-MD"


def die(msg: str) -> None:
    print("错误: %s" % msg, file=sys.stderr)
    sys.exit(1)


def append_banner(root: Path) -> None:
    path = root / "package/base-files/files/etc/banner"
    if not path.is_file():
        die("未找到 %s（不是 OpenWrt 源码树？）" % path)
    lines = path.read_text(encoding="utf-8").splitlines()
    found = changed = False
    for i, ln in enumerate(lines):
        if MARKER not in ln:
            continue
        found = True
        if ln != BANNER_LINE:
            lines[i] = BANNER_LINE
            changed = True
        break
    if not found:
        lines.append(BANNER_LINE)
        changed = True
    if not changed:
        print("    SSH banner 已含作者信息，跳过")
        return
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("    已写入 SSH banner: %s" % path)


def append_quoted_field(path: Path, key: str, label: str) -> None:
    """在 KEY='value' / KEY="value" 的收尾引号前追加 RELEASE_SUFFIX。"""
    if not path.is_file():
        die("未找到 %s" % path)
    lines = path.read_text(encoding="utf-8").splitlines()
    hits = [i for i, ln in enumerate(lines) if ln.startswith(key + "=")]
    if len(hits) != 1:
        die("%s 里 %s 出现 %d 次，期望 1 次" % (path, key, len(hits)))
    i = hits[0]
    line = lines[i]
    if MARKER in line:
        print("    %s 已含作者信息，跳过: %s" % (label, path))
        return
    prefix_sq = key + "='"
    prefix_dq = key + '="'
    if line.startswith(prefix_sq) and line.endswith("'") and len(line) > len(prefix_sq):
        lines[i] = line[:-1] + RELEASE_SUFFIX + "'"
    elif line.startswith(prefix_dq) and line.endswith('"') and len(line) > len(prefix_dq):
        lines[i] = line[:-1] + RELEASE_SUFFIX + '"'
    else:
        die("%s 的 %s 行格式已变，拒绝盲改:\n%s" % (path, key, line))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("    已追加 %s: %s" % (label, path))


def patch_release(root: Path) -> None:
    files = root / "package/base-files/files"
    append_quoted_field(
        files / "etc/openwrt_release",
        "DISTRIB_DESCRIPTION",
        "openwrt_release DISTRIB_DESCRIPTION",
    )
    os_release = files / "usr/lib/os-release"
    append_quoted_field(
        os_release,
        "OPENWRT_RELEASE",
        "os-release OPENWRT_RELEASE",
    )


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not (root / "rules.mk").is_file():
        die("%s 不像 OpenWrt 源码树（缺 rules.mk）" % root)
    print("写入作者信息 → %s" % root)
    append_banner(root)
    patch_release(root)


if __name__ == "__main__":
    main()
