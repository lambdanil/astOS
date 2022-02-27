#!/usr/bin/python3
import os
import sys
import subprocess

args = list(sys.argv)

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
    mounts = mount.split(" ")
    mount = mounts[len(mounts)-1]
    mount = mount.replace("@.overlays/overlay-","")
    return(mount)

def findnewtmp():
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
        if str(f"overlay-tmp{i}") not in overlays and str(f"etc-tmp{i}") not in overlays and str(f"var-tmp{i}") not in overlays and str(f"boot-tmp{i}") not in overlays:
            return(f"tmp{i}")
            break

def deploy(overlay,old_tmp):
    etc = overlay
    tmp = findnewtmp()
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
    switchtmp(old_tmp, tmp)
    os.system(f"btrfs sub set-default /.overlays/overlay-{tmp}")

def clone(overlay):
    i = findnew()
    os.system(f"btrfs sub snap -r /.overlays/overlay-{overlay} /.overlays/overlay-{i}")
    os.system(f"btrfs sub snap -r /.etc/etc-{overlay} /.etc/etc-{i}")
    os.system(f"btrfs sub snap -r /.var/var-{overlay} /.var/var-{i}")
    os.system(f"btrfs sub snap -r /.boot/boot-{overlay} /.boot/boot-{i}")

def new_overlay():
    i_old = findnew()
    os.system(f"btrfs sub create /.overlays/overlay-{i_old}")
    i = findnew()
    os.system(f"btrfs sub del /.overlays/overlay-{i}")
    os.system(f"btrfs sub snap /.base/base /.overlays/overlay-{i}")
    os.system(f"btrfs sub create /.etc/etc-{i}")
    os.system(f"btrfs sub create /.var/var-{i}")
    os.system(f"btrfs sub create /.boot/boot-{i}")
    os.system(f"cp --reflink=auto -r /.base/base/boot /.boot/boot-{i}")
    os.system(f"cp --reflink=auto -r /.base/base/var /.var/var-{i}")
    os.system(f"cp --reflink=auto -r /.base/base/etc /.etc/etc-{i}")
    os.system(f"btrfs sub snap -r /.overlays/overlay-{i} /.etc/etc-{i_old}")
    os.system(f"btrfs sub snap -r /.etc/etc-{i} /.etc/etc-{i_old}")
    os.system(f"btrfs sub snap -r /.var/var-{i} /.var/var-{i_old}")
    os.system(f"btrfs sub snap -r /.boot/boot-{i} /.boot/boot-{i_old}")
    os.system(f"btrfs sub del /.overlays/overlay-{i}")
    os.system(f"btrfs sub del /.var/var-{i}")
    os.system(f"btrfs sub del /.etc/etc-{i}")
    os.system(f"btrfs sub del /.boot/boot-{i}")

def update_etc(tmp):
    prepare(tmp)
    i = findnew()
    posttrans(i)
    deploy(i,tmp)

def chroot(overlay):
    prepare(overlay)
    os.system(f"arch-chroot /.overlays/overlay-chr")
    posttrans(overlay)

def unchr():
    os.system(f"btrfs sub del /.etc/etc-chr")
    os.system(f"btrfs sub del /.var/var-chr")
    os.system(f"btrfs sub del /.boot/boot-chr")
    os.system(f"btrfs sub del /.overlays/overlay-chr")

def untmp(old_tmp,new_tmp):
    i = 0
    overlays = os.listdir("/.overlays")
    for item in overlays:
        if "tmp" not in item:
            overlays.remove(item)
    print(old_tmp, overlays)
    overlays.remove(old_tmp)
    overlays.remove(new_tmp)
    for tmp in overlays:
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

def prepare(overlay):
    unchr()
    etc = overlay
    os.system(f"btrfs sub snap /.overlays/overlay-{overlay} /.overlays/overlay-chr")
    os.system("rm -rf /.overlays/overlay-chr/etc")
    os.system("rm -rf /.overlays/overlay-chr/var")
    os.system("rm -rf /.overlays/overlay-chr/boot")
    os.system(f"btrfs sub snap /.etc/etc-{overlay} /.overlays/overlay-chr/etc")
    os.system(f"btrfs sub snap /.var/var-{overlay} /.overlays/overlay-chr/var")
    os.system(f"btrfs sub snap /.boot/boot-{overlay} /.overlays/overlay-chr/boot")
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

def cupgrade(overlay,tmp):
    i = findnew()
    prepare(overlay)
    os.system(f"pacman -r /.overlays/overlay-chr -Syyu")
    posttrans(i)
    deploy(i,tmp)

def cinstall(overlay,pkg,tmp):
    i = findnew()
    prepare(overlay)
    os.system(f"pacman -r /.overlays/overlay-chr -S {pkg}")
    posttrans(i)
    deploy(i,tmp)

def switchtmp(tmp, new_tmp):
    part = get_part()
    os.system(f"mkdir /etc/mnt")
    os.system(f"mkdir /etc/mnt/boot")
    os.system(f"mount {part} -o subvol=@boot /etc/mnt/boot")

    new_grub = str("")
    conf = open('/etc/mnt/boot/grub/grub.cfg',"r")
    line = conf.readline()
    flen = str(subprocess.check_output("wc -l /etc/mnt/boot/grub/grub.cfg", shell=True))
    flen_list = flen.split(" ")
    flen = flen_list[0]
    flen = flen.replace("b'","")
    flen = flen.replace('\n',"")
    flen = int(flen)
    i = 0
    while True:
        if "subvol=" in line:
            line = subprocess.check_output(
                f"echo '{line}' | sed 's,[^ ]*[^ ],rootflags=subvol=@.overlays/overlay-{new_tmp}=,5'", shell=True)
        if str(i) in str(flen):
            break
        new_grub += line
        i += 1
    conf.close()
    conf = open("/etc/mnt/boot/grub/grub.cfg", "w", newline="\n")
    conf.write(new_grub)
    conf.close()

#    os.system(f"sed -i 's,subvol=@.overlays/overlay-{tmp},subvol=@.overlays/overlay-{new_tmp},' /etc/mnt/boot/grub/grub.cfg")
    os.system(f"sed -i 's,@.overlays/overlay-{tmp},@.overlays/overlay-{new_tmp},' /.overlays/overlay-{new_tmp}/etc/fstab")
    os.system(f"sed -i 's,@.etc/etc-{tmp},@.etc/etc-{new_tmp},' /.overlays/overlay-{new_tmp}/etc/fstab")
    os.system(f"sed -i 's,@.var/var-{tmp},@.var/var-{new_tmp},' /.overlays/overlay-{new_tmp}/etc/fstab")
    os.system(f"sed -i 's,@.boot/boot-{tmp},@.boot/boot-{new_tmp},' /.overlays/overlay-{new_tmp}/etc/fstab")
    os.system(f"cp --reflink=auto -r /.overlays/overlay-{new_tmp}/boot/* /etc/mnt/boot")
    os.system("umount /etc/mnt/boot")
    untmp(tmp,new_tmp)

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
    tmp = get_tmp()
    for arg in args:
        if arg == "new-overlay" or arg == "new":
            new_overlay()
        elif arg == "chroot" or arg == "cr":
            chroot(args[args.index(arg)+1])
        elif arg == "install" or arg == "i":
            install(args[args.index(arg)+1],args[args.index(arg)+2])
        elif arg == "cinstall" or arg == "ci":
            cinstall(overlay,args[args.index(arg)+1],tmp)
        elif arg == "clone":
            clone(args[args.index(arg)+1])
        elif arg == "list" or arg == "l":
            ls_overlay()
        elif arg == "mk-img" or arg == "img":
            mk_img(args[args.index(arg)+1])
        elif arg == "deploy":
            deploy(args[args.index(arg)+1],tmp)
        elif arg == "upgrade" or arg == "up":
            upgrade(args[args.index(arg)+1])
        elif arg == "cupgrade" or arg == "cup":
            cupgrade(overlay,tmp)
        elif arg == "etc-update" or arg == "etc":
            update_etc(tmp)
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