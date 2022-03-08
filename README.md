# astOS (Arch Snapshot Tree OS)
### An immutable Arch based distribution utilizing btrfs snapshots  

---
## What is astOS?  

astOS is a distribution based on Arch Linux  
unlike Arch it uses an immutable (read-only) root filesystem  
software is installed and configured into individual snapshot trees, which can then be deployed and booted into

**This has several advantages:**
* Stability 
  * Due to the system being mounted as read only, it's not possible to accidentally overwrite system files  
  * If the system runs into issues, you can easily rollback the last working snapshot within minutes
  * Updating your system is perfectly safe and risk-free
* Configurability
  * With the overlays organised into a tree, you can easily have multiple different configurations of your software available, with varying packages, without any interference
  * For example: you can have a single Gnome desktop installed and then have 2 overlays on top - one with your video games, with the newest kernel and drivers, and the other for work, with the LTS kernel and more stable software, you can then easily switch between these depending on what you're trying to do
  * You can also easily try out software without having to worry about breaking your system or polluting it with unnecessary files, for example you can try out a new desktop environment in a snapshot and then delete the snapshot after, without modifying your main system at all
  * This can also be used for multi-user system, where each user has a completely separate system with different software, and yet they can share certain packages such as kernels and drivers
  * astOS allows you to install software by chrooting into overlays, therefore you can use software such as the AUR to install additional packages
  * astOS is, just like Arch, very customizable, you can choose exactly which software you want to use
---
### Installation:
* Use the official arch iso  

Install git first
```
pacman -Sy git
```
Clone repository
```
git clone "https://github.com/CuBeRJAN/astOS"  
cd astOS  
```
Partition and format drive
```
lsblk  # Find your drive name
cfdisk /dev/*** # Format drive, make sure to add EFI partition, if using BIOS leave 2M before partition  
```
Run installer
```
python3 main.py /dev/<partition> /dev/<drive> /dev/<efi part> # You can skip the EFI partition if installing in BIOS mode
```
### Usage:
Overlay in the instructions below refers only to the number of the overlay.
#### Show filesystem tree
* The current tree has "*" next to it
```
ast tree
```
* You can also get the number of the currently booted snapshot with
```
ast current
```
#### Add descritption to snapshot
* Snapshots allow you to add a description to them for easier identification
```
ast desc <overlay> <description>
```
#### Delete a tree
* This removes the tree and all it's branches
```
ast del <tree>
```
#### Software installation
* You can also install software in chroot
* AUR can be used under the chroot
* Flatpak can be used for persistent package installation
```
ast install <overlay> <package>
```
* After installing you can sync the newly installed packages to all the branches of the tree with
```
ast sync <tree>
```
#### Updating
* To update a single overlay
```
ast upgrade <overlay>
```
* To recursively upgrade an entire tree
```
ast tree-update <overlay>
```
#### Custom boot configuration
* If you wish to use a custom grub configuration, chroot into an overlay and edit /etc/default/grub, then run this command outside chroot to generate new grub config
```
ast boot <snapshot>
```
#### chroot into snapshot 
* Once inside the chroot the OS behaves like regular Arch, so you can install and remove packages using pacman or similar
* Do NOT run ast from inside a chroot, it could cause serious damage to the system, there is a failsafe in place, which can be bypassed with ```--chroot``` if you really need to  
```
ast chroot <overlay>
```
#### Clone snapshot
* This clones the snapshot as a tree
```
ast clone <snapshot>
```
#### Create new tree branch
```
ast branch <snapshot to branch from>
```
#### Clone snapshot under same parent
```
ast cbranch <snapshot>
```
#### Clone snapshot under specified parent
```
ast ubranch <parent> <snapshot>
```
#### Create new base tree
```
ast new-tree
```
#### Deploy snapshot  
```
ast deploy <overlay>  
```
#### Update base which new snapshots are built from
```
ast base-update
```

## Known bugs

* When running ast without arguments - IndexError: list index out of range
* Running ast without root permissions shows a lot of errors
* GDM and LightDM may not work  
* Docker has issues with permissions, to fix run
```
sudo chmod 666 /var/run/docker.sock
```


# TODO: more docs
