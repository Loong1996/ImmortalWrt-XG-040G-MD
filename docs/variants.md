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
