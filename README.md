# ImmortalWrt for XG-040G-MD

ImmortalWrt firmware for NOKIA BELL XG-040G-MD

编译脚本基于 [dalutou/OpenWrt-for-XG-040G-MD](https://github.com/dalutou/OpenWrt-for-XG-040G-MD) 修改。

### 项目说明

* 固件源码使用 [Loong1996/immortalwrt](https://github.com/Loong1996/immortalwrt)，fork 自官方 [immortalwrt/immortalwrt](https://github.com/immortalwrt/immortalwrt)。master 线的设备支持压缩为单个提交叠在上游之上，便于持续跟进；25.12 线直接采用 [fzs209/immortalwrt](https://github.com/fzs209/immortalwrt) 的实测快照，不跟进上游（原因见下方分支说明）。
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

**分支选择建议：`master-XG-040G-MD`（默认）**

| 分支 | 源码基线 | 设备定义 | 内核 | 配置文件 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `master-XG-040G-MD` | immortalwrt `master`，落后 0 | 上游原生 `nokia_xg-040g-md-tcboot` | 6.18 | `config/xg-040g-md-master.config` | ✅ 已实机验证 |
| `openwrt-25.12-XG-040G-MD` | fzs209 的实测快照，**不跟进上游** | 自带 `bell_xg-040g-md` | 6.12 | `config/xg-040g-md.config` | ✅ 实测可用 |

master 线只有一个提交叠在上游之上，跟进上游只需 rebase 一次。

**25.12 线**：上游没有 XG-040G-MD 支持，设备 DTS、镜像定义、闪存补丁与 `luci-app-airoha-npu` 全部由 fzs209 的快照自带。

> ℹ️ **这条线固定在 fzs209 的快照上，刻意不跟进上游。** 曾经尝试把它 rebase 到 immortalwrt `openwrt-25.12` 最新，结果固件编得过但刷上去完全没有网络。原因是上游的 airoha 补丁栈已推进到 v7.2 的 `airoha_gdm_dev` 重构（`161-*`、`165-*`、`166`，共 13 个补丁），`310-10` 随之升级到新的 fwnode PCS API（`fwnode_phylink_pcs_parse()` 查找 `pcs-handle`），但 `310-09` 仍是旧版 PCS 驱动（从不调用 `fwnode_pcs_add_provider()`），`an7581.dtsi` 里也还是旧属性名 `pcs = <...>`。三者错配使 GDM4 在 probe 阶段拿到 `-ENODEV`，`airoha_eth` 整体探测失败，DSA 交换机随之找不到 conduit：
>
> ```
> mt7530-mmio 1fb58000.switch: Failed to register DSA switch: -517
> platform 1fb58000.switch: deferred probe pending: (reason unknown)
> ```
>
> `-ENODEV` 在 `really_probe()` 里走的是 `pr_debug`，日志里看不到 `airoha_eth` 的任何报错，极难排查。而旧的 `310-10` 挂在 `airoha_alloc_gdm_port()` 与 `port->dev` 上，正是 `161-01` 重写掉的部分，无法套回新树 —— 换句话说这条线要么停在旧快照，要么等上游把 `310-09` 与 dtsi 一并更新到新 API。既然旧快照实测稳定，就先停在这里。
>
> 那次 rebase 的状态归档在源码仓库的 `archive/openwrt-25.12-XG-040G-MD-upstream` 分支，供日后上游修好时参考。想要新内核与持续跟进上游，请用 master 线。

**master 线**：上游 master 已内核 6.18 且原生支持本机型。闪存、cpufreq、pcs-airoha 等补丁全部由上游承担，本项目只保留 `luci-app-airoha-npu`、一行 `nf_conntrack_max`，外加一个 tcboot 引导变体。6.12 时代的旧状态归档在源码仓库的 `archive/master-XG-040G-MD-6.12` 分支。

### 设备变体（分区布局与刷机方式）

实质是**三种分区布局**。25.12 线固定一种；master 线在 `Run workflow` 时用 **device_variant** 输入三选一（`tcboot` / `stock` / `ubi`，默认 `tcboot`），workflow 会自动改写 `.config` 的设备符号，25.12 分支则忽略该输入并给出 warning。

| 变体 | 分支 | 引导程序 | rootfs 空间 | MAC 来源 | 可回退原厂 |
| --- | --- | --- | --- | --- | --- |
| `tcboot` | master | 第三方 `tcboot.bin` | **255 MB** | ubi 的 `ri` 卷，缺失则随机 | 否 |
| `stock` | master | **原厂，不动** | 129 MB | 原厂 `ri` 分区 | **是** |
| `ubi` | master | OpenWrt U-Boot | **255.875 MB** | ubi 的 `ri` 卷，缺失则随机 | 否 |
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
* MAC 取自 ubi 中名为 `ri` 的卷，但**该卷不存在时会退化为随机 MAC，不影响启动**。这一步由 `preinit` 钩子在用户态完成，不是 dts 里的 nvmem —— 后者在缺卷时会让网络驱动永久停在 deferred probe，整机失联
* 因此**什么时候补上 `ri` 卷都可以**：`ubimkvol` + `ubiupdatevol` 写入后重启即生效，不需要重刷固件
* 没有 `ri` 卷时随机生成的 MAC 会固化在 `/etc/xg-040g-md-mac`，重启与 `sysupgrade` 后保持不变；恢复出厂设置会重新生成
* 与 25.12 线的 `bell_xg-040g-md` 分区表逐项一致，且声明了 `SUPPORTED_DEVICES += bell,xg-040g-md`，**可从 25.12 固件直接 sysupgrade 过来**
* 本变体**不含 `uboot-envtools`**，原因见下方「关于 `tcboot.bin` 这个引导程序」

##### 关于 `tcboot.bin` 这个引导程序

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
* 与 `tcboot` 一样，`ri` 的读取由 preinit 钩子在用户态完成，**没转存 `ri` 卷也能正常启动**（退化为随机 MAC）；转存过则拿到真实硬件 MAC

#### 互相能不能升级

| 从 → 到 | 可否 |
| --- | --- |
| 25.12 `bell` → master `tcboot` | **可以直接 sysupgrade**（分区表一致 + `SUPPORTED_DEVICES`） |
| `tcboot` ↔ `stock` | 不可以，分区表完全不同，需完整刷机 |
| `tcboot` ↔ `ubi` | 不可以，引导程序不同，需完整刷机 |
| `stock` ↔ `ubi` | 不可以，需完整刷机 |

> ⚠️ **`tcboot` 与 `ubi` 都会覆盖原厂引导和原厂分区表。** 其中 `ri`（MAC、序列号）与 `bosa`（光模块校准）是逐机唯一的出厂数据，没有公开来源。**刷这两种之前务必做整片 flash 备份**，参见上文的[原厂分区备份教程](https://www.right.com.cn/forum/thread-8467912-1-1.html)。
>
> ✅ **`tcboot` 变体已实机验证**：分区偏移与 `UBINIZE_OPTS` 正确，能引导、进系统，四个网口与 NPU、EN8811H 均正常。早期版本因 ubi 中缺少 `ri` 卷导致网络驱动永久 deferred probe，已通过去掉 dts 里的 nvmem 硬依赖、改由 preinit 钩子在用户态读取该卷解决。
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

页面上的可选清单取自源码树的 `tmp/.packageinfo`，所以**只列出该分支真正编得出来的包**，自建的 `luci-app-airoha-npu` 也在里面。`HIDDEN` 的包会被剔掉——它们在 menuconfig 里没有选项条目，勾了也不会生效，列出来只会让构建白失败一次。勾选后底部会生成一串包名，粘进 `Run workflow` 的 **附加软件包** 那一栏：

```
luci-app-nginx-manager luci-app-samba4 -luci-app-openclash
```

* 包名前加 `-` 表示从基础配置里移除
* 包名拼错、或该分支根本没这个包时，workflow 会在 `Load Custom Configuration` 步骤直接报错退出，不会让你等一两个小时编完才发现漏装
* 被其它已选软件包硬依赖的包移除不掉，这种情况只给 warning，固件里仍然会有
* 只影响本次编译；想长期带上，还是改上面那两份 `.config`

页面左上角的下拉框切换数据源，共四项——两条编译线各一项，外加两项官方索引：

* **编译索引**（首选）—— 带描述、分类、版本、依赖、冲突、许可证与上游地址，含自建包，且保证这条分支编得出来。
* **官方索引** —— 直接从 immortalwrt 下载站取（`25.12-SNAPSHOT` 与 `snapshots` 的 `aarch64_cortex-a53`），**不依赖任何构建**，Pages 一开就能用。代价是它整份数据**只有包名和版本两项**——`index.json` 的内容就是 `{"464xlat":"13", ...}`，没有第三个字段可挖。所以这一档没有描述、分类、依赖，也不含 kmod 与自建包，更不保证本源码树都编得出来，只能靠搜索用。

某条线的编译索引还不存在时，页面会自动回落到官方索引并在状态行说明原因。真编不出来的包名，workflow 那道核对会在编译前拦下，不会白等一两个小时。

搜索支持多词与模糊匹配：

* **多词** —— 空格分隔，每个词都要命中。`luci ddns`、`kmod usb storage` 这类最自然的输入现在都能搜到（以前整串当子串匹配，结果是 0 条）
* **模糊** —— 只按名字里字符出现的先后顺序命中即可，`lapdd` 能搜到 `luci-app-ddns`
* **按相关度排序** —— 用 fzy 那套子序列 DP 打分，连续命中有连击加成、词首命中有边界加成，所以完整子串天然排最前。搜 `npu` 第一条是 `luci-app-airoha-npu` 而不是恰好含 "npu" 的 `libinput`

点每行右侧的 **ⓘ** 展开详情：

* **信息** —— 版本号、许可证、上游主页（可点）
* **冲突** —— 与本包互斥、不能同时装的包
* **依赖** —— 直接依赖，另有「展开传递闭包」告诉你勾上它总共会带进多少个包
* **条件依赖** —— 形如 `USE_GLIBC ? librt`，只在对应配置项打开时才装，不计入闭包
* **被依赖** —— 谁需要它。这一栏回答「这个包能不能删」：只要列表里有一个被选中，写 `-包名` 也移除不掉，构建时只会给个 warning 然后照常编进固件

详情数据在单独的 `detail-<分支>.json` 里，点第一个 ⓘ 时才加载——主索引一万三千个包已经一兆多，多数人搜个名字勾上就走，没道理让所有人先把详情也下载下来。

**版本只能看，不能指定。** `.config` 里软件包只有开关位（`CONFIG_PACKAGE_xxx=y`），没有版本位，编出来是哪个版本完全取决于 `feeds update` 那一刻各 feed 仓库的 HEAD。唯一能控版本的层级是整个 feed（`feeds.conf.default` 里给 `src-git` 加 `^提交号` 后缀），粒度粗到没法当"指定版本"用。

#### 刷新索引（不用编译）

生成索引其实不需要编译——`tmp/.packageinfo` 是 `make defconfig` 阶段扫描 feeds 产生的，那时一行代码都还没编。所以另有一个 `Actions → 更新选包页索引 → Run workflow`，**十分钟左右**跑完，默认一次刷新两条线。

改了 `selector/` 下的东西、或者 feeds 更新了想刷新清单，用它就行，不必为此跑一次完整构建。正常构建成功时也会顺带更新对应那条线的索引。

选包页托管在本仓库的 `gh-pages` 分支（首次需在 `Settings → Pages` 里把源设为 `gh-pages`）；页面与索引生成脚本在 [`selector/`](selector/)。两条编译线各有一份索引，页面左上角可切换。

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
