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

| 分支 | 源码基线 | feeds | 状态 |
| --- | --- | --- | --- |
| `openwrt-25.12-XG-040G-MD` | 与 immortalwrt `openwrt-25.12` 同步，落后 0 | 五个 feed 全部锁定 `;openwrt-25.12` | 维护中 |
| `master-XG-040G-MD` | 停在 2026-05-11，落后 immortalwrt `master` 1611 个提交 | 未锁定，拉取 packages/luci 最新提交 | 仅保留，未跟进上游 |

两个分支内核同为 6.12。25.12 分支已 rebase 到上游最新，若干原本自带的闪存补丁改由上游的 mainline 回合提供（`backport-6.12/436`、`437` 提供 FM25G01B/FM25G02B，`429-01/02/03` 提供 regular 模式重读）；SkyHigh S35ML 支持（`430`、`431`）上游至今没有，仍由本项目自带。master 分支保持 2026-05-11 的原始状态，未做同步。

此外 25.12 分支的内核配置已启用完整 IPsec/XFRM 支持。

跟进上游（25.12 线）：

```bash
git clone https://github.com/Loong1996/immortalwrt.git -b openwrt-25.12-XG-040G-MD
cd immortalwrt
git remote add upstream https://github.com/immortalwrt/immortalwrt.git
git fetch upstream openwrt-25.12
git rebase upstream/openwrt-25.12    # 只有 1 个设备提交要 rebase
git push --force-with-lease
```

补丁目录 `patch-25.12/`、`patch-master/` 保留作对照参考，实际编译不使用。

> 注意：上游 `immortalwrt/immortalwrt` 的 master 已升级至内核 6.18 并移除了 `target/linux/airoha/patches-6.12/`。若尝试将 `master-XG-040G-MD` rebase 到上游最新，本项目的 airoha 补丁会被放入构建系统不再读取的目录，**不报错但设备支持会静默失效**。如需跟进上游，请使用 25.12 分支并以 merge 方式同步。

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
