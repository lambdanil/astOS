#!/usr/bin/python3
import os
import sys
import ast
import subprocess
from anytree.importer import DictImporter
from anytree.exporter import DictExporter
import anytree
import os

args = list(sys.argv)


def import_tree_file(treename):
    treefile = open(treename,"r")
    tree = ast.literal_eval(treefile.readline())
    return(tree)

def print_tree(tree):
    for pre, fill, node in anytree.RenderTree(tree):
        print("%s%s" % (pre, node.name))

def append_base_tree(tree,val):
    add = anytree.Node(val, parent=tree.root)

def add_node_to_parent(tree, id, val):
    par = (anytree.find(tree, filter_=lambda node: (str(node.name)+"x") in (str(id)+"x")))
    add = anytree.Node(val, parent=par)

def add_node_to_level(tree,id, val): # Broken
    par = (anytree.find(tree, filter_=lambda node: (str(node.name) + "x") in (str(id) + "x")))
    spar = str(par).split("/")
    nspar = (spar[len(spar)-2])
    npar = (anytree.find(tree, filter_=lambda node: (str(node.name) + "x") in (str(nspar) + "x")))
    add = anytree.Node(val, parent=npar)

def remove_node(tree, id):
    par = (anytree.find(tree, filter_=lambda node: (str(node.name)+"x") in (str(id)+"x")))
    par.parent = None
    print(par)
def write_tree(tree):
    exporter = DictExporter()
    to_write = exporter.export(tree)
    fsfile = open(fstreepath,"w")
    fsfile.write(str(to_write))

def return_children(tree, id):
    children = []
    par = (anytree.find(tree, filter_=lambda node: (str(node.name)+"x") in (str(id)+"x")))
    for child in anytree.PreOrderIter(par):
        children.append(child.name)
    return (children)

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
#    os.system(f"btrfs sub snap /.var/var-{overlay} /.var/var-{tmp}")
#    os.system(f"btrfs sub snap /var /.var/var-{tmp}")
    os.system(f"btrfs sub create /.var/var-{tmp}")
    os.system(f"cp --reflink=auto -r /.var/var-{etc}/* /.var/var-{tmp}")
    os.system(f"btrfs sub snap /.boot/boot-{overlay} /.boot/boot-{tmp}")
    os.system(f"mkdir /.overlays/overlay-{tmp}/etc")
    os.system(f"rm -rf /.overlays/overlay-{tmp}/var")
#    os.system(f"mkdir /.overlays/overlay-{tmp}/var")
    os.system(f"mkdir /.overlays/overlay-{tmp}/boot")
    os.system(f"cp --reflink=auto -r /.etc/etc-{etc}/* /.overlays/overlay-{tmp}/etc")
    os.system(f"btrfs sub snap /var /.overlays/overlay-{tmp}/var")
    os.system(f"cp --reflink=auto -r /.boot/boot-{etc}/* /.overlays/overlay-{tmp}/boot")
    os.system(f"echo '{overlay}' > /.overlays/overlay-{tmp}/etc/astpk.d/astpk-coverlay")
    os.system(f"echo '{etc}' > /.overlays/overlay-{tmp}/etc/astpk.d/astpk-cetc")
    os.system(f"echo '{overlay}' > /.etc/etc-{tmp}/astpk.d/astpk-coverlay")
    os.system(f"echo '{etc}' > /.etc/etc-{tmp}/astpk.d/astpk-cetc")
    switchtmp()
    os.system(f"cp --reflink=auto -r /.var/var-{etc}/* /.overlays/overlay-{tmp}/var/")
    os.system(f"cp --reflink=auto -r /.var/var-{etc}/lib/pacman/* /var/lib/pacman/")
    os.system(f"cp --reflink=auto -r /.var/var-{etc}/lib/systemd/* /var/lib/systemd/")
    os.system(f"btrfs sub set-default /.overlays/overlay-{tmp}")

def clone(overlay):
    i = findnew()
    os.system(f"btrfs sub snap -r /.overlays/overlay-{overlay} /.overlays/overlay-{i}")
    os.system(f"btrfs sub snap -r /.etc/etc-{overlay} /.etc/etc-{i}")
    os.system(f"btrfs sub snap -r /.var/var-{overlay} /.var/var-{i}")
    os.system(f"btrfs sub snap -r /.boot/boot-{overlay} /.boot/boot-{i}")
    add_node_to_parent(fstree,overlay,i)
    write_tree(fstree)

def extend_branch(overlay):
    i = findnew()
    os.system(f"btrfs sub snap -r /.overlays/overlay-{overlay} /.overlays/overlay-{i}")
    os.system(f"btrfs sub snap -r /.etc/etc-{overlay} /.etc/etc-{i}")
    os.system(f"btrfs sub snap -r /.var/var-{overlay} /.var/var-{i}")
    os.system(f"btrfs sub snap -r /.boot/boot-{overlay} /.boot/boot-{i}")
    add_node_to_parent(fstree,overlay,i)
    write_tree(fstree)

def clone_branch(overlay):
    i = findnew()
    os.system(f"btrfs sub snap -r /.overlays/overlay-{overlay} /.overlays/overlay-{i}")
    os.system(f"btrfs sub snap -r /.etc/etc-{overlay} /.etc/etc-{i}")
    os.system(f"btrfs sub snap -r /.var/var-{overlay} /.var/var-{i}")
    os.system(f"btrfs sub snap -r /.boot/boot-{overlay} /.boot/boot-{i}")
    add_node_to_level(fstree,overlay,i)
    write_tree(fstree)

def sync_tree(treename):
    unchr()
    children = return_children(fstree, treename)
    for child in children:
        os.system(f"btrfs sub snap /.overlays/overlay-{child} /.overlays/overlay-chr")
        os.system(f"btrfs sub snap /.var/var-{child} /.var/var-chr")
        os.system(f"cp --reflink=auto -r /.var/var-{treename}/lib/pacman/local/* /.var/var-chr/lib/pacman/local/")
        os.system(f"cp --reflink=auto -r /.var/var-{treename}/lib/systemd/* /.var/var-chr/lib/systemd/")
        os.system(f"cp --reflink=auto -r /.overlays/overlay-{treename}/* /.overlays/overlay-chr/")
        os.system(f"btrfs sub del /.overlays/overlay-{child}")
        os.system(f"btrfs sub del /.var/var-{child}")
        os.system(f"btrfs sub snap -r /.overlays/overlay-chr /.overlays/overlay-{child}")
        os.system(f"btrfs sub snap -r /.var/var-chr /.var/var-{child}")
        os.system(f"btrfs sub del /.overlays/overlay-chr")
        os.system(f"btrfs sub del /.var/var-chr")

def clone_as_tree(overlay):
    i = findnew()
    os.system(f"btrfs sub snap -r /.overlays/overlay-{overlay} /.overlays/overlay-{i}")
    os.system(f"btrfs sub snap -r /.etc/etc-{overlay} /.etc/etc-{i}")
    os.system(f"btrfs sub snap -r /.var/var-{overlay} /.var/var-{i}")
    os.system(f"btrfs sub snap -r /.boot/boot-{overlay} /.boot/boot-{i}")
    append_base_tree(fstree,i)
    write_tree(fstree)

def new_overlay():
    i = findnew()
    os.system(f"btrfs sub snap -r /.base/base /.overlays/overlay-{i}")
    os.system(f"btrfs sub snap -r /.etc/etc-0 /.etc/etc-{i}")
    os.system(f"btrfs sub snap -r /.var/var-0 /.var/var-{i}")
    os.system(f"btrfs sub snap -r /.boot/boot-0 /.boot/boot-{i}")
#    append_base_tree(fstree, i)
    add_node_to_parent(fstree, fstree.root, i)
    write_tree(fstree)

def show_fstree():
    print_tree(fstree)

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
    os.system(f"btrfs sub del /.overlays/overlay-chr/var")
    os.system(f"btrfs sub del /.overlays/overlay-chr")

def untmp():
    tmp = get_tmp()
    if "tmp0" in tmp:
        tmp = "tmp"
    else:
        tmp = "tmp0"
    os.system(f"btrfs sub del /.overlays/overlay-{tmp}/var")
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
#    os.system(f"btrfs sub del /.boot/boot-{overlay}")
#    os.system(f"btrfs sub del /.etc/etc-{overlay}")
#    os.system(f"btrfs sub del /.var/var-{overlay}")
#    os.system(f"btrfs sub del /.overlays/overlay-{overlay}")
    children = return_children(fstree,overlay)
    for child in children:
        os.system(f"btrfs sub del /.boot/boot-{child}")
        os.system(f"btrfs sub del /.etc/etc-{child}")
        os.system(f"btrfs sub del /.var/var-{child}")
        os.system(f"btrfs sub del /.overlays/overlay-{child}")
    remove_node(fstree,overlay)
    write_tree(fstree)

def prepare_base():
    unchr()
    os.system(f"btrfs sub snap /.base/base /.overlays/overlay-chr")
    os.system(f"rm -rf /.overlays/overlay-chr/var")
    os.system(f"btrfs sub snap /.base/var /.var/var-chr")
    os.system(f"btrfs sub snap /.base/var /.overlays/overlay-chr/var")

def posttrans_base():
    os.system("umount /.overlays/overlay-chr")
    os.system(f"btrfs sub del /.base/base")
    os.system(f"btrfs sub del /.base/var")
    os.system(f"btrfs sub snap -r /.overlays/overlay-chr/var /.base/base")
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
#    os.system(f"btrfs sub snap /.var/var-{overlay} /.var/var-chr")
    os.system(f"btrfs sub snap /var /.var/var-chr")
#    os.system(f"rm -rf /.overlays/overlay-chr/var")
    os.system("rm -rf /.overlays/overlay-chr/var")
    os.system(f"btrfs sub snap /var /.overlays/overlay-chr/var")
    os.system(f"chmod 0755 /.overlays/overlay-chr/var")
    os.system(f"cp -r --reflink=auto /.var/var-{overlay}/* /.overlays/overlay-chr/var/")
    os.system(f"cp -r --reflink=auto /.var/var-{overlay}/* /.var/var-chr/")
    os.system(f"btrfs sub snap /.boot/boot-{overlay} /.boot/boot-chr")
    os.system(f"cp -r --reflink=auto /.etc/etc-chr/* /.overlays/overlay-chr/etc")
#    os.system(f"cp -r --reflink=auto /.var/var-chr/* /.overlays/overlay-chr/var")
    os.system(f"cp -r --reflink=auto /.boot/boot-chr/* /.overlays/overlay-chr/boot")
    os.system("mount --bind /.overlays/overlay-chr /.overlays/overlay-chr")

def posttrans(overlay):
    etc = overlay
    os.system("umount /.overlays/overlay-chr")
    os.system(f"btrfs sub del /.overlays/overlay-{overlay}")
    os.system(f"cp -r --reflink=auto /.overlays/overlay-chr/etc/* /.etc/etc-chr")
    os.system(f"btrfs sub del /.var/var-chr")
    os.system(f"btrfs sub create /.var/var-chr")
    os.system(f"mkdir -p /.var/var-chr/lib/systemd")
    os.system(f"mkdir -p /.var/var-chr/lib/pacman")
    os.system(f"cp -r --reflink=auto /.overlays/overlay-chr/var/lib/systemd/* /.var/var-chr/lib/systemd")
    os.system(f"cp -r --reflink=auto /.overlays/overlay-chr/var/lib/pacman/* /.var/var-chr/lib/pacman")
    os.system(f"cp -r --reflink=auto /.overlays/overlay-chr/boot/* /.boot/boot-chr")
    os.system(f"btrfs sub del /.etc/etc-{etc}")
    os.system(f"btrfs sub del /.var/var-{etc}")
    os.system(f"btrfs sub del /.boot/boot-{etc}")
    os.system(f"btrfs sub snap -r /.etc/etc-chr /.etc/etc-{etc}")
    os.system(f"btrfs sub create /.var/var-{etc}")
    os.system(f"mkdir -p /.var/var-{etc}/lib/systemd")
    os.system(f"mkdir -p /.var/var-{etc}/lib/pacman")
    os.system(f"cp --reflink=auto -r /.var/var-chr/lib/systemd/* /.var/var-{etc}/lib/systemd")
    os.system(f"cp --reflink=auto -r /.var/var-chr/lib/pacman/* /.var/var-{etc}/lib/pacman")
    os.system(f"btrfs sub snap -r /.overlays/overlay-chr /.overlays/overlay-{overlay}")
#    os.system(f"btrfs sub snap -r /.var/var-chr /.var/var-{etc}")
    os.system(f"btrfs sub snap -r /.boot/boot-chr /.boot/boot-{etc}")

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
        os.system("cp --reflink=auto -r /.overlays/overlay-tmp/boot/* /etc/mnt/boot")
        os.system("sed -i 's,subvol=@.overlays/overlay-tmp0,subvol=@.overlays/overlay-tmp,' /etc/mnt/boot/grub/grub.cfg")
        os.system("sed -i 's,@.overlays/overlay-tmp0,@.overlays/overlay-tmp,' /.overlays/overlay-tmp/etc/fstab")
        os.system("sed -i 's,@.etc/etc-tmp0,@.etc/etc-tmp,' /.overlays/overlay-tmp/etc/fstab")
#        os.system("sed -i 's,@.var/var-tmp0,@.var/var-tmp,' /.overlays/overlay-tmp/etc/fstab")
        os.system("sed -i 's,@.boot/boot-tmp0,@.boot/boot-tmp,' /.overlays/overlay-tmp/etc/fstab")
    else:
        os.system("cp --reflink=auto -r /.overlays/overlay-tmp0/boot/* /etc/mnt/boot")
        os.system("sed -i 's,subvol=@.overlays/overlay-tmp,subvol=@.overlays/overlay-tmp0,' /etc/mnt/boot/grub/grub.cfg")
        os.system("sed -i 's,@.overlays/overlay-tmp,@.overlays/overlay-tmp0,' /.overlays/overlay-tmp0/etc/fstab")
        os.system("sed -i 's,@.etc/etc-tmp,@.etc/etc-tmp0,' /.overlays/overlay-tmp0/etc/fstab")
#        os.system("sed -i 's,@.var/var-tmp,@.var/var-tmp0,' /.overlays/overlay-tmp0/etc/fstab")
        os.system("sed -i 's,@.boot/boot-tmp,@.boot/boot-tmp0,' /.overlays/overlay-tmp0/etc/fstab")
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
    new_overlay()
    prepare(i)
    os.system(f"cp -r {imgpath} /.overlays/overlay-chr/init.py")
    os.system("arch-chroot /.overlays/overlay-chr python3 /init.py")
    posttrans(i)


def main(args):
    overlay = get_overlay()
    etc = overlay
    importer = DictImporter()
    exporter = DictExporter()
    global fstree
    global fstreepath
    fstreepath = str("/var/astpk/fstree")
    fstree = importer.import_(import_tree_file("/var/astpk/fstree"))
    for arg in args:
        if arg == "new-overlay" or arg == "new":
            new_overlay()
        elif arg == "chroot" or arg == "cr":
            chroot(args[args.index(arg)+1])
        elif arg == "install" or arg == "i":
            install(args[args.index(arg)+1],args[args.index(arg)+2])
        elif arg == "cinstall" or arg == "ci":
            cinstall(overlay,args[args.index(arg)+1])
        elif arg == "add-branch" or arg == "branch":
            extend_branch(args[args.index(arg)+1])
        elif arg == "clone" or arg == "tree-clone":
            clone_as_tree(args[args.index(arg)+1])
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
        elif arg == "sync" or arg == "tree-sync":
            sync_tree(args[args.index(arg)+1])
        elif arg  == "tree":
            show_fstree()
        elif (arg == args[1]):
            print("Operation not found.")


main(args)