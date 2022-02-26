# astOS
An immutable Arch based distribution utilizing btrfs snapshots  
!!! BETA !!!
---
### Installation:
* Use the official arch iso
* install git and clone this repository
```
    pacman -S git  
    git clone "https://github.com/CuBeRJAN/astOS"  
    cd astOS  
    lsblk  # Find your drive name
    cfdisk /dev/*** # Format drive, make sure to add EFI partition, if using BIOS leave 2M before partition  
    mkfs.btrfs /dev/*** # Your install partition here  
    python3 main.py /dev/<partition> /dev/<drive> /dev/<efi part> # You can skip the EFI partition if installing in BIOS mode
```
### Usage:
* Software installation
```
    ast install <overlay number> <package>
```
* chroot
```
    ast chroot <overlay>
```
* deploy
```
    ast deploy <overlay>  
```
# TODO: more docs
