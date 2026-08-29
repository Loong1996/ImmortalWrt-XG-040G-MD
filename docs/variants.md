# 设备变体（分区布局与刷机方式）

实质是**三种分区布局**。25.12 线固定一种；master 线在 `Run workflow` 时用 **device_variant** 输入三选一（`tcboot` / `stock` / `ubi`，默认 `tcboot`），workflow 会自动改写 `.config` 的设备符号，25.12 分支则忽略该输入并给出 warning。

| 变体 | 分支 | 引导程序 | rootfs 空间 | MAC 来源 | 可回退原厂 |
| --- | --- | --- | --- | --- | --- |
| `tcboot` | master | 第三方 `tcboot.bin` | **255 MB** | ubi 的 `ri` 卷，缺失则随机 | 否 |
| `stock` | master | **原厂，不动** | 129 MB | 原厂 `ri` 分区 | **是** |
| `ubi` | master | OpenWrt U-Boot | **255.875 MB** | ubi 的 `ri` 卷，缺失则随机 | 否 |
| （`bell_xg-040g-md`） | 25.12 | 第三方 `tcboot.bin` | **255 MB** | 无，随机生成 | 否 |

Release 的标题、正文与 tag 都会标出本次用的变体，例如 `XG-040G-MD-tcboot-1G-20260826-42`；25.12 线只有一个设备，tag 不带变体段。

## `tcboot` —— 第三方引导，空间最大

```
0x00000000   512 KB   bootloader    ← 第三方 tcboot.bin
0x00080000   512 KB   env
0x00100000   255 MB   ubi           ← kernel + rootfs + overlay
```

* **前提**：机器已刷入 [Nwrt 提供的 `tcboot.bin`](https://nwrt.kuroneko.host/flashdocs/XG-040G-MD.html)
* 刷机用附件 `factory.bin`，日常升级用 `sysupgrade.bin`
* 原厂分区表整片被覆盖 —— `romfile`、`nsb_1`/`nsb_2`、`bosa`、`ri`、`config`、`data` 全部消失
* MAC 取自 ubi 中名为 `ri` 的卷，但**该卷不存在时会退化为随机 MAC，不影响启动**。这一步由 `preinit` 钩子在用户态完成，不是 dts 里的 nvmem —— 后者在缺卷时会让网络驱动永久停在 deferred probe，整机失联
* 因此**什么时候补上 `ri` 卷都可以**：`ubimkvol` + `ubiupdatevol` 写入后重启即生效，不需要重刷固件
* 没有 `ri` 卷时随机生成的 MAC 会固化在 `/etc/xg-040g-md-mac`，重启与 `sysupgrade` 后保持不变；恢复出厂设置会重新生成
* 与 25.12 线的 `bell_xg-040g-md` 分区表逐项一致，且声明了 `SUPPORTED_DEVICES += bell,xg-040g-md`，**可从 25.12 固件直接 sysupgrade 过来**
* 本变体**不含 `uboot-envtools`**，原因见下方「关于 `tcboot.bin` 这个引导程序」

# 关于 `tcboot.bin` 这个引导程序

`tcboot.bin` 不是本项目构建的，以下信息由对二进制的分析得出：

| | |
| --- | --- |
| 基础 | [pepe2k/u-boot_mod](https://github.com/pepe2k/u-boot_mod) 的 Web 恢复界面移植到 Airoha AN7581 |
| U-Boot 版本 | 2025.01，构建于 2025-10-01 09:07:19 +0800 |
| 自定义版本号 | `uboot2.0 version:25.10.01` |
| 结构 | ATF FIP @ `0x800`：BL2 + 6 个签名证书 + BL31(LZMA) + U-Boot(LZMA, 752272 字节) |
| `bootext.ram` | 同一 FIP 但只含 BL2 + 证书，走 BootROM 的 RAM 加载预加载器 |

二进制里没有嵌入构建者的用户名或主机名。U-Boot 是 GPLv2，如需源码可向分发方索取。

## tcboot 的板级来源：Airoha EVB，不是本设备

解出 U-Boot 内嵌的 DTB（6032 字节）后，`model` 与 `compatible` 说明了一切：

```
model      = "Airoha EN7581 Evaluation Board"
compatible = "airoha,en7581-evb", "airoha,en7581"
```

**它用的是 Airoha 官方评估板的板级配置，不是 `nokia,xg-040g-md`**，整个二进制里也没有一处 `openwrt` / `immortalwrt` 字样。所以 **tcboot 不是从 OpenWrt 的 `uboot-airoha`（即 `ubi` 变体那个）改出来的** —— 后者是 `bl2 128K + ubi 255.875M`，布局完全不同，两者各走各的。

因果关系其实是反过来的：**tcboot 变体的分区表就写在 EVB 的 DTB 里**，本项目的 DTS 是按它反向对齐的。

```
partitions {
    bootloader@0    reg = <0x0      0x80000>    label = "bootloader"
    ubootenv@80000  reg = <0x80000  0x80000>    label = "env"
    ubi@100000      reg = <0x100000 0x0>        ← size=0，吃掉剩余全部
}
```

DTB 里确实带了 AN7581 该有的东西（NPU 的五段 `reserved-memory`、`atf-reserved-memory@80000000` 256K、PCS、switch、`airoha,en7581-snand`），但**设备级的东西一个都没有**。

### 一个根因解释四个怪现象

本文档记录的几个 tcboot 特有行为，原先看着是孤立瑕疵，其实都是同一个病因 ——「EVB 通用配置没有为这台设备适配」：

| 现象 | 根因 |
| --- | --- |
| `bootargs` 里 `root=/dev/ubiblock0_1` 按卷号硬编码 | EVB 通用配置，未做设备定制 |
| MAC 只能靠 preinit 从 ubi 的 `ri` 卷读 | EVB 的 DTB 里根本没有 nvmem / MAC 节点 |
| `memory` 写死 512M（`0x80000000` + `0x20000000`） | EVB 默认值，全靠 `bootm` 时 fixup 覆盖 |
| `env` 分区从未被写过、CRC 无效 | DTB 里定义了 512K，但 EVB 的默认环境是编译进去的 |

> 💡 以后再遇到 tcboot 的异常行为，第一反应应该是「EVB 的配置里有没有这东西」，而不是当成单独的 bug 去查。

### 网络栈：uIP，不是 lwIP

HTTP 响应头里是 `Server: uIP/0.9`。这说明作者是把 [u-boot_mod](https://github.com/pepe2k/u-boot_mod) 的 `httpd` 模块**连同 uIP 协议栈整体搬到了 U-Boot 2025.01**，而不是基于 U-Boot 自己的网络栈重写 —— u-boot_mod 基于的老 U-Boot 没有 TCP，所以自带了 uIP。

对「要不要给 `ubi` 变体补一个同样的网页救砖」而言这是好消息：uIP 是自包含实现，只依赖底层收发包接口，移植面很窄；而且 tcboot 已经证明这套代码能在 U-Boot 2025.01 + AN7581 上跑通。

另外，tcboot 的 U-Boot 里可用的网络命令只有 `bootp` / `dhcp` / `httpd` / `ping` / `tftpboot` / `tftpput` —— **没有 `tftpsrv`**（`CONFIG_CMD_TFTPSRV` 未启用）。

**网页救砖入口**：按住 reset 键上电，U-Boot 会在 `192.168.1.1` 启动 HTTP 服务器，提供三个上传端点 —— `firmware`（整机固件）、`spinand`（裸 flash）、`uboot`（引导本身）。这是比串口方便得多的恢复方式。

**内置默认环境**（`env` 分区 CRC 无效时 U-Boot 使用的值）：

```
loadaddr=0x81800000
ipaddr=192.168.1.1
serverip=192.168.1.10
bootargs=ubi.mtd=ubi root=/dev/ubiblock0_1 rootwait
bootdelay=3
bootcmd=echo "Booting from UBI..." && ubi part ubi && ubi read $loadaddr kernel && echo "Starting kernel..." && bootm $loadaddr
reset_factory=eraseenv && reset
```

> ⚠️ **不要在本变体上执行 `fw_setenv`。** `env` 分区从未被写过、CRC 无效，是**安全状态** —— U-Boot 会回落到上面这份正确的内置默认值。而 OpenWrt 的 `fw_setenv` 在 CRC 无效时用的是编译进它自己的通用默认值（`bootcmd=run distro_bootcmd`），一旦执行就会把这份与本机无关的环境连同正确的 CRC 写进 flash，U-Boot 从此不再使用内置默认值，直接掉进命令行。**整个过程不报错、返回 0，重启才失联。** 正因如此本变体已移除 `uboot-envtools` 整包。真需要可写的 env 时，先在 U-Boot 命令行执行一次 `saveenv`。

> 💡 `bootargs` 里的 `root=/dev/ubiblock0_1` 是**按卷号硬编码**的（kernel 是按卷名读取，不受影响）。因此 **UBI 卷的顺序不能改** —— 在 kernel 之前插入任何卷都会把 rootfs 顶到 2 号，导致 `Waiting for root device /dev/ubiblock0_1...` 卡死。

**串口救砖**：`Hit any key to stop autoboot` 时按键进入命令行，可用

```
setenv bootargs 'ubi.mtd=ubi root=/dev/ubiblock0_2 rootwait'   # 卷号错位时临时纠正
run bootcmd
```

`reset_factory` 等价于 `eraseenv && reset`。

## `stock` —— 寄生原厂分区，唯一可回退

```
0x00000000   512 KB    bootloader   原厂，不动
0x00080000   256 KB    romfile      不动
0x000c0000   40.5 MB   nsb_1        ← kernel (8 MB) 写这里
0x02940000   40.5 MB   nsb_2        原厂备份 bank，不动
0x051c0000   256 KB    bosa         光模块校准数据，不动
0x05200000   256 KB    ri           MAC / 序列号，不动
0x052c0000   10 MB     config       原厂配置，不动
0x05cc0000   129 MB    data         ← rootfs UBI 写这里
0x0e1a0000   10 MB     log          不动
```

* **不碰引导程序，变砖风险最低**
* MAC 从原厂 `ri` 分区经 nvmem 读取，是真实硬件 MAC，不需要任何脚本
* 保留 `nsb_2` 备份 bank 与全部出厂数据，**是唯一能刷回原厂固件的变体**
* 刷机用附件 `factory-kernel.bin` + `factory-rootfs.bin`
* 代价：rootfs 空间只有 129 MB（其余三种是 255 MB）

## `ubi` —— OpenWrt U-Boot，带救援镜像

```
0x00000000   128 KB      bl2
0x00020000   255.875 MB  ubi
```

* **会替换引导程序**。附件 `preloader.bin` 与 `bl31-uboot.fip` 需经 USB-TTL 走 BootROM 恢复流程刷入
* 这两个附件由 workflow 自动构建：`uboot-airoha` 的 `BUILD_DEVICES:=nokia_xg-040g-md-ubi` 会在选中该变体时自动勾选 U-Boot 包，它再拉 ATF 的 `trusted-firmware-a-an7581-bl31`，最后由 `fiptool` 打成 FIP
* 额外产出 `*-recovery.itb`，是 initramfs 救援镜像，另外三种变体都没有
* 升级用 `sysupgrade.itb`
* 原厂 `ri` 与 `bosa` 由官方转换流程转存为同名 UBI 卷，MAC 得以保留
* 与 `tcboot` 一样，`ri` 的读取由 preinit 钩子在用户态完成，**没转存 `ri` 卷也能正常启动**（退化为随机 MAC）；转存过则拿到真实硬件 MAC

## 互相能不能升级

| 从 → 到 | 可否 |
| --- | --- |
| 25.12 `bell` → master `tcboot` | **可以直接 sysupgrade**（分区表一致 + `SUPPORTED_DEVICES`） |
| `tcboot` ↔ `stock` | 不可以，分区表完全不同，需完整刷机 |
| `tcboot` ↔ `ubi` | 不可以，引导程序不同，需完整刷机 |
| `stock` ↔ `ubi` | 不可以，需完整刷机 |

> ⚠️ **`tcboot` 与 `ubi` 都会覆盖原厂引导和原厂分区表。** 其中 `ri`（MAC、序列号）与 `bosa`（光模块校准）是逐机唯一的出厂数据，没有公开来源。**刷这两种之前务必做整片 flash 备份**，参见[原厂分区备份教程](https://www.right.com.cn/forum/thread-8467912-1-1.html)。
>
> ✅ **`tcboot` 变体已实机验证**：分区偏移与 `UBINIZE_OPTS` 正确，能引导、进系统，四个网口与 NPU、EN8811H 均正常。早期版本因 ubi 中缺少 `ri` 卷导致网络驱动永久 deferred probe，已通过去掉 dts 里的 nvmem 硬依赖、改由 preinit 钩子在用户态读取该卷解决。
>
> ⚠️ 25.12 线的 `bell_xg-040g-md` 没有声明 `all_flash` 分区，**在跑着的系统里无法直接 dd 整片 flash**；master 的三个变体都有。

## 内存容量

原厂是 512M 颗粒。换过 1G / 2G 的机器**不需要单独编固件** —— workflow 的内存容量默认是 **自适应**。

原理：DTS 的 `memory` 节点只写 512M 作保底，标准 U-Boot 在 `bootm` 时会把自己探测到的真实容量 fixup 进 DTB，把这个保底值覆盖掉。

实测（`tcboot` 变体、1G 颗粒、刷的是 **512M 档**编出来的固件）：

```
U-Boot:  DRAM:  1 GiB
内核:    Initmem setup node 0 [mem 0x0000000080200000-0x00000000bfffffff]
         Memory: 948576K/1046528K available
```

`0xbfffffff` 是 1G 的末地址（512M 会停在 `0x9fffffff`），总量 1022MB —— fixup 确实生效。

| 变体 | 引导程序 | 自适应 |
| --- | --- | --- |
| `tcboot` | 第三方 U-Boot 2025.01 | ✅ 实测有效 |
| `ubi` | OpenWrt 自建 U-Boot | 同为标准 U-Boot，未实测 |
| `stock` | 原厂引导程序 | 未验证，换过颗粒建议手动指定 |

手动指定 `512M` / `1G` / `2G` 时，DTS 的 `memory` 被写死成该容量。**这时刷进更小颗粒的机器会起不来** —— 内核按 DTB 去访问不存在的物理地址。反过来（小容量固件刷大颗粒机器）只是白白浪费内存，不会出事。

### 两个属性的分工

```
/memory 的 reg                      声明有多少内存   ← 真正决定容量的
chosen/linux,usable-memory-range    最多用到哪一段，取交集，只减不增
```

`usable-memory-range` 走内核的 `memblock_cap_memory_range()`，那个函数体里全是 `memblock_remove_*`，**只能往少了裁，不会凭空多出内存**。所以本项目把它固定在 2G 的值，对任何容量都不构成裁剪，同时保住起点 `0x80200000` —— 那是上游给 ATF 那 2MB 的第一道保护，比 `reserved-memory` 的 `no-map` 更早生效（前者在 `setup_machine_fdt()` 里，后者要等到 `arm64_memblock_init()` 末尾）。

