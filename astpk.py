#!/usr/bin/python3
import os
import sys
import subprocess

args = list(sys.argv)
# etc-update, remove, rm-overlay, pac
def get_overlay():
    coverlay = open("/etc/astpk.d/astpk-coverlay","r")
    overlay = coverlay.readline()
    coverlay.close()
    return(overlay)

def get_part():
    cpart = open("/etc/astpk.d/astpk-part","r")
    part = cpart.readline()
    part = part.replace('\n',"")
    cpart.close()
    return(part)

def get_tmp():
    mount = str(subprocess.check_output("btrfs sub get-default /", shell=True))
    if "tmp0" in mount:
        return("tmp0")
    else:
        return("tmp")

def deploy(overlay):
    tmp = get_tmp()
    untmp()
    if "tmp0" in tmp:
        tmp = "tmp"
    else:
        tmp = "tmp0"
    etc = overlay
    os.system(f"btrfs sub snap /.overlays/overlay-{overlay} /.overlays/overlay-{tmp}")
    os.system(f"btrfs sub snap /.etc/etc-{overlay} /.etc/etc-{tmp}")
    os.system(f"btrfs sub snap /.var/var-{overlay} /.var/var-{tmp}")
    os.system(f"btrfs sub snap /.boot/boot-{overlay} /.boot/boot-{tmp}")
    os.system(f"mkdir /.overlays/overlay-{tmp}/etc")
    os.system(f"mkdir /.overlays/overlay-{tmp}/var")
    os.system(f"mkdir /.overlays/overlay-{tmp}/boot")
    os.system(f"cp --reflink=auto -r /.etc/etc-{etc}/* /.overlays/overlay-{tmp}/etc")
    os.system(f"cp --reflink=auto -r /.var/var-{etc}/* /.overlays/overlay-{tmp}/var")
    os.system(f"cp --reflink=auto -r /.boot/boot-{etc}/* /.overlays/overlay-{tmp}/boot")
    os.system(f"echo '{overlay}' > /.overlays/overlay-{tmp}/etc/astpk.d/astpk-coverlay")
    os.system(f"echo '{etc}' > /.overlays/overlay-{tmp}/etc/astpk.d/astpk-cetc")
    os.system(f"echo '{overlay}' > /.etc/etc-{tmp}/etc/astpk.d/astpk-coverlay")
    os.system(f"echo '{etc}' > /.etc/etc-{tmp}/etc/astpk.d/astpk-cetc")
    switchtmp()
    os.system(f"btrfs sub set-default /.overlays/overlay-{tmp}")

def clone(overlay):
    i = findnew()
    os.system(f"btrfs sub snap -r /.overlays/overlay-{overlay} /.overlays/overlay-{i}")
    os.system(f"btrfs sub snap -r /.etc/etc-{overlay} /.etc/etc-{i}")
    os.system(f"btrfs sub snap -r /.var/var-{overlay} /.var/var-{i}")
    os.system(f"btrfs sub snap -r /.boot/boot-{overlay} /.boot/boot-{i}")

def new_overlay():
    i = findnew()
    os.system(f"btrfs sub snap -r /.base/base /.overlays/overlay-{i}")
    os.system(f"btrfs sub snap -r /.etc/etc-0 /.etc/etc-{i}")
    os.system(f"btrfs sub snap -r /.var/var-0 /.var/var-{i}")
    os.system(f"btrfs sub snap -r /.boot/boot-0 /.boot/boot-{i}")

def update_etc():
    tmp = get_tmp()
    prepare(tmp)
    i = findnew()
    posttrans(i)
    deploy(i)

def chroot(overlay):
    prepare(overlay)
    os.system(f"arch-chroot /.overlays/overlay-chr")
    posttrans(overlay)

def unchr():
    os.system(f"btrfs sub del /.etc/etc-chr")
    os.system(f"btrfs sub del /.var/var-chr")
    os.system(f"btrfs sub del /.boot/boot-chr")
    os.system(f"btrfs sub del /.overlays/overlay-chr")

def untmp():
    tmp = get_tmp()
    if "tmp0" in tmp:
        tmp = "tmp"
    else:
        tmp = "tmp0"
    os.system(f"btrfs sub del /.overlays/overlay-{tmp}")
    os.system(f"btrfs sub del /.etc/etc-{tmp}")
    os.system(f"btrfs sub del /.var/var-{tmp}")
    os.system(f"btrfs sub del /.boot/boot-{tmp}")

def install(overlay,pkg):
    prepare(overlay)
    os.system(f"pacman -r /.overlays/overlay-chr -S {pkg}")
    posttrans(overlay)

def remove(overlay,pkg):
    prepare(overlay)
    os.system(f"pacman -r /.overlays/overlay-chr -R {pkg}")
    posttrans(overlay)

def pac(overlay,arg):
    prepare(overlay)
    os.system(f"arch-chroot /.overlays/overlay-chr pacman {arg}")
    posttrans(overlay)

def delete(overlay):
    os.system(f"btrfs sub del /.boot/boot-{overlay}")
    os.system(f"btrfs sub del /.etc/etc-{overlay}")
    os.system(f"btrfs sub del /.var/var-{overlay}")
    os.system(f"btrfs sub del /.overlays/overlay-{overlay}")

def prepare_base():
    unchr()
    os.system(f"btrfs sub snap /.base/base /.overlays/overlay-chr")

def posttrans_base():
    os.system("umount /.overlays/overlay-chr")
    os.system(f"btrfs sub del /.base/base")
    os.system(f"btrfs sub snap -r /.overlays/overlay-chr /.base/base")

def update_base():
    prepare_base()
    os.system(f"pacman -r /.overlays/overlay-chr -Syyu")
    posttrans_base()

def prepare(overlay):
    unchr()
    etc = overlay
    os.system(f"btrfs sub snap /.overlays/overlay-{overlay} /.overlays/overlay-chr")
    os.system(f"btrfs sub snap /.etc/etc-{overlay} /.etc/etc-chr")
    os.system(f"btrfs sub snap /.var/var-{overlay} /.var/var-chr")
    os.system(f"btrfs sub snap /.boot/boot-{overlay} /.boot/boot-chr")
    os.system(f"cp -r --reflink=auto /.etc/etc-chr/* /.overlays/overlay-chr/etc")
    os.system(f"cp -r --reflink=auto /.var/var-chr/* /.overlays/overlay-chr/var")
    os.system(f"cp -r --reflink=auto /.boot/boot-chr/* /.overlays/overlay-chr/boot")
    os.system("mount --bind /.overlays/overlay-chr /.overlays/overlay-chr")

def posttrans(overlay):
    etc = overlay
    os.system("umount /.overlays/overlay-chr")
    os.system(f"btrfs sub del /.overlays/overlay-{overlay}")
    os.system(f"btrfs sub del /.etc/etc-{overlay}")
    os.system(f"btrfs sub del /.var/var-{overlay}")
    os.system(f"btrfs sub del /.boot/boot-{overlay}")
    os.system(f"btrfs sub snap -r /.overlays/overlay-chr /.overlays/overlay-{overlay}")
    os.system(f"btrfs sub snap -r /.overlays/overlay-chr/etc /.etc/etc-{overlay}")
    os.system(f"btrfs sub snap -r /.overlays/overlay-chr/var /.var/var-{overlay}")
    os.system(f"btrfs sub snap -r /.overlays/overlay-chr/boot /.boot/boot-{overlay}")

def upgrade(overlay):
    prepare(overlay)
    os.system(f"pacman -r /.overlays/overlay-chr -Syyu")
    posttrans(overlay)

def cupgrade(overlay):
    i = findnew()
    prepare(overlay)
    os.system(f"pacman -r /.overlays/overlay-chr -Syyu")
    posttrans(i)
    deploy(i)

def cinstall(overlay,pkg):
    i = findnew()
    prepare(overlay)
    os.system(f"pacman -r /.overlays/overlay-chr -S {pkg}")
    posttrans(i)
    deploy(i)

def switchtmp():
    mount = get_tmp()
    part = get_part()
    if "tmp0" in mount:
        tmp = "tmp"
    else:
        tmp = "tmp0"
    os.system(f"mkdir /etc/mnt")
    os.system(f"mkdir /etc/mnt/boot")
    os.system(f"mount {part} -o subvol=@boot /etc/mnt/boot")
    if "tmp0" in mount:
        os.system("sed -i 's,subvol=@.overlays/overlay-tmp0,subvol=@.overlays/overlay-tmp,' /etc/mnt/boot/grub/grub.cfg")
        os.system("sed -i 's,@.overlays/overlay-tmp0,@.overlays/overlay-tmp,' /.overlays/overlay-tmp/etc/fstab")
        os.system("sed -i 's,@.etc/etc-tmp0,@.etc/etc-tmp,' /.overlays/overlay-tmp/etc/fstab")
        os.system("sed -i 's,@.var/var-tmp0,@.var/var-tmp,' /.overlays/overlay-tmp/etc/fstab")
        os.system("sed -i 's,@.boot/boot-tmp0,@.boot/boot-tmp,' /.overlays/overlay-tmp/etc/fstab")
    else:
        os.system("sed -i 's,subvol=@.overlays/overlay-tmp,subvol=@.overlays/overlay-tmp0,' /etc/mnt/boot/grub/grub.cfg")
        os.system("sed -i 's,@.overlays/overlay-tmp,@.overlays/overlay-tmp0,' /.overlays/overlay-tmp0/etc/fstab")
        os.system("sed -i 's,@.etc/etc-tmp,@.etc/etc-tmp0,' /.overlays/overlay-tmp0/etc/fstab")
        os.system("sed -i 's,@.var/var-tmp,@.var/var-tmp0,' /.overlays/overlay-tmp0/etc/fstab")
        os.system("sed -i 's,@.boot/boot-tmp,@.boot/boot-tmp0,' /.overlays/overlay-tmp0/etc/fstab")
        os.system("cp --reflink=auto -r /.overlays/overlay-tmp0/boot/* /etc/mnt/boot")
    os.system("umount /etc/mnt/boot")

def ls_overlay():
    overlays = os.listdir("/.overlays")
    descs = []
    for overlay in overlays:
        if os.path.isfile(f"/root/images/desc-{overlay}"):
            overfile = open(f"/root/images/desc-{overlay}")
            descs.append(str(overfile.readline()))
        else:
            descs.append("")
    for index in range(0, len(overlays)-1,+1):
        print(f"{overlays[index]} - {descs[index]}")


def findnew():
    i = 0
    overlays = os.listdir("/.overlays")
    etcs = os.listdir("/.etc")
    vars = os.listdir("/.var")
    boots = os.listdir("/.boot")
    overlays.append(etcs)
    overlays.append(vars)
    overlays.append(boots)
    while True:
        i += 1
        if str(f"overlay-{i}") not in overlays and str(f"etc-{i}") not in overlays and str(f"var-{i}") not in overlays and str(f"boot-{i}") not in overlays:
            return(i)
            break

def mk_img(imgpath):
    i = findnew()
    new_overlay(i)
    prepare(i)
    os.system(f"cp -r {imgpath} /.overlays/overlay-chr/init.py")
    os.system("arch-chroot /.overlays/overlay-chr python3 /init.py")
    posttrans(i)


def main(args):
    overlay = get_overlay()
    etc = overlay
    for arg in args:
        if arg == "new-overlay" or arg == "new":
            new_overlay()
        elif arg == "chroot" or arg == "cr":
            chroot(args[args.index(arg)+1])
        elif arg == "install" or arg == "i":
            install(args[args.index(arg)+1],args[args.index(arg)+2])
        elif arg == "cinstall" or arg == "ci":
            cinstall(overlay,args[args.index(arg)+1])
        elif arg == "clone":
            clone(args[args.index(arg)+1])
        elif arg == "list" or arg == "l":
            ls_overlay()
        elif arg == "mk-img" or arg == "img":
            mk_img(args[args.index(arg)+1])
        elif arg == "deploy":
            deploy(args[args.index(arg)+1])
        elif arg == "upgrade" or arg == "up":
            upgrade(args[args.index(arg)+1])
        elif arg == "cupgrade" or arg == "cup":
            cupgrade(overlay)
        elif arg == "etc-update" or arg == "etc":
            update_etc()
        elif arg == "current" or arg == "c":
            print(overlay)
        elif arg == "rm-overlay" or arg == "del":
            delete(args[args.index(arg)+1])
        elif arg == "remove" or arg == "r":
            remove(overlay,args[args.index(arg)+1])
        elif arg == "pac" or arg == "p":
            args_2 = args
            args_2.remove(args_2[0])
            args_2.remove(args_2[1])
            pac(str(" ").join(args_2))
        elif arg == "base-update" or arg == "bu":
            update_base()
        elif (arg == args[1]):
            print("Operation not found.")


main(args)