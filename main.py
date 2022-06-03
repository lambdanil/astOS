#!/usr/bin/python3
import os
import time
import sys
import subprocess

# TODO: the installer needs a proper rewrite

args = list(sys.argv)

def clear():
    os.system("clear")

def to_uuid(part):
    uuid = str(subprocess.check_output(f"blkid -s UUID -o value {part}", shell=True))
    return uuid.replace("b'","").replace('"',"").replace("\\n'","")

def main(args):

    while True:
        clear()
        print("Welcome to the astOS installer!\n\n\n\n\n")
        print("Select installation profile:\n1. Minimal install - suitable for embedded devices or servers\n2. Desktop install (Gnome) - suitable for workstations\n3. Desktop install (KDE Plasma)")
        InstallProfile = str(input("> "))
        if InstallProfile == "1":
            DesktopInstall = 0
            break
        if InstallProfile == "2":
            DesktopInstall = 1
            break
        if InstallProfile == "3":
            DesktopInstall = 2
            break

    clear()
    while True:
        print("Select a timezone (type list to list):")
        zone = input("> ")
        if zone == "list":
            os.system("ls /usr/share/zoneinfo | less")
        else:
            timezone = str(f"/usr/share/zoneinfo/{zone}")
            break

    clear()
    print("Enter hostname:")
    hostname = input("> ")

    os.system("pacman -S --noconfirm archlinux-keyring")
    os.system(f"mkfs.btrfs -f {args[1]}")

    if os.path.exists("/sys/firmware/efi"):
        efi = True
    else:
        efi = False

    os.system(f"mount {args[1]} /mnt")
    btrdirs = ["@","@.snapshots","@home","@var","@etc","@boot"]
    mntdirs = ["",".snapshots","home","var","etc","boot"]

    for btrdir in btrdirs:
        os.system(f"btrfs sub create /mnt/{btrdir}")

    os.system(f"umount /mnt")
    os.system(f"mount {args[1]} -o subvol=@,compress=zstd,noatime /mnt")

    for mntdir in mntdirs:
        os.system(f"mkdir /mnt/{mntdir}")
        os.system(f"mount {args[1]} -o subvol={btrdirs[mntdirs.index(mntdir)]},compress=zstd,noatime /mnt/{mntdir}")

    os.system("mkdir -p /mnt/{tmp,root}")
    os.system("mkdir -p /mnt/.snapshots/{rootfs,etc,var,boot,tmp,root}")

    if efi:
        os.system("mkdir /mnt/boot/efi")
        os.system(f"mount {args[3]} /mnt/boot/efi")

    os.system("pacstrap /mnt base linux linux-firmware nano python3 python-anytree dhcpcd arch-install-scripts btrfs-progs networkmanager grub")

    if efi:
        os.system("pacstrap /mnt efibootmgr")

    mntdirs_n = mntdirs
    mntdirs_n.remove("")
    os.system(f"echo 'UUID=\"{to_uuid(args[1])}\" / btrfs subvol=@,compress=zstd,noatime,ro 0 0' > /mnt/etc/fstab")

    for mntdir in mntdirs_n:
        os.system(f"echo 'UUID=\"{to_uuid(args[1])}\" /{mntdir} btrfs subvol=@{mntdir},compress=zstd,noatime 0 0' >> /mnt/etc/fstab")

    if efi:
        os.system(f"echo 'UUID=\"{to_uuid(args[3])}\" /boot/efi vfat umask=0077 0 2' >> /mnt/etc/fstab")

    os.system("echo '/.snapshots/ast/root /root none bind 0 0' >> /mnt/etc/fstab")
    os.system("echo '/.snapshots/ast/tmp /tmp none bind 0 0' >> /mnt/etc/fstab")

    astpart = to_uuid(args[1])

    os.system(f"mkdir -p /mnt/usr/share/ast/db")
    os.system(f"echo '0' > /mnt/usr/share/ast/snap")

    os.system(f"echo 'NAME=\"astOS\"' > /mnt/etc/os-release")
    os.system(f"echo 'PRETTY_NAME=\"astOS\"' >> /mnt/etc/os-release")
    os.system(f"echo 'ID=astos' >> /mnt/etc/os-release")
    os.system(f"echo 'BUILD_ID=rolling' >> /mnt/etc/os-release")
    os.system(f"echo 'ANSI_COLOR=\"38;2;23;147;209\"' >> /mnt/etc/os-release")
    os.system(f"echo 'HOME_URL=\"https://github.com/CuBeRJAN/astOS\"' >> /mnt/etc/os-release")
    os.system(f"echo 'LOGO=astos-logo' >> /mnt/etc/os-release")
    os.system(f"cp -r /mnt/var/lib/pacman/* /mnt/usr/share/ast/db")
    os.system(f"sed -i s,\"#DBPath      = /var/lib/pacman/\",\"DBPath      = /usr/share/ast/db/\",g /mnt/etc/pacman.conf")
    os.system(f"echo 'DISTRIB_ID=\"astOS\"' > /mnt/etc/lsb-release")
    os.system(f"echo 'DISTRIB_RELEASE=\"rolling\"' >> /mnt/etc/lsb-release")
    os.system(f"echo 'DISTRIB_DESCRIPTION=astOS' >> /mnt/etc/lsb-release")

    os.system(f"arch-chroot /mnt ln -sf {timezone} /etc/localtime")
    os.system("echo 'en_US UTF-8' >> /mnt/etc/locale.gen")
#    os.system("sed -i s/'^#'// /mnt/etc/locale.gen")
#    os.system("sed -i s/'^ '/'#'/ /mnt/etc/locale.gen")
    os.system(f"arch-chroot /mnt locale-gen")
    os.system(f"arch-chroot /mnt hwclock --systohc")
    os.system(f"echo 'LANG=en_US.UTF-8' > /mnt/etc/locale.conf")
    os.system(f"echo {hostname} > /mnt/etc/hostname")

    os.system("sed -i '0,/@/{s,@,@.snapshots/rootfs/snapshot-tmp,}' /mnt/etc/fstab")
    os.system("sed -i '0,/@etc/{s,@etc,@.snapshots/etc/etc-tmp,}' /mnt/etc/fstab")
#    os.system("sed -i '0,/@var/{s,@var,@.snapshots/var/var-tmp,}' /mnt/etc/fstab")
    os.system("sed -i '0,/@boot/{s,@boot,@.snapshots/boot/boot-tmp,}' /mnt/etc/fstab")
    os.system("mkdir -p /mnt/.snapshots/ast/images")
    os.system("arch-chroot /mnt btrfs sub set-default /.snapshots/rootfs/snapshot-tmp")

    os.system("arch-chroot /mnt ln -s /.snapshots/ast /var/lib/ast")    

    clear()
    os.system("arch-chroot /mnt passwd")
    while True:
        print("did your password set properly (y/n)?")
        reply = input("> ")
        if reply.casefold() == "y":
            break
        else:
            clear()
            os.system("arch-chroot /mnt passwd")

    os.system("arch-chroot /mnt systemctl enable NetworkManager")
    os.system("mkdir -p /mnt/.snapshots/{ast,boot,etc,rootfs,var}")
    os.system("echo {\\'name\\': \\'root\\', \\'children\\': [{\\'name\\': \\'0\\'}]} > /mnt/.snapshots/ast/fstree")

    if DesktopInstall:
        os.system("echo {\\'name\\': \\'root\\', \\'children\\': [{\\'name\\': \\'0\\'},{\\'name\\': \\'1\\'}]} > /mnt/.snapshots/ast/fstree")
        os.system(f"echo '{astpart}' > /mnt/.snapshots/ast/part")

    os.system(f"arch-chroot /mnt sed -i s,Arch,astOS,g /etc/default/grub")
    os.system(f"arch-chroot /mnt grub-install {args[2]}")
    os.system(f"arch-chroot /mnt grub-mkconfig {args[2]} -o /boot/grub/grub.cfg")
    os.system("sed -i '0,/subvol=@/{s,subvol=@,subvol=@.snapshots/rootfs/snapshot-tmp,g}' /mnt/boot/grub/grub.cfg")
    os.system("cp ./astpk.py /mnt/usr/local/sbin/ast")
    os.system("arch-chroot /mnt chmod +x /usr/local/sbin/ast")
    os.system("btrfs sub snap -r /mnt /mnt/.snapshots/rootfs/snapshot-0")
    os.system("btrfs sub create /mnt/.snapshots/etc/etc-tmp")
    os.system("btrfs sub create /mnt/.snapshots/var/var-tmp")
    os.system("btrfs sub create /mnt/.snapshots/boot/boot-tmp")
#    os.system("cp --reflink=auto -r /mnt/var/* /mnt/.snapshots/var/var-tmp")
    os.system("mkdir -p /mnt/.snapshots/var/var-tmp/lib/{pacman,systemd}")
    os.system("cp --reflink=auto -r /mnt/var/lib/pacman/* /mnt/.snapshots/var/var-tmp/lib/pacman/")
    os.system("cp --reflink=auto -r /mnt/var/lib/systemd/* /mnt/.snapshots/var/var-tmp/lib/systemd/")
    os.system("cp --reflink=auto -r /mnt/boot/* /mnt/.snapshots/boot/boot-tmp")
    os.system("cp --reflink=auto -r /mnt/etc/* /mnt/.snapshots/etc/etc-tmp")
    os.system("btrfs sub snap -r /mnt/.snapshots/var/var-tmp /mnt/.snapshots/var/var-0")
    os.system("btrfs sub snap -r /mnt/.snapshots/boot/boot-tmp /mnt/.snapshots/boot/boot-0")
    os.system("btrfs sub snap -r /mnt/.snapshots/etc/etc-tmp /mnt/.snapshots/etc/etc-0")
    os.system(f"echo '{astpart}' > /mnt/.snapshots/ast/part")

    if DesktopInstall == 1:
        os.system(f"echo '1' > /mnt/usr/share/ast/snap")
        os.system("pacstrap /mnt flatpak gnome gnome-extra gnome-themes-extra gdm pipewire pipewire-pulse sudo")
        clear()
        print("Enter username (all lowercase, max 8 letters)")
        username = input("> ")
        while True:
            print("did your set username properly (y/n)?")
            reply = input("> ")
            if reply.casefold() == "y":
                break
            else:
                clear()
                print("Enter username (all lowercase, max 8 letters)")
                username = input("> ")
        os.system(f"arch-chroot /mnt useradd {username}")
        os.system(f"arch-chroot /mnt passwd {username}")
        while True:
            print("did your password set properly (y/n)?")
            reply = input("> ")
            if reply.casefold() == "y":
                break
            else:
                clear()
                os.system(f"arch-chroot /mnt passwd {username}")
        os.system(f"arch-chroot /mnt usermod -aG audio,input,video,wheel {username}")
        os.system(f"arch-chroot /mnt passwd -l root")
        os.system(f"chmod +w /mnt/etc/sudoers")
        os.system(f"echo '%wheel ALL=(ALL:ALL) ALL' >> /mnt/etc/sudoers")
        os.system(f"chmod -w /mnt/etc/sudoers")
        os.system(f"arch-chroot /mnt mkdir /home/{username}")
        os.system(f"echo 'export XDG_RUNTIME_DIR=\"/run/user/1000\"' >> /home/{username}/.bashrc")
        os.system(f"arch-chroot /mnt chown -R {username} /home/{username}")
        os.system(f"arch-chroot /mnt systemctl enable gdm")
        os.system(f"cp -r /mnt/var/lib/pacman/* /mnt/usr/share/ast/db")
        os.system("btrfs sub snap -r /mnt /mnt/.snapshots/rootfs/snapshot-1")
        os.system("btrfs sub del /mnt/.snapshots/etc/etc-tmp")
        os.system("btrfs sub del /mnt/.snapshots/var/var-tmp")
        os.system("btrfs sub del /mnt/.snapshots/boot/boot-tmp")
        os.system("btrfs sub create /mnt/.snapshots/etc/etc-tmp")
        os.system("btrfs sub create /mnt/.snapshots/var/var-tmp")
        os.system("btrfs sub create /mnt/.snapshots/boot/boot-tmp")
#        os.system("cp --reflink=auto -r /mnt/var/* /mnt/.snapshots/var/var-tmp")
        os.system("mkdir -p /mnt/.snapshots/var/var-tmp/lib/{pacman,systemd}")
        os.system("cp --reflink=auto -r /mnt/var/lib/pacman/* /mnt/.snapshots/var/var-tmp/lib/pacman/")
        os.system("cp --reflink=auto -r /mnt/var/lib/systemd/* /mnt/.snapshots/var/var-tmp/lib/systemd/")
        os.system("cp --reflink=auto -r /mnt/boot/* /mnt/.snapshots/boot/boot-tmp")
        os.system("cp --reflink=auto -r /mnt/etc/* /mnt/.snapshots/etc/etc-tmp")
        os.system("btrfs sub snap -r /mnt/.snapshots/var/var-tmp /mnt/.snapshots/var/var-1")
        os.system("btrfs sub snap -r /mnt/.snapshots/boot/boot-tmp /mnt/.snapshots/boot/boot-1")
        os.system("btrfs sub snap -r /mnt/.snapshots/etc/etc-tmp /mnt/.snapshots/etc/etc-1")
        os.system("btrfs sub snap /mnt/.snapshots/rootfs/snapshot-1 /mnt/.snapshots/rootfs/snapshot-tmp")

    elif DesktopInstall == 2:
        os.system(f"echo '1' > /mnt/usr/share/ast/snap")
        os.system("pacstrap /mnt flatpak plasma xorg kde-applications sddm pipewire pipewire-pulse sudo")
        clear()
        print("Enter username (all lowercase, max 8 letters)")
        username = input("> ")
        while True:
            print("did your set username properly (y/n)?")
            reply = input("> ")
            if reply.casefold() == "y":
                break
            else:
                clear()
                print("Enter username (all lowercase, max 8 letters)")
                username = input("> ")
        os.system(f"arch-chroot /mnt useradd {username}")
        os.system(f"arch-chroot /mnt passwd {username}")
        while True:
            print("did your password set properly (y/n)?")
            reply = input("> ")
            if reply.casefold() == "y":
                break
            else:
                clear()
                os.system(f"arch-chroot /mnt passwd {username}")
        os.system(f"arch-chroot /mnt usermod -aG audio,input,video,wheel {username}")
        os.system(f"arch-chroot /mnt passwd -l root")
        os.system(f"chmod +w /mnt/etc/sudoers")
        os.system(f"echo '%wheel ALL=(ALL:ALL) ALL' >> /mnt/etc/sudoers")
        os.system(f"echo '[Theme]' > /mnt/etc/sddm.conf")
        os.system(f"echo 'Current=breeze' >> /mnt/etc/sddm.conf")
        os.system(f"chmod -w /mnt/etc/sudoers")
        os.system(f"arch-chroot /mnt mkdir /home/{username}")
        os.system(f"echo 'export XDG_RUNTIME_DIR=\"/run/user/1000\"' >> /home/{username}/.bashrc")
        os.system(f"arch-chroot /mnt chown -R {username} /home/{username}")
        os.system(f"arch-chroot /mnt systemctl enable sddm")
        os.system(f"cp -r /mnt/var/lib/pacman/* /mnt/usr/share/ast/db")
        os.system("btrfs sub snap -r /mnt /mnt/.snapshots/rootfs/snapshot-1")
        os.system("btrfs sub del /mnt/.snapshots/etc/etc-tmp")
        os.system("btrfs sub del /mnt/.snapshots/var/var-tmp")
        os.system("btrfs sub del /mnt/.snapshots/boot/boot-tmp")
        os.system("btrfs sub create /mnt/.snapshots/etc/etc-tmp")
        os.system("btrfs sub create /mnt/.snapshots/var/var-tmp")
        os.system("btrfs sub create /mnt/.snapshots/boot/boot-tmp")
#        os.system("cp --reflink=auto -r /mnt/var/* /mnt/.snapshots/var/var-tmp")
        os.system("mkdir -p /mnt/.snapshots/var/var-tmp/lib/{pacman,systemd}")
        os.system("cp --reflink=auto -r /mnt/var/lib/pacman/* /mnt/.snapshots/var/var-tmp/lib/pacman/")
        os.system("cp --reflink=auto -r /mnt/var/lib/systemd/* /mnt/.snapshots/var/var-tmp/lib/systemd/")
        os.system("cp --reflink=auto -r /mnt/boot/* /mnt/.snapshots/boot/boot-tmp")
        os.system("cp --reflink=auto -r /mnt/etc/* /mnt/.snapshots/etc/etc-tmp")
        os.system("btrfs sub snap -r /mnt/.snapshots/var/var-tmp /mnt/.snapshots/var/var-1")
        os.system("btrfs sub snap -r /mnt/.snapshots/boot/boot-tmp /mnt/.snapshots/boot/boot-1")
        os.system("btrfs sub snap -r /mnt/.snapshots/etc/etc-tmp /mnt/.snapshots/etc/etc-1")
        os.system("btrfs sub snap /mnt/.snapshots/rootfs/snapshot-1 /mnt/.snapshots/rootfs/snapshot-tmp")

    else:
        os.system("btrfs sub snap /mnt/.snapshots/rootfs/snapshot-0 /mnt/.snapshots/rootfs/snapshot-tmp")

    os.system("cp -r /mnt/root/. /mnt/.snapshots/root/")
    os.system("cp -r /mnt/tmp/. /mnt/.snapshots/tmp/")
    os.system("rm -rf /mnt/root/*")
    os.system("rm -rf /mnt/tmp/*")
#    os.system("umount /mnt/var")

    if efi:
        os.system("umount /mnt/boot/efi")

    os.system("umount /mnt/boot")
#    os.system("mkdir /mnt/.snapshots/var/var-tmp")
#    os.system("mkdir /mnt/.snapshots/boot/boot-tmp")
#    os.system(f"mount {args[1]} -o subvol=@var,compress=zstd,noatime /mnt/.snapshots/var/var-tmp")
    os.system(f"mount {args[1]} -o subvol=@boot,compress=zstd,noatime /mnt/.snapshots/boot/boot-tmp")
#    os.system("cp --reflink=auto -r /mnt/.snapshots/var/var-tmp/* /mnt/var")
    os.system("cp --reflink=auto -r /mnt/.snapshots/boot/boot-tmp/* /mnt/boot")
    os.system("umount /mnt/etc")
#    os.system("mkdir /mnt/.snapshots/etc/etc-tmp")
    os.system(f"mount {args[1]} -o subvol=@etc,compress=zstd,noatime /mnt/.snapshots/etc/etc-tmp")
    os.system("cp --reflink=auto -r /mnt/.snapshots/etc/etc-tmp/* /mnt/etc")

    if DesktopInstall:
        os.system("cp --reflink=auto -r /mnt/.snapshots/etc/etc-1/* /mnt/.snapshots/rootfs/snapshot-tmp/etc")
        os.system("cp --reflink=auto -r /mnt/.snapshots/var/var-1/* /mnt/.snapshots/rootfs/snapshot-tmp/var")
        os.system("cp --reflink=auto -r /mnt/.snapshots/boot/boot-1/* /mnt/.snapshots/rootfs/snapshot-tmp/boot")
    else:
        os.system("cp --reflink=auto -r /mnt/.snapshots/etc/etc-0/* /mnt/.snapshots/rootfs/snapshot-tmp/etc")
        os.system("cp --reflink=auto -r /mnt/.snapshots/var/var-0/* /mnt/.snapshots/rootfs/snapshot-tmp/var")
        os.system("cp --reflink=auto -r /mnt/.snapshots/boot/boot-0/* /mnt/.snapshots/rootfs/snapshot-tmp/boot")

    os.system("umount -R /mnt")
    os.system(f"mount {args[1]} /mnt")
    os.system("btrfs sub del /mnt/@")
    os.system("umount -R /mnt")
    clear()
    print("Installation complete")
    print("You can reboot now :)")

main(args)

