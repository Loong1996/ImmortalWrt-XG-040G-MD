# ImmortalWrt for XG-040G-MD

ImmortalWrt firmware for NOKIA BELL XG-040G-MD

编译脚本基于 [dalutou/OpenWrt-for-XG-040G-MD](https://github.com/dalutou/OpenWrt-for-XG-040G-MD) 修改。

### 项目说明

* 固件源码使用 [Loong1996/immortalwrt](https://github.com/Loong1996/immortalwrt)，fork 自官方 [immortalwrt/immortalwrt](https://github.com/immortalwrt/immortalwrt)，设备支持压缩为单个提交叠在上游之上，便于持续跟进。设备补丁最初来自 [fzs209/immortalwrt](https://github.com/fzs209/immortalwrt)。
* 闪存适配（SkyHigh S35ML02G300 与 Fudan Micro FM25G02B）：25.12 线的 SkyHigh 支持仍由本项目自带（`backport-6.12/430`、`431`，源自 [xiangtailiang/openwrt](https://github.com/xiangtailiang/openwrt)），FM25G02B 已改由上游 `backport-6.12/436`、`437` 提供；master 线两者均由上游 6.18 承担。
* 基于 [XG-040G-MD (AN7581) NPU 固件加载报错分析与修复记录](https://github.com/xiangtailiang/OpenWrt-for-XG-040G-MD/blob/main/docs/npu-firmware-load.md) 修复内核日志报错：
    ```text
    airoha-npu 1e900000.npu: Direct firmware load for airoha/en7581_npu_rv32.bin failed with error -2
    ```
* [获取超级密码](https://www.right.com.cn/FORUM/thread-8440823-1-1.html)
* [拆机、刷机、配置、原厂分区备份 教程](https://www.right.com.cn/forum/thread-8467912-1-1.html)
* 使用 [Nwrt](https://nwrt.kuroneko.host/flashdocs/XG-040G-MD.html) 提供的 [tcboot.bin](https://pan.baidu.com/s/1UWUXmZro0XFKmP-UHnbc1A?pwd=Nwrt#list/path=%2FNwrt%E5%9B%BA%E4%BB%B6%2F%E5%85%89%E7%8C%AB%E8%B4%9D%E5%B0%94) 作为引导程序。
* **⚠️ 重要：请准备好 USB-TTL，做好随时救砖的准备。**

### 编译

本仓库只包含编译配置、补丁与 CI 流程，固件源码在 [Loong1996/immortalwrt](https://github.com/Loong1996/immortalwrt)，补丁已内置于源码分支，无需手动执行 `patch.sh`。

1. Fork 本仓库，在 Actions 页面启用 workflow
2. `Actions → XG-040G-MD → Run workflow`，选择编译分支与内存颗粒容量（想额外加装软件包，见下方[选包页](#临时加装软件包选包页)）
3. 约 1~2 小时后，固件发布在本仓库的 Releases 中

**分支选择建议：`openwrt-25.12-XG-040G-MD`（默认）**

| 分支 | 源码基线 | 设备定义 | 内核 | 配置文件 |
| --- | --- | --- | --- | --- |
| `openwrt-25.12-XG-040G-MD` | immortalwrt `openwrt-25.12`，落后 0 | 自带 `bell_xg-040g-md` | 6.12 | `config/xg-040g-md.config` |
| `master-XG-040G-MD` | immortalwrt `master`，落后 0 | 上游原生 `nokia_xg-040g-md-tcboot` | 6.18 | `config/xg-040g-md-master.config` |

两条线各自只有 1~2 个提交叠在上游之上，跟进上游只需 rebase 一次。

**25.12 线**：上游没有 XG-040G-MD 支持，设备 DTS、镜像定义与 SkyHigh S35ML 闪存补丁（`backport-6.12/430`、`431`）均由本项目自带。FM25G01B/FM25G02B 已改由上游 `backport-6.12/436`、`437` 提供。

**master 线**：上游 master 已内核 6.18 且原生支持本机型。闪存、cpufreq、pcs-airoha 等补丁全部由上游承担，本项目只保留 `luci-app-airoha-npu`、一行 `nf_conntrack_max`，外加一个 tcboot 引导变体。6.12 时代的旧状态归档在源码仓库的 `archive/master-XG-040G-MD-6.12` 分支。

### 设备变体（分区布局与刷机方式）

实质是**三种分区布局**。25.12 线固定一种；master 线在 `Run workflow` 时用 **device_variant** 输入三选一（`tcboot` / `stock` / `ubi`，默认 `tcboot`），workflow 会自动改写 `.config` 的设备符号，25.12 分支则忽略该输入并给出 warning。

| 变体 | 分支 | 引导程序 | rootfs 空间 | MAC 来源 | 可回退原厂 |
| --- | --- | --- | --- | --- | --- |
| `tcboot` | master | 第三方 `tcboot.bin` | **255 MB** | ubi 的 `ri` 卷，自动初始化 | 否 |
| `stock` | master | **原厂，不动** | 129 MB | 原厂 `ri` 分区 | **是** |
| `ubi` | master | OpenWrt U-Boot | **255.875 MB** | ubi 的 `ri` 卷，**需自行转存** | 否 |
| （`bell_xg-040g-md`） | 25.12 | 第三方 `tcboot.bin` | **255 MB** | 无，随机生成 | 否 |

Release 的标题、正文与 tag 都会标出本次用的变体，例如 `XG-040G-MD-tcboot-1G-20260826-42`；25.12 线只有一个设备，tag 不带变体段。

#### `tcboot` —— 第三方引导，空间最大

```
0x00000000   512 KB   bootloader    ← 第三方 tcboot.bin
0x00080000   512 KB   env
0x00100000   255 MB   ubi           ← kernel + rootfs + overlay
```

* **前提**：机器已刷入 [Nwrt 提供的 `tcboot.bin`](https://nwrt.kuroneko.host/flashdocs/XG-040G-MD.html)
* 刷机用附件 `factory.bin`，日常升级用 `sysupgrade.bin`
* 原厂分区表整片被覆盖 —— `romfile`、`nsb_1`/`nsb_2`、`bosa`、`ri`、`config`、`data` 全部消失
* MAC 取自 ubi 中名为 `ri` 的卷。`factory.bin` 会预留一个全零的 `ri` 占位卷，首次启动时固件自动把本次的 MAC 写进去，此后每次启动都是同一个值 —— **不需要原厂备份也能正常工作**
* 有原厂 `ri` 备份的，刷完后用 `ubiupdatevol` 写入即可得到真实硬件 MAC；`sysupgrade` 只重建 `kernel` / `rootfs` / `rootfs_data` 三个卷，不会覆盖 `ri`
* 与 25.12 线的 `bell_xg-040g-md` 分区表逐项一致，且声明了 `SUPPORTED_DEVICES += bell,xg-040g-md`。但 **25.12 线的 ubi 里没有 `ri` 卷，直接 sysupgrade 过来会因缺卷而无网络**，必须刷一次 `factory.bin`（见下方升级表）

#### `stock` —— 寄生原厂分区，唯一可回退

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

#### `ubi` —— OpenWrt U-Boot，带救援镜像

```
0x00000000   128 KB      bl2
0x00020000   255.875 MB  ubi
```

* **会替换引导程序**。附件 `preloader.bin` 与 `bl31-uboot.fip` 需经 USB-TTL 走 BootROM 恢复流程刷入
* 这两个附件由 workflow 自动构建：`uboot-airoha` 的 `BUILD_DEVICES:=nokia_xg-040g-md-ubi` 会在选中该变体时自动勾选 U-Boot 包，它再拉 ATF 的 `trusted-firmware-a-an7581-bl31`，最后由 `fiptool` 打成 FIP
* 额外产出 `*-recovery.itb`，是 initramfs 救援镜像，另外三种变体都没有
* 升级用 `sysupgrade.itb`
* 原厂 `ri` 与 `bosa` 由官方转换流程转存为同名 UBI 卷，MAC 得以保留
* ⚠️ **必须完成 `ri` 卷的转存**。该变体没有 `tcboot` 那样的占位卷兜底，`ri` 缺失时 `airoha_eth` 会因 nvmem 拿不到 MAC 而永久停在 deferred probe，整机无网络且日志里没有任何报错，表现为：

  ```
  mt7530-mmio 1fb58000.switch: Failed to register DSA switch: -517
  platform 1fb58000.switch: deferred probe pending: (reason unknown)
  platform 1fb50000.ethernet: deferred probe pending: (reason unknown)
  ```

  可用 `cat /sys/kernel/debug/devices_deferred` 与 `ubinfo -a` 确认

#### 互相能不能升级

| 从 → 到 | 可否 |
| --- | --- |
| 25.12 `bell` → master `tcboot` | 分区表一致，`sysupgrade` 能刷进去，但 **25.12 的 ubi 没有 `ri` 卷，刷完会无网络**。需改刷一次 `factory.bin`，之后即可正常 `sysupgrade` |
| `tcboot` ↔ `stock` | 不可以，分区表完全不同，需完整刷机 |
| `tcboot` ↔ `ubi` | 不可以，引导程序不同，需完整刷机 |
| `stock` ↔ `ubi` | 不可以，需完整刷机 |

> ⚠️ **`tcboot` 与 `ubi` 都会覆盖原厂引导和原厂分区表。** 其中 `ri`（MAC、序列号）与 `bosa`（光模块校准）是逐机唯一的出厂数据，没有公开来源。**刷这两种之前务必做整片 flash 备份**，参见上文的[原厂分区备份教程](https://www.right.com.cn/forum/thread-8467912-1-1.html)。
>
> ℹ️ **`tcboot` 变体的引导已实机验证**：分区偏移与 `UBINIZE_OPTS` 正确，tcboot 能引导其产出的镜像并进入系统。早期版本因 ubi 中缺少 `ri` 卷导致网络驱动永久 deferred probe，已由 `factory.bin` 预留占位卷修复；修复后的网络功能待复测。
>
> ⚠️ 25.12 线的 `bell_xg-040g-md` 没有声明 `all_flash` 分区，**在跑着的系统里无法直接 dd 整片 flash**；master 的三个变体都有。

此外 25.12 分支的内核配置已启用完整 IPsec/XFRM 支持。

跟进上游：

```bash
git clone https://github.com/Loong1996/immortalwrt.git -b openwrt-25.12-XG-040G-MD
cd immortalwrt
git remote add upstream https://github.com/immortalwrt/immortalwrt.git
git fetch upstream openwrt-25.12
git rebase upstream/openwrt-25.12    # 只有 1 个设备提交要 rebase
git push --force-with-lease
```

补丁目录 `patch-25.12/` 保留作 25.12 线的对照参考，实际编译不使用。master 线已完全依赖上游，无对应补丁目录。

### 自定义软件包

两条线各有一份配置，改包需**两份都改**（内容目前完全一致）：

* 25.12 线 —— [`config/xg-040g-md.config`](config/xg-040g-md.config)
* master 线 —— [`config/xg-040g-md-master.config`](config/xg-040g-md-master.config)

编辑后提交即可，依赖由 `make defconfig` 自动补全。当前已内置：

* **代理**：Passwall（Xray / sing-box / geoview）、OpenClash
* **DNS**：dnsmasq-full（dnssec + ipset + nftset）、SmartDNS、AdGuardHome
* **网络工具**：SQM、UPnP、DDNS、Watchcat、nlbwmon、ttyd、irqbalance、tcpdump-mini、iperf3、conntrack
* **系统**：Argon 主题、attendedsysupgrade、apk 包管理界面、USB 存储与 extroot、中文语言包

每个 Release 都会附带一份 `custom-packages.txt`，列出该次编译实际勾选的自定义软件包（按配置文件分组，带注释）；固件实际安装的完整包列表见同一 Release 中的 `*.manifest`。

#### 临时加装软件包（选包页）

不想动配置文件、只是这次编译想多带几个包时，用选包页：

**<https://loong1996.github.io/ImmortalWrt-XG-040G-MD/>**

页面上的可选清单由每次成功编译自动导出（取自源码树的 `tmp/.packageinfo`），所以**只列出该分支真正编得出来的包**，自建的 `luci-app-airoha-npu` 也在里面。勾选后底部会生成一串包名，粘进 `Run workflow` 的 **附加软件包** 那一栏：

```
luci-app-nginx-manager luci-app-samba4 -luci-app-openclash
```

* 包名前加 `-` 表示从基础配置里移除
* 包名拼错、或该分支根本没这个包时，workflow 会在 `Load Custom Configuration` 步骤直接报错退出，不会让你等一两个小时编完才发现漏装
* 被其它已选软件包硬依赖的包移除不掉，这种情况只给 warning，固件里仍然会有
* 只影响本次编译；想长期带上，还是改上面那两份 `.config`

页面左上角的下拉框切换数据源，共四项——两条编译线各一项，外加两项官方索引：

* **编译索引**（首选）—— 每次成功编译后自动导出，带描述与分类、含 `luci-app-airoha-npu` 这类自建包，且保证这条分支编得出来。
* **官方索引** —— 直接从 immortalwrt 下载站取（`25.12-SNAPSHOT` 与 `snapshots` 的 `aarch64_cortex-a53`），**不依赖编译**，Pages 一开就能用。代价是官方 `index.json` 只有包名和版本，**没有描述、没有分类，也不含 kmod 与自建包**，更不保证本源码树都编得出来。所以这一档只能靠搜索用，不提供分类折叠。

某条线的编译索引还不存在时（刚开 Pages、还没跑过构建），页面会自动回落到官方索引，并在状态行说明原因。真编不出来的包名，workflow 那道核对会在编译前拦下，不会白等一两个小时。

选包页托管在本仓库的 `gh-pages` 分支，由构建流程自动更新（首次需在 `Settings → Pages` 里把源设为 `gh-pages`）；页面与索引生成脚本在 [`selector/`](selector/)。两条编译线各有一份索引，页面左上角可切换。

使用注意：

* Passwall 与 OpenClash **不要同时启用**，两者都会接管 nftables 规则链与 dnsmasq 配置
* dnsmasq / SmartDNS / AdGuardHome 默认均监听 53 端口，刷机后需手动规划端口分配
* 不在官方 feed 中的第三方插件，需在 workflow 的 `Install Feeds` 步骤前添加克隆步骤

## OpenWrt Snapshots
![snapshot1](snapshots/screenshot.jpg)
---

### 鸣谢 / Credits

感谢以下仓库提供的补丁与技术支持：

* [xiangtailiang/openwrt](https://github.com/xiangtailiang/openwrt)
* [bingoguo93/immortalwrt](https://github.com/bingoguo93/immortalwrt)
* [OpenWRT-fanboy/OpenW1700k](https://github.com/OpenWRT-fanboy/OpenW1700k)
