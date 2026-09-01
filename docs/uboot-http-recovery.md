# U-Boot 网页救砖

`ubi` 变体的 U-Boot 里内置了一个恢复页面。**机器刷坏了，插上网线用浏览器就能救回来** —— 不用串口，不用在电脑上架 TFTP 服务器，不用装任何工具。

已合入 `master-XG-040G-MD` 主线，开发过程的完整提交历史归档在 `archive/master-XG-040G-MD-httpd`。

> 想要图文版、从零开始的操作教程（含实拍接线图与串口截图），见 **[网页救砖指南](https://loong1996.github.io/ImmortalWrt-XG-040G-MD/recovery-guide.html)**。本文档是技术参考，覆盖设计取舍与踩过的坑。

> 只对 `ubi` 变体有效。`tcboot` 变体用的是第三方引导程序，`stock` 用原厂引导，都不经过这个 U-Boot。

---

## 怎么用

### 进恢复页

两条路，都不需要串口：

| 什么时候 | 怎么进 |
| --- | --- |
| 想主动刷机 | **按住 reset 上电**，一直按着，等面板五个绿灯开始**流水**再松手（约 15 秒） |
| 机器起不来了 | **什么都不用做** —— 从 NAND 引导失败后会自己循环起网页，插上网线即可 |

这段时间里有一部分是 bootmenu 的等待。`button reset` 读的是那一瞬间的电平，不是累计计时，所以「一直按住」比「按几下」可靠。**流水灯亮起来就是进去了。**

### 传文件

1. 网线插到串口打印的那个口（`Using xxx device` 那行；没有串口就一个个试，通常是 LAN1）
2. 电脑或手机的网口设成自动获取 IP，会拿到 `192.168.1.100`
3. 浏览器打开 **`192.168.1.1`**
4. 「固件」那一格选 `...-ubi-squashfs-sysupgrade.itb`，点「上传并刷写」
5. 确认对话框里核对一遍，点「开始写入」

**不用先配静态 IP** —— U-Boot 里带了个最小 DHCP 服务器，专门为了省掉这一步，那正是救砖流程最容易卡住的地方。

### 面板灯是唯一的进度来源

| 面板 | 含义 | 能拔网线吗 |
| --- | --- | --- |
| 五灯**流水** | 在等你上传 | ❌ 还在传 |
| 五灯**齐闪** | 正在写 flash | ✅ 随便拔 |
| 熄灭后重启 | 写完了 | ✅ |

**上传结束后网页就没用了。** `net_loop()` 在写入开始前就返回，连接已经关闭，浏览器和设备之间没有通道 —— 页面上那句「写入期间页面收不到任何消息」说的就是这件事。

拔网线随时安全，写 flash 不经过网络。**要命的是断电** —— 齐闪期间断电才是真的砖。

### 刷写等于恢复出厂

`ubi_write_production` 会先删掉 `rootfs_data` 给新卷腾地方，所以**网页刷写必然清空配置**，不管勾没勾任何选项。

系统还能进的话，请用 `sysupgrade -c` 保留配置。这个页面的定位是「系统起不来了」。

---

## 首次迁移：从 tcboot / 原厂 换到 ubi 布局

只有这一次需要串口，之后再也不用。

**① 串口进 BootROM，xmodem 传两个文件**

按住 reset 上电，看到 `Press x` 时按 `x`，依次传：

```
immortalwrt-airoha-an7581-nokia_xg-040g-md-ubi-preloader.bin      ← BootROM 收，进 SRAM
immortalwrt-airoha-an7581-nokia_xg-040g-md-ubi-bl31-uboot.fip     ← BL2 收，进 DRAM
```

传两个是硬约束：BootROM 只把 BL2 收进 SRAM，那里放不下 431 KB，它也不解析 FIP 里的 BL33。

**reset 一直按着不要松。**

**② U-Boot 在 RAM 里起来，直接进网页**

`_firstboot` 的第一件事就是 `run check_buttons` —— 在碰 flash 之前先看按键。这一刀是「一轮 xmodem 就够」的全部依据：没有它，RAM 里的 U-Boot 会直奔 `_init_env`，在异构 flash 布局上建卷失败、回落 `ubi_format` 然后 `reset`，把刚传进来的东西一起丢掉。

看到流水灯就松手。

**③ 网页一次传完三样**

展开「引导程序（仅首次迁移需要）」：

| 格子 | 文件 |
| --- | --- |
| 固件 | `...-ubi-squashfs-sysupgrade.itb` |
| BL2 | `...-ubi-preloader.bin` |
| U-Boot | `...-ubi-bl31-uboot.fip` |
| ☑ 重建 UBI | **必须勾** —— 旧布局上没有有效的 UBI，不擦就建不了卷 |

**④ 自动重启，完成**

`_firstboot` 会建出 `ubootenv` / `ubootenv2` / `ri` / `bosa`，然后正常引导。

> ⚠️ **重建 UBI 会擦掉出厂 MAC。** `ri` 卷没了，`ethaddr_factory` 读不到，MAC 变成默认值。从[原厂备份](backup-and-restore.md)里把 `ri` 写回去即可，随时能做，不影响使用。

### 日常更新引导器就不用勾了

BL2 走 `mtd`，完全不碰 UBI；FIP 走 `ubi_write_fip`，它自己只换 `fip` 那一个卷。**只要 `ubi part ubi` 挂得上，就不要勾重建。**

覆盖正在运行的 U-Boot 是安全的：SPI-NAND 不能 XIP，当前这份早就解压在 DRAM 里跑了，和 flash 上的副本没关系。

---

## 补丁清单

都在 `package/boot/uboot-airoha/patches/`：

| 补丁 | 做什么 |
| --- | --- |
| `202-net-add-httpd-recovery-server` | 全部的 httpd —— 新增 `net/httpd.c`，外加 `net.c` / `Kconfig` / `Makefile` / `net-legacy.h` 四处挂接 |
| `950-configs-xg-040g-md-enable-httpd` | defconfig 开 `PROT_TCP` / `CMD_HTTPD` / `CYCLIC` |
| `951-defenvs-xg-040g-md-httpd-recovery` | 触发路径，与两条 httpd 专用的 env 脚本 |
| `952-xg-040g-md-bootmenu-web-recovery-branding` | 引导菜单署名、手动开服务的菜单项 |

`206`（DRAM 容量探测）编号挨着但**与网页救砖无关**，是独立的 bug 修复，影响所有 an7581 设备 —— 见[设备变体 → 内存容量](variants.md#内存容量)。分开放是为了以后单独提上游时不用再拆。

> **为什么只有一个 httpd 补丁**
>
> 开发时它是五个（骨架 → 上传 → DHCP 与面板灯 → 引导器 → 页面），合进主线时压成了一个。
>
> `patches/` 目录的语义是「**对上游源码的修改集**」，不是提交历史。`net/httpd.c` 是我们新增的文件，让它被五个补丁层层重写的代价是实打实的：构建时同一个文件反复 apply 五次、想知道最终形态得在脑子里叠四层 diff、上游同步时冲突面变成五份。而且没有哪一层是可以单独回退的 —— 你不会想只去掉「DHCP」或「页面」，它们本来就是一个功能。
>
> 对照同目录里合理的分法：`100`–`111` 是 backport，一个补丁对应上游一个 commit；`200` / `201` 是两件互不相干的事。**分开要有理由，「开发时是分步做的」不算理由。**
>
> 开发过程的原貌（五个补丁、21 个提交）留在 `archive/master-XG-040G-MD-httpd`。

### `951` 改了什么

```
check_buttons=if button reset ; then httpd ; fi              ← 原来是 run boot_tftp
boot_ubi=run boot_production ; run boot_httpd_forever        ← 原来是 boot_tftp_forever
boot_httpd_forever=while true ; do httpd ; sleep 1 ; done    ← 新增
_firstboot=... ; run check_buttons ; run ethaddr_factory ...  ← 开头插入按键检查
httpd_write_bl2=mtd erase bl2 && mtd write bl2 $loadaddr 0x800 $filesize
httpd_format_ubi=ubi detach ; mtd erase ubi && ubi part ubi
```

`httpd_write_bl2` 用 `mtd write` 的 offset 参数让 mtd 自己跳过前 `0x800` 字节（BootROM 在那里找 FIP），省掉官方脚本里 `mw.b $loadaddr 0xff 0x800` 那一步 —— 因为 part 是**就地刷写**的，不搬到 `$loadaddr`。

`httpd_format_ubi` 是去掉 `reset` 的 `ubi_format`，好让同一次会话接着写卷。

**TFTP 一条没删**：bootmenu 的第 2、4、5、6 项照旧，`boot_tftp*` 全套变量都在。自动路径走浏览器，手动路径留 TFTP。

### `952` 改了什么

菜单原来看不出这是哪来的固件 —— 和一份原厂 UBI 引导长得一模一样，进到菜单里的人也没有路径找回项目。

```
bootmenu_title=  ... ( ( ( OpenWrt-Web 0.1.0 ) ) )    ← 加了网页 U-Boot 版本号
bootmenu_8=\e[31mStart web recovery server (http://192.168.1.1)\e[0m=httpd ; run bootmenu_confirm_return
bootmenu_9=About - github.com/Loong1996/ImmortalWrt-XG-040G-MD=run show_about ; run bootmenu_confirm_return
show_about=echo ; echo Web recovery U-Boot by Loong ; echo Project: ... ; echo Author: ... ; echo
```

外加 `httpd_start_server()` 开头多打一行版本与仓库地址，给看串口、不看网页的人。

几处需要知道的：

- **屏幕上显示 9 和 10，env 里是 `bootmenu_8` / `bootmenu_9`。** `cmd/bootmenu.c` 的快捷键是 `'1' + index`，下标 0 那项画成「1.」。
- **第 10 项画出来是「a.」不是「10.」。** 快捷键只有一个字符：1–9 之后接 a–z，0 留给 Exit。所以仓库地址写在标题里而不是藏在按键后面 —— 不按也要能看见，按下去才补上作者页。
- **第 9 项是红的**，和写引导器的那两项同色：它是刷机入口，且一旦进去，机器就离开菜单直到被中断。
- **版本号写了两遍**：`bootmenu_title` 里一份，`net/httpd.c` 的 `WEB_VERSION` 一份。env 是纯文本，看不见 C 宏。两处都在 `952` 这一个补丁里，改的时候一起改。

> **老机器升级引导器后看不到新菜单，这是正常的。**
>
> `CONFIG_ENV_IS_IN_UBI`：`ubootenv` 卷里存的是**完整一份**环境，加载时整个盖掉编译进固件的默认值。已经初始化过 env 的机器换了新 FIP，菜单还是旧的 —— 新加的 `bootmenu_8` / `bootmenu_9` 根本不在它的环境里。
>
> 要让新默认值生效，二选一：菜单里跑一次**第 8 项** `Reset all settings to factory defaults`，或者网页刷机时勾上**先重建 UBI**（后者连出厂 MAC 一起擦，只在首次迁移时才该勾）。首次迁移过来的机器走 `_firstboot`，直接就是新的。

---

## 几个关键决定

### 用 U-Boot 自己的 TCP，不移植 uIP

tcboot 里嵌了 uIP 0.9（响应头 `Server: uIP/0.9`），因为它的基础 U-Boot 还没有 TCP 栈。现代 U-Boot 有 `net/tcp.c`，`net/fastboot_tcp.c` 就是现成的 TCP 服务器模板。

| | 移植 uIP | 用自带 TCP |
| --- | --- | --- |
| 新增代码 | ~4000 行 | ~130 行（202 的规模） |
| 与 tftpboot / dhcp 共存 | 要处理两套栈抢网卡 | 天然共存 |
| 上游可维护性 | 长期背一份 fork | 跟着上游走 |

### 零拷贝

`rx()` 回调给的是**流偏移**，所以可以直接 `memcpy` 到 `$loadaddr + offset`，几十 MB 的镜像不需要第二份内存。各个 part 也是**就地刷写**，不搬移 —— 只在刷之前按 64 字节向前对齐一下，踩到的是它自己的 multipart 头（最短也有 ~90 字节），碰不到前一个 part 的数据。

### 刷写逻辑留在 env 里，但不依赖它

每一步优先跑 env 脚本，找不到就用编译进二进制的等价命令。这不是冗余 —— 见下面的坑。

### 面板灯是刷写阶段唯一的通道

写入是同步阻塞的，`net_loop()` 的 timeout handler 那时已经停了。闪灯靠 cyclic 框架驱动：SPI-NAND 层每写一页调一次 `schedule()`（`drivers/mtd/nand/spi/core.c`），所以 64 MB 的写入过程中灯照样闪。

`CONFIG_CYCLIC_MAX_CPU_TIME_US` 默认 5000 μs，写 5 个 GPIO 够不着。万一超了会打印 `cyclic function httpd-flash took too long` 并注销回调 —— **灯停在某个状态，但刷写完全不受影响，别当成死机去断电。**

### 二次确认只拦不可逆的两种

不做笼统的「确定要刷吗」。走到那个按钮已经过了按住 reset 上电、插网线、开浏览器、选文件四道门，不存在误点；救砖时多一次点击只是多一个出错环节，而每次都弹的确认框两次之后就变成条件反射。

拦的是**重来一次也救不回**的两种：

| 情况 | 后果 |
| --- | --- |
| 文件名对不上 | `.itb` 进了 BL2 格 → 写到 flash `0x800`，BootROM 认不出 → **只能串口 xmodem** |
| 勾了重建 UBI | 出厂 MAC、U-Boot 环境、全部设置一起没 |

刷错固件不在此列 —— 那种情况机器还能再进这个页面重来。

文件名检查按扩展名（`.itb` / `preloader*.bin` / `.fip`），**只提醒不拦死**，文件名是可以被改的。

---

## 踩过的坑

### 1. `simple_strtoul()` 不跳前导空白

```
httpd: refusing 0 byte upload
```

`Content-Length: 12345` 从冒号后解析，U-Boot 的 `simple_strtoul()` 遇到空格直接返回 0（`lib/strto.c` 只处理 `0x` 前缀），和 libc 的行为不一样。

**这个坑差点被测试掩盖过去** —— 桩代码用的是 libc 的 `strtoul`，它会跳空白，所以本地全过、真机必挂。后来把桩改成忠实复现 U-Boot 的行为，才在本地复现出同一条错误信息。**桩要模仿被测环境的怪癖，不是模仿正确行为。**

### 2. 救砖工具不能依赖 flash 上的 env

```
## Error: "httpd_write_bl2" not defined
```

机器上一次测试时 `_firstboot` 建过 `ubootenv` 卷并 `saveenv`，那份旧 env 会盖掉 fip 里编译进去的默认值。**救砖工具依赖 flash 上的 env，而 flash 上的 env 恰恰是最可能过时或损坏的那份** —— 需要救砖的时候，正是它靠不住的时候。

现在每步都有内置兜底。

好在 BL2 是第一步，它一失败整个序列就中止，UBI 没被格式化、`fit` 卷完好 —— 「引导器先于固件」这个顺序在这里兜住了。

### 3. 分类要放在 `on_rcv_nxt_update()`，不能放 `rx()`

`rx()` 收到的第一个 TCP 段可能短于 4 字节，`memcmp(buf, "POST", 4)` 就越界了。`on_rcv_nxt_update()` 保证 `[0..rx_bytes-1]` 已经连续到齐。

这个是**测试抓出来的**，用 `chunk=1`（每次只喂 1 字节）跑的时候暴露。

### 4. defenv 的 patch context 要从 fork 里取

从 `openwrt/openwrt` 抄的 context 里 `bootfile*` 是 `openwrt-` 前缀，ImmortalWrt 是 `immortalwrt-` —— `Hunk #1 FAILED`，白等一个半小时。

**改哪棵树就从哪棵树取 context。**

### 5. 编译期宏的中文不要用 `\x` 转义

页脚一度显示 `U-Boot ç½é¡µæç `。生成补丁的脚本里我用了 `'\xe7\xbd\x91'` 写「网」，Python 把它当成三个 Latin-1 字符，写文件时又编了一遍 UTF-8：

```
应该是:  e7 bd 91           网
实际是:  c3 a7 c2 bd c2 91  ç½
```

现在源码里直接写中文，并加了一条检查：不许出现 `c3 a7 c2` 这类双重编码序列。

### 6. 验证判据本身也会错

给 `999` 测试补丁写验证方法时，我说「看串口有没有打印 `*** TEST BUILD ***`」。它永远不会出现 —— `bootcmd` 只有经 bootmenu 第 0 项才会被执行，而那个补丁把 `bootmenu_delay` 设成了 `-1`，菜单根本不往下走。正确判据是「停在菜单上」。

**一个编译要一个半小时，判据写错的代价和代码写错一样大。**

---

## 验证方式

每次改动都跑三层，因为真机编译一次约 1.5 小时：

1. **语法** —— 用一套桩头文件 `gcc -fsyntax-only -Wall -Wextra`
2. **行为** —— 17 个用例，覆盖 multipart 解析（含 1 字节碎片、2 MB、payload 里混入 boundary 前缀）、多文件上传、刷写序列与对齐、内置兜底、DHCP、失败重试、自动重启
3. **补丁** —— `patch -p1 --dry-run` 打到真实的 U-Boot 源码上，再比对应用结果与被测源码**逐字节一致**

页面另外还有：HTML 标签配对检查、`node --check` 校验每一段内联 JS、以及把真实的 `up()` 函数拿到 node 里跑确认对话框的各种状态。

刷之前从 fip 里解出 U-Boot 二进制核对一遍：

```bash
python3 - "$FIP" <<'EOF'
import sys, lzma
d = open(sys.argv[1], 'rb').read()
off = 0x10
while off + 40 <= len(d):
    uuid = d[off:off+16]
    o = int.from_bytes(d[off+16:off+24], 'little')
    sz = int.from_bytes(d[off+24:off+32], 'little')
    if uuid == b'\0' * 16:
        break
    blob = d[o:o+sz]
    if blob[:1] == b'\x5d':                       # FIP 第二段是 LZMA 压的 U-Boot
        open('uboot.bin', 'wb').write(
            lzma.LZMADecompressor(lzma.FORMAT_ALONE).decompress(blob))
    off += 40
EOF
strings -a uboot.bin | grep -E 'U-Boot 20'        # 版本串带源码 commit
strings -a uboot.bin | grep -E '^(check_buttons|boot_ubi|httpd_)'
```

版本串里嵌着源码的 commit sha，可以确认刷的到底是哪一版。中文要按 UTF-8 字节搜（`grep -a`），`strings` 只认 ASCII。

---

## 还没做的

* **刷写进度做不到。** 不是没做，是结构上不行：`net_loop()` 在写入开始前就返回，连接已关，页面轮询没人应答。要做就得把刷写拆进网络循环里分块跑 —— 那是把一条简单可靠的救砖路径换成一个状态机，对救砖场景不划算。
* **推上游。** `206` 是实打实的 bug 修复，值得提给 immortalwrt；httpd 这套是否适合上游还没想好。
