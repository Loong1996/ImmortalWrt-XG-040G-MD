# 源码分支与跟进上游

**分支选择建议：`master-XG-040G-MD`（默认）**

| 分支 | 源码基线 | 设备定义 | 内核 | 配置文件 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `master-XG-040G-MD` | immortalwrt `master`，落后 0 | 上游原生 `nokia_xg-040g-md-ubi`（推荐）等 | 6.18 | `config/xg-040g-md-master.config` | ✅ 已实机验证 |
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

**master 线**：上游 master 已内核 6.18 且原生支持本机型。闪存、cpufreq、pcs-airoha 等补丁全部由上游承担，本项目只保留 `luci-app-airoha-npu`、一行 `nf_conntrack_max`，以及作者魔改的 UBI U-Boot（网页救砖、DRAM 探测、复旦颗粒）。`tcboot` 变体还在，但刷机不再维护。6.12 时代的旧状态归档在源码仓库的 `archive/master-XG-040G-MD-6.12` 分支。

## 其它

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
