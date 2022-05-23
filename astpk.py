#!/usr/bin/python3
import sys
import ast # Heh funny name coincidence with project name
import subprocess
from anytree.importer import DictImporter
from anytree.exporter import DictExporter
import anytree
import os
import re

args = list(sys.argv)

# TODO ------------
# General code cleanup
# Maybe port for other distros?
# A clean way to completely unistall ast
# -----------------

# Directories
# All images share one /var
# boot is always at @boot
# *-tmp - temporary directories used to boot deployed image
# *-chr - temporary directories used to chroot into image or copy images around
# /.var/var-* == individual var for each image
# /.etc/etc-* == individual etc for each image
# /.snapshots/snapshot-* == images
# /root/images/*-desc == descriptions
# /etc/astpk.d/c* == files that store current snapshot info, should be moved to /var actually, fix that later
# /var/astpk(/fstree) == ast files, stores fstree

# Import filesystem tree file in this function
def import_tree_file(treename):
    treefile = open(treename,"r")
    tree = ast.literal_eval(treefile.readline())
    return(tree)

# Print out tree with descriptions
def print_tree(tree):
    snapshot = get_snapshot()
    for pre, fill, node in anytree.RenderTree(tree):
        if os.path.isfile(f"/root/images/{node.name}-desc"):
            descfile = open(f"/root/images/{node.name}-desc","r")
            desc = descfile.readline()
            descfile.close()
        else:
            desc = ""
        if str(node.name) == "0":
            desc = "base image"
        if snapshot != str(node.name):
            print("%s%s - %s" % (pre, node.name, desc))
        else:
            print("%s%s*- %s" % (pre, node.name, desc))

# Write new description
def write_desc(snapshot, desc):
    os.system(f"touch /root/images/{snapshot}-desc")
    descfile = open(f"/root/images/{snapshot}-desc","w")
    descfile.write(desc)
    descfile.close()

# Add to root tree
def append_base_tree(tree,val):
    add = anytree.Node(val, parent=tree.root)

# Add child to node
def add_node_to_parent(tree, id, val):
    par = (anytree.find(tree, filter_=lambda node: ("x"+str(node.name)+"x") in ("x"+str(id)+"x"))) 
    add = anytree.Node(val, parent=par)

# Clone within node
def add_node_to_level(tree,id, val): 
    npar = get_parent(tree, id)
    par = (anytree.find(tree, filter_=lambda node: ("x"+str(node.name)+"x") in ("x"+str(npar)+"x")))
    add = anytree.Node(val, parent=par)

# Remove node from tree
def remove_node(tree, id):
    par = (anytree.find(tree, filter_=lambda node: ("x"+str(node.name)+"x") in ("x"+str(id)+"x")))
    par.parent = None

# Save tree to file
def write_tree(tree):
    exporter = DictExporter()
    to_write = exporter.export(tree)
    fsfile = open(fstreepath,"w")
    fsfile.write(str(to_write))

# Get parent
def get_parent(tree, id):
    par = (anytree.find(tree, filter_=lambda node: ("x"+str(node.name)+"x") in ("x"+str(id)+"x")))
    return(par.parent.name)

# Return all children for node
def return_children(tree, id):
    children = []
    par = (anytree.find(tree, filter_=lambda node: ("x"+str(node.name)+"x") in ("x"+str(id)+"x")))
    for child in anytree.PreOrderIter(par):
        children.append(child.name)
    if id in children:
        children.remove(id)
    return (children)

# Return order to recurse tree
def recurstree(tree, cid):
    order = []
    for child in (return_children(tree,cid)):
        par = get_parent(tree, child)
        if child != cid:
            order.append(par)
            order.append(child)
    return (order)

# Get current snapshot
def get_snapshot():
    csnapshot = open("/etc/astpk.d/astpk-csnapshot","r")
    snapshot = csnapshot.readline()
    csnapshot.close()
    snapshot = snapshot.replace('\n',"")
    return(snapshot)

# Get drive partition
def get_part():
    cpart = open("/etc/astpk.d/astpk-part","r")
    part = cpart.readline()
    part = part.replace('\n',"")
    cpart.close()
    return(part)

# Get tmp partition state
def get_tmp():
    mount = str(subprocess.check_output("mount | grep 'on / type'", shell=True))
    if "tmp0" in mount:
        return("tmp0")
    else:
        return("tmp")

# Deploy image
def deploy(snapshot):
    if not (os.path.exists(f"/.snapshots/snapshot-{snapshot}")):
        print("cannot deploy, snapshot doesn't exist")
    else:
        update_boot(snapshot)
        tmp = get_tmp()
        os.system(f"btrfs sub set-default /.snapshots/snapshot-{tmp} >/dev/null 2>&1") # Set default volume
        untmp()
        if "tmp0" in tmp:
            tmp = "tmp"
        else:
            tmp = "tmp0"
        etc = snapshot
        os.system(f"btrfs sub snap /.snapshots/snapshot-{snapshot} /.snapshots/snapshot-{tmp} >/dev/null 2>&1")
        os.system(f"btrfs sub snap /.etc/etc-{snapshot} /.etc/etc-{tmp} >/dev/null 2>&1")
        os.system(f"btrfs sub create /.var/var-{tmp} >/dev/null 2>&1")
        os.system(f"cp --reflink=auto -r /.var/var-{etc}/* /.var/var-{tmp} >/dev/null 2>&1")
        os.system(f"btrfs sub snap /.boot/boot-{snapshot} /.boot/boot-{tmp} >/dev/null 2>&1")
        os.system(f"mkdir /.snapshots/snapshot-{tmp}/etc >/dev/null 2>&1")
        os.system(f"rm -rf /.snapshots/snapshot-{tmp}/var >/dev/null 2>&1")
        os.system(f"mkdir /.snapshots/snapshot-{tmp}/boot >/dev/null 2>&1")
        os.system(f"cp --reflink=auto -r /.etc/etc-{etc}/* /.snapshots/snapshot-{tmp}/etc >/dev/null 2>&1")
        os.system(f"btrfs sub snap /var /.snapshots/snapshot-{tmp}/var >/dev/null 2>&1")
        os.system(f"cp --reflink=auto -r /.boot/boot-{etc}/* /.snapshots/snapshot-{tmp}/boot >/dev/null 2>&1")
        os.system(f"echo '{snapshot}' > /.snapshots/snapshot-{tmp}/etc/astpk.d/astpk-csnapshot")
        os.system(f"echo '{etc}' > /.snapshots/snapshot-{tmp}/etc/astpk.d/astpk-cetc")
        os.system(f"echo '{snapshot}' > /.etc/etc-{tmp}/astpk.d/astpk-csnapshot")
        os.system(f"echo '{etc}' > /.etc/etc-{tmp}/astpk.d/astpk-cetc")
        switchtmp()
        #os.system(f"rm -rf /var/lib/pacman/* >/dev/null 2>&1") # Clean pacman and systemd directories before copy
        os.system(f"rm -rf /var/lib/systemd/* >/dev/null 2>&1")
        os.system(f"rm -rf /.snapshots/snapshot-{tmp}/var/lib/systemd/* >/dev/null 2>&1")
        #os.system(f"rm -rf /.snapshots/snapshot-{tmp}/var/lib/pacman/* >/dev/null 2>&1")
        os.system(f"cp --reflink=auto -r /.var/var-{etc}/* /.snapshots/snapshot-{tmp}/var/ >/dev/null 2>&1")
        #os.system(f"cp --reflink=auto -r /.var/var-{etc}/lib/pacman/* /var/lib/pacman/ >/dev/null 2>&1") # Copy pacman and systemd directories
        os.system(f"cp --reflink=auto -r /.var/var-{etc}/lib/systemd/* /var/lib/systemd/ >/dev/null 2>&1")
        #os.system(f"cp --reflink=auto -r /.var/var-{etc}/lib/pacman/* /.snapshots/snapshot-{tmp}/var/lib/pacman/")
        os.system(f"cp --reflink=auto -r /.var/var-{etc}/lib/systemd/* /.snapshots/snapshot-{tmp}/var/lib/systemd/ >/dev/null 2>&1")
        os.system(f"btrfs sub set-default /.snapshots/snapshot-{tmp}") # Set default volume
        #os.system(f"chattr -RV +i /.snapshots/snapshot-{tmp}/usr > /dev/null 2>&1")
        print(f"{snapshot} was deployed to /")

# Add node to branch
def extend_branch(snapshot):
    if not (os.path.exists(f"/.snapshots/snapshot-{snapshot}")):
        print("cannot branch, snapshot doesn't exist")
    else:
        i = findnew()
        os.system(f"btrfs sub snap -r /.snapshots/snapshot-{snapshot} /.snapshots/snapshot-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.etc/etc-{snapshot} /.etc/etc-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.var/var-{snapshot} /.var/var-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.boot/boot-{snapshot} /.boot/boot-{i} >/dev/null 2>&1")
        add_node_to_parent(fstree,snapshot,i)
        write_tree(fstree)
        print(f"branch {i} added to {snapshot}")

# Clone branch under same parent,
def clone_branch(snapshot):
    if not (os.path.exists(f"/.snapshots/snapshot-{snapshot}")):
        print("cannot clone, snapshot doesn't exist")
    else:
        i = findnew()
        os.system(f"btrfs sub snap -r /.snapshots/snapshot-{snapshot} /.snapshots/snapshot-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.etc/etc-{snapshot} /.etc/etc-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.var/var-{snapshot} /.var/var-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.boot/boot-{snapshot} /.boot/boot-{i} >/dev/null 2>&1")
        add_node_to_level(fstree,snapshot,i)
        write_tree(fstree)
        desc = str(f"clone of {snapshot}")
        write_desc(i, desc)
        print(f"branch {i} added to parent of {snapshot}")

# Clone under specified parent
def clone_under(snapshot, branch):
    if not (os.path.exists(f"/.snapshots/snapshot-{snapshot}")) or (not(os.path.exists(f"/.snapshots/snapshot-{branch}"))):
        print("cannot clone, snapshot doesn't exist")
    else:
        i = findnew()
        os.system(f"btrfs sub snap -r /.snapshots/snapshot-{branch} /.snapshots/snapshot-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.etc/etc-{branch} /.etc/etc-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.var/var-{branch} /.var/var-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.boot/boot-{branch} /.boot/boot-{i} >/dev/null 2>&1")
        add_node_to_parent(fstree,snapshot,i)
        write_tree(fstree)
        desc = str(f"clone of {snapshot}")
        write_desc(i, desc)
        print(f"branch {i} added to {snapshot}")

# Lock ast
def ast_lock():
    os.system("touch /var/astpk/lock-disable")

# Unlock
def ast_unlock():
    os.system("rm -rf /var/astpk/lock")

def get_lock():
    if os.path.exists("/var/astpk/lock"):
        return(True)
    else:
        return(False)

# Recursively remove package in tree
def remove_from_tree(tree,treename,pkg):
    if not (os.path.exists(f"/.snapshots/snapshot-{treename}")):
        print("cannot update, tree doesn't exist")
    else:
        remove(treename, pkg)
        order = recurstree(tree, treename)
        if len(order) > 2:
            order.remove(order[0])
            order.remove(order[0])
        while True:
            if len(order) < 2:
                break
            arg = order[0]
            sarg = order[1]
            print(arg,sarg)
            order.remove(order[0])
            order.remove(order[0])
            remove(sarg,pkg)
        print(f"tree {treename} was updated")

# Recursively run an update in tree
def update_tree(tree,treename):
    if not (os.path.exists(f"/.snapshots/snapshot-{treename}")):
        print("cannot update, tree doesn't exist")
    else:
        upgrade(treename)
        order = recurstree(tree, treename)
        if len(order) > 2:
            order.remove(order[0])
            order.remove(order[0])
        while True:
            if len(order) < 2:
                break
            arg = order[0]
            sarg = order[1]
            print(arg,sarg)
            order.remove(order[0])
            order.remove(order[0])
            autoupgrade(sarg)
        print(f"tree {treename} was updated")

# Recursively run an update in tree
def run_tree(tree,treename,cmd):
    if not (os.path.exists(f"/.snapshots/snapshot-{treename}")):
        print("cannot update, tree doesn't exist")
    else:
        prepare(treename)
        os.system(f"chroot /.snapshots/snapshot-chr{treename} {cmd}")
        posttrans(treename)
        order = recurstree(tree, treename)
        if len(order) > 2:
            order.remove(order[0])
            order.remove(order[0])
        while True:
            if len(order) < 2:
                break
            arg = order[0]
            sarg = order[1]
            print(arg,sarg)
            order.remove(order[0])
            order.remove(order[0])
            prepare(sarg)
            os.system(f"chroot /.snapshots/snapshot-chr{sarg} {cmd}")
            posttrans(sarg)
        print(f"tree {treename} was updated")

# Sync tree and all it's snapshots
def sync_tree(tree,treename,forceOffline):
    if not (os.path.exists(f"/.snapshots/snapshot-{treename}")):
        print("cannot sync, tree doesn't exist")
    else:
        if not forceOffline: # Syncing tree automatically updates it, unless 'force-sync' is used
            update_tree(tree, treename)
        order = recurstree(tree, treename)
        if len(order) > 2:
            order.remove(order[0])
            order.remove(order[0])
        while True:
            if len(order) < 2:
                break
            arg = order[0]
            sarg = order[1]
            print(arg,sarg)
            order.remove(order[0])
            order.remove(order[0])
            prepare(sarg)
            #os.system(f"cp --reflink=auto -r /.var/var-{arg}/lib/pacman/local/* /.var/var-chr{sarg}/lib/pacman/local/ >/dev/null 2>&1")
            os.system(f"cp --reflink=auto -r /.var/var-{arg}/lib/systemd/* /.var/var-chr{sarg}/lib/systemd/ >/dev/null 2>&1")
            #os.system(f"cp --reflink=auto -r /.var/var-{arg}/lib/pacman/local/* /.snapshots/snapshot-chr{sarg}/var/lib/pacman/local/ >/dev/null 2>&1")
            os.system(f"cp --reflink=auto -r /.var/var-{arg}/lib/systemd/* /.snapshots/snapshot-chr{sarg}/var/lib/systemd/ >/dev/null 2>&1")
            os.system(f"cp --reflink=auto -n -r /.snapshots/snapshot-{arg}/* /.snapshots/snapshot-chr{sarg}/ >/dev/null 2>&1")
            posttrans(sarg)
        print(f"tree {treename} was synced")

# Clone tree
def clone_as_tree(snapshot):
    if not (os.path.exists(f"/.snapshots/snapshot-{snapshot}")):
        print("cannot clone, snapshot doesn't exist")
    else:
        i = findnew()
        os.system(f"btrfs sub snap -r /.snapshots/snapshot-{snapshot} /.snapshots/snapshot-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.etc/etc-{snapshot} /.etc/etc-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.var/var-{snapshot} /.var/var-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.boot/boot-{snapshot} /.boot/boot-{i} >/dev/null 2>&1")
        append_base_tree(fstree,i)
        write_tree(fstree)
        desc = str(f"clone of {snapshot}")
        write_desc(i, desc)
        print(f"tree {i} cloned from {snapshot}")

# Creates new tree from base file
def new_snapshot():
    i = findnew()
    os.system(f"btrfs sub snap -r /.snapshots/snapshot-0 /.snapshots/snapshot-{i} >/dev/null 2>&1")
    os.system(f"btrfs sub snap -r /.etc/etc-0 /.etc/etc-{i} >/dev/null 2>&1")
    os.system(f"btrfs sub snap -r /.boot/boot-0 /.boot/boot-{i} >/dev/null 2>&1")
    os.system(f"btrfs sub snap -r /.var/var-0 /.var/var-{i} >/dev/null 2>&1")
#    append_base_tree(fstree, i)
    append_base_tree(fstree,i)
    write_tree(fstree)
    print(f"new tree {i} created")

# Calls print function
def show_fstree():
    print_tree(fstree)

# Saves changes made to /etc to image
def update_etc():
    tmp = get_tmp()
    snapshot = get_snapshot()
    os.system(f"btrfs sub del /.etc/etc-{snapshot} >/dev/null 2>&1")
    os.system(f"btrfs sub snap -r /.etc/etc-{tmp} /.etc/etc-{snapshot} >/dev/null 2>&1")

# Update boot
def update_boot(snapshot):
    if not (os.path.exists(f"/.snapshots/snapshot-{snapshot}")):
        print("cannot update boot, snapshot doesn't exist")
    else:
        tmp = get_tmp()
        part = get_part()
        prepare(snapshot)
        os.system(f"chroot /.snapshots/snapshot-chr{snapshot} grub-mkconfig {part} -o /boot/grub/grub.cfg")
        os.system(f"chroot /.snapshots/snapshot-chr{snapshot} sed -i s,snapshot-chr{snapshot},snapshot-{tmp},g /boot/grub/grub.cfg")
        os.system(f"chroot /.snapshots/snapshot-chr{snapshot} sed -i '0,/astOS\ Linux/s//astOS\ Linux\ snapshot\ {snapshot}/' /boot/grub/grub.cfg")
        posttrans(snapshot)

# Chroot into snapshot
def chroot(snapshot):
    if not (os.path.exists(f"/.snapshots/snapshot-{snapshot}")):
        print("cannot chroot, snapshot doesn't exist")
    elif snapshot == "0":
        print("changing base image is not allowed")
    else:
        prepare(snapshot)
        os.system(f"chroot /.snapshots/snapshot-chr{snapshot}")
        posttrans(snapshot)

# Run command in snapshot
def chrrun(snapshot,cmd):
    if not (os.path.exists(f"/.snapshots/snapshot-{snapshot}")):
        print("cannot chroot, snapshot doesn't exist")
    elif snapshot == "0":
        print("changing base image is not allowed")
    else:
        prepare(snapshot)
        os.system(f"chroot /.snapshots/snapshot-chr{snapshot} {cmd}")
        posttrans(snapshot)

# Clean chroot mount dirs
def unchr(snapshot):
    os.system(f"btrfs sub del /.etc/etc-chr{snapshot} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.var/var-chr{snapshot} >/dev/null 2>&1")
    os.system(f"rm -rf /.var/var-chr{snapshot} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.boot/boot-chr{snapshot} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.snapshots/snapshot-chr{snapshot}/* >/dev/null 2>&1")
    os.system(f"btrfs sub del /.snapshots/snapshot-chr{snapshot} >/dev/null 2>&1")

# Clean tmp dirs
def untmp():
    tmp = get_tmp()
    if "tmp0" in tmp:
        tmp = "tmp"
    else:
        tmp = "tmp0"
    os.system(f"btrfs sub del /.snapshots/snapshot-{tmp}/* >/dev/null 2>&1")
    os.system(f"btrfs sub del /.snapshots/snapshot-{tmp} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.etc/etc-{tmp} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.var/var-{tmp} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.boot/boot-{tmp} >/dev/null 2>&1")

# Install live
def live_install(pkg):
    tmp = get_tmp()
    part = get_part()
    #os.system(f"chattr -RV -i /.snapshots/snapshot-{tmp}/usr > /dev/null 2>&1")
    os.system(f"mount --bind /.snapshots/snapshot-{tmp} /.snapshots/snapshot-{tmp} > /dev/null 2>&1")
    os.system(f"mount --bind /home /.snapshots/snapshot-{tmp}/home > /dev/null 2>&1")
    os.system(f"mount --bind /var /.snapshots/snapshot-{tmp}/var > /dev/null 2>&1")
    os.system(f"mount --bind /etc /.snapshots/snapshot-{tmp}/etc > /dev/null 2>&1")
    os.system(f"mount --bind /tmp /.snapshots/snapshot-{tmp}/tmp > /dev/null 2>&1")
    os.system(f"arch-chroot /.snapshots/snapshot-{tmp} pacman -S  --overwrite \\* --noconfirm {pkg}")
    os.system(f"umount /.snapshots/snapshot-{tmp}/* > /dev/null 2>&1")
    os.system(f"umount /.snapshots/snapshot-{tmp} > /dev/null 2>&1")
    #os.system(f"chattr -RV +i /.snapshots/snapshot-{tmp}/usr > /dev/null 2>&1")

# Live unlocked shell
def live_unlock():
    tmp = get_tmp()
    part = get_part()
    #os.system(f"chattr -RV -i /.snapshots/snapshot-{tmp}/usr > /dev/null 2>&1")
    os.system(f"mount --bind /.snapshots/snapshot-{tmp} /.snapshots/snapshot-{tmp} > /dev/null 2>&1")
    os.system(f"mount --bind /home /.snapshots/snapshot-{tmp}/home > /dev/null 2>&1")
    os.system(f"mount --bind /var /.snapshots/snapshot-{tmp}/var > /dev/null 2>&1")
    os.system(f"mount --bind /etc /.snapshots/snapshot-{tmp}/etc > /dev/null 2>&1")
    os.system(f"mount --bind /tmp /.snapshots/snapshot-{tmp}/tmp > /dev/null 2>&1")
    os.system(f"arch-chroot /.snapshots/snapshot-{tmp}")
    os.system(f"umount /.snapshots/snapshot-{tmp}/* > /dev/null 2>&1")
    os.system(f"umount /.snapshots/snapshot-{tmp} > /dev/null 2>&1")
    #os.system(f"chattr -RV +i /.snapshots/snapshot-{tmp}/usr > /dev/null 2>&1")

# Install packages
def install(snapshot,pkg):
    if not (os.path.exists(f"/.snapshots/snapshot-{snapshot}")):
        print("cannot install, snapshot doesn't exist")
    elif snapshot == "0":
        print("changing base image is not allowed")
    else:
        prepare(snapshot)
        excode = str(os.system(f"chroot /.snapshots/snapshot-chr{snapshot} pacman -S {pkg} --overwrite '/var/*'"))
        if int(excode) == 0:
            posttrans(snapshot)
            print(f"snapshot {snapshot} updated successfully")
        else:
            print("install failed, changes were discarded")

# Remove packages
def remove(snapshot,pkg):
    if not (os.path.exists(f"/.snapshots/snapshot-{snapshot}")):
        print("cannot remove, snapshot doesn't exist")
    elif snapshot == "0":
        print("changing base image is not allowed")
    else:
        prepare(snapshot)
        excode = str(os.system(f"chroot /.snapshots/snapshot-chr{snapshot} pacman --noconfirm -Rns {pkg}"))
        if int(excode) == 0:
            posttrans(snapshot)
            print(f"snapshot {snapshot} updated successfully")
        else:
            print("remove failed, changes were discarded")

# Delete tree or branch
def delete(snapshot):
    print(f"Are you sure you want to delete snapshot {snapshot}? (y/N)")
    choice = input("> ")
    run = True
    if choice.casefold() != "y":
        print("Aborted")
        run = False
    if not (os.path.exists(f"/.snapshots/snapshot-{snapshot}")):
        print("cannot delete, tree doesn't exist")
    elif snapshot == "0":
        print("changing base image is not allowed")
    elif run == True:
        children = return_children(fstree,snapshot)
        os.system(f"btrfs sub del /.boot/boot-{snapshot} >/dev/null 2>&1")
        os.system(f"btrfs sub del /.etc/etc-{snapshot} >/dev/null 2>&1")
        os.system(f"btrfs sub del /.var/var-{snapshot} >/dev/null 2>&1")
        os.system(f"btrfs sub del /.snapshots/snapshot-{snapshot} >/dev/null 2>&1")
        for child in children: # This deletes the node itself along with it's children
            os.system(f"btrfs sub del /.boot/boot-{child} >/dev/null 2>&1")
            os.system(f"btrfs sub del /.etc/etc-{child} >/dev/null 2>&1")
            os.system(f"btrfs sub del /.var/var-{child} >/dev/null 2>&1")
            os.system(f"btrfs sub del /.snapshots/snapshot-{child} >/dev/null 2>&1")
        remove_node(fstree,snapshot) # Remove node from tree or root
        write_tree(fstree)
        print(f"snapshot {snapshot} removed")

# Update base
def update_base():
    prepare("0")
    os.system(f"chroot /.snapshots/snapshot-chr0 pacman -Syyu")
    posttrans("0")

def get_efi():
    if os.path.exists("/sys/firmware/efi"):
        efi = True
    else:
        efi = False
    return(efi)

# Prepare snapshot to chroot dir to install or chroot into
def prepare(snapshot):
    unchr(snapshot)
    part = get_part()
    etc = snapshot
    os.system(f"btrfs sub snap /.snapshots/snapshot-{snapshot} /.snapshots/snapshot-chr{snapshot} >/dev/null 2>&1")
    os.system(f"btrfs sub snap /.etc/etc-{snapshot} /.etc/etc-chr{snapshot} >/dev/null 2>&1")
    os.system(f"mkdir -p /.var/var-chr{snapshot} >/dev/null 2>&1")
    os.system(f"mount --bind /.snapshots/snapshot-chr{snapshot} /.snapshots/snapshot-chr{snapshot} >/dev/null 2>&1") # Pacman gets weird when chroot directory is not a mountpoint, so this mount is necessary
    os.system(f"mount --bind /var /.snapshots/snapshot-chr{snapshot}/var >/dev/null 2>&1")
    os.system(f"mount --rbind /dev /.snapshots/snapshot-chr{snapshot}/dev >/dev/null 2>&1")
    os.system(f"mount --rbind /sys /.snapshots/snapshot-chr{snapshot}/sys >/dev/null 2>&1")
    os.system(f"mount --rbind /tmp /.snapshots/snapshot-chr{snapshot}/tmp >/dev/null 2>&1")
    os.system(f"mount --rbind /proc /.snapshots/snapshot-chr{snapshot}/proc >/dev/null 2>&1")
    #os.system(f"chmod 0755 /.snapshots/snapshot-chr/var >/dev/null 2>&1") # For some reason the permission needs to be set here
    os.system(f"btrfs sub snap /.boot/boot-{snapshot} /.boot/boot-chr{snapshot} >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.etc/etc-chr{snapshot}/* /.snapshots/snapshot-chr{snapshot}/etc >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.boot/boot-chr{snapshot}/* /.snapshots/snapshot-chr{snapshot}/boot >/dev/null 2>&1")
    #os.system(f"rm -rf /.snapshots/snapshot-chr{snapshot}/var/lib/pacman/* >/dev/null 2>&1")
    os.system(f"rm -rf /.snapshots/snapshot-chr{snapshot}/var/lib/systemd/* >/dev/null 2>&1")
    #os.system(f"cp -r --reflink=auto /.var/var-{snapshot}/lib/pacman/* /.snapshots/snapshot-chr{snapshot}/var/lib/pacman/ >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.var/var-{snapshot}/lib/systemd/* /.snapshots/snapshot-chr{snapshot}/var/lib/systemd/ >/dev/null 2>&1")
    os.system(f"mount --bind /home /.snapshots/snapshot-chr{snapshot}/home >/dev/null 2>&1")
    os.system(f"mount --rbind /run /.snapshots/snapshot-chr{snapshot}/run >/dev/null 2>&1")
    os.system(f"cp /etc/machine-id /.snapshots/snapshot-chr{snapshot}/etc/machine-id")
    os.system(f"mount --bind /etc/resolv.conf /.snapshots/snapshot-chr{snapshot}/etc/resolv.conf >/dev/null 2>&1")

# Post transaction function, copy from chroot dirs back to read only image dir
def posttrans(snapshot):
    etc = snapshot
    tmp = get_tmp()
    os.system(f"umount /.snapshots/snapshot-chr{snapshot} >/dev/null 2>&1")
    os.system(f"umount /.snapshots/snapshot-chr{snapshot}/etc/resolv.conf >/dev/null 2>&1")
    os.system(f"umount /.snapshots/snapshot-chr{snapshot}/home >/dev/null 2>&1")
    os.system(f"umount /.snapshots/snapshot-chr{snapshot}/run >/dev/null 2>&1")
    os.system(f"umount /.snapshots/snapshot-chr{snapshot}/dev >/dev/null 2>&1")
    os.system(f"umount /.snapshots/snapshot-chr{snapshot}/sys >/dev/null 2>&1")
    os.system(f"umount /.snapshots/snapshot-chr{snapshot}/proc >/dev/null 2>&1")
    os.system(f"btrfs sub del /.snapshots/snapshot-{snapshot} >/dev/null 2>&1")
    os.system(f"rm -rf /.etc/etc-chr{snapshot}/* >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.snapshots/snapshot-chr{snapshot}/etc/* /.etc/etc-chr{snapshot} >/dev/null 2>&1")
    os.system(f"rm -rf /.var/var-chr{snapshot}/* >/dev/null 2>&1")
    os.system(f"mkdir -p /.var/var-chr{snapshot}/lib/systemd >/dev/null 2>&1")
    #os.system(f"mkdir -p /.var/var-chr{snapshot}/lib/pacman >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.snapshots/snapshot-chr{snapshot}/var/lib/systemd/* /.var/var-chr{snapshot}/lib/systemd >/dev/null 2>&1")
    #os.system(f"cp -r --reflink=auto /.snapshots/snapshot-chr{snapshot}/var/lib/pacman/* /.var/var-chr{snapshot}/lib/pacman >/dev/null 2>&1")
    os.system(f"cp -r -n --reflink=auto /.snapshots/snapshot-chr{snapshot}/var/cache/pacman/pkg/* /var/cache/pacman/pkg/ >/dev/null 2>&1")
    os.system(f"rm -rf /.boot/boot-chr{snapshot}/* >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.snapshots/snapshot-chr{snapshot}/boot/* /.boot/boot-chr{snapshot} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.etc/etc-{etc} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.var/var-{etc} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.boot/boot-{etc} >/dev/null 2>&1")
    os.system(f"btrfs sub snap -r /.etc/etc-chr{snapshot} /.etc/etc-{etc} >/dev/null 2>&1")
    os.system(f"btrfs sub create /.var/var-{etc} >/dev/null 2>&1")
    os.system(f"mkdir -p /.var/var-{etc}/lib/systemd >/dev/null 2>&1")
    #os.system(f"mkdir -p /.var/var-{etc}/lib/pacman >/dev/null 2>&1")
    os.system(f"cp --reflink=auto -r /.var/var-chr{snapshot}/lib/systemd/* /.var/var-{etc}/lib/systemd >/dev/null 2>&1")
    #os.system(f"cp --reflink=auto -r /.var/var-chr{snapshot}/lib/pacman/* /.var/var-{etc}/lib/pacman >/dev/null 2>&1")
    #os.system(f"rm -rf /var/lib/pacman/* >/dev/null 2>&1")
    #os.system(f"cp --reflink=auto -r /.snapshots/snapshot-{tmp}/var/lib/pacman/* /var/lib/pacman >/dev/null 2>&1")
    os.system(f"rm -rf /var/lib/systemd/* >/dev/null 2>&1")
    os.system(f"cp --reflink=auto -r /.snapshots/snapshot-{tmp}/var/lib/systemd/* /var/lib/systemd >/dev/null 2>&1")
    #os.system(f"cp --reflink=auto -r -n /.snapshots/snapshot-chr{snapshot}/var/lib/* /var/lib/ >/dev/null 2>&1")
    #os.system(f"cp --reflink=auto -r -n /.snapshots/snapshot-chr{snapshot}/var/games/* /var/games/ >/dev/null 2>&1")
    os.system(f"btrfs sub snap -r /.snapshots/snapshot-chr{snapshot} /.snapshots/snapshot-{snapshot} >/dev/null 2>&1")
#    os.system(f"btrfs sub snap -r /.var/var-chr{snapshot} /.var/var-{etc} >/dev/null 2>&1")
    os.system(f"btrfs sub snap -r /.boot/boot-chr{snapshot} /.boot/boot-{etc} >/dev/null 2>&1")
    unchr(snapshot)

# Upgrade snapshot
def upgrade(snapshot):
    if not (os.path.exists(f"/.snapshots/snapshot-{snapshot}")):
        print("cannot upgrade, snapshot doesn't exist")
    elif snapshot == "0":
        print("changing base image is not allowed")
    else:
        prepare(snapshot)
        excode = str(os.system(f"chroot /.snapshots/snapshot-chr{snapshot} pacman -Syyu")) # Default upgrade behaviour is now "safe" update, meaning failed updates get fully discarded
        if int(excode) == 0:
            posttrans(snapshot)
            print(f"snapshot {snapshot} updated successfully")
        else:
            print("update failed, changes were discarded")

# Noninteractive update
def autoupgrade(snapshot):
    prepare(snapshot)
    excode = str(os.system(f"chroot /.snapshots/snapshot-chr{snapshot} pacman --noconfirm -Syyu"))
    if int(excode) == 0:
        posttrans(snapshot)
        os.system("echo 0 > /var/astpk/upstate")
        os.system("echo $(date) >> /var/astpk/upstate")
    else:
        os.system("echo 1 > /var/astpk/upstate")
        os.system("echo $(date) >> /var/astpk/upstate")

# Check if last update was successful
def check_update():
    upstate = open("/var/astpk/upstate", "r")
    line = upstate.readline()
    date = upstate.readline()
    if "1" in line:
        print(f"Last update on {date} failed")
    if "0" in line:
        print(f"Last update on {date} completed succesully")
    upstate.close()

def chroot_check():
    chroot = True # When inside chroot
    with open("/proc/mounts", "r") as mounts:
        for line in mounts:
            if str("/.snapshots btrfs") in str(line):
                chroot = False
    return(chroot)

# Rollback last booted deployment
def rollback():
    tmp = get_tmp()
    i = findnew()
    clone_as_tree(tmp)
    write_desc(i, "rollback")
    deploy(i)

# Switch between /tmp deployments
def switchtmp():
    mount = get_tmp()
    part = get_part()
    # This part is useless? Dumb stuff
    os.system(f"mkdir -p /etc/mnt/boot >/dev/null 2>&1")
    os.system(f"mount {part} -o subvol=@boot /etc/mnt/boot >/dev/null 2>&1") # Mount boot partition for writing
    if "tmp0" in mount:
        os.system("cp --reflink=auto -r /.snapshots/snapshot-tmp/boot/* /etc/mnt/boot")
        os.system("sed -i 's,@.snapshots/snapshot-tmp0,@.snapshots/snapshot-tmp,g' /etc/mnt/boot/grub/grub.cfg") # Overwrite grub config boot subvolume
        os.system("sed -i 's,@.snapshots/snapshot-tmp0,@.snapshots/snapshot-tmp,g' /.snapshots/snapshot-tmp/boot/grub/grub.cfg")
        os.system("sed -i 's,@.snapshots/snapshot-tmp0,@.snapshots/snapshot-tmp,g' /.snapshots/snapshot-tmp/etc/fstab") # Write fstab for new deployment
        os.system("sed -i 's,@.etc/etc-tmp0,@.etc/etc-tmp,g' /.snapshots/snapshot-tmp/etc/fstab")
#        os.system("sed -i 's,@.var/var-tmp0,@.var/var-tmp,g' /.snapshots/snapshot-tmp/etc/fstab")
        os.system("sed -i 's,@.boot/boot-tmp0,@.boot/boot-tmp,g' /.snapshots/snapshot-tmp/etc/fstab")
        sfile = open("/.snapshots/snapshot-tmp0/etc/astpk.d/astpk-csnapshot","r")
        snap = sfile.readline()
        snap = snap.replace(" ", "")
        sfile.close()
    else:
        os.system("cp --reflink=auto -r /.snapshots/snapshot-tmp0/boot/* /etc/mnt/boot")
        os.system("sed -i 's,@.snapshots/snapshot-tmp,@.snapshots/snapshot-tmp0,g' /etc/mnt/boot/grub/grub.cfg")
        os.system("sed -i 's,@.snapshots/snapshot-tmp,@.snapshots/snapshot-tmp0,g' /.snapshots/snapshot-tmp0/boot/grub/grub.cfg")
        os.system("sed -i 's,@.snapshots/snapshot-tmp,@.snapshots/snapshot-tmp0,g' /.snapshots/snapshot-tmp0/etc/fstab")
        os.system("sed -i 's,@.etc/etc-tmp,@.etc/etc-tmp0,g' /.snapshots/snapshot-tmp0/etc/fstab")
#        os.system("sed -i 's,@.var/var-tmp,@.var/var-tmp0,g' /.snapshots/snapshot-tmp0/etc/fstab")
        os.system("sed -i 's,@.boot/boot-tmp,@.boot/boot-tmp0,g' /.snapshots/snapshot-tmp0/etc/fstab")
        sfile = open("/.snapshots/snapshot-tmp/etc/astpk.d/astpk-csnapshot", "r")
        snap = sfile.readline()
        snap = snap.replace(" ","")
        sfile.close()
    #
    grubconf = open("/etc/mnt/boot/grub/grub.cfg","r")
    line = grubconf.readline()
    while "BEGIN /etc/grub.d/10_linux" not in line:
        line = grubconf.readline()
    line = grubconf.readline()
    gconf = str("")
    while "}" not in line:
        gconf = str(gconf)+str(line)
        line = grubconf.readline()
    if "snapshot-tmp0" in gconf:
        gconf = gconf.replace("snapshot-tmp0","snapshot-tmp")
    else:
        gconf = gconf.replace("snapshot-tmp", "snapshot-tmp0")
    if "astOS Linux" in gconf:
        gconf = re.sub('\d', '', gconf)
        gconf = gconf.replace(f"astOS Linux snapshot",f"astOS last booted deployment (snapshot {snap})")
    grubconf.close()
    os.system("sed -i '$ d' /etc/mnt/boot/grub/grub.cfg")
    grubconf = open("/etc/mnt/boot/grub/grub.cfg", "a")
    grubconf.write(gconf)
    grubconf.write("}\n")
    grubconf.write("### END /etc/grub.d/41_custom ###")
    grubconf.close()

    grubconf = open("/.snapshots/snapshot-tmp0/boot/grub/grub.cfg","r")
    line = grubconf.readline()
    while "BEGIN /etc/grub.d/10_linux" not in line:
        line = grubconf.readline()
    line = grubconf.readline()
    gconf = str("")
    while "}" not in line:
        gconf = str(gconf)+str(line)
        line = grubconf.readline()
    if "snapshot-tmp0" in gconf:
        gconf = gconf.replace("snapshot-tmp0","snapshot-tmp")
    else:
        gconf = gconf.replace("snapshot-tmp", "snapshot-tmp0")
    if "astOS Linux" in gconf:
        gconf = re.sub('\d', '', gconf)
        gconf = gconf.replace(f"astOS Linux snapshot", f"astOS last booted deployment (snapshot {snap})")
    grubconf.close()
    os.system("sed -i '$ d' /.snapshots/snapshot-tmp0/boot/grub/grub.cfg")
    grubconf = open("/.snapshots/snapshot-tmp0/boot/grub/grub.cfg", "a")
    grubconf.write(gconf)
    grubconf.write("}\n")
    grubconf.write("### END /etc/grub.d/41_custom ###")
    grubconf.close()
    os.system("umount /etc/mnt/boot >/dev/null 2>&1")

# Clear all temporary snapshots
def tmpclear():
    os.system(f"btrfs sub del /.etc/etc-chr* >/dev/null 2>&1")
    os.system(f"btrfs sub del /.var/var-chr* >/dev/null 2>&1")
    os.system(f"rm -rf /.var/var-chr* >/dev/null 2>&1")
    os.system(f"btrfs sub del /.boot/boot-chr* >/dev/null 2>&1")
    os.system(f"btrfs sub del /.snapshots/snapshot-chr*/* >/dev/null 2>&1")
    os.system(f"btrfs sub del /.snapshots/snapshot-chr* >/dev/null 2>&1")

# Find new unused image dir
def findnew():
    i = 0
    snapshots = os.listdir("/.snapshots")
    etcs = os.listdir("/.etc")
    vars = os.listdir("/.var")
    boots = os.listdir("/.boot")
    snapshots.append(etcs)
    snapshots.append(vars)
    snapshots.append(boots)
    while True:
        i += 1
        if str(f"snapshot-{i}") not in snapshots and str(f"etc-{i}") not in snapshots and str(f"var-{i}") not in snapshots and str(f"boot-{i}") not in snapshots:
            return(i)

# Main function
def main(args):
    snapshot = get_snapshot() # Get current snapshot
    etc = snapshot
    importer = DictImporter() # Dict importer
    exporter = DictExporter() # And exporter
    isChroot = chroot_check()
    lock = get_lock() # True = locked
    global fstree # Currently these are global variables, fix sometime
    global efi
    global fstreepath # ---
    fstreepath = str("/var/astpk/fstree") # Path to fstree file
    efi = get_efi()
    fstree = importer.import_(import_tree_file("/var/astpk/fstree")) # Import fstree file
    # Recognize argument and call appropriate function
    for arg in args:
        if isChroot == True and ("--chroot" not in args):
            print("Please don't use ast inside a chroot")
            break
        if arg == "new-tree" or arg == "new":
            new_snapshot()
        elif arg == "boot-update" or arg == "boot":
            update_boot(args[args.index(arg)+1])
        elif arg == "chroot" or arg == "cr" and (lock != True):
            ast_lock()
            chroot(args[args.index(arg)+1])
            ast_unlock()
        elif arg == "live-chroot":
            ast_lock()
            live_unlock()
            ast_unlock()
        elif arg == "install" or (arg == "in") and (lock != True):
            ast_lock()
            args_2 = args
            args_2.remove(args_2[0])
            args_2.remove(args_2[0])
            live = False
            if args_2[0] == "--live":
                live = True
                args_2.remove(args_2[0])
            csnapshot = args_2[0]
            args_2.remove(args_2[0])
            install(csnapshot, str(" ").join(args_2))
            if live:
                live_install(str(" ").join(args_2))
            ast_unlock()
        elif arg == "run" and (lock != True):
            ast_lock()
            args_2 = args
            args_2.remove(args_2[0])
            args_2.remove(args_2[0])
            csnapshot = args_2[0]
            args_2.remove(args_2[0])
            chrrun(csnapshot, str(" ").join(args_2))
            ast_unlock()
        elif arg == "add-branch" or arg == "branch":
            extend_branch(args[args.index(arg)+1])
        elif arg == "tmpclear" or arg == "tmp":
            tmpclear()
        elif arg == "clone-branch" or arg == "cbranch":
            clone_branch(args[args.index(arg)+1])
        elif arg == "clone-under" or arg == "ubranch":
            clone_under(args[args.index(arg)+1], args[args.index(arg)+2])
        elif arg == "clone" or arg == "tree-clone":
            clone_as_tree(args[args.index(arg)+1])
        elif arg == "deploy":
            deploy(args[args.index(arg)+1])
        elif arg == "rollback":
            rollback()
        elif arg == "upgrade" or arg == "up" and (lock != True):
            ast_lock()
            upgrade(args[args.index(arg)+1])
            ast_unlock()
        elif arg == "etc-update" or arg == "etc" and (lock != True):
            ast_lock()
            update_etc()
            ast_unlock()
        elif arg == "current" or arg == "c":
            print(snapshot)
        elif arg == "rm-snapshot" or arg == "del":
            delete(args[args.index(arg)+1])
        elif arg == "remove" and (lock != True):
            args_2 = args
            args_2.remove(args_2[0])
            args_2.remove(args_2[0])
            csnapshot = args_2[0]
            args_2.remove(args_2[0])
            remove(csnapshot, str(" ").join(args_2))
            ast_unlock()
        elif arg == "desc" or arg == "description":
            n_lay = args[args.index(arg)+1]
            args_2 = args
            args_2.remove(args_2[0])
            args_2.remove(args_2[0])
            args_2.remove(args_2[0])
            write_desc(n_lay, str(" ").join(args_2))
        elif arg == "base-update" or arg == "bu" and (lock != True):
            ast_lock()
            update_base()
            ast_unlock()
        elif arg == "sync" or arg == "tree-sync" and (lock != True):
            ast_lock()
            sync_tree(fstree,args[args.index(arg)+1],False)
            ast_unlock()
        elif arg == "fsync" or arg == "force-sync" and (lock != True):
            ast_lock()
            sync_tree(fstree,args[args.index(arg)+1],True)
            ast_unlock()
        elif arg == "auto-upgrade" and (lock != True):
            ast_lock()
            autoupgrade(snapshot)
            ast_unlock()
        elif arg == "check":
            check_update()
        elif arg == "tree-upgrade" or arg == "tupgrade" and (lock != True):
            ast_lock()
            upgrade(args[args.index(arg)+1])
            update_tree(fstree,args[args.index(arg)+1])
            ast_unlock()
        elif arg == "tree-run" or arg == "trun" and (lock != True):
            ast_lock()
            args_2 = args
            args_2.remove(args_2[0])
            args_2.remove(args_2[0])
            csnapshot = args_2[0]
            args_2.remove(args_2[0])
            run_tree(fstree, csnapshot, str(" ").join(args_2))
            ast_unlock()
        elif arg == "tree-rmpkg" or arg == "tremove" and (lock != True):
            ast_lock()
            args_2 = args
            args_2.remove(args_2[0])
            args_2.remove(args_2[0])
            csnapshot = args_2[0]
            args_2.remove(args_2[0])
            remove(csnapshot, str(" ").join(args_2))
            remove_from_tree(fstree, csnapshot, str(" ").join(args_2))
            ast_unlock()
        elif arg  == "tree":
            show_fstree()
        elif (lock == True):
            print("Error, ast is locked. To force unlock use 'rm -rf /var/astpk/lock'.")
            break
        elif (arg == args[1]):
            print("Operation not found.")

# Call main
main(args)
