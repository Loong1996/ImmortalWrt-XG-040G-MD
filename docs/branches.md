# 源码分支与跟进上游

**分支选择建议：`master-XG-040G-MD`（默认）**

| 分支 | 源码基线 | 设备定义 | 内核 | 配置文件 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `master-XG-040G-MD` | immortalwrt `master`，落后 0 | 上游原生 `nokia_xg-040g-md-ubi`（推荐）等 | 6.18 | `config/xg-040g-md-master.config` | ✅ 已实机验证 |
| `master-airoha` | 同上，整理版 | 同上，**无 tcboot** | 6.18 | 同上 | ⚠️ 待实机验证 |
| `openwrt-25.12-XG-040G-MD` | fzs209 的实测快照，**不跟进上游** | 自带 `bell_xg-040g-md` | 6.12 | `config/xg-040g-md.config` | ✅ 实测可用 |

## `master-airoha` —— 整理后的 master 线

> 这次整理的完整说明与**实机验收清单**见 [master-airoha 迁移说明](master-airoha-migration.md)。

把 `master-XG-040G-MD` 那 15 个零散提交按主题重新捋成 9 个，并做了三件事：

* **删掉 `tcboot` 变体**（dts、分区表 dtsi、291 行的 `patches-6.18/608` CPU PLL
  回退补丁、镜像定义）。刷机早已不再维护，而那个内核补丁打在上游正在活跃改动的
  `airoha-cpu-pmdomain` 上，是整棵树里维护成本最高的单项
* **`luci-app-airoha-npu` 出树**，改由本仓库 `packages/` 以 `src-link` feed 提供
  （顺带丢掉 3 张约 3 MB 的 README 截图）
* **复旦闪存补丁收编**：原先放在本仓库 `patch/uboot-airoha/`、编译时 `cp` 进去，
  现在是源码树里正常的 `120`、`121`。少一种机制

收缩效果：

| | `master-XG-040G-MD` | `master-airoha` |
| --- | --- | --- |
| 文件数 | 35 | **18** |
| 行数 | +4782 / -10 | **+2713 / -3** |
| 改动上游已有文件 | 10 个 | **6 个** |

删 tcboot 顺带让 `an7581.mk`、`target.mk`、`02_network`、`airoha_an7581`
**四个文件整个回到上游原样**——其中 `an7581.mk` 原本为了给 tcboot 剔除
`uboot-envtools`，往 evb、gemtek w1700k、nokia valyrian 这些无关机型的定义里各插了
一行，正是每次跟上游都会撞车的地方。

剩下的 6 个改动文件才是 rebase 会报冲突的全部范围：

```
package/kernel/linux/files/sysctl-nf-conntrack.conf
target/linux/airoha/an7581/base-files/etc/board.d/01_leds
target/linux/airoha/an7581/config-6.18
target/linux/airoha/dts/an7581-nokia_xg-040g-md-common.dtsi
target/linux/airoha/dts/an7581-nokia_xg-040g-md-ubi.dts
target/linux/airoha/dts/an758x-nokia_xg-040g-common.dtsi
```

> ⚠️ **rebase 只覆盖上面这 6 个文件。** 其余 12 个是纯新增，它们依赖的上游文件
> 上游怎么改，rebase 都不会吭声——那部分交给[漂移检查](upstream-drift.md)。

每个提交都带 `Topic: common` / `Topic: nokia-xg-040g-md` 标记，加第二款机型时公共
部分不需要复制第二份。原提交的完整设计说明保留在 `master-XG-040G-MD` 分支里。

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

**master 线**：上游 master 已内核 6.18 且原生支持本机型。闪存、cpufreq、pcs-airoha 等补丁全部由上游承担，本项目只保留 `luci-app-airoha-npu`、一行 `nf_conntrack_max`，以及作者魔改的 UBI U-Boot（网页救砖、DRAM 探测、复旦颗粒）。6.12 时代的旧状态归档在源码仓库的 `archive/master-XG-040G-MD-6.12` 分支。

`tcboot` 变体在 `master-XG-040G-MD` 上还编得出来（刷机不再维护），在 `master-airoha` 上**已彻底移除**。

> 注意：`master-airoha` 移除 tcboot 也就移除了 `SUPPORTED_DEVICES += bell,xg-040g-md`，
> 即 25.12 线的 `bell_xg-040g-md` 机器**不能再直接 sysupgrade 到这条线**。仍需要那条
> 升级路径的话，用 `master-XG-040G-MD` 的 tcboot 固件当跳板。

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

`patch/uboot-airoha/`（复旦颗粒的 `120`、`121`）只为 `master-XG-040G-MD` 与 `xpon-test`
保留，编译时由 `build.sh` / CI 拷进源码树。`master-airoha` 已把这两个补丁收编进源码树，
不走这条路径。

## `master-airoha` 怎么跟进上游

跟 rebase 一起还有一套漂移检查，因为 **rebase 只覆盖 6 个文件**，其余 12 个纯新增
文件所依赖的上游改动它一概不报。完整流程、每周报告的读法、盯梢清单怎么维护，见
[跟进上游：漂移检查怎么用](upstream-drift.md)。

```bash
git clone https://github.com/Loong1996/immortalwrt.git -b master-airoha
cd immortalwrt
git remote add upstream https://github.com/immortalwrt/immortalwrt.git
git fetch upstream master
git rebase upstream/master
```
