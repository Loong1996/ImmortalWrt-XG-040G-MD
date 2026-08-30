#!/usr/bin/env python3
"""在默认 SSH banner 与 LuCI 概览「固件版本」后面追加作者信息。

全量编译不读 make FILES=（那是 ImageBuilder 的接口，还会和 kmod 的 FILES
变量撞名）。这里直接改 immortalwrt 源码树里的模板：banner 仍走 %D %V %C
替换，LuCI 仍拼接发行版 + LuCI 版本，只在末尾多一段固定文字。

幂等：已含仓库 URL 则跳过。feeds 更新 / git reset 之后再跑一次即可。
"""
from __future__ import annotations

import sys
from pathlib import Path

# LuCI 固件版本本来就用 / 分隔，追加时带斜杠；SSH banner 是新起一行，不要斜杠。
BANNER_LINE = " Loong · https://github.com/Loong1996/ImmortalWrt-XG-040G-MD"
LUCI_SUFFIX = " / Loong · https://github.com/Loong1996/ImmortalWrt-XG-040G-MD"
MARKER = "github.com/Loong1996/ImmortalWrt-XG-040G-MD"
LUCI_OLD = "(luciversion || '')"
LUCI_NEW = "(luciversion || '') + '%s'" % LUCI_SUFFIX


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


def patch_luci(root: Path) -> None:
    found: list[Path] = []
    seen: set[Path] = set()
    for p in root.glob("**/luci-mod-status/**/view/status/include/10_system.js"):
        real = p.resolve()
        if real in seen:
            continue
        seen.add(real)
        found.append(p)
    if not found:
        die("未找到 luci-mod-status 的 10_system.js，请先 ./scripts/feeds install -a")

    patched = skipped = 0
    for path in found:
        text = path.read_text(encoding="utf-8")
        if MARKER in text:
            print("    LuCI 10_system.js 已含作者信息，跳过: %s" % path)
            skipped += 1
            continue
        lines = text.splitlines(keepends=True)
        hits = [i for i, ln in enumerate(lines) if "Firmware Version" in ln]
        if len(hits) != 1:
            die("%s 里 Firmware Version 出现 %d 次，期望 1 次" % (path, len(hits)))
        i = hits[0]
        if LUCI_OLD not in lines[i]:
            die("%s 的固件版本行格式已变，拒绝盲改:\n%s" % (path, lines[i].rstrip()))
        lines[i] = lines[i].replace(LUCI_OLD, LUCI_NEW, 1)
        path.write_text("".join(lines), encoding="utf-8")
        print("    已追加 LuCI 固件版本: %s" % path)
        patched += 1
    if patched == 0 and skipped == 0:
        die("没有可改的 10_system.js")


def main() -> None:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    if not (root / "rules.mk").is_file():
        die("%s 不像 OpenWrt 源码树（缺 rules.mk）" % root)
    print("写入作者信息 → %s" % root)
    append_banner(root)
    patch_luci(root)


if __name__ == "__main__":
    main()
