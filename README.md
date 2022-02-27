# astOS
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
* Software installation
  * You can also install using chroot
```
ast install <overlay> <package>
```
* Updating
```
ast upgrade <overlay>
```
* chroot into overlay 
  * Once inside the chroot the OS behaves like regular Arch, so you can install and remove packages using pacman
```
ast chroot <overlay>
```
* Clone overlay
```
ast clone <overlay>
```
* Create new base overlay
```
ast new-overlay
```
* Deploy overlay    **!!! This will trigger a reboot !!!**
```
ast deploy <overlay>  
```
* Update base which new overlays are built from
```
ast base-update
```
# TODO: more docs
