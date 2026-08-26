# ImmortalWrt for XG-040G-MD

ImmortalWrt firmware for NOKIA BELL XG-040G-MD

编译脚本基于 [dalutou/OpenWrt-for-XG-040G-MD](https://github.com/dalutou/OpenWrt-for-XG-040G-MD) 修改。

### 项目说明

* 固件源码使用 [Loong1996/immortalwrt](https://github.com/Loong1996/immortalwrt)，fork 自官方 [immortalwrt/immortalwrt](https://github.com/immortalwrt/immortalwrt)，设备支持压缩为单个提交叠在上游之上，便于持续跟进。设备补丁最初来自 [fzs209/immortalwrt](https://github.com/fzs209/immortalwrt)。
* 基于 [xiangtailiang/openwrt](https://github.com/xiangtailiang/openwrt) 仓库的补丁适配 SkyHigh S35ML02G300 和 Fudan Micro FM25G02B 闪存。
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
2. `Actions → XG-040G-MD → Run workflow`，选择编译分支与内存颗粒容量
3. 约 1~2 小时后，固件发布在本仓库的 Releases 中

**分支选择建议：`openwrt-25.12-XG-040G-MD`（默认）**

| 分支 | 源码基线 | 设备定义 | 内核 | 配置文件 |
| --- | --- | --- | --- | --- |
| `openwrt-25.12-XG-040G-MD` | immortalwrt `openwrt-25.12`，落后 0 | 自带 `bell_xg-040g-md` | 6.12 | `config/xg-040g-md.config` |
| `master-XG-040G-MD` | immortalwrt `master`，落后 0 | 上游原生 `nokia_xg-040g-md` | 6.18 | `config/xg-040g-md-master.config` |

两条线各自只有 1 个设备提交叠在上游之上，跟进上游只需 rebase 一次。

**25.12 线**：上游没有 XG-040G-MD 支持，设备 DTS、镜像定义与 SkyHigh S35ML 闪存补丁（`backport-6.12/430`、`431`）均由本项目自带。FM25G01B/FM25G02B 已改由上游 `backport-6.12/436`、`437` 提供。

**master 线**：上游 master 已内核 6.18 且原生支持本机型，提供 `nokia_xg-040g-md`（保留原厂引导）与 `nokia_xg-040g-md-ubi`（OpenWrt U-Boot 布局，额外产出 `preloader.bin` / `bl31-uboot.fip`）两个变体。自制的 `bell_xg-040g-md` 已弃用，闪存、cpufreq、pcs-airoha 等补丁全部由上游承担，本项目只保留 `luci-app-airoha-npu` 与一行 `nf_conntrack_max`。6.12 时代的旧状态归档在源码仓库的 `archive/master-XG-040G-MD-6.12` 分支。

> ⚠️ **两条线的分区布局不同，不能互相 sysupgrade。** 25.12 线 `IMAGE_SIZE` 为 261120k，master 线 stock 变体为 131968k。首次切换必须完整刷机，并接好 USB-TTL。
>
> ⚠️ master 线默认选的是不动引导的 `nokia_xg-040g-md`。若你的机器跑的是 OpenWrt U-Boot 布局，需在 `config/xg-040g-md-master.config` 里换成 `nokia_xg-040g-md-ubi`，文件头部有说明。

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

编辑 [`config/xg-040g-md.config`](config/xg-040g-md.config) 后提交即可，依赖由 `make defconfig` 自动补全。当前已内置：

* **代理**：Passwall（Xray / sing-box / geoview）、OpenClash
* **DNS**：dnsmasq-full（dnssec + ipset + nftset）、SmartDNS、AdGuardHome
* **网络工具**：SQM、UPnP、DDNS、Watchcat、nlbwmon、ttyd、irqbalance、tcpdump-mini、iperf3、conntrack
* **系统**：Argon 主题、attendedsysupgrade、apk 包管理界面、USB 存储与 extroot、中文语言包

每个 Release 都会附带一份 `custom-packages.txt`，列出该次编译实际勾选的自定义软件包（按配置文件分组，带注释）；固件实际安装的完整包列表见同一 Release 中的 `*.manifest`。

使用注意：

* Passwall 与 OpenClash **不要同时启用**，两者都会接管 nftables 规则链与 dnsmasq 配置
* dnsmasq / SmartDNS / AdGuardHome 默认均监听 53 端口，刷机后需手动规划端口分配
* 不在官方 feed 中的第三方插件，需在 workflow 的 `Install Feeds` 步骤前添加克隆步骤

## OpenWrt Snapshots
![snapshot1](snapshots/screenshot.bmp)
---

### 鸣谢 / Credits

感谢以下仓库提供的补丁与技术支持：

* [xiangtailiang/openwrt](https://github.com/xiangtailiang/openwrt)
* [bingoguo93/immortalwrt](https://github.com/bingoguo93/immortalwrt)
* [OpenWRT-fanboy/OpenW1700k](https://github.com/OpenWRT-fanboy/OpenW1700k)
