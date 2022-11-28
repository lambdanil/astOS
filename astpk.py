#!/usr/bin/python3

import sys
import ast
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
# Implement AUR package maintenance between snapshots
# -----------------

# Directories
# All snapshots share one /var
# global boot is always at @boot
# *-tmp - temporary directories used to boot deployed snapshot
# *-chr - temporary directories used to chroot into snapshot or copy snapshots around
# /.snapshots/ast/ast == symlinked into /usr/local/bin/ast
# /.snapshots/etc/etc-* == individual /etc for each snapshot
# /.snapshots/boot/boot-* == individual /boot for each snapshot
# /.snapshots/rootfs/snapshot-* == snapshots
# /.snapshots/ast/snapshots/*-desc == descriptions
# /usr/share/ast == files that store current snapshot info
# /usr/share/ast/db == package database
# /var/lib/ast(/fstree) == ast files, stores fstree, symlink to /.snapshots/ast

#   Import filesystem tree file in this function
def import_tree_file(treename):
    treefile = open(treename,"r")
    tree = ast.literal_eval(treefile.readline())
    return(tree)

#   Print out tree with descriptions
def print_tree(tree):
    snapshot = get_snapshot()
    for pre, fill, node in anytree.RenderTree(tree):
        if os.path.isfile(f"/.snapshots/ast/snapshots/{node.name}-desc"):
            descfile = open(f"/.snapshots/ast/snapshots/{node.name}-desc","r")
            desc = descfile.readline()
            descfile.close()
        else:
            desc = ""
        if str(node.name) == "0":
            desc = "base snapshot"
        if snapshot != str(node.name):
            print("%s%s - %s" % (pre, node.name, desc))
        else:
            print("%s%s*- %s" % (pre, node.name, desc))

#   Write new description
def write_desc(snapshot, desc):
    os.system(f"touch /.snapshots/ast/snapshots/{snapshot}-desc")
    descfile = open(f"/.snapshots/ast/snapshots/{snapshot}-desc","w")
    descfile.write(desc)
    descfile.close()

#   Add to root tree
def append_base_tree(tree,val):
    add = anytree.Node(val, parent=tree.root)

#   Add child to node
def add_node_to_parent(tree, id, val):
    par = (anytree.find(tree, filter_=lambda node: ("x"+str(node.name)+"x") in ("x"+str(id)+"x")))
    add = anytree.Node(val, parent=par)

#   Clone within node
def add_node_to_level(tree,id, val):
    npar = get_parent(tree, id)
    par = (anytree.find(tree, filter_=lambda node: ("x"+str(node.name)+"x") in ("x"+str(npar)+"x")))
    add = anytree.Node(val, parent=par)

#   Remove node from tree
def remove_node(tree, id):
    par = (anytree.find(tree, filter_=lambda node: ("x"+str(node.name)+"x") in ("x"+str(id)+"x")))
    par.parent = None

#   Save tree to file
def write_tree(tree):
    exporter = DictExporter()
    to_write = exporter.export(tree)
    fsfile = open(fstreepath,"w")
    fsfile.write(str(to_write))

#   Get parent
def get_parent(tree, id):
    par = (anytree.find(tree, filter_=lambda node: ("x"+str(node.name)+"x") in ("x"+str(id)+"x")))
    return(par.parent.name)

#   Return all children for node
def return_children(tree, id):
    children = []
    par = (anytree.find(tree, filter_=lambda node: ("x"+str(node.name)+"x") in ("x"+str(id)+"x")))
    for child in anytree.PreOrderIter(par):
        children.append(child.name)
    if id in children:
        children.remove(id)
    return (children)

#   Return order to recurse tree
def recurstree(tree, cid):
    order = []
    for child in (return_children(tree,cid)):
        par = get_parent(tree, child)
        if child != cid:
            order.append(par)
            order.append(child)
    return (order)

#   Get current snapshot
def get_snapshot():
    csnapshot = open("/usr/share/ast/snap","r")
    snapshot = csnapshot.readline()
    csnapshot.close()
    snapshot = snapshot.replace('\n',"")
    return(snapshot)

#   Get drive partition
def get_part():
    cpart = open("/.snapshots/ast/part","r")
    uuid = cpart.readline().replace('\n',"")
    cpart.close()
    part = str(subprocess.check_output(f"blkid | grep '{uuid}' | awk '{{print $1}}'", shell=True))
    return(part.replace(":","").replace("b'","").replace("\\n'",""))

#   Get tmp partition state
def get_tmp():
    mount = str(subprocess.check_output("cat /proc/mounts | grep ' / btrfs'", shell=True))
    if "tmp0" in mount:
        return("tmp0")
    else:
        return("tmp")

#   Deploy snapshot
def deploy(snapshot):
    if not (os.path.exists(f"/.snapshots/rootfs/snapshot-{snapshot}")):
        print(f"F: cannot deploy as snapshot {snapshot} doesn't exist.")
    else:
        update_boot(snapshot)
        tmp = get_tmp()
        os.system(f"btrfs sub set-default /.snapshots/rootfs/snapshot-{tmp} >/dev/null 2>&1") # Set default volume
        untmp()
        if "tmp0" in tmp:
            tmp = "tmp"
        else:
            tmp = "tmp0"
        etc = snapshot
        os.system(f"btrfs sub snap /.snapshots/rootfs/snapshot-{snapshot} /.snapshots/rootfs/snapshot-{tmp} >/dev/null 2>&1")
        os.system(f"btrfs sub snap /.snapshots/etc/etc-{snapshot} /.snapshots/etc/etc-{tmp} >/dev/null 2>&1")
#        os.system(f"btrfs sub create /.snapshots/var/var-{tmp} >/dev/null 2>&1")
 #       os.system(f"cp --reflink=auto -r /.snapshots/var/var-{etc}/* /.snapshots/var/var-{tmp} >/dev/null 2>&1")
        os.system(f"btrfs sub snap /.snapshots/boot/boot-{snapshot} /.snapshots/boot/boot-{tmp} >/dev/null 2>&1")
        os.system(f"mkdir /.snapshots/rootfs/snapshot-{tmp}/etc >/dev/null 2>&1")
        os.system(f"rm -rf /.snapshots/rootfs/snapshot-{tmp}/var >/dev/null 2>&1")
        os.system(f"mkdir /.snapshots/rootfs/snapshot-{tmp}/boot >/dev/null 2>&1")
        os.system(f"cp --reflink=auto -r /.snapshots/etc/etc-{etc}/* /.snapshots/rootfs/snapshot-{tmp}/etc >/dev/null 2>&1")
        os.system(f"btrfs sub snap /var /.snapshots/rootfs/snapshot-{tmp}/var >/dev/null 2>&1")
        os.system(f"cp --reflink=auto -r /.snapshots/boot/boot-{etc}/* /.snapshots/rootfs/snapshot-{tmp}/boot >/dev/null 2>&1")
        os.system(f"echo '{snapshot}' > /.snapshots/rootfs/snapshot-{tmp}/usr/share/ast/snap")
        switchtmp()
        os.system(f"rm -rf /var/lib/systemd/* >/dev/null 2>&1")
        os.system(f"rm -rf /.snapshots/rootfs/snapshot-{tmp}/var/lib/systemd/* >/dev/null 2>&1")
#        os.system(f"cp --reflink=auto -r /.snapshots/var/var-{etc}/* /.snapshots/rootfs/snapshot-{tmp}/var/ >/dev/null 2>&1")
#        os.system(f"cp --reflink=auto -r /.snapshots/var/var-{etc}/lib/systemd/* /var/lib/systemd/ >/dev/null 2>&1")
#        os.system(f"cp --reflink=auto -r /.snapshots/var/var-{etc}/lib/systemd/* /.snapshots/rootfs/snapshot-{tmp}/var/lib/systemd/ >/dev/null 2>&1")
        os.system(f"btrfs sub set-default /.snapshots/rootfs/snapshot-{tmp}") # Set default volume
        print(f"Snapshot {snapshot} deployed to /.")

#   Add node to branch
def extend_branch(snapshot, desc=""):
    if not (os.path.exists(f"/.snapshots/rootfs/snapshot-{snapshot}")):
        print(f"F: cannot branch as snapshot {snapshot} doesn't exist.")
    else:
        i = findnew()
        os.system(f"btrfs sub snap -r /.snapshots/rootfs/snapshot-{snapshot} /.snapshots/rootfs/snapshot-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.snapshots/etc/etc-{snapshot} /.snapshots/etc/etc-{i} >/dev/null 2>&1")
#        os.system(f"btrfs sub snap -r /.snapshots/var/var-{snapshot} /.snapshots/var/var-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.snapshots/boot/boot-{snapshot} /.snapshots/boot/boot-{i} >/dev/null 2>&1")
        add_node_to_parent(fstree,snapshot,i)
        write_tree(fstree)
        if desc: write_desc(i, desc)
        print(f"Branch {i} added under snapshot {snapshot}.")

#   Recursively clone an entire tree
def clone_recursive(snapshot):
    if not (os.path.exists(f"/.snapshots/rootfs/snapshot-{snapshot}")):
        print(f"F: cannot clone as tree {snapshot} doesn't exist.")
    else:
        parent = get_parent(fstree, snapshot)
        children = return_children(fstree, snapshot)
        ch = children.copy()
        children.insert(0, snapshot)
        ntree = clone_branch(snapshot)
        new_children = ch.copy()
        new_children.insert(0, ntree)
        for child in ch:
            i = clone_under(new_children[children.index(get_parent(fstree, child))], child)
            new_children[children.index(child)] = i

#   Clone branch under same parent,
def clone_branch(snapshot):
    if not (os.path.exists(f"/.snapshots/rootfs/snapshot-{snapshot}")):
        print(f"F: cannot clone as snapshot {snapshot} doesn't exist.")
    else:
        i = findnew()
        os.system(f"btrfs sub snap -r /.snapshots/rootfs/snapshot-{snapshot} /.snapshots/rootfs/snapshot-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.snapshots/etc/etc-{snapshot} /.snapshots/etc/etc-{i} >/dev/null 2>&1")
#        os.system(f"btrfs sub snap -r /.snapshots/var/var-{snapshot} /.snapshots/var/var-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.snapshots/boot/boot-{snapshot} /.snapshots/boot/boot-{i} >/dev/null 2>&1")
        add_node_to_level(fstree,snapshot,i)
        write_tree(fstree)
        desc = str(f"clone of {snapshot}")
        write_desc(i, desc)
        print(f"Branch {i} added to parent of {snapshot}.")
        return i

#   Clone under specified parent
def clone_under(snapshot, branch):
    if not (os.path.exists(f"/.snapshots/rootfs/snapshot-{snapshot}")):
        print(f"F: cannot clone as snapshot {snapshot} doesn't exist.")
    elif not (os.path.exists(f"/.snapshots/rootfs/snapshot-{branch}")):
        print(f"F: cannot clone as snapshot {branch} doesn't exist.")
    else:
        i = findnew()
        os.system(f"btrfs sub snap -r /.snapshots/rootfs/snapshot-{branch} /.snapshots/rootfs/snapshot-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.snapshots/etc/etc-{branch} /.snapshots/etc/etc-{i} >/dev/null 2>&1")
#        os.system(f"btrfs sub snap -r /.snapshots/var/var-{branch} /.snapshots/var/var-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.snapshots/boot/boot-{branch} /.snapshots/boot/boot-{i} >/dev/null 2>&1")
        add_node_to_parent(fstree,snapshot,i)
        write_tree(fstree)
        desc = str(f"clone of {branch}")
        write_desc(i, desc)
        print(f"Branch {i} added under snapshot {snapshot}.")
        return i

#   Recursively remove package in tree
def remove_from_tree(tree,treename,pkg):
    if not (os.path.exists(f"/.snapshots/rootfs/snapshot-{treename}")):
        print(f"F: cannot update as tree {treename} doesn't exist.")
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
        print(f"Tree {treename} updated.")

#   Recursively run an update in tree
def update_tree(tree,treename):
    if not (os.path.exists(f"/.snapshots/rootfs/snapshot-{treename}")):
        print(f"F: cannot update as tree {treename} doesn't exist.")
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
        print(f"Tree {treename} updated.")

#   Recursively run an update in tree
def run_tree(tree,treename,cmd):
    if not (os.path.exists(f"/.snapshots/rootfs/snapshot-{treename}")):
        print(f"F: cannot update as tree {treename} doesn't exist.")
    else:
        prepare(treename)
        os.system(f"chroot /.snapshots/rootfs/snapshot-chr{treename} {cmd}")
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
            if os.path.exists(f"/.snapshots/rootfs/snapshot-chr{sarg}"):
                snapshot = sarg
                print(f"F: snapshot {snapshot} appears to be in use. If you're certain it's not in use clear lock with 'ast unlock {snapshot}'.")
                print("tree command cancelled.")
                return
            else:
                prepare(sarg)
                os.system(f"chroot /.snapshots/rootfs/snapshot-chr{sarg} {cmd}")
                posttrans(sarg)
        print(f"Tree {treename} updated.")

#   Sync tree and all it's snapshots
def sync_tree(tree,treename,forceOffline,Live):
    if not (os.path.exists(f"/.snapshots/rootfs/snapshot-{treename}")):
        print(f"F: cannot sync as tree {treename} doesn't exist.")
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
            if os.path.exists(f"/.snapshots/rootfs/snapshot-chr{sarg}"):
                snapshot = sarg
                print(f"F: snapshot {snapshot} appears to be in use. If you're certain it's not in use clear lock with 'ast unlock {snapshot}'.")
                print("tree sync cancelled.")
                return
            else:
                prepare(sarg)
 #               os.system(f"cp --reflink=auto -r /.snapshots/var/var-{arg}/lib/systemd/* /.snapshots/var/var-chr{sarg}/lib/systemd/ >/dev/null 2>&1")
 #               os.system(f"cp --reflink=auto -r /.snapshots/var/var-{arg}/lib/systemd/* /.snapshots/rootfs/snapshot-chr{sarg}/var/lib/systemd/ >/dev/null 2>&1")
                os.system("mkdir -p /.snapshots/tmp-db/local/")
                os.system("rm -rf /.snapshots/tmp-db/local/*")
                pkg_list_to = str(subprocess.check_output(f"chroot /.snapshots/rootfs/snapshot-chr{sarg} pacman -Qq", shell=True))[2:][:-1].split("\\n")[:-1]
                pkg_list_from = str(subprocess.check_output(f"chroot /.snapshots/rootfs/snapshot-{arg} pacman -Qq", shell=True))[2:][:-1].split("\\n")[:-1]
                # Get packages to be inherited
                pkg_list_from = [j for j in pkg_list_from if j not in pkg_list_to]
                os.system(f"cp -r /.snapshots/rootfs/snapshot-chr{sarg}/usr/share/ast/db/local/* /.snapshots/tmp-db/local/")
                os.system(f"cp --reflink=auto -n -r /.snapshots/rootfs/snapshot-{arg}/* /.snapshots/rootfs/snapshot-chr{sarg}/ >/dev/null 2>&1")
                os.system(f"rm -rf /.snapshots/rootfs/snapshot-chr{sarg}/usr/share/ast/db/local/*")
                os.system(f"cp -r /.snapshots/tmp-db/local/* /.snapshots/rootfs/snapshot-chr{sarg}/usr/share/ast/db/local/")
                for entry in pkg_list_from:
                    os.system(f"bash -c 'cp -r /.snapshots/rootfs/snapshot-{arg}/usr/share/ast/db/local/{entry}-[0-9]* /.snapshots/rootfs/snapshot-chr{sarg}/usr/share/ast/db/local/'")
                os.system("rm -rf /.snapshots/tmp-db/local/*")
                posttrans(sarg)
                if int(sarg) == int(get_snapshot()) and Live: # Live sync
                    tmp = get_tmp()
                    os.system("mkdir -p /.snapshots/tmp-db/local/")
                    os.system("rm -rf /.snapshots/tmp-db/local/*")
                    pkg_list_to = str(subprocess.check_output(f"chroot /.snapshots/rootfs/snapshot-{tmp} pacman -Qq", shell=True))[2:][:-1].split("\\n")[:-1]
                    pkg_list_from = str(subprocess.check_output(f"chroot /.snapshots/rootfs/snapshot-{arg} pacman -Qq", shell=True))[2:][:-1].split("\\n")[:-1]
                    # Get packages to be inherited
                    pkg_list_from = [j for j in pkg_list_from if j not in pkg_list_to]
                    os.system(f"cp -r /.snapshots/rootfs/snapshot-{tmp}/usr/share/ast/db/local/* /.snapshots/tmp-db/local/")
                    os.system(f"cp --reflink=auto -n -r /.snapshots/rootfs/snapshot-{arg}/* /.snapshots/rootfs/snapshot-{tmp}/ >/dev/null 2>&1")
                    os.system(f"rm -rf /.snapshots/rootfs/snapshot-{tmp}/usr/share/ast/db/local/*")
                    os.system(f"cp -r /.snapshots/tmp-db/local/* /.snapshots/rootfs/snapshot-{tmp}/usr/share/ast/db/local/")
                    for entry in pkg_list_from:
                        os.system(f"bash -c 'cp -r /.snapshots/rootfs/snapshot-{arg}/usr/share/ast/db/local/{entry}-[0-9]* /.snapshots/rootfs/snapshot-{tmp}/usr/share/ast/db/local/'")
                os.system("rm -rf /.snapshots/tmp-db/local/*")

        print(f"Tree {treename} synced.")

#   Clone tree
def clone_as_tree(snapshot):
    if not (os.path.exists(f"/.snapshots/rootfs/snapshot-{snapshot}")):
        print(f"F: cannot clone as snapshot {snapshot} doesn't exist.")
    else:
        i = findnew()
        os.system(f"btrfs sub snap -r /.snapshots/rootfs/snapshot-{snapshot} /.snapshots/rootfs/snapshot-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.snapshots/etc/etc-{snapshot} /.snapshots/etc/etc-{i} >/dev/null 2>&1")
 #       os.system(f"btrfs sub snap -r /.snapshots/var/var-{snapshot} /.snapshots/var/var-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.snapshots/boot/boot-{snapshot} /.snapshots/boot/boot-{i} >/dev/null 2>&1")
        append_base_tree(fstree,i)
        write_tree(fstree)
        desc = str(f"clone of {snapshot}")
        write_desc(i, desc)
        print(f"Tree {i} cloned from {snapshot}.")

#   Creates new tree from base file
def new_snapshot(desc=""):
    i = findnew()
    os.system(f"btrfs sub snap -r /.snapshots/rootfs/snapshot-0 /.snapshots/rootfs/snapshot-{i} >/dev/null 2>&1")
    os.system(f"btrfs sub snap -r /.snapshots/etc/etc-0 /.snapshots/etc/etc-{i} >/dev/null 2>&1")
    os.system(f"btrfs sub snap -r /.snapshots/boot/boot-0 /.snapshots/boot/boot-{i} >/dev/null 2>&1")
#    os.system(f"btrfs sub snap -r /.snapshots/var/var-0 /.snapshots/var/var-{i} >/dev/null 2>&1")
    append_base_tree(fstree,i)
    write_tree(fstree)
    if desc: write_desc(i, desc)
    print(f"New tree {i} created.")

#   Calls print function
def show_fstree():
    print_tree(fstree)

#   Saves changes made to /etc to snapshot
def update_etc():
    tmp = get_tmp()
    snapshot = get_snapshot()
    os.system(f"btrfs sub del /.snapshots/etc/etc-{snapshot} >/dev/null 2>&1")
    os.system(f"btrfs sub snap -r /.snapshots/etc/etc-{tmp} /.snapshots/etc/etc-{snapshot} >/dev/null 2>&1")

#   Update boot
def update_boot(snapshot):
    if not (os.path.exists(f"/.snapshots/rootfs/snapshot-{snapshot}")):
        print(f"F: cannot update boot as snapshot {snapshot} doesn't exist.")
    else:
        tmp = get_tmp()
        part = get_part()
        prepare(snapshot)
        os.system(f"chroot /.snapshots/rootfs/snapshot-chr{snapshot} grub-mkconfig {part} -o /boot/grub/grub.cfg")
        os.system(f"chroot /.snapshots/rootfs/snapshot-chr{snapshot} sed -i s,snapshot-chr{snapshot},snapshot-{tmp},g /boot/grub/grub.cfg")
        os.system(f"chroot /.snapshots/rootfs/snapshot-chr{snapshot} sed -i '0,/astOS\ Linux/s//astOS\ Linux\ snapshot\ {snapshot}/' /boot/grub/grub.cfg")
        posttrans(snapshot)

#   Chroot into snapshot
def chroot(snapshot):
    if not (os.path.exists(f"/.snapshots/rootfs/snapshot-{snapshot}")):
        print(f"F: cannot chroot as snapshot {snapshot} doesn't exist.")
    elif snapshot == "0":
        print("F: changing base snapshot is not allowed.")
    elif os.path.exists(f"/.snapshots/rootfs/snapshot-chr{snapshot}"): # Make sure snapshot is not in use by another ast process
        print(f"F: snapshot {snapshot} appears to be in use. If you're certain it's not in use clear lock with 'ast unlock {snapshot}'.")
    else:
        prepare(snapshot)
        excode = str(os.system(f"chroot /.snapshots/rootfs/snapshot-chr{snapshot}"))
        if int(excode) == 0:
            posttrans(snapshot)
            return 0
        else:
            unchr(snapshot)
            print("F: discarding changes...")
            return 1
            
        
#   Edit per-snapshot configuration
def per_snap_conf(snapshot):
    if not (os.path.exists(f"/.snapshots/rootfs/snapshot-{snapshot}")):
        print(f"F: cannot chroot as snapshot {snapshot} doesn't exist.")
    elif snapshot == "0":
        print("F: changing base snapshot is not allowed.")
    else:
        prepare(snapshot)
        os.system(f"$EDITOR /.snapshots/rootfs/snapshot-chr{snapshot}/etc/ast.conf")
        posttrans(snapshot)

#   Run command in snapshot
def chrrun(snapshot,cmd):
    if not (os.path.exists(f"/.snapshots/rootfs/snapshot-{snapshot}")):
        print(f"F: cannot chroot as snapshot {snapshot} doesn't exist.")
    elif snapshot == "0":
        print("F: changing base snapshot is not allowed.")
    elif os.path.exists(f"/.snapshots/rootfs/snapshot-chr{snapshot}"): # Make sure snapshot is not in use by another ast process
        print(f"F: snapshot {snapshot} appears to be in use. If you're certain it's not in use clear lock with 'ast unlock {snapshot}'.")
    else:
        prepare(snapshot)
        excode = str(os.system(f"chroot /.snapshots/rootfs/snapshot-chr{snapshot} {cmd}"))
        if int(excode) == 0:
            posttrans(snapshot)
            return 0
        else:
            unchr(snapshot)
            print("F: command in chroot failed, discarding changes")
            return 1

#   Clean chroot mount dirs
def unchr(snapshot):
    os.system(f"btrfs sub del /.snapshots/etc/etc-chr{snapshot} >/dev/null 2>&1")
#    os.system(f"btrfs sub del /.snapshots/var/var-chr{snapshot} >/dev/null 2>&1")
#    os.system(f"rm -rf /.snapshots/var/var-chr{snapshot} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.snapshots/boot/boot-chr{snapshot} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.snapshots/rootfs/snapshot-chr{snapshot}/* >/dev/null 2>&1")
    os.system(f"btrfs sub del /.snapshots/rootfs/snapshot-chr{snapshot} >/dev/null 2>&1")

#   Clean tmp dirs
def untmp():
    tmp = get_tmp()
    if "tmp0" in tmp:
        tmp = "tmp"
    else:
        tmp = "tmp0"
    os.system(f"btrfs sub del /.snapshots/rootfs/snapshot-{tmp}/* >/dev/null 2>&1")
    os.system(f"btrfs sub del /.snapshots/rootfs/snapshot-{tmp} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.snapshots/etc/etc-{tmp} >/dev/null 2>&1")
#    os.system(f"btrfs sub del /.snapshots/var/var-{tmp} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.snapshots/boot/boot-{tmp} >/dev/null 2>&1")

#   Install live
def live_install(pkg,is_aur):
    tmp = get_tmp()
    part = get_part()
    options = get_persnap_options(tmp)
    os.system(f"mount --bind /.snapshots/rootfs/snapshot-{tmp} /.snapshots/rootfs/snapshot-{tmp} >/dev/null 2>&1")
    os.system(f"mount --bind /home /.snapshots/rootfs/snapshot-{tmp}/home >/dev/null 2>&1")
    os.system(f"mount --bind /var /.snapshots/rootfs/snapshot-{tmp}/var >/dev/null 2>&1")
    os.system(f"mount --bind /etc /.snapshots/rootfs/snapshot-{tmp}/etc >/dev/null 2>&1")
    os.system(f"mount --bind /tmp /.snapshots/rootfs/snapshot-{tmp}/tmp >/dev/null 2>&1")
    if options["aur"] == "True":
        aur = True
    else:
        aur = False
    if aur and not aur_check(tmp):
        excode = aur_setup_live(tmp)
        if excode:
            os.system(f"umount /.snapshots/rootfs/snapshot-{tmp}/* >/dev/null 2>&1")
            os.system(f"umount /.snapshots/rootfs/snapshot-{tmp} >/dev/null 2>&1")
            print("F: Live installation failed!")
            return excode

    ### REVIEW_LATER - error checking, handle the situtaion better altogether
    if is_aur and not aur:
        print("F: AUR is not enabled in current live snapshot, but is enabled in target.\nEnable AUR for live snapshot? (y/n)")
        reply = input("> ")
        while reply.casefold() != "y" and reply.casefold() != "n":
            print("Please enter 'y' or 'n':")
            reply = input("> ")
        if reply == "y":
            aur = True
            if not aur_check(tmp):
                excode = aur_setup_live(tmp)
                if excode:
                    os.system(f"umount /.snapshots/rootfs/snapshot-{tmp}/* >/dev/null 2>&1")
                    os.system(f"umount /.snapshots/rootfs/snapshot-{tmp} >/dev/null 2>&1")
                    print("F: Live installation failed!")
                    return excode
        else:
            aur = False

    print("please wait, finishing installation...")
    if not aur:
        excode = int(os.system(f"arch-chroot /.snapshots/rootfs/snapshot-{tmp} pacman -Sy --overwrite \\* --noconfirm {pkg} >/dev/null 2>&1"))
    else:
        excode = int(os.system(f"arch-chroot /.snapshots/rootfs/snapshot-{tmp} su aur -c 'paru -Sy --overwrite \\* --noconfirm {pkg}' >/dev/null 2>&1"))
    os.system(f"umount /.snapshots/rootfs/snapshot-{tmp}/* >/dev/null 2>&1")
    os.system(f"umount /.snapshots/rootfs/snapshot-{tmp} >/dev/null 2>&1")
    if not excode:
        print("done!")
    else:
        print("F: Live installation failed!")

#   Live unlocked shell
def live_unlock():
    tmp = get_tmp()
    part = get_part()
    os.system(f"mount --bind /.snapshots/rootfs/snapshot-{tmp} /.snapshots/rootfs/snapshot-{tmp} >/dev/null 2>&1")
    os.system(f"mount --bind /home /.snapshots/rootfs/snapshot-{tmp}/home >/dev/null 2>&1")
    os.system(f"mount --bind /var /.snapshots/rootfs/snapshot-{tmp}/var >/dev/null 2>&1")
    os.system(f"mount --bind /etc /.snapshots/rootfs/snapshot-{tmp}/etc >/dev/null 2>&1")
    os.system(f"mount --bind /tmp /.snapshots/rootfs/snapshot-{tmp}/tmp >/dev/null 2>&1")
    os.system(f"arch-chroot /.snapshots/rootfs/snapshot-{tmp}")
    os.system(f"umount /.snapshots/rootfs/snapshot-{tmp}/* >/dev/null 2>&1")
    os.system(f"umount /.snapshots/rootfs/snapshot-{tmp} >/dev/null 2>&1")

# Returns True if AUR is enabled, False if not
# if AUR is enabled then sets it up inside snapshot
def setup_aur_if_enabled(snapshot):
    options = get_persnap_options(snapshot)
    aur = False
    if options["aur"] == 'True':
        aur = True
        if aur and not aur_check(snapshot):
            prepare(snapshot)
            excode = int(aur_setup(snapshot))
            if excode:
                unchr(snapshot)
                print("F: Setting up AUR failed!")
                sys.exit()
            posttrans(snapshot)
    return aur


#   Install packages
def install(snapshot,pkg):
    if not (os.path.exists(f"/.snapshots/rootfs/snapshot-{snapshot}")):
        print(f"F: cannot install as snapshot {snapshot} doesn't exist.")
    elif snapshot == "0":
        print("F: changing base snapshot is not allowed.")
    elif os.path.exists(f"/.snapshots/rootfs/snapshot-chr{snapshot}"): # Make sure snapshot is not in use by another ast process
        print(f"F: snapshot {snapshot} appears to be in use. If you're certain it's not in use clear lock with 'ast unlock {snapshot}'.")
    else:
        aur = setup_aur_if_enabled(snapshot)
        prepare(snapshot)
        if not aur:
            excode = str(os.system(f"chroot /.snapshots/rootfs/snapshot-chr{snapshot} pacman -S {pkg} --overwrite '/var/*'"))
        else:
            excode = str(os.system(f"chroot /.snapshots/rootfs/snapshot-chr{snapshot} su aur -c \"paru -S {pkg} --overwrite '/var/*'\""))

        if int(excode) == 0:
            posttrans(snapshot)
            print(f"Package {pkg} installed in snapshot {snapshot} successfully.")
            return 0
        else:
            unchr(snapshot)
            print("F: install failed and changes discarded.")
            return 1

#   Install from a text file
def install_profile(snapshot, profile):
    install(snapshot, subprocess.check_output(f"cat {profile}", shell=True).decode('utf-8').strip())

#   Remove packages
def remove(snapshot,pkg):
    if not (os.path.exists(f"/.snapshots/rootfs/snapshot-{snapshot}")):
        print(f"F: cannot remove as snapshot {snapshot} doesn't exist.")
    elif snapshot == "0":
        print("F: changing base snapshot is not allowed.")
    elif os.path.exists(f"/.snapshots/rootfs/snapshot-chr{snapshot}"):
        print(f"F: snapshot {snapshot} appears to be in use. If you're certain it's not in use clear lock with 'ast unlock {snapshot}'.")
    else:
        prepare(snapshot)
        excode = str(os.system(f"chroot /.snapshots/rootfs/snapshot-chr{snapshot} pacman --noconfirm -Rns {pkg}"))
        if int(excode) == 0:
            posttrans(snapshot)
            print(f"Package {pkg} removed from snapshot {snapshot} successfully.")
        else:
            unchr(snapshot)
            print("F: remove failed and changes discarded.")

#   Delete tree or branch
def delete(snapshot):
    print(f"Are you sure you want to delete snapshot {snapshot}? (y/N)")
    choice = input("> ")
    run = True
    if choice.casefold() != "y":
        print("Aborted")
        run = False
    if not (os.path.exists(f"/.snapshots/rootfs/snapshot-{snapshot}")):
        print(f"F: cannot delete as snapshot {snapshot} doesn't exist.")
    elif snapshot == "0":
        print("F: changing base snapshot is not allowed.")
    elif run == True:
        children = return_children(fstree,snapshot)
        os.system(f"btrfs sub del /.snapshots/boot/boot-{snapshot} >/dev/null 2>&1")
        os.system(f"btrfs sub del /.snapshots/etc/etc-{snapshot} >/dev/null 2>&1")
#        os.system(f"btrfs sub del /.snapshots/var/var-{snapshot} >/dev/null 2>&1")
        os.system(f"btrfs sub del /.snapshots/rootfs/snapshot-{snapshot} >/dev/null 2>&1")
        # Make sure temporary chroot directories are deleted as well
        if (os.path.exists(f"/.snapshots/rootfs/snapshot-chr{snapshot}")):
            os.system(f"btrfs sub del /.snapshots/boot/boot-chr{snapshot} >/dev/null 2>&1")
            os.system(f"btrfs sub del /.snapshots/etc/etc-chr{snapshot} >/dev/null 2>&1")
            os.system(f"btrfs sub del /.snapshots/rootfs/snapshot-chr{snapshot} >/dev/null 2>&1")
        for child in children: # This deletes the node itself along with it's children
            os.system(f"btrfs sub del /.snapshots/boot/boot-{child} >/dev/null 2>&1")
            os.system(f"btrfs sub del /.snapshots/etc/etc-{child} >/dev/null 2>&1")
 #           os.system(f"btrfs sub del /.snapshots/var/var-{child} >/dev/null 2>&1")
            os.system(f"btrfs sub del /.snapshots/rootfs/snapshot-{child} >/dev/null 2>&1")
            if (os.path.exists(f"/.snapshots/rootfs/snapshot-chr{child}")):
                os.system(f"btrfs sub del /.snapshots/boot/boot-chr{child} >/dev/null 2>&1")
                os.system(f"btrfs sub del /.snapshots/etc/etc-chr{child} >/dev/null 2>&1")
                os.system(f"btrfs sub del /.snapshots/rootfs/snapshot-chr{child} >/dev/null 2>&1")
        remove_node(fstree,snapshot) # Remove node from tree or root
        write_tree(fstree)
        print(f"Snapshot {snapshot} removed.")

#   Update base
def update_base():
    snapshot = "0"
    if os.path.exists(f"/.snapshots/rootfs/snapshot-chr{snapshot}"):
        print(f"F: snapshot {snapshot} appears to be in use. If you're certain it's not in use clear lock with 'ast unlock {snapshot}'.")
    else:
        prepare(snapshot)
        excode = str(os.system(f"chroot /.snapshots/rootfs/snapshot-chr{snapshot} pacman -Syyu"))
        if int(excode) == 0:
            posttrans(snapshot)
            print(f"Snapshot {snapshot} upgraded successfully.")
        else:
            unchr(snapshot)
            print("F: upgrade failed and changes discarded.")



#   Prepare snapshot to chroot dir to install or chroot into
def prepare(snapshot):
    unchr(snapshot)
    part = get_part()
    etc = snapshot
    os.system(f"btrfs sub snap /.snapshots/rootfs/snapshot-{snapshot} /.snapshots/rootfs/snapshot-chr{snapshot} >/dev/null 2>&1")
    os.system(f"btrfs sub snap /.snapshots/etc/etc-{snapshot} /.snapshots/etc/etc-chr{snapshot} >/dev/null 2>&1")
 #   os.system(f"mkdir -p /.snapshots/var/var-chr{snapshot} >/dev/null 2>&1")
    # pacman gets weird when chroot directory is not a mountpoint, so the following mount is necessary
    os.system(f"mount --bind /.snapshots/rootfs/snapshot-chr{snapshot} /.snapshots/rootfs/snapshot-chr{snapshot} >/dev/null 2>&1")
    os.system(f"mount --bind /var /.snapshots/rootfs/snapshot-chr{snapshot}/var >/dev/null 2>&1")
    os.system(f"mount --rbind /dev /.snapshots/rootfs/snapshot-chr{snapshot}/dev >/dev/null 2>&1")
    os.system(f"mount --rbind /sys /.snapshots/rootfs/snapshot-chr{snapshot}/sys >/dev/null 2>&1")
    os.system(f"mount --rbind /tmp /.snapshots/rootfs/snapshot-chr{snapshot}/tmp >/dev/null 2>&1")
    os.system(f"mount --rbind /proc /.snapshots/rootfs/snapshot-chr{snapshot}/proc >/dev/null 2>&1")
    os.system(f"btrfs sub snap /.snapshots/boot/boot-{snapshot} /.snapshots/boot/boot-chr{snapshot} >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.snapshots/etc/etc-chr{snapshot}/* /.snapshots/rootfs/snapshot-chr{snapshot}/etc >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.snapshots/boot/boot-chr{snapshot}/* /.snapshots/rootfs/snapshot-chr{snapshot}/boot >/dev/null 2>&1")
    os.system(f"rm -rf /.snapshots/rootfs/snapshot-chr{snapshot}/var/lib/systemd/* >/dev/null 2>&1")
 #   os.system(f"cp -r --reflink=auto /.snapshots/var/var-{snapshot}/lib/systemd/* /.snapshots/rootfs/snapshot-chr{snapshot}/var/lib/systemd/ >/dev/null 2>&1")
    os.system(f"mount --bind /home /.snapshots/rootfs/snapshot-chr{snapshot}/home >/dev/null 2>&1")
    os.system(f"mount --rbind /run /.snapshots/rootfs/snapshot-chr{snapshot}/run >/dev/null 2>&1")
    os.system(f"cp /etc/machine-id /.snapshots/rootfs/snapshot-chr{snapshot}/etc/machine-id")
    os.system(f"mkdir -p /.snapshots/rootfs/snapshot-chr{snapshot}/.snapshots/ast && cp -f /.snapshots/ast/fstree /.snapshots/rootfs/snapshot-chr{snapshot}/.snapshots/ast/")
    os.system(f"mount --bind /etc/resolv.conf /.snapshots/rootfs/snapshot-chr{snapshot}/etc/resolv.conf >/dev/null 2>&1")
    os.system(f"mount --bind /root /.snapshots/rootfs/snapshot-chr{snapshot}/root >/dev/null 2>&1")

#   Post transaction function, copy from chroot dirs back to read only snapshot dir
def posttrans(snapshot):
    etc = snapshot
    tmp = get_tmp()
    os.system(f"umount /.snapshots/rootfs/snapshot-chr{snapshot} >/dev/null 2>&1")
    os.system(f"umount /.snapshots/rootfs/snapshot-chr{snapshot}/etc/resolv.conf >/dev/null 2>&1")
    os.system(f"umount /.snapshots/rootfs/snapshot-chr{snapshot}/root >/dev/null 2>&1")
    os.system(f"umount /.snapshots/rootfs/snapshot-chr{snapshot}/home >/dev/null 2>&1")
    os.system(f"umount /.snapshots/rootfs/snapshot-chr{snapshot}/run >/dev/null 2>&1")
    os.system(f"umount /.snapshots/rootfs/snapshot-chr{snapshot}/dev >/dev/null 2>&1")
    os.system(f"umount /.snapshots/rootfs/snapshot-chr{snapshot}/sys >/dev/null 2>&1")
    os.system(f"umount /.snapshots/rootfs/snapshot-chr{snapshot}/proc >/dev/null 2>&1")
    os.system(f"btrfs sub del /.snapshots/rootfs/snapshot-{snapshot} >/dev/null 2>&1")
    os.system(f"rm -rf /.snapshots/etc/etc-chr{snapshot}/* >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.snapshots/rootfs/snapshot-chr{snapshot}/etc/* /.snapshots/etc/etc-chr{snapshot} >/dev/null 2>&1")
 #   os.system(f"rm -rf /.snapshots/var/var-chr{snapshot}/* >/dev/null 2>&1")
 #   os.system(f"mkdir -p /.snapshots/var/var-chr{snapshot}/lib/systemd >/dev/null 2>&1")
 #   os.system(f"cp -r --reflink=auto /.snapshots/rootfs/snapshot-chr{snapshot}/var/lib/systemd/* /.snapshots/var/var-chr{snapshot}/lib/systemd >/dev/null 2>&1")
    os.system(f"cp -r -n --reflink=auto /.snapshots/rootfs/snapshot-chr{snapshot}/var/cache/pacman/pkg/* /var/cache/pacman/pkg/ >/dev/null 2>&1")
    os.system(f"rm -rf /.snapshots/boot/boot-chr{snapshot}/* >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.snapshots/rootfs/snapshot-chr{snapshot}/boot/* /.snapshots/boot/boot-chr{snapshot} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.snapshots/etc/etc-{etc} >/dev/null 2>&1")
 #   os.system(f"btrfs sub del /.snapshots/var/var-{etc} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.snapshots/boot/boot-{etc} >/dev/null 2>&1")
    os.system(f"btrfs sub snap -r /.snapshots/etc/etc-chr{snapshot} /.snapshots/etc/etc-{etc} >/dev/null 2>&1")
 #   os.system(f"btrfs sub create /.snapshots/var/var-{etc} >/dev/null 2>&1")
  #  os.system(f"mkdir -p /.snapshots/var/var-{etc}/lib/systemd >/dev/null 2>&1")
  #  os.system(f"cp --reflink=auto -r /.snapshots/var/var-chr{snapshot}/lib/systemd/* /.snapshots/var/var-{etc}/lib/systemd >/dev/null 2>&1")
    os.system(f"rm -rf /var/lib/systemd/* >/dev/null 2>&1")
    os.system(f"cp --reflink=auto -r /.snapshots/rootfs/snapshot-{tmp}/var/lib/systemd/* /var/lib/systemd >/dev/null 2>&1")
    os.system(f"btrfs sub snap -r /.snapshots/rootfs/snapshot-chr{snapshot} /.snapshots/rootfs/snapshot-{snapshot} >/dev/null 2>&1")
    os.system(f"btrfs sub snap -r /.snapshots/boot/boot-chr{snapshot} /.snapshots/boot/boot-{etc} >/dev/null 2>&1")
    unchr(snapshot)

#   Upgrade snapshot
def upgrade(snapshot):
    if not (os.path.exists(f"/.snapshots/rootfs/snapshot-{snapshot}")):
        print(f"F: cannot upgrade as snapshot {snapshot} doesn't exist.")
    elif snapshot == "0":
        print("F: changing base snapshot is not allowed.")
    elif os.path.exists(f"/.snapshots/rootfs/snapshot-chr{snapshot}"):
        print(f"F: snapshot {snapshot} appears to be in use. If you're certain it's not in use clear lock with 'ast unlock {snapshot}'.")
    else:
        aur = setup_aur_if_enabled(snapshot)
        prepare(snapshot)
        if not aur:
            excode = str(os.system(f"chroot /.snapshots/rootfs/snapshot-chr{snapshot} pacman -Syyu")) # Default upgrade behaviour is now "safe" update, meaning failed updates get fully discarded
        else:
            excode = str(os.system(f"chroot /.snapshots/rootfs/snapshot-chr{snapshot} su aur -c 'paru -Syyu'"))
        if int(excode) == 0:
            posttrans(snapshot)
            print(f"Snapshot {snapshot} upgraded successfully.")
        else:
            unchr(snapshot)
            print("F: upgrade failed and changes discarded.")

#   Refresh snapshot
def refresh(snapshot):
    if not (os.path.exists(f"/.snapshots/rootfs/snapshot-{snapshot}")):
        print(f"F: cannot refresh as snapshot {snapshot} doesn't exist.")
    elif snapshot == "0":
        print("F: changing base snapshot is not allowed.")
    elif os.path.exists(f"/.snapshots/rootfs/snapshot-chr{snapshot}"):
        print(f"F: snapshot {snapshot} appears to be in use. If you're certain it's not in use clear lock with 'ast unlock {snapshot}'.")
    else:
        prepare(snapshot)
        excode = str(os.system(f"chroot /.snapshots/rootfs/snapshot-chr{snapshot} pacman -Syy"))
        if int(excode) == 0:
            posttrans(snapshot)
            print(f"Snapshot {snapshot} refreshed successfully.")
        else:
            unchr(snapshot)
            print("F: refresh failed and changes discarded.")

#   Noninteractive update
def autoupgrade(snapshot):
    aur = setup_aur_if_enabled(snapshot)
    prepare(snapshot)
    if not aur:
        excode = str(os.system(f"chroot /.snapshots/rootfs/snapshot-chr{snapshot} pacman --noconfirm -Syyu"))
    else:
        excode = str(os.system(f"chroot /.snapshots/rootfs/snapshot-chr{snapshot} su aur -c 'paru --noconfirm -Syy'"))
    if int(excode) == 0:
        posttrans(snapshot)
        os.system("echo 0 > /.snapshots/ast/upstate")
        os.system("echo $(date) >> /.snapshots/ast/upstate")
    else:
        unchr(snapshot)
        os.system("echo 1 > /.snapshots/ast/upstate")
        os.system("echo $(date) >> /.snapshots/ast/upstate")

#   Check if last update was successful
def check_update():
    upstate = open("/.snapshots/ast/upstate", "r")
    line = upstate.readline()
    date = upstate.readline()
    if "1" in line:
        print(f"F: Last update on {date} failed.")
    if "0" in line:
        print(f"Last update on {date} completed successfully.")
    upstate.close()

def chroot_check():
    chroot = True # When inside chroot
    with open("/proc/mounts", "r") as mounts:
        for line in mounts:
            if str("/.snapshots btrfs") in str(line):
                chroot = False
    return(chroot)

#   Rollback last booted deployment
def rollback():
    tmp = get_tmp()
    i = findnew()
    clone_as_tree(tmp)
    write_desc(i, "rollback")
    deploy(i)

#   Switch between /tmp deployments
def switchtmp():
    mount = get_tmp()
    part = get_part()
    os.system(f"mkdir -p /etc/mnt/boot >/dev/null 2>&1")
    os.system(f"mount {part} -o subvol=@boot /etc/mnt/boot") # Mount boot partition for writing
    if "tmp0" in mount:
        os.system("cp --reflink=auto -r /.snapshots/rootfs/snapshot-tmp/boot/* /etc/mnt/boot")
        os.system("sed -i 's,@.snapshots/rootfs/snapshot-tmp0,@.snapshots/rootfs/snapshot-tmp,g' /etc/mnt/boot/grub/grub.cfg") # Overwrite grub config boot subvolume
        os.system("sed -i 's,@.snapshots/rootfs/snapshot-tmp0,@.snapshots/rootfs/snapshot-tmp,g' /.snapshots/rootfs/snapshot-tmp/boot/grub/grub.cfg")
        os.system("sed -i 's,@.snapshots/rootfs/snapshot-tmp0,@.snapshots/rootfs/snapshot-tmp,g' /.snapshots/rootfs/snapshot-tmp/etc/fstab") # Write fstab for new deployment
        os.system("sed -i 's,@.snapshots/etc/etc-tmp0,@.snapshots/etc/etc-tmp,g' /.snapshots/rootfs/snapshot-tmp/etc/fstab")
        os.system("sed -i 's,@.snapshots/boot/boot-tmp0,@.snapshots/boot/boot-tmp,g' /.snapshots/rootfs/snapshot-tmp/etc/fstab")
        sfile = open("/.snapshots/rootfs/snapshot-tmp0/usr/share/ast/snap","r")
        snap = sfile.readline()
        snap = snap.replace(" ", "")
        sfile.close()
    else:
        os.system("cp --reflink=auto -r /.snapshots/rootfs/snapshot-tmp0/boot/* /etc/mnt/boot")
        os.system("sed -i 's,@.snapshots/rootfs/snapshot-tmp,@.snapshots/rootfs/snapshot-tmp0,g' /etc/mnt/boot/grub/grub.cfg")
        os.system("sed -i 's,@.snapshots/rootfs/snapshot-tmp,@.snapshots/rootfs/snapshot-tmp0,g' /.snapshots/rootfs/snapshot-tmp0/boot/grub/grub.cfg")
        os.system("sed -i 's,@.snapshots/rootfs/snapshot-tmp,@.snapshots/rootfs/snapshot-tmp0,g' /.snapshots/rootfs/snapshot-tmp0/etc/fstab")
        os.system("sed -i 's,@.snapshots/etc/etc-tmp,@.snapshots/etc/etc-tmp0,g' /.snapshots/rootfs/snapshot-tmp0/etc/fstab")
        os.system("sed -i 's,@.snapshots/boot/boot-tmp,@.snapshots/boot/boot-tmp0,g' /.snapshots/rootfs/snapshot-tmp0/etc/fstab")
        sfile = open("/.snapshots/rootfs/snapshot-tmp/usr/share/ast/snap", "r")
        snap = sfile.readline()
        snap = snap.replace(" ","")
        sfile.close()
    #
    snap = snap.replace('\n',"")
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
        gconf = re.sub('snapshot \d', '', gconf)
        gconf = gconf.replace(f"astOS Linux",f"astOS last booted deployment (snapshot {snap})")
    grubconf.close()
    os.system("sed -i '$ d' /etc/mnt/boot/grub/grub.cfg")
    grubconf = open("/etc/mnt/boot/grub/grub.cfg", "a")
    grubconf.write(gconf)
    grubconf.write("}\n")
    grubconf.write("### END /etc/grub.d/41_custom ###")
    grubconf.close()

    grubconf = open("/.snapshots/rootfs/snapshot-tmp0/boot/grub/grub.cfg","r")
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
        gconf = re.sub('snapshot \d', '', gconf)
        gconf = gconf.replace(f"astOS Linux", f"astOS last booted deployment (snapshot {snap})")
    grubconf.close()
    os.system("sed -i '$ d' /.snapshots/rootfs/snapshot-tmp0/boot/grub/grub.cfg")
    grubconf = open("/.snapshots/rootfs/snapshot-tmp0/boot/grub/grub.cfg", "a")
    grubconf.write(gconf)
    grubconf.write("}\n")
    grubconf.write("### END /etc/grub.d/41_custom ###")
    grubconf.close()
    os.system("umount /etc/mnt/boot >/dev/null 2>&1")

#   Show diff of packages between 2 snapshots TODO: make this function not depend on bash
def snapshot_diff(snap1, snap2):
    if not os.path.exists(f"/.snapshots/rootfs/snapshot-{snap1}"):
        print(f"Snapshot {snap1} not found.")
    elif not os.path.exists(f"/.snapshots/rootfs/snapshot-{snap2}"):
        print(f"Snapshot {snap2} not found.")
    else:
        os.system(f"bash -c \"diff <(ls /.snapshots/rootfs/snapshot-{snap1}/usr/share/ast/db/local) <(ls /.snapshots/rootfs/snapshot-{snap2}/usr/share/ast/db/local) | grep '^>\|^<' | sort\"")


#   Remove temporary chroot for specified snapshot only
#   This unlocks the snapshot for use by other functions
def snapshot_unlock(snap):
    os.system(f"btrfs sub del /.snapshots/rootfs/snapshot-chr{snap} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.snapshots/etc/etc-chr{snap} >/dev/null 2>&1")
#    os.system(f"btrfs sub del /.snapshots/var/var-chr{snap} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.snapshots/boot/boot-chr{snap} >/dev/null 2>&1")

#   Show some basic ast commands
def ast_help():
    print("all ast commands, aside from 'ast tree' must be used with root permissions!")
    print("\n\ntree manipulation commands:")
    print("\ttree - show the snapshot tree")
    print("\tdiff <snapshot 1> <snapshot 2> - show package diff between snapshots")
    print("\tcurrent - return current snapshot number")
    print("\tdesc <snapshot> <description> - set a description for snapshot by number")
    print("\tdel <tree> - delete a tree and all it's branches recursively")
    print("\tchroot <snapshot> - open a root shell inside specified snapshot")
    print("\tlive-chroot - open a read-write shell inside currently booted snapshot (changes are discarded on new deployment)")
    print("\trun <snapshot> <command> - execute command inside another snapshot")
    print("\ttree-run <tree> <command> - execute command inside another snapshot and all snapshots below it")
    print("\tclone <snapshot> - create a copy of snapshot")
    print("\tclone-tree <snapshot> - clone a tree recursively")
    print("\tbranch <snapshot> - create a new branch from snapshot")
    print("\tcbranch <snapshot> - copy snapshot under same parent branch")
    print("\tubranch <parent> <snapshot> - copy snapshot under specified parent")
    print("\tnew - create a new base snapshot")
    print("\tdeploy <snapshot> - deploy a snapshot for next boot")
    print("\tbase-update - update the base image")
    print("\n\npackage management commands:")
    print("\tinstall <snapshot> <package> - install a package inside specified snapshot")
    print("\tsync <tree> - sync package and configuration changes recursively, requires an internet connection")
    print("\tforce-sync <tree> - same thing as sync but doesn't update snapshots, potentially riskier")
    print("\tremove <snapshot> <package(s)> - remove package(s) from snapshot")
    print("\ttree-rmpkg <tree> <package(s)> - remove package(s) from tree recursively")
    print("\tupgrade <snapshot> - update all packages in snapshot")
    print("\ttree-upgrade <tree> - update all packages in snapshot recursively")
    print("\trollback - rollback the deployment to the last booted snapshot")
    print("\n\nto update ast itself use 'ast ast-sync'")

#   Update ast itself
def ast_sync():
    cdir = os.getcwd()
    os.chdir("/tmp")
    excode = str(os.system("curl -O 'https://raw.githubusercontent.com/CuBeRJAN/astOS/main/astpk.py'"))
    if int(excode) == 0:
        os.system("cp ./astpk.py /.snapshots/ast/ast")
        os.system("chmod +x /.snapshots/ast/ast")
        print("ast updated succesfully.")
    else:
        print("F: failed to download ast")
    os.chdir(cdir)

#   Get per-snapshot configuration options from /etc/ast.conf
def get_persnap_options(snap):
    options = {"aur":"False"} # defaults here
    if not os.path.exists(f"/.snapshots/etc/etc-{snap}/ast.conf"):
        return options
    with open(f"/.snapshots/etc/etc-{snap}/ast.conf", "r") as optfile:
        for line in optfile:
            left, right = line.split("::") # Split options with '::'
            options[left] = right[:-1] # Remove newline here
    return options

# Check if AUR is setup right
def aur_check(snap):
    return os.path.exists(f"/.snapshots/rootfs/snapshot-{snap}/usr/bin/paru")

# Set up AUR support for snapshot
def aur_setup(snap):
    required = ["sudo", "git", "base-devel"]
    excode = int(os.system(f"chroot /.snapshots/rootfs/snapshot-chr{snap} pacman -Sy --needed --noconfirm {' '.join(required)}"))
    if excode:
        print("F: failed to install necessary packages to target!")
        unchr(snap)
        return str(excode)
    os.system(f"chroot /.snapshots/rootfs/snapshot-chr{snap} useradd aur")
    os.system(f"chmod +w /.snapshots/rootfs/snapshot-chr{snap}/etc/sudoers")
    os.system(f"echo 'aur ALL=(ALL:ALL) NOPASSWD: ALL' >> /.snapshots/rootfs/snapshot-chr{snap}/etc/sudoers")
    os.system(f"chmod -w /.snapshots/rootfs/snapshot-chr{snap}/etc/sudoers")
    os.system(f"chroot /.snapshots/rootfs/snapshot-chr{snap} mkdir -p /home/aur")
    os.system(f"chroot /.snapshots/rootfs/snapshot-chr{snap} chown -R aur /home/aur >/dev/null 2>&1")
    # TODO: more checking here
    excode = int(os.system(f"chroot /.snapshots/rootfs/snapshot-chr{snap} su aur -c 'rm -rf /home/aur/paru-bin && cd /home/aur && git clone https://aur.archlinux.org/paru-bin.git' >/dev/null 2>&1"))
    if excode:
        print("F: failed to download paru-bin")
        unchr(snap)
        return excode
    excode = int(os.system(f"chroot /.snapshots/rootfs/snapshot-chr{snap} su aur -c 'cd /home/aur/paru-bin && makepkg -si'"))
    if excode:
        print("F: failed installing paru-bin")
        unchr(snap)
        return excode
    return 0

# Set up AUR support for live snapshot
def aur_setup_live(snap):
    tmp = snap
    print("setting up AUR...")
    excode = int(os.system(f"arch-chroot /.snapshots/rootfs/snapshot-{snap} pacman -S --noconfirm --needed sudo git base-devel >/dev/null 2>&1"))
    if excode:
        return excode
    os.system(f"chroot /.snapshots/rootfs/snapshot-{snap} useradd aur")
    os.system(f"chmod +w /.snapshots/rootfs/snapshot-{snap}/etc/sudoers")
    os.system(f"echo 'aur ALL=(ALL:ALL) NOPASSWD: ALL' >> /.snapshots/rootfs/snapshot-{snap}/etc/sudoers")
    os.system(f"chmod -w /.snapshots/rootfs/snapshot-{snap}/etc/sudoers")
    os.system(f"chroot /.snapshots/rootfs/snapshot-{snap} mkdir -p /home/aur")
    os.system(f"chroot /.snapshots/rootfs/snapshot-{snap} chown -R aur /home/aur >/dev/null 2>&1")
    # TODO: no error checking here
    excode = int(os.system(f"arch-chroot /.snapshots/rootfs/snapshot-{snap} su aur -c 'rm -rf /home/aur/paru-bin && cd /home/aur && git clone https://aur.archlinux.org/paru-bin.git' >/dev/null 2>&1"))
    if excode:
        print("F: failed to download paru-bin")
        return excode
    excode = int(os.system(f"arch-chroot /.snapshots/rootfs/snapshot-{snap} su aur -c 'cd /home/aur/paru-bin && makepkg --noconfirm -si >/dev/null 2>&1'"))
    if excode:
        print("F: failed installing paru-bin")
        return excode
    return 0

# Clear all temporary snapshots
def tmpclear():
    os.system(f"btrfs sub del /.snapshots/etc/etc-chr* >/dev/null 2>&1")
#    os.system(f"btrfs sub del /.snapshots/var/var-chr* >/dev/null 2>&1")
#    os.system(f"rm -rf /.snapshots/var/var-chr* >/dev/null 2>&1")
    os.system(f"btrfs sub del /.snapshots/boot/boot-chr* >/dev/null 2>&1")
    os.system(f"btrfs sub del /.snapshots/rootfs/snapshot-chr*/* >/dev/null 2>&1")
    os.system(f"btrfs sub del /.snapshots/rootfs/snapshot-chr* >/dev/null 2>&1")

#   Find new unused snapshot dir
def findnew():
    i = 0
    snapshots = os.listdir("/.snapshots/rootfs")
    etcs = os.listdir("/.snapshots/etc")
#    vars = os.listdir("/.snapshots/var")
    boots = os.listdir("/.snapshots/boot")
    snapshots.append(etcs)
    snapshots.append(vars)
    snapshots.append(boots)
    while True:
        i += 1
        if str(f"snapshot-{i}") not in snapshots and str(f"etc-{i}") not in snapshots and str(f"var-{i}") not in snapshots and str(f"boot-{i}") not in snapshots:
            return(i)

#   Main function
def main(args):
    snapshot = get_snapshot() # Get current snapshot
    etc = snapshot
    importer = DictImporter() # Dict importer
    exporter = DictExporter() # And exporter
    isChroot = chroot_check()
    global fstree # Currently these are global variables, fix sometime
    global fstreepath # ---
    fstreepath = str("/.snapshots/ast/fstree") # Path to fstree file
    fstree = importer.import_(import_tree_file("/.snapshots/ast/fstree")) # Import fstree file
    # Recognize argument and call appropriate function
    if len(args) > 1:
        arg = args[1]
    else:
        print("You need to specify an operation, see 'ast help' for help.")
        sys.exit()
    if isChroot == True and ("--chroot" not in args):
        print("Please don't use ast inside a chroot!")
    elif arg == "new-tree" or arg == "new":
        args_2 = args
        args_2.remove(args_2[0])
        args_2.remove(args_2[0])
        new_snapshot(str(" ").join(args_2))
    elif arg == "boot-update" or arg == "boot":
        update_boot(args[args.index(arg)+1])
    elif arg == "chroot" or arg == "cr":
        chroot(args[args.index(arg)+1])
    elif arg == "live-chroot":
        live_unlock()
    elif arg == "install" or (arg == "in"):
        args_2 = args
        args_2.remove(args_2[0])
        args_2.remove(args_2[0])
        live = False
        if args_2[0] == "--live":
            args_2.remove(args_2[0])
        if args_2[0] == get_snapshot(): # If installing into current snapshot automatically use live install
            live = True
        if args_2[0] == "--not-live": # Disable live-install for current snapshot
            args_2.remove(args_2[0])
            live = False
        csnapshot = args_2[0]
        args_2.remove(args_2[0])
        if get_persnap_options(csnapshot)["aur"] == "True":
            aur = True
        else:
            aur = False
        excode = install(csnapshot, str(" ").join(args_2))
        if live and not excode: # only perform the live_install if the first install was successful
            live_install(str(" ").join(args_2), aur)
    elif arg == "run":
        args_2 = args
        args_2.remove(args_2[0])
        args_2.remove(args_2[0])
        csnapshot = args_2[0]
        args_2.remove(args_2[0])
        chrrun(csnapshot, str(" ").join(args_2))
    elif arg == "add-branch" or arg == "branch":
        extend_branch(args[args.index(arg)+1])
    elif arg == "edit-conf" or arg == "edit":
        per_snap_conf(args[args.index(arg)+1])
    elif arg == "tmpclear" or arg == "tmp":
        tmpclear()
    elif arg == "clone-branch" or arg == "cbranch":
        clone_branch(args[args.index(arg)+1])
    elif arg == "clone-under" or arg == "ubranch":
        clone_under(args[args.index(arg)+1], args[args.index(arg)+2])
    elif arg == "diff":
        snapshot_diff(args[args.index(arg)+1], args[args.index(arg)+2])
    elif arg == "clone":
        clone_as_tree(args[args.index(arg)+1])
    elif arg == "clone-tree":
        clone_recursive(args[args.index(arg)+1])
    elif arg == "deploy":
        deploy(args[args.index(arg)+1])
    elif arg == "rollback":
        rollback()
    elif arg == "upgrade" or arg == "up":
        upgrade(args[args.index(arg)+1])
    elif arg == "unlock":
        snapshot_unlock(args[args.index(arg)+1])
    elif arg == "refresh" or arg == "ref":
        refresh(args[args.index(arg)+1])
    elif arg == "etc-update" or arg == "etc":
        update_etc()
    elif arg == "current" or arg == "c":
        print(snapshot)
    elif arg == "rm-snapshot" or arg == "del":
        delete(args[args.index(arg)+1])
    elif arg == "remove":
        args_2 = args
        args_2.remove(args_2[0])
        args_2.remove(args_2[0])
        csnapshot = args_2[0]
        args_2.remove(args_2[0])
        remove(csnapshot, str(" ").join(args_2))
    elif arg == "desc" or arg == "description":
        n_lay = args[args.index(arg)+1]
        args_2 = args
        args_2.remove(args_2[0])
        args_2.remove(args_2[0])
        args_2.remove(args_2[0])
        write_desc(n_lay, str(" ").join(args_2))
    elif arg == "base-update" or arg == "bu":
        update_base()
    elif arg == "help":
        ast_help()
    elif arg == "ast-sync":
        ast_sync()
    elif arg == "sync" or arg == "tree-sync":
        live = True
        if len(args) > 3:
            if args[2] == "--not-live":
                live = False
        if not live:
            sync_tree(fstree,args[args.index(arg)+2],False,live)
        else:
            sync_tree(fstree,args[args.index(arg)+1],False,live)
    elif arg == "fsync" or arg == "force-sync":
        live = True
        if len(args) > 3:
            if args[2] == "--not-live":
                live = False
        if not live:
            sync_tree(fstree,args[args.index(arg)+2],True,live)
        else:
            sync_tree(fstree,args[args.index(arg)+1],True,live)
    elif arg == "auto-upgrade":
        autoupgrade(snapshot)
    elif arg == "check":
        check_update()
    elif arg == "tree-upgrade" or arg == "tupgrade":
        update_tree(fstree,args[args.index(arg)+1])
    elif arg == "tree-run" or arg == "trun":
        args_2 = args
        args_2.remove(args_2[0])
        args_2.remove(args_2[0])
        csnapshot = args_2[0]
        args_2.remove(args_2[0])
        run_tree(fstree, csnapshot, str(" ").join(args_2))
    elif arg == "tree-rmpkg" or arg == "tremove":
        args_2 = args
        args_2.remove(args_2[0])
        args_2.remove(args_2[0])
        csnapshot = args_2[0]
        args_2.remove(args_2[0])
        remove(csnapshot, str(" ").join(args_2))
        remove_from_tree(fstree, csnapshot, str(" ").join(args_2))
    elif arg == "tree":
        show_fstree()
    else:
        print("Operation not found.")

# Call main
main(args)
