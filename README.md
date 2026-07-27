# ImmortalWrt for XG-040G-MD

ImmortalWrt firmware for NOKIA BELL XG-040G-MD

编译脚本基于 [dalutou/OpenWrt-for-XG-040G-MD](https://github.com/dalutou/OpenWrt-for-XG-040G-MD) 修改。

### 项目说明

* 固件源码使用 [fzs209/immortalwrt](https://github.com/fzs209/immortalwrt)。
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

本仓库只包含编译配置、补丁与 CI 流程，固件源码在 [fzs209/immortalwrt](https://github.com/fzs209/immortalwrt)，补丁已内置于源码分支，无需手动执行 `patch.sh`。

1. Fork 本仓库，在 Actions 页面启用 workflow
2. （可选）在 `Settings → Secrets and variables → Actions` 添加 `REPO_TOKEN`，值为任意具有 `public_repo` 权限的 PAT
3. `Actions → XG-040G-MD → Run workflow`，选择编译分支
4. 约 1~2 小时后，固件发布在本仓库的 Releases 中

**分支选择建议：`openwrt-25.12-XG-040G-MD`**

两个分支对 XG-040G-MD 的补丁完全一致——设备 DTS、镜像定义（分区/`IMAGE_SIZE`/`DEVICE_PACKAGES`）、`target.mk` 及五个闪存补丁均相同，内核同为 6.12。差别只在 feeds：

| 分支 | feeds | 说明 |
| --- | --- | --- |
| `openwrt-25.12-XG-040G-MD` | 锁定 `;openwrt-25.12` | feeds 与源码同处稳定分支线，仅收 bugfix |
| `master-XG-040G-MD` | 未锁定分支 | 源码停在 2026-05-11，但会拉取 packages/luci 的最新提交，存在版本错配风险 |

此外 25.12 分支的内核配置已启用完整 IPsec/XFRM 支持。

> 注意：上游 `immortalwrt/immortalwrt` 的 master 已升级至内核 6.18 并移除了 `target/linux/airoha/patches-6.12/`。若尝试将 `master-XG-040G-MD` rebase 到上游最新，本项目的 airoha 补丁会被放入构建系统不再读取的目录，**不报错但设备支持会静默失效**。如需跟进上游，请使用 25.12 分支并以 merge 方式同步。

### 自定义软件包

编辑 [`config/xg-040g-md.config`](config/xg-040g-md.config) 后提交即可，依赖由 `make defconfig` 自动补全。当前已内置：

* **代理**：Passwall（Xray / sing-box / geoview）、OpenClash
* **DNS**：dnsmasq-full（dnssec + ipset + nftset）、SmartDNS、AdGuardHome
* **网络工具**：SQM、UPnP、DDNS、Watchcat、nlbwmon、ttyd、irqbalance、tcpdump-mini、iperf3、conntrack
* **系统**：Argon 主题、attendedsysupgrade、apk 包管理界面、USB 存储与 extroot、中文语言包

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
