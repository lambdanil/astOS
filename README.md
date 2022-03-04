# astOS (Arch Snapshot Tree OS)
An immutable Arch based distribution utilizing btrfs snapshots  
!!! BETA !!!
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
mkfs.btrfs /dev/*** # Your install partition here  
```
Run installer
```
python3 main.py /dev/<partition> /dev/<drive> /dev/<efi part> # You can skip the EFI partition if installing in BIOS mode
```
### Usage:
Overlay in the instructions below refers only to the number of the overlay.
#### Show filesystem tree
```
ast tree
```
#### Show which image is currently booted
```
ast current
```
#### Add descritption to overlay
```
ast desc <overlay> <description>
```
#### Delete a tree
```
ast del <tree>
```
#### Software installation
* You can also install using chroot
```
ast install <overlay> <package>
```
#### Updating
```
ast upgrade <overlay>
```
#### chroot into overlay 
* Once inside the chroot the OS behaves like regular Arch, so you can install and remove packages using pacman
* Do NOT run ast from inside a chroot, it could cause serious damage to the system, there is a failsafe in place, which can be bypassed with ```--chroot``` if you really need to  
* Make sure to take a btrfs snapshot of /var before making any serious changes to it in a chroot, as /var is a mutable directory
* You can chroot into the image of the running system and then deploy it again, as the currently running system is actually a copy of the image
```
ast chroot <overlay>
```
#### Clone overlay
* This clones the deployment as a root tree deployment
```
ast clone <overlay>
```
#### Create new tree branch
```
ast branch <tree/branch to branch from>
```
#### Create new base tree
```
ast new-overlay
```
#### Recursively sync tree and all it's branches
```
ast sync <tree>
```
#### Deploy overlay    **!!! This will trigger a reboot !!!**
```
ast deploy <overlay>  
```
#### Update base which new images are built from
```
ast base-update
```
# TODO: more docs
