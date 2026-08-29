# U-Boot 网页救砖（进行中）

给 `ubi` 变体的 OpenWrt U-Boot 加一个浏览器上传固件的界面，让它在救砖体验上追平第三方 `tcboot`。

> **状态**：第 1 步已实机验证通过 —— U-Boot 自带的 TCP 栈在 AN7581 上能跑，网页能打开。第 2 步（上传与刷写）开发中。
> **源码分支**：[`Loong1996/immortalwrt` 的 `master-XG-040G-MD-httpd`](https://github.com/Loong1996/immortalwrt/tree/master-XG-040G-MD-httpd)，与 `master-XG-040G-MD` 的差异只有 `uboot-airoha` 的三个 patch。
> **编译**：`Run workflow` 的编译分支选 `master-XG-040G-MD-httpd`，设备变体选 `ubi`。

## 为什么做这件事

`ubi` 变体在别的方面都优于 `tcboot`（设备级适配、可复现构建、上游同步、少一个 out-of-tree 补丁，见[设备变体](variants.md)），唯一的短板是**免串口救砖的门槛**：

| | tcboot | 官方 ubi |
| --- | --- | --- |
| 用户要做什么 | 浏览器打开 `192.168.1.1`，选文件，点上传 | 装 TFTP **服务器**、网卡设 `192.168.1.254`、文件名一字不差 |
| 出错反馈 | 网页上有进度 | 只有电源灯 + 串口日志 |

对不接串口的人来说 TFTP 那套是个黑盒 —— `bootfile` 默认叫 `immortalwrt-airoha-an7581-nokia_xg-040g-md-ubi-initramfs-recovery.itb`，名字错一个字符就静默失败。

## 官方 U-Boot 已经有的救砖能力

动手之前先把现成的东西摸清楚了，结论是**功能覆盖上官方比 tcboot 更全，缺的只是网页这个前端形式**。以下均来自对官方 `bl31-uboot.fip` 的二进制分析（解出 LZMA 段后提取字符串）。

**按键触发的 TFTP 恢复**（不需要串口）：

```sh
bootcmd=run check_buttons ; run boot_ubi
check_buttons=if button reset ; then run boot_tftp ; fi
```

**引导失败自动无限重试**（连按键都不用）：

```sh
boot_ubi=run boot_production ; run boot_tftp_forever
boot_tftp_forever=led $bootled_status on ; while true ; do run boot_tftp ; sleep 1 ; done
```

**连引导自身都能远程更新**：

```sh
boot_tftp_write_bl2=mw.b $loadaddr 0xff 0x800 ; setexpr loadaddr_bl2 $loadaddr + 0x800 ; \
                    tftpboot $loadaddr_bl2 $bootfile_bl2 && run mtd_write_bl2
boot_tftp_write_fip=tftpboot $loadaddr $bootfile_fip && run ubi_write_fip && run reset_factory
```

> 💡 `mw.b $loadaddr 0xff 0x800` 印证了 AN7581 BootROM 的固定约定：**flash 上 BL2 分区的前 `0x800` 字节留空，真正的 FIP 从 `0x800` 开始**。这和拆 `tcboot.bin` 时发现的「ATF FIP @ `0x800`」完全一致。

**UBI 卷由 U-Boot 自己创建**，`ri` / `bosa` 空卷会被自动补上，MAC 在 U-Boot 层就从 `ri` 卷读出来（这是上游 `uboot-airoha: add readmem command` 那个提交的用途）：

```sh
ethaddr_factory=ubi read 0x90000000 ri && env readmem -b ethaddr 0x9000003e 0x6
ubi_create_board_data=ubi check bosa || ubi create bosa 0x40000 || run ubi_format ; \
                      ubi check ri   || ubi create ri   0x40000 || run ubi_format
```

**所以这个项目要补的只有一个 HTTP 前端**，刷写逻辑全部复用现成的环境脚本。

## 技术选型：用 U-Boot 自带的 TCP，不移植 uIP

`tcboot` 的网页救砖用的是 uIP —— HTTP 响应头里写着 `Server: uIP/0.9`。它是把 [u-boot_mod](https://github.com/pepe2k/u-boot_mod) 的 `httpd` 模块**连同整个 uIP 协议栈**搬到 U-Boot 2025.01 的，因为它基于的老 U-Boot 没有 TCP。

而 U-Boot 自 2020 年起传统网络栈就带 TCP（`net/tcp.c`），`net/fastboot_tcp.c` 是现成的 TCP 服务器范例。

| | 移植 uIP（tcboot 的路） | 用 U-Boot 自带 TCP |
| --- | --- | --- |
| 引入代码 | uIP 0.9 约 3000 行 + httpd 1000 行 | 只写 httpd，约 130 行 |
| 网络栈 | 第三方，与 U-Boot 的并存 | U-Boot 自己维护的 |
| 影响现有功能 | 需处理收发接管 | 无，`tftpboot`/`dhcp`/`bootmenu` 照常 |
| 上游可接受度 | 低 | 高 |

`uboot-airoha` 里已有 `200-cmd-bootmenu-custom-title.patch`、`201-cmd-env-readmem.patch` 这类上游自定义命令，加功能是被接受的做法。

### 实现骨架

```c
static int on_create(struct tcp_stream *tcp)
{
	if (tcp->lport != 80)
		return 0;
	tcp->rx = httpd_rx;                     /* 数据落到 $loadaddr */
	tcp->tx = httpd_tx;                     /* 吐页面 */
	tcp->on_rcv_nxt_update = ...;           /* 解析请求 */
	tcp->on_snd_una_update = ...;           /* 发完并确认后关连接 */
	return 1;
}
```

两个关键细节：

* `tcp->rx` 的 `rx_offs` 是**流内偏移**，所以固件数据可以直接落到 `$loadaddr + (rx_offs - body_start)`，**不需要几十 MB 的中间缓冲**。
* 关连接必须放在 `on_snd_una_update`，不能放 `tx` —— `struct tcp_stream::tx` 的注释明确警告在 tx 回调里调 `tcp_stream_close()` 会破坏流。
* `tcp->priv` 用作**每连接**的状态标志，不能用全局变量：浏览器会同时开好几个连接（favicon、预取），全局标志会互相踩。

## 三个 patch

放在 `package/boot/uboot-airoha/patches/`：

| patch | 作用 |
| --- | --- |
| `202-net-add-minimal-httpd-server.patch` | 新增 `net/httpd.c`；`enum proto_t` 加 `HTTPD`；`net_loop()` 分发；`net/Kconfig` 加 `CMD_HTTPD` |
| `950-configs-xg-040g-md-enable-httpd.patch` | defconfig 开 `CONFIG_PROT_TCP` 与 `CONFIG_CMD_HTTPD` |
| `999-defenvs-...-TESTBUILD-no-autoboot.patch` | **仅测试用**，见下方警告 |

> ⚠️ **编号必须大于 401。** `configs/an7581_nokia_xg-040g-md_defconfig` 与 `defenvs/an7581_nokia_xg-040g-md_env` 都是 `401-add-nokia-xg-040g-md.patch` 创建的，编号更小的 patch 应用时这两个文件还不存在。

## 第 1 步：在内存里验证，不碰 flash

把 U-Boot 灌进 DRAM 跑，**flash 一个字节都不动**，断电重启就回到 tcboot。零风险，还绕开了「换引导」的鸡生蛋问题（BL2 要从 UBI 的 `fip` 卷加载 U-Boot，而 `fip` 卷要 U-Boot 起来才能建）。

```
① BootROM ──收 preloader.bin──→  SRAM 里跑，初始化 DDR
② BL2     ──收 bl31-uboot.fip──→ U-Boot 在 DRAM 跑起来
                                  ↑ flash 仍是原样，断电即回滚
③ 串口敲 httpd，浏览器验证
```

### ⚠️ 必须先掐掉默认环境里的自动流程

官方默认环境是**为全新板子写的**，第一次上电会自动格式化 flash：

```sh
bootmenu_delay=0   # cmd/bootmenu.c: "If delay is 0 do not create menu, just run first entry"
bootmenu_0=Initialize environment.=run _firstboot
_firstboot     -> _init_env -> ubi_create_env
ubi_create_env -> ubi create ubootenv ... || run ubi_format
ubi_format     -> mtd erase ubi
```

在还跑着 tcboot 的机器上：新 U-Boot 的 DTB 认为 `ubi` 分区从 `0x20000` 起，那里不是有效 UBI → attach 失败 → 建卷失败 → **`mtd erase ubi` 擦掉 `0x20000` 往上的一切**。而 tcboot 的 FIP 占 `0x0~0x80000`，会被拦腰截断。再加上 `bootdelay=0`，**没有打断的机会**。

`999` 那个 patch 就是把四处改成无害值：

| | 官方原值 | 测试值 |
| --- | --- | --- |
| `bootcmd` | `run check_buttons ; run boot_ubi` | 无害 echo |
| `bootdelay` | `0` | `3` |
| `bootmenu_delay` | `0` | `-1`（永远等用户选） |
| `bootmenu_0` | `run _firstboot` | 无害 echo |

**验证通过后要删掉它**，正式固件需要那些自动流程。

### 刷之前先验二进制

不用拿机器试，编完直接查 fip 就能确认三个 patch 是否生效：

```sh
# 找 LZMA 段解出 U-Boot（FIP 里第二段是 U-Boot，第一段是 BL31）
python3 -c "
import struct,lzma,sys
d=open(sys.argv[1],'rb').read(); pos=0
while True:
    i=d.find(b'\x5d\x00\x00',pos)
    if i<0: break
    u=struct.unpack('<Q',d[i+5:i+13])[0]
    if 0<u<8*1024*1024:
        out=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE).decompress(d[i:])
        open(f'uboot-{i:06x}.bin','wb').write(out); print(hex(i),len(out))
    pos=i+1
" bl31-uboot.fip

strings -n 6 uboot-*.bin | grep -E '^httpd$|U-Boot HTTP server is alive'          # 202/950
strings -n 6 uboot-*.bin | grep -E '^(bootcmd|bootdelay|bootmenu_delay|bootmenu_0)='  # 999
```

### 验证结果 ✅

实测（`ubi` 变体、灌内存不刷 flash）：

* U-Boot 体积 `771920 → 779096`（+7176 字节），就是 httpd 加 TCP 栈的重量；FIP `314013 → 317314`，而 `fip` 是 1 MB 静态卷，空间毫无压力
* U-Boot 起来后**停在 bootmenu 等待**（`bootmenu_delay=-1` 生效），按 **ESC** 进命令行
* `setenv ipaddr 192.168.1.1` 后敲 `httpd`，浏览器打开 `http://192.168.1.1` 正常显示页面

于是确认：**U-Boot 自带的 TCP 栈在 AN7581 上工作正常，网卡在 U-Boot 阶段正常，不需要引入 uIP。**

> 💡 `setenv ipaddr` 不能省 —— 默认环境里只有 `serverip` 没有 `ipaddr`，而 `net_loop()` 对 `HTTPD` 会检查它。

## 踩过的坑

**一、patch 的 context 必须取自 ImmortalWrt，不能用 OpenWrt 上游。** 两边的 `defenvs` 里 `bootfile*` 前缀不同：

```diff
-bootfile=openwrt-airoha-an7581-nokia_xg-040g-md-ubi-initramfs-recovery.itb
+bootfile=immortalwrt-airoha-an7581-nokia_xg-040g-md-ubi-initramfs-recovery.itb
```

第一版 `999` 的 Hunk #1 正好把这三行当 context 用了，编译到 U-Boot 阶段才 `Hunk #1 FAILED`，白跑一个半小时。改 `net/*`、`defconfig` 这类两边一致的文件不受影响。

**二、`bootcmd` 不是直接执行的。** 它通过 bootmenu 的第 0 项间接触发：

```sh
bootmenu_0d=Run default boot command.=run boot_default
boot_default=run bootcmd ; run boot_tftp_forever
```

所以 `999` 里改的那句 `bootcmd` echo **永远不会出现**（`bootmenu_delay=-1` 让第 0 项不再自动执行）。判断 `999` 是否生效的正确依据是**停在菜单不动**，不是看那行日志。

**三、workflow 的分支匹配是精确的。** `Generate Variables` 里原本是 `case "$REPO_BRANCH" in master-XG-040G-MD)`，新分支会掉进 `*)` 被当成 25.12 线处理，用上 `bell_xg-040g-md` 和 6.12 的配置。已改为前缀匹配 `master-XG-040G-MD*)`。

## 后续

**第 2 步：上传与刷写。** 三件事 —— 解析 `multipart/form-data` 找到文件数据起点；数据按流内偏移直接落 `$loadaddr`；收完 `setenv filesize` 并 `run ubi_write_production`。后端不用自己写，官方脚本已经把删旧卷、建新卷、`iminfo` 校验都做好了，比 tcboot 手拼的 `mtd write` 更完善。

未验证的风险：**U-Boot 的 TCP 是简化实现**，重传和窗口处理都比较原始，几十 MB 的 POST 是另一回事。先用几 MB 的小文件验证通路，再上完整固件试稳定性。

**第 3 步：改触发方式。** 把默认环境里的 `check_buttons` 指向 httpd，按住 reset 上电就出网页：

```sh
check_buttons=if button reset ; then led $bootled_status on ; httpd ; fi
```

这一步要等第 2 步验证通过再做 —— 否则万一 httpd 有问题，就把唯一的免串口救砖入口给堵了。
