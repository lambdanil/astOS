#!/usr/bin/python3
import os
import time
import sys

args = list(sys.argv)
# startup-service; startup; astpk-part; astpk-cbase; astpk-coverlay; astpk-cetc; astpk-firstboot

def clear():
    os.system("clear")

def main(args):
    while True:
        clear()
        print("Welcome to the astOS installer!\n\n\n\n\n")
        print("Select installation profile:\n1. Minimal install - suitable for embedded devices or servers\n2. Desktop install - suitable for workstations")
        InstallProfile = str(input("> "))
        if InstallProfile == "1":
            DesktopInstall = 0
            break
        if InstallProfile == "2":
            DesktopInstall = 1
            break
    os.system("pacman --noconfirm -Sy")
    confirm = "n"
    os.system(f"mkfs.btrfs -f {args[1]}")
    if os.path.exists("/sys/firmware/efi"):
        efi = True
    else:
        efi = False
#    efi = False #
    os.system(f"mount {args[1]} /mnt")
    btrdirs = ["@","@.etc","@.overlays","@home","@tmp","@root","@.var","@var","@etc","@boot","@.boot"]
    mntdirs = ["",".etc",".overlays","home","tmp","root",".var","var","etc","boot",".boot"]
    for btrdir in btrdirs:
        os.system(f"btrfs sub create /mnt/{btrdir}")
    os.system(f"umount /mnt")
    os.system(f"mount {args[1]} -o subvol=@,compress=zstd,noatime /mnt")
    os.system("mkdir /mnt/boot")
    os.system("mkdir /mnt/etc")
    os.system("mkdir /mnt/var")
    for mntdir in mntdirs:
        os.system(f"mkdir /mnt/{mntdir}")
        os.system(f"mount {args[1]} -o subvol={btrdirs[mntdirs.index(mntdir)]},compress=zstd,noatime /mnt/{mntdir}")
    if efi:
        os.system("mkdir /mnt/boot/efi")
        os.system(f"mount {args[3]} /mnt/boot/efi")
    os.system("pacstrap /mnt base vim linux-lts linux-firmware python-anytree dhcpcd btrfs-progs python3 git arch-install-scripts networkmanager grub")
    if efi:
        os.system("pacstrap /mnt efibootmgr")
    mntdirs_n = mntdirs
    mntdirs_n.remove("")
    os.system(f"echo '{args[1]} / btrfs subvol=@,compress=zstd,noatime,ro 0 0' > /mnt/etc/fstab")
    for mntdir in mntdirs_n:
        os.system(f"echo '{args[1]} /{mntdir} btrfs subvol=@{mntdir},compress=zstd,noatime 0 0' >> /mnt/etc/fstab")
    if efi:
        os.system(f"echo '{args[3]} /boot/efi vfat umask=0077 0 2' >> /mnt/etc/fstab")
    os.system("mkdir /mnt/etc/astpk.d")
    os.system(f"echo '{args[1]}' > /mnt/etc/astpk.d/astpk-part")
    os.system(f"echo '0' > /mnt/etc/astpk.d/astpk-coverlay")
    os.system(f"echo '0' > /mnt/etc/astpk.d/astpk-cetc")

    os.system(f"echo 'NAME=\"astOS\"' > /mnt/etc/os-release")
    os.system(f"echo 'PRETTY_NAME=\"astOS\"' >> /mnt/etc/os-release")
    os.system(f"echo 'ID=astos' >> /mnt/etc/os-release")
    os.system(f"echo 'BUILD_ID=rolling' >> /mnt/etc/os-release")
    os.system(f"echo 'ANSI_COLOR=\"38;2;23;147;209\"' >> /mnt/etc/os-release")
    os.system(f"echo 'HOME_URL=\"https://github.com/CuBeRJAN/astOS\"' >> /mnt/etc/os-release")
    os.system(f"echo 'LOGO=astos-logo' >> /mnt/etc/os-release")
    os.system(f"mkdir /mnt/usr/share/ast")
    os.system(f"cp -r /mnt/var/lib/pacman/* /mnt/usr/share/ast")
    os.system(f"sed -i s,\"#DBPath      = /var/lib/pacman/\",\"DBPath      = /usr/share/ast/\",g /mnt/etc/pacman.conf")
    os.system(f"echo 'DISTRIB_ID=\"astOS\"' > /mnt/etc/lsb-release")
    os.system(f"echo 'DISTRIB_RELEASE=\"rolling\"' >> /mnt/etc/lsb-release")
    os.system(f"echo 'DISTRIB_DESCRIPTION=astOS' >> /mnt/etc/lsb-release")
    clear()

    while True:
        print("Select a timezone (type list to list):")
        zone = input("> ")
        if zone == "list":
            os.system("ls /usr/share/zoneinfo | less")
        else:
            timezone = str(f"/usr/share/zoneinfo/{zone}")
            break
    os.system(f"arch-chroot /mnt ln -sf {timezone} /etc/localtime")
    os.system("echo 'en_US UTF-8' >> /mnt/etc/locale.gen")
    #os.system("sed -i s/'^#'// /mnt/etc/locale.gen")
    #os.system("sed -i s/'^ '/'#'/ /mnt/etc/locale.gen")
    os.system(f"arch-chroot /mnt locale-gen")
    os.system(f"arch-chroot /mnt hwclock --systohc")
    os.system(f"echo 'LANG=en_US.UTF-8' > /mnt/etc/locale.conf")
    clear()
    print("Enter hostname:")
    hostname = input("> ")
    os.system(f"echo {hostname} > /mnt/etc/hostname")

    os.system("sed -i '0,/@/{s,@,@.overlays/overlay-tmp,}' /mnt/etc/fstab")
    os.system("sed -i '0,/@etc/{s,@etc,@.etc/etc-tmp,}' /mnt/etc/fstab")
#    os.system("sed -i '0,/@var/{s,@var,@.var/var-tmp,}' /mnt/etc/fstab")
    os.system("sed -i '0,/@boot/{s,@boot,@.boot/boot-tmp,}' /mnt/etc/fstab")
    os.system("mkdir -p /mnt/root/images")
    os.system("arch-chroot /mnt btrfs sub set-default /.overlays/overlay-tmp")
    clear()
    os.system("arch-chroot /mnt passwd")
    while True:
        print("did your password set properly (y/n)?")
        reply = input("> ")
        if reply.casefold() == "y":
            break
        else:
            os.system("arch-chroot /mnt passwd")
    os.system("arch-chroot /mnt systemctl enable dhcpcd")
    os.system("mkdir -p /mnt/var/astpk/")
    os.system("echo {\\'name\\': \\'root\\', \\'children\\': [{\\'name\\': \\'0\\'}]} > /mnt/var/astpk/fstree")
    if DesktopInstall:
        os.system("echo {\\'name\\': \\'root\\', \\'children\\': [{\\'name\\': \\'0\\'},{\\'name\\': \\'1\\'}]} > /mnt/var/astpk/fstree")
    os.system(f"arch-chroot /mnt sed -i s,Arch,astOS,g /etc/default/grub")
    os.system(f"arch-chroot /mnt grub-install {args[2]}")
    os.system(f"arch-chroot /mnt grub-mkconfig {args[2]} -o /boot/grub/grub.cfg")
    os.system("sed -i '0,/subvol=@/{s,subvol=@,subvol=@.overlays/overlay-tmp,g}' /mnt/boot/grub/grub.cfg")
    os.system("cp ./astpk.py /mnt/usr/bin/ast")
    os.system("arch-chroot /mnt chmod +x /usr/bin/ast")
    os.system("btrfs sub snap -r /mnt /mnt/.overlays/overlay-0")
    os.system("btrfs sub create /mnt/.etc/etc-tmp")
    os.system("btrfs sub create /mnt/.var/var-tmp")
    os.system("btrfs sub create /mnt/.boot/boot-tmp")
#    os.system("cp --reflink=auto -r /mnt/var/* /mnt/.var/var-tmp")
    os.system("mkdir -p /mnt/.var/var-tmp/lib/pacman")
    os.system("mkdir -p /mnt/.var/var-tmp/lib/systemd")
    os.system("cp --reflink=auto -r /mnt/var/lib/pacman/* /mnt/.var/var-tmp/lib/pacman/")
    os.system("cp --reflink=auto -r /mnt/var/lib/systemd/* /mnt/.var/var-tmp/lib/systemd/")
    os.system("cp --reflink=auto -r /mnt/boot/* /mnt/.boot/boot-tmp")
    os.system("cp --reflink=auto -r /mnt/etc/* /mnt/.etc/etc-tmp")
    os.system("btrfs sub snap -r /mnt/.var/var-tmp /mnt/.var/var-0")
    os.system("btrfs sub snap -r /mnt/.boot/boot-tmp /mnt/.boot/boot-0")
    os.system("btrfs sub snap -r /mnt/.etc/etc-tmp /mnt/.etc/etc-0")
    if DesktopInstall:
        os.system(f"echo '1' > /mnt/etc/astpk.d/astpk-coverlay")
        os.system(f"echo '1' > /mnt/etc/astpk.d/astpk-cetc")
        os.system("pacstrap /mnt flatpak gnome gnome-extra gnome-themes-extra gdm pipewire pipewire-pulse podman sudo")
        clear()
        print("Enter username (all lowercase, max 8 letters)")
        username = input("> ")
        while True:
            print("did your set username properly (y/n)?")
            reply = input("> ")
            if reply.casefold() == "y":
                break
            else:
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
        os.system(f"cp -r /mnt/var/lib/pacman/* /mnt/usr/share/ast")

        os.system("btrfs sub snap -r /mnt /mnt/.overlays/overlay-1")
        os.system("btrfs sub del /mnt/.etc/etc-tmp")
        os.system("btrfs sub del /mnt/.var/var-tmp")
        os.system("btrfs sub del /mnt/.boot/boot-tmp")
        os.system("btrfs sub create /mnt/.etc/etc-tmp")
        os.system("btrfs sub create /mnt/.var/var-tmp")
        os.system("btrfs sub create /mnt/.boot/boot-tmp")
        #    os.system("cp --reflink=auto -r /mnt/var/* /mnt/.var/var-tmp")
        os.system("mkdir -p /mnt/.var/var-tmp/lib/pacman")
        os.system("mkdir -p /mnt/.var/var-tmp/lib/systemd")
        os.system("cp --reflink=auto -r /mnt/var/lib/pacman/* /mnt/.var/var-tmp/lib/pacman/")
        os.system("cp --reflink=auto -r /mnt/var/lib/systemd/* /mnt/.var/var-tmp/lib/systemd/")
        os.system("cp --reflink=auto -r /mnt/boot/* /mnt/.boot/boot-tmp")
        os.system("cp --reflink=auto -r /mnt/etc/* /mnt/.etc/etc-tmp")
        os.system("btrfs sub snap -r /mnt/.var/var-tmp /mnt/.var/var-1")
        os.system("btrfs sub snap -r /mnt/.boot/boot-tmp /mnt/.boot/boot-1")
        os.system("btrfs sub snap -r /mnt/.etc/etc-tmp /mnt/.etc/etc-1")
        os.system("btrfs sub snap /mnt/.overlays/overlay-1 /mnt/.overlays/overlay-tmp")
    else:
        os.system("btrfs sub snap /mnt/.overlays/overlay-0 /mnt/.overlays/overlay-tmp")

#    os.system("umount /mnt/var")
    os.system("umount /mnt/boot")
    if efi:
        os.system("umount /mnt/boot/efi")
#    os.system("mkdir /mnt/.var/var-tmp")
    os.system("mkdir /mnt/.boot/boot-tmp")
#    os.system(f"mount {args[1]} -o subvol=@var,compress=zstd,noatime /mnt/.var/var-tmp")
    os.system(f"mount {args[1]} -o subvol=@boot,compress=zstd,noatime /mnt/.boot/boot-tmp")
#    os.system("cp --reflink=auto -r /mnt/.var/var-tmp/* /mnt/var")
    os.system("cp --reflink=auto -r /mnt/.boot/boot-tmp/* /mnt/boot")
    os.system("umount /mnt/etc")
    os.system("mkdir /mnt/.etc/etc-tmp")
    os.system(f"mount {args[1]} -o subvol=@etc,compress=zstd,noatime /mnt/.etc/etc-tmp")
    os.system("cp --reflink=auto -r /mnt/.etc/etc-tmp/* /mnt/etc")
    if DesktopInstall:
        os.system("cp --reflink=auto -r /mnt/.etc/etc-1/* /mnt/.overlays/overlay-tmp/etc")
        os.system("cp --reflink=auto -r /mnt/.var/var-1/* /mnt/.overlays/overlay-tmp/var")
        os.system("cp --reflink=auto -r /mnt/.boot/boot-1/* /mnt/.overlays/overlay-tmp/boot")
    else:
        os.system("cp --reflink=auto -r /mnt/.etc/etc-0/* /mnt/.overlays/overlay-tmp/etc")
        os.system("cp --reflink=auto -r /mnt/.var/var-0/* /mnt/.overlays/overlay-tmp/var")
        os.system("cp --reflink=auto -r /mnt/.boot/boot-0/* /mnt/.overlays/overlay-tmp/boot")

    os.system("umount -R /mnt")
    os.system(f"mount {args[1]} /mnt")
    os.system("btrfs sub del /mnt/@")
    os.system("umount -R /mnt")
    clear()
    print("Installation complete")
    print("You can reboot now :)")

main(args)
