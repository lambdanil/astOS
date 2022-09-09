# astOS (Arch Snapshot Tree OS)
### 一个运用了Btrfs快照的基于Arch的发行版  

![astos-logo](logo.jpg)

---

## 目录
* [什么是astOS？](#什么是astos)
* [astOS和其他类似发行版的比较](#astos和其他类似发行版的比较)
* [帮助使用ast和astOS](#帮助使用ast和astos)
  * [安装](#安装)
  * [安装后操作](#安装后操作)
  * [快照管理与部署](#快照管理与部署)
  * [软件包管理](#软件包管理)
* [额外帮助](#额外帮助)
  * [更新Pacman密钥](#更新pacman密钥)
  * [在/etc中保存配置](#在etc中保存配置)
  * [配置双启动](#配置双启动)
  * [更新ast工具](#更新ast工具)
  * [为ast工具排除故障](#为ast工具排除故障)
* [已知漏洞](#已知漏洞)
* [贡献](#贡献)
* [社区](#社区)

---

## 什么是astOS？ 

astOS是一个基于[Arch Linux](https://archlinux.org)的现代化发行版。  
不像Arch Linux那样，它使用了一个不可变（只读）的根文件系统，软件和配置被安放在独立的快照中，然后它们可以被部署并启动。这些软件并没有使用astOS专用的软件包管理器，而是依赖于Arch Linux的[pacman](https://wiki.archlinux.org/title/pacman)管理器。


**这带来了一些优点：**

* 安全性
  * 即使一个软件被以最高权限运行，它也不能在系统中植入病毒程序。
* 稳定性和可依赖性
  * 因为系统被挂载为只读模式，意外修改系统文件是不可能的。
  * 如果系统出现问题，你可以轻松地快速回滚到上一个快照版本。
  * 原子更新——它让升级整个系统变得更加安全可靠。
  * 得益于快照功能，你可以放心安装最新的软件而不会让系统变得不稳定。
  * 你不需要对astOS进行太多维护，因为它内置的ast工具会自动在系统更新后创建快照，并在部署到新快照前检查系统是否被正确地升级。
* 可配置性
  * 得益于树形的快照系统，你可以同时拥有多套不同的配置，而它们彼此间不会有任何干扰。\
  比如：你可以在同一个Gnome桌面环境中同时拥有两个快照——一个带有最新的内核和驱动，用于游戏；另一个带有LTS内核和更加稳定的软件，用于工作。你可以轻松地在它们之间切换，取决于你的需求。
  * 你也可以放心地尝试新的软件，而不用担心破坏掉系统或者被垃圾文件污染环境。\
  比如：你可以在某个快照内尝试一个新的桌面环境，事后删除这个快照，这样系统仍然会保持最开始的样子。
  * 快照系统也可以被用于搭建多用户系统，这样每个用户拥有不同的软件和独立的空间，同时他们可以共享基础组件比如内核和驱动。
  * astOS允许用户通过事后chroot进快照来安装软件，因此你可以从某些地方比如AUR安装额外软件。
  * astOS就像Arch Linux,它十分可定制，你可以选择去使用哪些软件包。
* 因为astOS的可靠性和它的自动更新功能，它很适合被用于个人电脑或者嵌入式设备。
* astOS也可以利用开发容器映像和容器化软件包成为工作站系统或多用途发行版。

---
## astOS和其他类似发行版的比较
* **NixOS** - astOS有一个更加传统的文件目录结构。NixOS完全地由Nix编程语言配置，但astOS使用Arch Linux的软件包。astOS占用更少的存储空间，并可以更加快速简单地配置系统（尽管这让可重建性变得不如NixOS），同时配置拥有更大的灵活性。astOS是FHS完备的，软件能更好地运行在它之上。
  * 为了实现类似NixOS的功能，astOS允许用户使用Ansible工具来声明式地进行配置。
* **Fedora Silverblue/Kinoite** - astOS有更好的可定制性，但这需要更多手动配置。astOS还支持双启动，不像Silverblue。 
* **OpenSUSE MicroOS** - astOS有更好的可定制性，正如上面所说的，但这需要更多手动配置。astOS和MicroOS的相似之处是它们都运用了Btrfs快照。astOS官方支持KDE Plasma桌面环境，同时其他桌面环境可选，但MicroOS仅支持Gnome。astOS还支持双启动，也能在不重新启动的情况下安装软件或修改系统。

---
## 帮助使用ast和astOS
### 安装
* astOS从Arch Linux官方镜像环境中安装，你可以从这里下载[https://archlinux.org](https://archlinux.org)。
* 如果在安装过程中遇到软件包安装问题，请确保你使用的是最新版镜像，并检查pacman密钥是否需要更新。
* 安装astOS需要网络连接。
* 现在astOS安装程序提供4种安装方式，分别是最小化安装、Gnome桌面环境、KDE Plasma桌面环境和MATE桌面环境，在未来，更多桌面环境会被添加。
* 你可以根据需求简单地更改安装脚本（但未经更改的安装脚本是稳定的）。

首先安装git——这让你能够下载安装脚本

```
pacman -Sy git
```
克隆仓库

```
git clone "https://github.com/CuBeRJAN/astOS"  
cd astOS  
```
分区并格式化硬盘

* 如果安装在BIOS引导系统，选择dos（MBR）分区表。
* 如果安装在EFI引导系统，选择GPT分区表。
* EFI分区必须被格式化为FAT32文件系统（```mkfs.fat -F32 /dev/<part>```）。

```
lsblk  # 查找硬盘名称
cfdisk /dev/*** # 硬盘分区，确保添加一个EFI分区，如果选择BIOS安装，请预留2MiB空间 
mkfs.btrfs /dev/*** # 将分区格式化为btrfs文件系统，不要跳过这一步！
```
运行安装脚本

```
python3 main.py /dev/<partition> /dev/<drive> /dev/<efi part> # 如果选择BIOS引导系统，不要添加第三个参数！
```

### 安装后操作
* 如果你选择了自动安装某个桌面环境，那么你无需再手动进行这些安装后操作。
* 一些关于安装后的操作可以在[ArchWiki](https://wiki.archlinux.org/title/general_recommendations)查看，但对于astOS这个特殊的发行版，需要首先进行以下的步骤：
  * 首先用`ast clone 0`从`base`复制一个快照。
  * 然后执行`ast chroot <snapshot>`，chroot进这个新的快照。之后执行以下操作：
    * 添加新的用户`useradd <username>`。
    * 设置该用户的密码`passwd <username>`。
    * 设置root用户的新密码`passwd root`。
    * 用`pacman`安装其他软件（桌面环境、容器等）。
    * 用`exit`退出chroot环境。
    * 你可以用`ast deploy <snapshot>`来部署快照。

#### 额外帮助
* 我们推荐查阅[Arch wiki](https://wiki.archlinux.org/)来获取astOS以外的帮助。
* 在[Github issues页面](https://github.com/CuBeRJAN/astOS/issues)反馈漏洞。
* **提示：你可以运行`ast help`来快速查阅可用的命令。**

### 快照管理与部署

#### 基础（Base）快照
* 快照`0`被保留为基础系统快照，它是不可变的，且只能通过`ast base-update`更新。
#### 打印快照系统树

```
ast tree
```

* 输出看起来像这样：

```
root - root
├── 0 - base snapshot
└── 1 - multiuser system
    └── 4 - applications
        ├── 6 - MATE full desktop
        └── 2*- Plasma full desktop
```
* 星号表示当前被选为默认的快照。

* 你也可以获取当前的快照的序号：

```
ast current
```
#### 为快照添加描述
* 你可以为快照添加描述以易于辨认：

```
ast desc <snapshot> <description>
```
#### 删除快照树
* 删除某树及其所有分支：

```
ast del <tree>
```
#### 自定义启动配置
* 如果你需要使用一个自定义GRUB配置，chroot进一个快照然后编辑`/etc/default/grub`，然后部署这个快照并重新启动。

#### chroot进入快照 
* 在快照内，系统操作就像普通的Arch Linux,所以你可以用`pacman`安装或删除软件包或者其他操作。
* 不要在chroot环境中运行`ast`，这将会对系统造成破坏，所以有一个保护措施。如果执意要在chroot环境中运行`ast`，请传递`--chroot`参数（不推荐）。
* 请用`exit`正确退出chroot环境，否则对系统的更改不会被保存。
* 如果没有通过`exit`退出chroot环境，将会遗留垃圾，可以用`ast tmp`清理它们。


```
ast chroot <snapshot>
```

* 你可以在当前启动的快照中进入一个解锁的shell环境，运行：

```
ast live-chroot
```

* 在这个解锁的shell环境中所做的更改将不会在新的部署中保存。

#### 其他chroot选项

* 在快照内运行指定命令：

```
ast run <snapshot> <command>
```

* 在快照与其所有分支快照中运行指定命令：

```
ast tree-run <tree> <command>
```

#### 克隆快照
* 将快照克隆为新的快照树：

```
ast clone <snapshot>
```

#### 递归克隆快照树  
* 递归地克隆整个快照树：

```
ast clone-tree <snapshot>
```

#### 创建新的快照树分支
* 为指定快照创建分支：

```
ast branch <snapshot to branch from>
```
#### 克隆快照至同一父快照下：

```
ast cbranch <snapshot>
```
#### 克隆快照到指定父快照下：
* 确保事后同步快照树。

```
ast ubranch <parent> <snapshot>
```
#### 创建新的基础（Base）快照：

```
ast new
```
#### 部署快照：
* 事后重新启动来进入新部署的快照。

```
ast deploy <snapshot>  
```

#### 更新基础（Base）快照：

```
ast base-update
```
* 提示：基础（Base）快照本身位于`/.snapshots/rootfs/snapshot-0`，但它配套的`/var`和`/etc`目录分别位于`/.snapshots/var/var-0`和`/.snapshots/etc/etc-0`，因此如果你真的需要在基础（Base）快照中进行配置更改，你可以将其挂载为读写模式，工作完成后再将其重新挂载为只读模式。

### 软件包管理

#### 软件安装
* 在chroot环境中可以通过`pacman`安装软件。
* 在chroot环境中也可以使用AUR。
* 也安装Flatpak包。
* 使用容器来安装也可以，比如使用[distrobox](https://github.com/89luca89/distrobox)。

```
ast install <snapshot> <package>
```

* 要在安装新软件包后将其同步到其所有分支，请运行：
  * 自动这也会更新快照树中的所有快照。

```
ast sync <tree>
```

* 如果想要在同步时不更新快照（可能会造成软件包重复），请运行：

```
ast force-sync <tree>
```

* astOS原生支持AUR
* 在启用AUR支持前我们需要保证`paru`没有被安装：

```
ast remove <snapshot> paru
```

* 启用AUR支持需要编辑快照配置文件：

```
EDITOR=nano ast edit-conf <snapshot> # 设置EDITOR变量来选择想要用的编辑器
```

* 在打开的页面中添加下面这一行文字：

```
aur::True
```

* 保存并退出。
* 现在AUR支持被启用了——`ast install`以及其他命令现在可以被用于管理AUR软件。
#### 删除软件

* 为单个快照删除：

```
ast remove <snapshot> <package or packages>
```

* 为某个快照及其所有子快照删除：

```
ast tree-rmpkg <tree> <pacakge or packages>
```


#### 更新软件
* 我们推荐在更新之前进行快照克隆，以便在更新出现错误时回滚。
* 这只会更新系统软件包，要更新ast工具，请看“[更新ast工具](#更新ast工具)” 

* 为单个快照更新：

```
ast upgrade <snapshot>
```
* 为某个快照及其所有子快照更新：

```
ast tree-upgrade <tree>
```

* 可以使用自动化工具（比如crontab）来简单高效地自动更新。

* 如果系统在更新后无法启动，可以在GRUB启动菜单中选择上一个正常运行的部署，启动后进行回滚操作。

```
ast rollback
```

* 然后可以重新启动进一个正常工作的系统。

## 额外帮助

### 更新Pacman密钥

* Arch Linux的pacman软件包管理器偶尔需要更新，可以运行：

```
ast install <snapshots> archlinux-keyring
```

### 在/etc中保存配置
* 通常配置应该在`ast chroot`中进行，但有时你可能会想在当前运行的系统中进行配置，请使用：

```
ast etc-update
```

* 这将会允许你编辑`/etc`中的文件，然后保存。

### 配置双启动
* astOS可以通过GRUB启动引导程序支持双启动。
* 在安装astOS时选择已存在的EFI分区，比如Windows创建的。
首先安装`os-prober`软件包：

```
ast install <snapshot> os-prober
```

然后编辑GRUB配置：

```
ast chroot <snapshot>
echo 'GRUB_DISABLE_OS_PROBER=false' >> /etc/default/grub
exit
```

最后只需要部署这个快照来应用新的GRUB配置：

```
ast deploy <snapshot>
```

如果Windows被找到，你可以在输出文本中找到：`Found Windows Boot Manager on...`。\
如果Windows没有被找到，请安装`ntfs-3g`软件包，然后重新部署快照。

### 更新ast工具
* 当运行`ast upgrade`时，`ast`不会被更新，所以有时需要手动更新`ast`。
* 请运行：

```
ast ast-sync
```

### 为ast工具排除故障

- 有时候需要为ast工具排除故障
将`ast`复制到某个地方：

```
cp /usr/local/sbin/ast astpk.py
```

下面的命令会输出`astpk.py`的结果，所以它有时挺有用：

```
sed -i -e s,\ 2\>\&1\>\ \/dev\/null,,g astpk.py
```

如果你编辑过`ast`文件，请事后恢复它。

## 已知漏洞

* 不带参数运行`ast`将会报错`IndexError: list index out of range`。
* 在没有管理员权限的情况下运行`ast`不会出现错误信息，而是`permission denied`。
* 交换分区（Swap）无法工作，所以我们推荐使用交换文件（Swapfile）或者zram。
* Docker有权限问题，要修复它，请运行：
```
sudo chmod 666 /var/run/docker.sock
```

* If you run into any issues, report them on [the issues page](https://github.com/CuBeRJAN/astOS/issues)
* 遇到问题请在[GitHub issues页面](https://github.com/CuBeRJAN/astOS/issues)反馈。

# 贡献
* 欢迎进行代码和文档贡献！
* 我们也希望您能够积极地反馈漏洞。
* 在开启PR前请测试您的代码。

# 社区
* 欢迎加入我们的[Discord](https://discord.gg/YVHEC6XNZw)，与我们共同交流、互相帮助！
* 祝你快快无忧照照无虑！

---

**本项目使用AGPLv3许可证**

