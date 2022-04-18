#!/usr/bin/python3
import sys
import ast # Heh funny name coincidence with project name
import subprocess
from anytree.importer import DictImporter
from anytree.exporter import DictExporter
import anytree
import os

args = list(sys.argv)


# TODO ------------
# Test EFI
# General code cleanup
# Handle bootloader updates better
# Clean up code, add more comments to code.
# Add documentation, improve /etc merges (currently unhandled), make the tree sync write less data maybe?
# Maybe port for other distros?
# -----------------

# Directories
# All images share one /var, but pacman and systemd directories (potentionally more in the future) are unique to each image to avoid issues
# boot is always at @boot
# *-tmp - temporary directories used to boot deployed image
# *-chr - temporary directories used to chroot into image or copy images around
# /.var/var-* == individual var for each image
# /.etc/etc-* == individual etc for each image
# /.overlays/overlay-* == images
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
    overlay = get_overlay()
    for pre, fill, node in anytree.RenderTree(tree):
        if os.path.isfile(f"/root/images/{node.name}-desc"):
            descfile = open(f"/root/images/{node.name}-desc","r")
            desc = descfile.readline()
            descfile.close()
        else:
            desc = ""
        if str(node.name) == "0":
            desc = "base image"
        if overlay != str(node.name):
            print("%s%s - %s" % (pre, node.name, desc))
        else:
            print("%s%s*- %s" % (pre, node.name, desc))

# Write new description
def write_desc(overlay, desc):
    os.system(f"touch /root/images/{overlay}-desc")
    descfile = open(f"/root/images/{overlay}-desc","w")
    descfile.write(desc)
    descfile.close()

# Add to root tree
def append_base_tree(tree,val):
    add = anytree.Node(val, parent=tree.root)

# Add child to node
def add_node_to_parent(tree, id, val):
    par = (anytree.find(tree, filter_=lambda node: ("x"+str(node.name)+"x") in ("x"+str(id)+"x"))) # Not entirely sure how the lambda stuff here works, but it does ¯\_(ツ)_/¯
    add = anytree.Node(val, parent=par)

# Clone within node
def add_node_to_level(tree,id, val): # Broken, likely useless, probably remove later
    npar = get_parent(tree, id)
    par = (anytree.find(tree, filter_=lambda node: ("x"+str(node.name)+"x") in ("x"+str(npar)+"x")))
    add = anytree.Node(val, parent=par)

# Remove node from tree
def remove_node(tree, id):
    par = (anytree.find(tree, filter_=lambda node: ("x"+str(node.name)+"x") in ("x"+str(id)+"x")))
    par.parent = None
    print(par)

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

# Return only the first branch of children
def return_current_children(tree, id):
    children = list(return_children(tree,id))
    cchildren = []
    par = (anytree.find(tree, filter_=lambda node: ("x"+str(node.name)+"x") in ("x"+str(id)+"x")))
    index = 0
    for child in anytree.PreOrderIter(par):
        if index != 0:
            schildren = return_children(tree, child.name)
            if len(schildren) > 0:
                schildren.remove(schildren[0])
            print(schildren)
            for item in schildren:
                if item in children:
                    children.remove(item)
        index += 1
    children.remove(id)
    return (children)

# Get current overlay
def get_overlay():
    coverlay = open("/etc/astpk.d/astpk-coverlay","r")
    overlay = coverlay.readline()
    coverlay.close()
    overlay = overlay.replace('\n',"")
    return(overlay)

# Get drive partition
def get_part():
    cpart = open("/etc/astpk.d/astpk-part","r")
    part = cpart.readline()
    part = part.replace('\n',"")
    cpart.close()
    return(part)

# Get tmp partition state
def get_tmp():
    mount = str(subprocess.check_output("mount | grep 'on / type'", shell=True)) # Maybe not ideal? idk might fix(?) sometime
    if "tmp0" in mount:
        return("tmp0")
    else:
        return("tmp")


# Deploy image
def deploy(overlay):
    if not (os.path.exists(f"/.overlays/overlay-{overlay}")):
        print("cannot deploy, overlay doesn't exist")
    else:
        update_boot(overlay)
        tmp = get_tmp()
        os.system(f"btrfs sub set-default /.overlays/overlay-{tmp} >/dev/null 2>&1") # Set default volume
        untmp()
        if "tmp0" in tmp:
            tmp = "tmp"
        else:
            tmp = "tmp0"
        etc = overlay
        os.system(f"btrfs sub snap /.overlays/overlay-{overlay} /.overlays/overlay-{tmp} >/dev/null 2>&1")
        os.system(f"btrfs sub snap /.etc/etc-{overlay} /.etc/etc-{tmp} >/dev/null 2>&1")
        os.system(f"btrfs sub create /.var/var-{tmp} >/dev/null 2>&1")
        os.system(f"cp --reflink=auto -r /.var/var-{etc}/* /.var/var-{tmp} >/dev/null 2>&1")
        os.system(f"btrfs sub snap /.boot/boot-{overlay} /.boot/boot-{tmp} >/dev/null 2>&1")
        os.system(f"mkdir /.overlays/overlay-{tmp}/etc >/dev/null 2>&1")
        os.system(f"rm -rf /.overlays/overlay-{tmp}/var >/dev/null 2>&1")
        os.system(f"mkdir /.overlays/overlay-{tmp}/boot >/dev/null 2>&1")
        os.system(f"cp --reflink=auto -r /.etc/etc-{etc}/* /.overlays/overlay-{tmp}/etc >/dev/null 2>&1")
        os.system(f"btrfs sub snap /var /.overlays/overlay-{tmp}/var >/dev/null 2>&1")
        os.system(f"cp --reflink=auto -r /.boot/boot-{etc}/* /.overlays/overlay-{tmp}/boot >/dev/null 2>&1")
        os.system(f"echo '{overlay}' > /.overlays/overlay-{tmp}/etc/astpk.d/astpk-coverlay")
        os.system(f"echo '{etc}' > /.overlays/overlay-{tmp}/etc/astpk.d/astpk-cetc")
        os.system(f"echo '{overlay}' > /.etc/etc-{tmp}/astpk.d/astpk-coverlay")
        os.system(f"echo '{etc}' > /.etc/etc-{tmp}/astpk.d/astpk-cetc")
        switchtmp()
        #os.system(f"rm -rf /var/lib/pacman/* >/dev/null 2>&1") # Clean pacman and systemd directories before copy
        os.system(f"rm -rf /var/lib/systemd/* >/dev/null 2>&1")
        os.system(f"rm -rf /.overlays/overlay-{tmp}/var/lib/systemd/* >/dev/null 2>&1")
        #os.system(f"rm -rf /.overlays/overlay-{tmp}/var/lib/pacman/* >/dev/null 2>&1")
        os.system(f"cp --reflink=auto -r /.var/var-{etc}/* /.overlays/overlay-{tmp}/var/ >/dev/null 2>&1")
        #os.system(f"cp --reflink=auto -r /.var/var-{etc}/lib/pacman/* /var/lib/pacman/ >/dev/null 2>&1") # Copy pacman and systemd directories
        os.system(f"cp --reflink=auto -r /.var/var-{etc}/lib/systemd/* /var/lib/systemd/ >/dev/null 2>&1")
        #os.system(f"cp --reflink=auto -r /.var/var-{etc}/lib/pacman/* /.overlays/overlay-{tmp}/var/lib/pacman/")
        os.system(f"cp --reflink=auto -r /.var/var-{etc}/lib/systemd/* /.overlays/overlay-{tmp}/var/lib/systemd/ >/dev/null 2>&1")
        os.system(f"btrfs sub set-default /.overlays/overlay-{tmp}") # Set default volume
        #os.system(f"chattr -RV +i /.overlays/overlay-{tmp}/usr > /dev/null 2>&1")
        print(f"{overlay} was deployed to /")

# Add node to branch
def extend_branch(overlay):
    if not (os.path.exists(f"/.overlays/overlay-{overlay}")):
        print("cannot branch, overlay doesn't exist")
    else:
        i = findnew()
        os.system(f"btrfs sub snap -r /.overlays/overlay-{overlay} /.overlays/overlay-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.etc/etc-{overlay} /.etc/etc-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.var/var-{overlay} /.var/var-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.boot/boot-{overlay} /.boot/boot-{i} >/dev/null 2>&1")
        add_node_to_parent(fstree,overlay,i)
        write_tree(fstree)
        print(f"branch {i} added to {overlay}")

# Clone branch under same parent,
def clone_branch(overlay):
    if not (os.path.exists(f"/.overlays/overlay-{overlay}")):
        print("cannot clone, overlay doesn't exist")
    else:
        i = findnew()
        os.system(f"btrfs sub snap -r /.overlays/overlay-{overlay} /.overlays/overlay-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.etc/etc-{overlay} /.etc/etc-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.var/var-{overlay} /.var/var-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.boot/boot-{overlay} /.boot/boot-{i} >/dev/null 2>&1")
        add_node_to_level(fstree,overlay,i)
        write_tree(fstree)
        desc = str(f"clone of {overlay}")
        write_desc(i, desc)
        print(f"branch {i} added to parent of {overlay}")

# Clone under specified parent
def clone_under(overlay, branch):
    if not (os.path.exists(f"/.overlays/overlay-{overlay}")) or (not(os.path.exists(f"/.overlays/overlay-{branch}"))):
        print("cannot clone, overlay doesn't exist")
    else:
        i = findnew()
        os.system(f"btrfs sub snap -r /.overlays/overlay-{branch} /.overlays/overlay-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.etc/etc-{branch} /.etc/etc-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.var/var-{branch} /.var/var-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.boot/boot-{branch} /.boot/boot-{i} >/dev/null 2>&1")
        add_node_to_parent(fstree,overlay,i)
        write_tree(fstree)
        desc = str(f"clone of {overlay}")
        write_desc(i, desc)
        print(f"branch {i} added to {overlay}")

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
    if not (os.path.exists(f"/.overlays/overlay-{treename}")):
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
    if not (os.path.exists(f"/.overlays/overlay-{treename}")):
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
            prepare(sarg)
            os.system(f"chroot /.overlays/overlay-chr{sarg} pacman --noconfirm -Syyu")
            posttrans(sarg)
        print(f"tree {treename} was updated")

# Recursively run an update in tree
def run_tree(tree,treename,cmd):
    if not (os.path.exists(f"/.overlays/overlay-{treename}")):
        print("cannot update, tree doesn't exist")
    else:
        prepare(treename)
        os.system(f"chroot /.overlays/overlay-chr{treename} {cmd}")
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
            os.system(f"chroot /.overlays/overlay-chr{sarg} {cmd}")
            posttrans(sarg)
        print(f"tree {treename} was updated")


# Sync tree and all it's overlays
def sync_tree(tree,treename):
    if not (os.path.exists(f"/.overlays/overlay-{treename}")):
        print("cannot sync, tree doesn't exist")
    else:
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
            #os.system(f"cp --reflink=auto -r /.var/var-{arg}/lib/pacman/local/* /.overlays/overlay-chr{sarg}/var/lib/pacman/local/ >/dev/null 2>&1")
            os.system(f"cp --reflink=auto -r /.var/var-{arg}/lib/systemd/* /.overlays/overlay-chr{sarg}/var/lib/systemd/ >/dev/null 2>&1")
            os.system(f"cp --reflink=auto -n -r /.overlays/overlay-{arg}/* /.overlays/overlay-chr{sarg}/ >/dev/null 2>&1")
            posttrans(sarg)
        print(f"tree {treename} was synced")

# Clone tree
def clone_as_tree(overlay):
    if not (os.path.exists(f"/.overlays/overlay-{overlay}")):
        print("cannot clone, overlay doesn't exist")
    else:
        i = findnew()
        os.system(f"btrfs sub snap -r /.overlays/overlay-{overlay} /.overlays/overlay-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.etc/etc-{overlay} /.etc/etc-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.var/var-{overlay} /.var/var-{i} >/dev/null 2>&1")
        os.system(f"btrfs sub snap -r /.boot/boot-{overlay} /.boot/boot-{i} >/dev/null 2>&1")
        append_base_tree(fstree,i)
        write_tree(fstree)
        desc = str(f"clone of {overlay}")
        write_desc(i, desc)
        print(f"tree {i} cloned from {overlay}")

# Creates new tree from base file
def new_overlay():
    i = findnew()
    os.system(f"btrfs sub snap -r /.overlays/overlay-0 /.overlays/overlay-{i} >/dev/null 2>&1")
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

# Re-deploys current image, saves changes made to /etc to image
def update_etc():
    tmp = get_tmp()
    prepare(tmp)
    overlay = get_overlay()
    posttrans(overlay)
    deploy(overlay)

# Update boot
def update_boot(overlay):
    if not (os.path.exists(f"/.overlays/overlay-{overlay}")):
        print("cannot update boot, overlay doesn't exist")
    else:
        tmp = get_tmp()
        part = get_part()
        prepare(overlay)
        os.system(f"chroot /.overlays/overlay-chr{overlay} grub-mkconfig {part} -o /boot/grub/grub.cfg")
        os.system(f"chroot /.overlays/overlay-chr{overlay} sed -i s,overlay-chr{overlay},overlay-{tmp},g /boot/grub/grub.cfg")
        posttrans(overlay)

# Chroot into overlay
def chroot(overlay):
    if not (os.path.exists(f"/.overlays/overlay-{overlay}")):
        print("cannot chroot, overlay doesn't exist")
    elif overlay == "0":
        print("changing base image is not allowed")
    else:
        prepare(overlay)
        os.system(f"chroot /.overlays/overlay-chr{overlay}") # Arch specific chroot command because pacman is weird without it
        posttrans(overlay)

# Run command in snapshot
def chrrun(overlay,cmd):
    if not (os.path.exists(f"/.overlays/overlay-{overlay}")):
        print("cannot chroot, overlay doesn't exist")
    elif overlay == "0":
        print("changing base image is not allowed")
    else:
        prepare(overlay)
        os.system(f"chroot /.overlays/overlay-chr{overlay} {cmd}") # Arch specific chroot command because pacman is weird without it
        posttrans(overlay)

# Clean chroot mount dirs
def unchr(overlay):
    os.system(f"btrfs sub del /.etc/etc-chr{overlay} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.var/var-chr{overlay} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.boot/boot-chr{overlay} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.overlays/overlay-chr{overlay}/* >/dev/null 2>&1")
    os.system(f"btrfs sub del /.overlays/overlay-chr{overlay} >/dev/null 2>&1")

# Clean tmp dirs
def untmp():
    tmp = get_tmp()
    if "tmp0" in tmp:
        tmp = "tmp"
    else:
        tmp = "tmp0"
    os.system(f"btrfs sub del /.overlays/overlay-{tmp}/* >/dev/null 2>&1")
    os.system(f"btrfs sub del /.overlays/overlay-{tmp} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.etc/etc-{tmp} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.var/var-{tmp} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.boot/boot-{tmp} >/dev/null 2>&1")

# Install live
def live_install(pkg):
    tmp = get_tmp()
    part = get_part()
    #os.system(f"chattr -RV -i /.overlays/overlay-{tmp}/usr > /dev/null 2>&1")
    os.system(f"mount --bind /.overlays/overlay-{tmp} /.overlays/overlay-{tmp} > /dev/null 2>&1")
    os.system(f"mount --bind /home /.overlays/overlay-{tmp}/home > /dev/null 2>&1")
    os.system(f"mount --bind /var /.overlays/overlay-{tmp}/var > /dev/null 2>&1")
    os.system(f"mount --bind /etc /.overlays/overlay-{tmp}/etc > /dev/null 2>&1")
    os.system(f"mount --bind /tmp /.overlays/overlay-{tmp}/tmp > /dev/null 2>&1")
    os.system(f"arch-chroot /.overlays/overlay-{tmp} pacman -S  --overwrite \\* --noconfirm {pkg}")
    os.system(f"umount /.overlays/overlay-{tmp}/* > /dev/null 2>&1")
    os.system(f"umount /.overlays/overlay-{tmp} > /dev/null 2>&1")
    #os.system(f"chattr -RV +i /.overlays/overlay-{tmp}/usr > /dev/null 2>&1")

# Live unlocked shell
def live_unlock():
    tmp = get_tmp()
    part = get_part()
    #os.system(f"chattr -RV -i /.overlays/overlay-{tmp}/usr > /dev/null 2>&1")
    os.system(f"mount --bind /.overlays/overlay-{tmp} /.overlays/overlay-{tmp} > /dev/null 2>&1")
    os.system(f"mount --bind /home /.overlays/overlay-{tmp}/home > /dev/null 2>&1")
    os.system(f"mount --bind /var /.overlays/overlay-{tmp}/var > /dev/null 2>&1")
    os.system(f"mount --bind /etc /.overlays/overlay-{tmp}/etc > /dev/null 2>&1")
    os.system(f"mount --bind /tmp /.overlays/overlay-{tmp}/tmp > /dev/null 2>&1")
    os.system(f"arch-chroot /.overlays/overlay-{tmp}")
    os.system(f"umount /.overlays/overlay-{tmp}/* > /dev/null 2>&1")
    os.system(f"umount /.overlays/overlay-{tmp} > /dev/null 2>&1")
    #os.system(f"chattr -RV +i /.overlays/overlay-{tmp}/usr > /dev/null 2>&1")

# Install packages
def install(overlay,pkg):
    if not (os.path.exists(f"/.overlays/overlay-{overlay}")):
        print("cannot install, overlay doesn't exist")
    elif overlay == "0":
        print("changing base image is not allowed")
    else:
        prepare(overlay)
        os.system(f"chroot /.overlays/overlay-chr{overlay} pacman -S {pkg}") 
        posttrans(overlay)

# Remove packages
def remove(overlay,pkg):
    if not (os.path.exists(f"/.overlays/overlay-{overlay}")):
        print("cannot remove, overlay doesn't exist")
    elif overlay == "0":
        print("changing base image is not allowed")
    else:
        prepare(overlay)
        os.system(f"chroot /.overlays/overlay-chr{overlay} pacman --noconfirm -Rns {pkg}")
        posttrans(overlay)

# Pass arguments to pacman
def pac(overlay,arg):
    if not (os.path.exists(f"/.overlays/overlay-{overlay}")):
        print("cannot run pacman, overlay doesn't exist")
    elif overlay == "0":
        print("changing base image is not allowed")
    else:
        prepare(overlay)
        os.system(f"chroot /.overlays/overlay-chr{overlay} pacman {arg}")
        posttrans(overlay)

# Delete tree or branch
def delete(overlay):
    print(f"Are you sure you want to delete overlay {overlay}? (y/N)")
    choice = input("> ")
    run = True
    if choice.casefold() != "y":
        print("Aborted")
        run = False
    if not (os.path.exists(f"/.overlays/overlay-{overlay}")):
        print("cannot delete, tree doesn't exist")
    elif overlay == "0":
        print("changing base image is not allowed")
    elif run == True:
        children = return_children(fstree,overlay)
        os.system(f"btrfs sub del /.boot/boot-{overlay} >/dev/null 2>&1")
        os.system(f"btrfs sub del /.etc/etc-{overlay} >/dev/null 2>&1")
        os.system(f"btrfs sub del /.var/var-{overlay} >/dev/null 2>&1")
        os.system(f"btrfs sub del /.overlays/overlay-{overlay}")
        for child in children: # This deletes the node itself along with it's children
            os.system(f"btrfs sub del /.boot/boot-{child} >/dev/null 2>&1")
            os.system(f"btrfs sub del /.etc/etc-{child} >/dev/null 2>&1")
            os.system(f"btrfs sub del /.var/var-{child} >/dev/null 2>&1")
            os.system(f"btrfs sub del /.overlays/overlay-{child} >/dev/null 2>&1")
        remove_node(fstree,overlay) # Remove node from tree or root
        write_tree(fstree)
        print(f"overlay {overlay} removed")


# Update base
def update_base():
    prepare("0")
    os.system(f"chroot /.overlays/overlay-chr0 pacman -Syyu")
    posttrans("0")

def get_efi():
    if os.path.exists("/sys/firmware/efi"):
        efi = True
    else:
        efi = False
    return(efi)

# Prepare overlay to chroot dir to install or chroot into
def prepare(overlay):
    unchr(overlay)
    part = get_part()
    etc = overlay
    os.system(f"btrfs sub snap /.overlays/overlay-{overlay} /.overlays/overlay-chr{overlay} >/dev/null 2>&1")
    os.system(f"btrfs sub snap /.etc/etc-{overlay} /.etc/etc-chr{overlay} >/dev/null 2>&1")
    os.system(f"mkdir -p /.var/var-chr{overlay} >/dev/null 2>&1")
    os.system(f"mount --bind /.overlays/overlay-chr{overlay} /.overlays/overlay-chr{overlay} >/dev/null 2>&1") # Pacman gets weird when chroot directory is not a mountpoint, so this unusual mount is necessary
    os.system(f"mount --bind /var /.overlays/overlay-chr{overlay}/var >/dev/null 2>&1")
    os.system(f"mount --rbind /dev /.overlays/overlay-chr{overlay}/dev >/dev/null 2>&1")
    os.system(f"mount --rbind /sys /.overlays/overlay-chr{overlay}/sys >/dev/null 2>&1")
    os.system(f"mount --rbind /tmp /.overlays/overlay-chr{overlay}/tmp >/dev/null 2>&1")
    os.system(f"mount --rbind /proc /.overlays/overlay-chr{overlay}/proc >/dev/null 2>&1")
    #os.system(f"chmod 0755 /.overlays/overlay-chr/var >/dev/null 2>&1") # For some reason the permission needs to be set here
    os.system(f"btrfs sub snap /.boot/boot-{overlay} /.boot/boot-chr{overlay} >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.etc/etc-chr{overlay}/* /.overlays/overlay-chr{overlay}/etc >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.boot/boot-chr{overlay}/* /.overlays/overlay-chr{overlay}/boot >/dev/null 2>&1")
    #os.system(f"rm -rf /.overlays/overlay-chr{overlay}/var/lib/pacman/* >/dev/null 2>&1")
    os.system(f"rm -rf /.overlays/overlay-chr{overlay}/var/lib/systemd/* >/dev/null 2>&1")
    #os.system(f"cp -r --reflink=auto /.var/var-{overlay}/lib/pacman/* /.overlays/overlay-chr{overlay}/var/lib/pacman/ >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.var/var-{overlay}/lib/systemd/* /.overlays/overlay-chr{overlay}/var/lib/systemd/ >/dev/null 2>&1")
    os.system(f"mount --bind /home /.overlays/overlay-chr{overlay}/home >/dev/null 2>&1")
    os.system(f"mount --rbind /run /.overlays/overlay-chr{overlay}/run >/dev/null 2>&1")
    os.system(f"cp /etc/machine-id /.overlays/overlay-chr{overlay}/etc/machine-id")
    os.system(f"mount --bind /etc/resolv.conf /.overlays/overlay-chr{overlay}/etc/resolv.conf >/dev/null 2>&1")


# Post transaction function, copy from chroot dirs back to read only image dir
def posttrans(overlay):
    etc = overlay
    tmp = get_tmp()
    os.system(f"umount /.overlays/overlay-chr{overlay} >/dev/null 2>&1")
    os.system(f"umount /.overlays/overlay-chr{overlay}/etc/resolv.conf >/dev/null 2>&1")
    os.system(f"umount /.overlays/overlay-chr{overlay}/home >/dev/null 2>&1")
    os.system(f"umount /.overlays/overlay-chr{overlay}/run >/dev/null 2>&1")
    os.system(f"umount /.overlays/overlay-chr{overlay}/dev >/dev/null 2>&1")
    os.system(f"umount /.overlays/overlay-chr{overlay}/sys >/dev/null 2>&1")
    os.system(f"umount /.overlays/overlay-chr{overlay}/proc >/dev/null 2>&1")
    os.system(f"btrfs sub del /.overlays/overlay-{overlay} >/dev/null 2>&1")
    os.system(f"rm -rf /.etc/etc-chr{overlay}/* >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.overlays/overlay-chr{overlay}/etc/* /.etc/etc-chr{overlay} >/dev/null 2>&1")
    os.system(f"rm -rf /.var/var-chr{overlay}/* >/dev/null 2>&1")
    os.system(f"mkdir -p /.var/var-chr{overlay}/lib/systemd >/dev/null 2>&1")
    #os.system(f"mkdir -p /.var/var-chr{overlay}/lib/pacman >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.overlays/overlay-chr{overlay}/var/lib/systemd/* /.var/var-chr{overlay}/lib/systemd >/dev/null 2>&1")
    #os.system(f"cp -r --reflink=auto /.overlays/overlay-chr{overlay}/var/lib/pacman/* /.var/var-chr{overlay}/lib/pacman >/dev/null 2>&1")
    os.system(f"cp -r -n --reflink=auto /.overlays/overlay-chr{overlay}/var/cache/pacman/pkg/* /var/cache/pacman/pkg/ >/dev/null 2>&1")
    os.system(f"rm -rf /.boot/boot-chr{overlay}/* >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.overlays/overlay-chr{overlay}/boot/* /.boot/boot-chr{overlay} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.etc/etc-{etc} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.var/var-{etc} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.boot/boot-{etc} >/dev/null 2>&1")
    os.system(f"btrfs sub snap -r /.etc/etc-chr{overlay} /.etc/etc-{etc} >/dev/null 2>&1")
    os.system(f"btrfs sub create /.var/var-{etc} >/dev/null 2>&1")
    os.system(f"mkdir -p /.var/var-{etc}/lib/systemd >/dev/null 2>&1")
    #os.system(f"mkdir -p /.var/var-{etc}/lib/pacman >/dev/null 2>&1")
    os.system(f"cp --reflink=auto -r /.var/var-chr{overlay}/lib/systemd/* /.var/var-{etc}/lib/systemd >/dev/null 2>&1")
    #os.system(f"cp --reflink=auto -r /.var/var-chr{overlay}/lib/pacman/* /.var/var-{etc}/lib/pacman >/dev/null 2>&1")
    #os.system(f"rm -rf /var/lib/pacman/* >/dev/null 2>&1")
    #os.system(f"cp --reflink=auto -r /.overlays/overlay-{tmp}/var/lib/pacman/* /var/lib/pacman >/dev/null 2>&1")
    os.system(f"rm -rf /var/lib/systemd/* >/dev/null 2>&1")
    os.system(f"cp --reflink=auto -r /.overlays/overlay-{tmp}/var/lib/systemd/* /var/lib/systemd >/dev/null 2>&1")
    #os.system(f"cp --reflink=auto -r -n /.overlays/overlay-chr{overlay}/var/lib/* /var/lib/ >/dev/null 2>&1")
    #os.system(f"cp --reflink=auto -r -n /.overlays/overlay-chr{overlay}/var/games/* /var/games/ >/dev/null 2>&1")
    os.system(f"btrfs sub snap -r /.overlays/overlay-chr{overlay} /.overlays/overlay-{overlay} >/dev/null 2>&1")
#    os.system(f"btrfs sub snap -r /.var/var-chr{overlay} /.var/var-{etc} >/dev/null 2>&1")
    os.system(f"btrfs sub snap -r /.boot/boot-chr{overlay} /.boot/boot-{etc} >/dev/null 2>&1")
    unchr(overlay)

# Upgrade overlay
def upgrade(overlay):
    if not (os.path.exists(f"/.overlays/overlay-{overlay}")):
        print("cannot upgrade, overlay doesn't exist")
    elif overlay == "0":
        print("changing base image is not allowed")
    else:
        prepare(overlay)
        os.system(f"chroot /.overlays/overlay-chr{overlay} pacman -Syyu")
        posttrans(overlay)

# Noninteractive update
def autoupgrade(overlay):
    clone_as_tree(overlay)
    prepare(overlay)
    excode = str(os.system(f"chroot /.overlays/overlay-chr{overlay} pacman --noconfirm -Syyu"))
    if excode != "127":
        posttrans(overlay)
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
            if str("/.overlays btrfs") in str(line):
                chroot = False
    return(chroot)

# Rollback last booted deployment
def rollback():
    tmp = get_tmp()
    i = findnew()
    clone_as_tree(tmp)
    write_desc(i, "rollback")
    deploy(i)

# Switch between /tmp deployments !!! Reboot after this function !!!
def switchtmp():
    mount = get_tmp()
    part = get_part()
    # This part is useless? Dumb stuff
    if "tmp0" in mount:
        tmp = "tmp"
    else:
        tmp = "tmp0"
    # ---
    os.system(f"mkdir /etc/mnt >/dev/null 2>&1")
    os.system(f"mkdir /etc/mnt/boot >/dev/null 2>&1")
    os.system(f"mount {part} -o subvol=@boot /etc/mnt/boot >/dev/null 2>&1") # Mount boot partition for writing
    if "tmp0" in mount:
        os.system("cp --reflink=auto -r /.overlays/overlay-tmp/boot/* /etc/mnt/boot")
        os.system("sed -i 's,@.overlays/overlay-tmp0,@.overlays/overlay-tmp,g' /etc/mnt/boot/grub/grub.cfg") # Overwrite grub config boot subvolume
        os.system("sed -i 's,@.overlays/overlay-tmp0,@.overlays/overlay-tmp,g' /.overlays/overlay-tmp/boot/grub/grub.cfg")
        os.system("sed -i 's,@.overlays/overlay-tmp0,@.overlays/overlay-tmp,g' /.overlays/overlay-tmp/etc/fstab") # Write fstab for new deployment
        os.system("sed -i 's,@.etc/etc-tmp0,@.etc/etc-tmp,g' /.overlays/overlay-tmp/etc/fstab")
#        os.system("sed -i 's,@.var/var-tmp0,@.var/var-tmp,g' /.overlays/overlay-tmp/etc/fstab")
        os.system("sed -i 's,@.boot/boot-tmp0,@.boot/boot-tmp,g' /.overlays/overlay-tmp/etc/fstab")
    else:
        os.system("cp --reflink=auto -r /.overlays/overlay-tmp0/boot/* /etc/mnt/boot")
        os.system("sed -i 's,@.overlays/overlay-tmp,@.overlays/overlay-tmp0,g' /etc/mnt/boot/grub/grub.cfg")
        os.system("sed -i 's,@.overlays/overlay-tmp,@.overlays/overlay-tmp0,g' /.overlays/overlay-tmp0/boot/grub/grub.cfg")
        os.system("sed -i 's,@.overlays/overlay-tmp,@.overlays/overlay-tmp0,g' /.overlays/overlay-tmp0/etc/fstab")
        os.system("sed -i 's,@.etc/etc-tmp,@.etc/etc-tmp0,g' /.overlays/overlay-tmp0/etc/fstab")
#        os.system("sed -i 's,@.var/var-tmp,@.var/var-tmp0,g' /.overlays/overlay-tmp0/etc/fstab")
        os.system("sed -i 's,@.boot/boot-tmp,@.boot/boot-tmp0,g' /.overlays/overlay-tmp0/etc/fstab")
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
    if "overlay-tmp0" in gconf:
        gconf = gconf.replace("overlay-tmp0","overlay-tmp")
    else:
        gconf = gconf.replace("overlay-tmp", "overlay-tmp0")
    if "astOS Linux" in gconf:
        gconf = gconf.replace("astOS Linux","astOS last booted deployment")
    grubconf.close()
    os.system("sed -i '$ d' /etc/mnt/boot/grub/grub.cfg")
    grubconf = open("/etc/mnt/boot/grub/grub.cfg", "a")
    grubconf.write(gconf)
    grubconf.write("}\n")
    grubconf.write("### END /etc/grub.d/41_custom ###")
    grubconf.close()

    grubconf = open("/.overlays/overlay-tmp0/boot/grub/grub.cfg","r")
    line = grubconf.readline()
    while "BEGIN /etc/grub.d/10_linux" not in line:
        line = grubconf.readline()
    line = grubconf.readline()
    gconf = str("")
    while "}" not in line:
        gconf = str(gconf)+str(line)
        line = grubconf.readline()
    if "overlay-tmp0" in gconf:
        gconf = gconf.replace("overlay-tmp0","overlay-tmp")
    else:
        gconf = gconf.replace("overlay-tmp", "overlay-tmp0")
    if "astOS Linux" in gconf:
        gconf = gconf.replace("astOS Linux","astOS last booted deployment")
    grubconf.close()
    os.system("sed -i '$ d' /.overlays/overlay-tmp0/boot/grub/grub.cfg")
    grubconf = open("/.overlays/overlay-tmp0/boot/grub/grub.cfg", "a")
    grubconf.write(gconf)
    grubconf.write("}\n")
    grubconf.write("### END /etc/grub.d/41_custom ###")
    grubconf.close()


    #
    os.system("umount /etc/mnt/boot >/dev/null 2>&1")

# Clear all temporary snapshots
def tmpclear():
    os.system(f"btrfs sub del /.etc/etc-chr* >/dev/null 2>&1")
    os.system(f"btrfs sub del /.var/var-chr* >/dev/null 2>&1")
    os.system(f"btrfs sub del /.boot/boot-chr* >/dev/null 2>&1")
    os.system(f"btrfs sub del /.overlays/overlay-chr*/* >/dev/null 2>&1")
    os.system(f"btrfs sub del /.overlays/overlay-chr* >/dev/null 2>&1")

# Find new unused image dir
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

# Main function
def main(args):
    overlay = get_overlay() # Get current overlay
    etc = overlay
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
            new_overlay()
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
            coverlay = args_2[0]
            args_2.remove(args_2[0])
            install(coverlay, str(" ").join(args_2))
            if live:
                live_install(str(" ").join(args_2))
            ast_unlock()
        elif arg == "run" and (lock != True):
            ast_lock()
            args_2 = args
            args_2.remove(args_2[0])
            args_2.remove(args_2[0])
            coverlay = args_2[0]
            args_2.remove(args_2[0])
            chrrun(coverlay, str(" ").join(args_2))
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
            print(overlay)
        elif arg == "rm-overlay" or arg == "del":
            delete(args[args.index(arg)+1])
        elif arg == "remove" and (lock != True):
            args_2 = args
            args_2.remove(args_2[0])
            args_2.remove(args_2[0])
            coverlay = args_2[0]
            args_2.remove(args_2[0])
            remove(coverlay, str(" ").join(args_2))
            ast_unlock()
        elif arg == "pac" or arg == "p" and (lock != True):
            ast_lock()
            args_2 = args
            args_2.remove(args_2[0])
            args_2.remove(args_2[0])
            coverlay = args_2[0]
            args_2.remove(args_2[0])
            pac(coverlay, str(" ").join(args_2))
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
            sync_tree(fstree,args[args.index(arg)+1])
            ast_unlock()
        elif arg == "auto-upgrade" and (lock != True):
            ast_lock()
            autoupgrade(overlay)
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
            coverlay = args_2[0]
            args_2.remove(args_2[0])
            run_tree(fstree, coverlay, str(" ").join(args_2))
            ast_unlock()
        elif arg == "tree-rmpkg" or arg == "tremove" and (lock != True):
            ast_lock()
            args_2 = args
            args_2.remove(args_2[0])
            args_2.remove(args_2[0])
            coverlay = args_2[0]
            args_2.remove(args_2[0])
            remove(coverlay, str(" ").join(args_2))
            remove_from_tree(fstree, coverlay, str(" ").join(args_2))
            ast_unlock()
        elif arg  == "tree":
            show_fstree()
        elif (lock == True):
            print("Error, ast is locked. To force unlock use 'rm -rf /var/astpk/lock'.")
            break
        elif (arg == args[1]):
            print("Operation not found.")

# Call main (duh)
main(args)
