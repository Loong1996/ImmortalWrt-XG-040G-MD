# 自定义软件包

两条线各有一份配置，改包需**两份都改**（内容目前完全一致）：

* 25.12 线 —— [`config/xg-040g-md.config`](../config/xg-040g-md.config)
* master 线 —— [`config/xg-040g-md-master.config`](../config/xg-040g-md-master.config)

编辑后提交即可，依赖由 `make defconfig` 自动补全。当前已内置：

* **DNS**：dnsmasq-full（dnssec + ipset + nftset）
* **网络工具**：SQM、UPnP、DDNS、Watchcat、nlbwmon、ttyd 网页终端、irqbalance
* **诊断工具**：tcpdump-mini、iperf3、mtr-json、bind-dig、lsof、iftop、conntrack、htop、stress-ng
* **系统**：Argon 主题、attendedsysupgrade、apk 包管理界面、USB 存储与 extroot、中文语言包、scp/sftp（`openssh-sftp-server`，dropbear 自己不提供 SFTP 子系统，不装它 `scp` 用不了）

**默认不带代理与去广告。** Passwall、OpenClash、AdGuardHome、SmartDNS 都很个人化，而且是体积的绝对大头——它们带的 sing-box(14.3 MB)、xray-core(10.4 MB)、adguardhome(10.9 MB)、openclash(7.8 MB)、geoview(2.8 MB) 五项就占了原固件的八成。拿掉之后固件从 **54 MB 降到约 12 MB**，基本等于"[官方默认包](https://downloads.immortalwrt.org/snapshots/targets/airoha/an7581/profiles.json) + LuCI 中文界面 + USB/extroot + 诊断工具"。

需要的人去[选包页](#临时加装软件包选包页)勾上，重编一次即可。要搜的名字：

| 想要 | 选包页上搜这些 |
| --- | --- |
| Passwall | `luci-app-passwall` `xray-core` `sing-box` `geoview` |
| OpenClash | `luci-app-openclash` `ruby` `ruby-yaml` |
| AdGuard Home | `luci-app-adguardhome` `adguardhome` |
| SmartDNS | `smartdns` `luci-app-smartdns` |

引擎要单独选——`luci-app-passwall` 的引擎是靠它自己的 `INCLUDE_*` 子选项带的，那些不是包名，选包页列不出来，所以得把 `xray-core`、`sing-box` 一起勾上。

`kmod-nft-tproxy` 与 `kmod-tun` **特意保留**（两个加起来不到 30 KB）。内核模块事后补不了，删了的话"去选包页加回代理"这条路就断了——页面上会直接标成红色的「缺 N 内核模块」。

每个 Release 都会附带一份 `custom-packages.txt`，列出该次编译实际勾选的自定义软件包（按配置文件分组，带注释）；固件实际安装的完整包列表见同一 Release 中的 `*.manifest`。

## 临时加装软件包（选包页）

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

左上角第二个下拉框切换视图：

* **全部软件包** —— 按分类折叠的完整可选清单，默认
* **仅看改动** —— 只列本次增删的包
* **本次固件清单** —— 这次编出来的固件里会有哪些包

固件清单里每一行都会进固件，所以复选框在这个视图会误导（勾/不勾读起来像"在/不在"）。这里换成两个记号：

* **●** 配置里点名要的
* **○** 依赖带进来的，你没点名

点记号可以互换。把 ○ 改成 ●，意思是"就算带它进来的那个包被移掉，我也要它"；把 ● 改回去则未必会离开清单——`adguardhome` 取消点名后仍然留着，因为 `luci-app-adguardhome` 还依赖它；而 `autocore` 这种配置里点名的一取消就直接离开清单，底部串出现 `-autocore`。

固件清单分四档统计，比如 `基础配置 85 ＋ 依赖带入 202 ＋ 本次新增 1 ＋ 新增带入 47`。前两档直接来自 `.packageinfo` 索引里 defconfig 已经算好的结果，准确；后两档是页面自己叠加的。

这份清单**不能从依赖图重算**，只能拿 defconfig 的结果当起点。实测过：从 85 个显式勾选出发算传递闭包只得 266 个，而 defconfig 的真实答案是 287 个——漏掉的 29 个是 `base-files`、`busybox` 这类 target 默认包和条件依赖，多出的 8 个是 `firewall`、`iptables-*` 这些 defconfig 在互斥备选里没挑中的。

两处不准要知道：「新增带入」是**下限**，只算无条件依赖；**移除之后清单偏多**，被移除的包腾出来的依赖不会跟着消失（那要 defconfig 重算才知道，页面不猜）。

页面左上角第一个下拉框切换数据源，共四项——两条编译线各一项，外加两项官方索引：

* **编译索引**（首选）—— 带描述、分类、版本、依赖、冲突、许可证与上游地址，含自建包，且保证这条分支编得出来。
* **官方索引** —— 直接从 immortalwrt 下载站取（`25.12-SNAPSHOT` 与 `snapshots` 的 `aarch64_cortex-a53`），**不依赖任何构建**，Pages 一开就能用。代价是它整份数据**只有包名和版本两项**——`index.json` 的内容就是 `{"464xlat":"13", ...}`，没有第三个字段可挖。所以这一档没有描述、分类、依赖，也不含 kmod 与自建包，更不保证本源码树都编得出来，只能靠搜索用。

某条线的编译索引还不存在时，页面会自动回落到官方索引并在状态行说明原因。真编不出来的包名，workflow 那道核对会在编译前拦下，不会白等一两个小时。

搜索支持多词与模糊匹配：

* **多词** —— 空格分隔，每个词都要命中。`luci ddns`、`kmod usb storage` 这类最自然的输入现在都能搜到（以前整串当子串匹配，结果是 0 条）
* **模糊** —— 只按名字里字符出现的先后顺序命中即可，`lapdd` 能搜到 `luci-app-ddns`
* **按相关度排序** —— 用 fzy 那套子序列 DP 打分，连续命中有连击加成、词首命中有边界加成，所以完整子串天然排最前。搜 `npu` 第一条是 `luci-app-airoha-npu` 而不是恰好含 "npu" 的 `libinput`

点每行右侧的 **ⓘ** 展开详情：

* **事后能不能装** —— 见下一段
* **信息** —— 版本号、许可证、上游主页（可点）
* **冲突** —— 与本包互斥、不能同时装的包
* **依赖** —— 直接依赖，另有「展开传递闭包」告诉你勾上它总共会带进多少个包
* **条件依赖** —— 形如 `USE_GLIBC ? librt`，只在对应配置项打开时才装，不计入闭包
* **被依赖** —— 谁需要它。这一栏回答「这个包能不能删」：只要列表里有一个被选中，写 `-包名` 也移除不掉，构建时只会给个 warning 然后照常编进固件

超过 40 个的列表（被依赖、可装性里缺的依赖）默认截断，底下有「展开全部 N 个」。按钮上写着总数，因为 `libc` 被 **7229** 个包依赖，一次全铺开是要花点时间的。

详情数据在单独的 `detail-<分支>.json` 里，主索引渲染完之后在后台取回来——行尾的可装性标记要用它里面的依赖图。两份文件 gzip 后分别是 164 KB 和 70 KB，拆开是为了让首屏先出来。

**刷完机还能不能补装。** 没勾的包，行尾会标出它事后能不能用 `apk add` 装上：

| 标记 | 含义 |
| --- | --- |
| 可后装 | 依赖都已在固件里，刷完机直接 `apk add` 就行，不用重编 |
| 缺 N 依赖 | 缺的都不是内核模块，官方源多半能自动补齐 |
| 缺 N 内核模块 | 依赖里有内核模块不在固件里，事后补不了 |
| 只能编进固件 | 本体自己就是内核模块 |

内核模块补不了，是因为每个 kmod 都硬依赖一个带哈希的内核版本：

```
你的固件   kernel 6.18.44~c3e3e221bd513a781451e164ab71a3b5-r1
官方源     kernel 6.18.44~7c08b90b811abacfe00d9dfacc86634c-r1
```

同样是 6.18.44，哈希却对不上——它由内核配置与补丁算出来，自建固件跟官方源必然不同。所以官方 kmod 装不上自建固件，反过来也一样，kmod 只有编固件这一次机会。官方 kmod 甚至是按 `targets/<目标>/<子目标>/kmods/<版本>-<哈希>/` 分目录托管的，你那个哈希在人家那儿根本不存在。

红黄两档的包展开 ⓘ 会多出两个按钮：

* **补齐依赖** —— 把闭包里固件还缺的包全部加进选中列表
* **只补内核模块** —— 只加其中的内核模块

两个都**不会把本体勾上**。本体留到刷完机再 `apk add`，版本跟着官方源走，以后 `apk upgrade` 也能跟进，不必为它重编固件。`luci-app-dockerman` 是个好例子：「补齐依赖」会把 docker、containerd、dockerd、runc 一起编进固件，等于 docker 已经装好了；「只补内核模块」只塞 11 个 kmod，docker 本体刷完机再装。

两点提醒。**自建固件混用官方源不是官方支持的用法**——纯脚本包基本没事，带 `.so` 的包可能因为 base 不同步出问题，所以黄档写的是"多半能装"而不是打包票。另外这套标记只是把"装的时候才发现缺"提前到"选包的时候就看见"，**并没有省掉事先判断这个动作**；真想一劳永逸，得在配置里开 `CONFIG_ALL_KMODS=y` 把 1400 多个 kmod 全编出来，代价是编译时间大涨。

**选包页上显示的版本只能看，不能在这里指定**（事后 `apk add` 装的本体是另一回事，见上一段）。`.config` 里软件包只有开关位（`CONFIG_PACKAGE_xxx=y`），没有版本位，编出来是哪个版本取决于 `feeds update` 那一刻各 feed 仓库的 HEAD。要钉死某个包的版本，见下方[指定软件包版本](#指定软件包版本)。

## 刷新索引（不用编译）

生成索引其实不需要编译——`tmp/.packageinfo` 是 `make defconfig` 阶段扫描 feeds 产生的，那时一行代码都还没编。所以另有一个 `Actions → 更新选包页索引 → Run workflow`，**十分钟左右**跑完，默认一次刷新两条线。

改了 `selector/` 下的东西、或者 feeds 更新了想刷新清单，用它就行，不必为此跑一次完整构建。正常构建成功时也会顺带更新对应那条线的索引。

选包页托管在本仓库的 `gh-pages` 分支（首次需在 `Settings → Pages` 里把源设为 `gh-pages`）；页面与索引生成脚本在 [`selector/`](../selector/)。两条编译线各有一份索引，页面左上角可切换。

使用注意：

* Passwall 与 OpenClash **不要同时启用**，两者都会接管 nftables 规则链与 dnsmasq 配置
* dnsmasq / SmartDNS / AdGuardHome 默认均监听 53 端口，刷机后需手动规划端口分配
* 不在官方 feed 中的第三方插件，需在 workflow 的 `Install Feeds` 步骤前添加克隆步骤

## 指定软件包版本

版本写在 feed 的包 Makefile 里，不在 `.config`。[`config/pkg-versions.txt`](../config/pkg-versions.txt) 用来覆盖它，一行一个 `<包名> <版本>`，两条编译线共用：

```
sing-box    1.13.19
xray-core   25.8.3
```

编译前 workflow 会：

1. 在 `feeds/*/*/<包名>/Makefile` 里定位该包
2. 改写 `PKG_VERSION`，把 `PKG_HASH` 临时设成 `skip`
3. 跑一次 `make package/feeds/<feed>/<包名>/download` 把 tarball 拉下来
4. 算出实际 sha256 写回 `PKG_HASH`，**再跑一次 download 确认校验能过**

所以只填版本号，**不用自己算哈希**。Release 正文的「🔖 软件包版本覆盖」会列出本次改了哪些包。

### 限制

* **只支持 tarball 源。** Makefile 里有 `PKG_SOURCE_PROTO:=git` 的包会直接报错退出 —— 那种要改的是 `PKG_SOURCE_VERSION` 与 `PKG_MIRROR_HASH`，机制不同
* **版本必须是上游真实存在的 tag**，否则下载 404，构建立刻失败，不会等一两小时编完才发现
* **跨大版本升级可能编译失败。** feed 里的 Makefile 是按它自带的那个版本写的，build tag、依赖、补丁都不会跟着变
* 只影响本次编译产物，**不影响刷完机后 `apk` 源里的版本**

### 例：sing-box

immortalwrt feed 锁在 **1.12.25**，而上游正式版已经到 **1.13.19**。Go 工具链这一关不用担心，feed 提供的 `GO_DEFAULT_VERSION` 是 1.27，比谁的要求都高：

| sing-box | go.mod 要求 | 能否编 |
| --- | --- | --- |
| 1.12.25（feed 默认） | go 1.23.1 | ✅ |
| 1.13.19（最新正式） | go 1.24.7 | ✅ |
| 1.14.0-rc | go 1.25.5 | ✅ |

真正的风险在 build tag —— Makefile 里那十来个 `SING_BOX_TINY_BUILD_*` 对应 sing-box 的 `with_quic`、`with_gvisor` 等 tag，上游增删过的话，多余的 Go 会忽略、缺失的只是功能不开，一般不至于编译失败，但没实测过。另外 1.14 还是 rc，配置格式可能有 breaking change，`luci-app-passwall` 未必跟得上。

查上游有哪些 tag：

```sh
gh api repos/SagerNet/sing-box/releases --jq '.[].tag_name'
```
