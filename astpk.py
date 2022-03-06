#!/usr/bin/python3
import os
import sys
import ast # Heh funny name coincidence with project name
import subprocess
from anytree.importer import DictImporter
from anytree.exporter import DictExporter
import anytree
import os

args = list(sys.argv)


# TODO ------------
# Make delete recursive
# Test EFI
# General code cleanup
# Handle bootloader updates better
# Test and improve image building, fix meaningless errors on output, clean up code, add more comments to code.
# Add documentation, improve /etc merges (currently unhandled), make the tree sync write less data maybe?
# Make trees sync recursively
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

# Reverse tmp deploy image
def rdeploy(overlay):
    tmp = get_tmp()
    if "tmp0" in tmp:
        tmp = "tmp"
    else:
        tmp = "tmp0"
    os.system(f"btrfs sub set-default /.overlays/overlay-{tmp} >/dev/null 2>&1")  # Set default volume
    untmp()
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
    rswitchtmp()
    os.system(f"rm -rf /var/lib/pacman/* >/dev/null 2>&1") # Clean pacman and systemd directories before copy
    os.system(f"rm -rf /var/lib/systemd/* >/dev/null 2>&1")
    os.system(f"cp --reflink=auto -r /.var/var-{etc}/* /.overlays/overlay-{tmp}/var/ >/dev/null 2>&1")
    os.system(f"cp --reflink=auto -r /.var/var-{etc}/lib/pacman/* /var/lib/pacman/ >/dev/null 2>&1") # Copy pacman and systemd directories
    os.system(f"cp --reflink=auto -r /.var/var-{etc}/lib/systemd/* /var/lib/systemd/ >/dev/null 2>&1")
    print(f"/ was rolled back to {overlay}")



# Deploy image
def deploy(overlay):
    if not (os.path.exists(f"/.overlays/overlay-{overlay}")):
        print("cannot deploy, overlay doesn't exist")
    else:
        tmp = get_tmp()
        untmp()
#    unchr()
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
#    update_boot(overlay)
        switchtmp()
        os.system(f"rm -rf /var/lib/pacman/* >/dev/null 2>&1") # Clean pacman and systemd directories before copy
        os.system(f"rm -rf /var/lib/systemd/* >/dev/null 2>&1")
        os.system(f"cp --reflink=auto -r /.var/var-{etc}/* /.overlays/overlay-{tmp}/var/ >/dev/null 2>&1")
        os.system(f"cp --reflink=auto -r /.var/var-{etc}/lib/pacman/* /var/lib/pacman/ >/dev/null 2>&1") # Copy pacman and systemd directories
        os.system(f"cp --reflink=auto -r /.var/var-{etc}/lib/systemd/* /var/lib/systemd/ >/dev/null 2>&1")
        os.system(f"btrfs sub set-default /.overlays/overlay-{tmp} >/dev/null 2>&1") # Set default volume
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

# Recursivly run an update in tree
def update_tree(tree,treename):
    if not (os.path.exists(f"/.overlays/overlay-{treename}")):
        print("cannot update, tree doesn't exist")
    else:
        unchr()
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
            os.system(f"btrfs sub snap /.overlays/overlay-{sarg} /.overlays/overlay-chr >/dev/null 2>&1")
            os.system(f"btrfs sub snap /.var/var-{sarg} /.var/var-chr >/dev/null 2>&1")
            os.system(f"btrfs sub snap /.boot/boot-{sarg} /.boot/boot-chr >/dev/null 2>&1")
            os.system(f"cp --reflink=auto -r /.var/var-{arg}/lib/pacman/local/* /.var/var-chr/lib/pacman/local/ >/dev/null 2>&1")
            os.system(f"cp --reflink=auto -r /.var/var-{arg}/lib/systemd/* /.var/var-chr/lib/systemd/ >/dev/null 2>&1")
            os.system(f"cp --reflink=auto -r /.overlays/overlay-{arg}/* /.overlays/overlay-chr/ >/dev/null 2>&1")
            os.system(f"arch-chroot /mnt pacman -Syyu")
            os.system(f"btrfs sub del /.overlays/overlay-{sarg} >/dev/null 2>&1")
            os.system(f"btrfs sub del /.var/var-{sarg}  >/dev/null 2>&1")
            os.system(f"btrfs sub del /.boot/boot-{sarg} >/dev/null 2>&1")
            os.system(f"btrfs sub snap -r /.overlays/overlay-chr /.overlays/overlay-{sarg} >/dev/null 2>&1")
            os.system(f"btrfs sub snap -r /.var/var-chr /.var/var-{sarg} >/dev/null 2>&1")
            os.system(f"btrfs sub snap -r /.boot/boot-chr /.boot/boot-{sarg} >/dev/null 2>&1")
            os.system(f"btrfs sub del /.overlays/overlay-chr >/dev/null 2>&1")
            os.system(f"btrfs sub del /.var/var-chr >/dev/null 2>&1")
            os.system(f"btrfs sub del /.boot/boot-chr >/dev/null 2>&1")
            print(f"tree {treename} was updated")

# Sync tree and all it's overlays
def sync_tree(tree,treename):
    if not (os.path.exists(f"/.overlays/overlay-{treename}")):
        print("cannot sync, tree doesn't exist")
    else:
        unchr()
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
            os.system(f"btrfs sub snap /.overlays/overlay-{sarg} /.overlays/overlay-chr >/dev/null 2>&1")
            os.system(f"btrfs sub snap /.var/var-{sarg} /.var/var-chr >/dev/null 2>&1")
            os.system(f"btrfs sub snap /.boot/boot-{sarg} /.boot/boot-chr >/dev/null 2>&1")
            os.system(f"cp --reflink=auto -r /.var/var-{arg}/lib/pacman/local/* /.var/var-chr/lib/pacman/local/ >/dev/null 2>&1")
            os.system(f"cp --reflink=auto -r /.var/var-{arg}/lib/systemd/* /.var/var-chr/lib/systemd/ >/dev/null 2>&1")
            os.system(f"cp --reflink=auto -r /.overlays/overlay-{arg}/* /.overlays/overlay-chr/ >/dev/null 2>&1")
            os.system(f"btrfs sub del /.overlays/overlay-{sarg} >/dev/null 2>&1")
            os.system(f"btrfs sub del /.var/var-{sarg} >/dev/null 2>&1")
            os.system(f"btrfs sub del /.boot/boot-{sarg} >/dev/null 2>&1")
            os.system(f"btrfs sub snap -r /.overlays/overlay-chr /.overlays/overlay-{sarg} >/dev/null 2>&1")
            os.system(f"btrfs sub snap -r /.var/var-chr /.var/var-{sarg} >/dev/null 2>&1")
            os.system(f"btrfs sub snap -r /.boot/boot-chr /.boot/boot-{sarg} >/dev/null 2>&1")
            os.system(f"btrfs sub del /.overlays/overlay-chr >/dev/null 2>&1")
            os.system(f"btrfs sub del /.var/var-chr >/dev/null 2>&1")
            os.system(f"btrfs sub del /.boot/boot-chr >/dev/null 2>&1")
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
        unchr()
        tmp = get_tmp()
        if "tmp0" in tmp:
            tmp = "tmp"
        else:
            tmp = "tmp0"
        part = get_part()
        prepare(overlay)
        os.system(f"arch-chroot /.overlays/overlay-chr grub-mkconfig {part} -o /boot/grub/grub.cfg")
        os.system(f"arch-chroot /.overlays/overlay-chr sed -i s/overlay-chr/overlay-{tmp}/g /boot/grub/grub.cfg")
        posttrans(overlay)

# Chroot into overlay
def chroot(overlay):
    if not (os.path.exists(f"/.overlays/overlay-{overlay}")):
        print("cannot chroot, overlay doesn't exist")
    elif overlay == "0":
        print("changing base image is not allowed")
    else:
        prepare(overlay)
        os.system(f"arch-chroot /.overlays/overlay-chr") # Arch specific chroot command because pacman is weird without it
        posttrans(overlay)

# Clean chroot mount dirs
def unchr():
    os.system(f"btrfs sub del /.etc/etc-chr >/dev/null 2>&1")
    os.system(f"btrfs sub del /.var/var-chr >/dev/null 2>&1")
    os.system(f"btrfs sub del /.boot/boot-chr >/dev/null 2>&1")
    os.system(f"btrfs sub del /.overlays/overlay-chr/* >/dev/null 2>&1")
    os.system(f"btrfs sub del /.overlays/overlay-chr >/dev/null 2>&1")

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


# Install packages
def install(overlay,pkg):
    if not (os.path.exists(f"/.overlays/overlay-{overlay}")):
        print("cannot install, overlay doesn't exist")
    elif overlay == "0":
        print("changing base image is not allowed")
    else:
        prepare(overlay)
        os.system(f"pacman -r /.overlays/overlay-chr -S {pkg}") # Actually doesn't chroot but uses target root instead, doesn't really make a difference, same for remove function
        posttrans(overlay)

# Remove packages
def remove(overlay,pkg):
    if not (os.path.exists(f"/.overlays/overlay-{overlay}")):
        print("cannot remove, overlay doesn't exist")
    elif overlay == "0":
        print("changing base image is not allowed")
    else:
        prepare(overlay)
        os.system(f"pacman -r /.overlays/overlay-chr -R {pkg}")
        posttrans(overlay)

# Pass arguments to pacman
def pac(overlay,arg):
    if not (os.path.exists(f"/.overlays/overlay-{overlay}")):
        print("cannot run pacman, overlay doesn't exist")
    elif overlay == "0":
        print("changing base image is not allowed")
    else:
        prepare(overlay)
        os.system(f"arch-chroot /.overlays/overlay-chr pacman {arg}")
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
    os.system(f"pacman -r /.overlays/overlay-chr -Syyu")
    posttrans("0")

def get_efi():
    if os.path.exists("/sys/firmware/efi"):
        efi = True
    else:
        efi = False
    return(efi)

# Prepare overlay to chroot dir to install or chroot into
def prepare(overlay):
    unchr()
    etc = overlay
    os.system(f"btrfs sub snap /.overlays/overlay-{overlay} /.overlays/overlay-chr >/dev/null 2>&1")
    os.system(f"btrfs sub snap /.etc/etc-{overlay} /.etc/etc-chr >/dev/null 2>&1")
    os.system(f"btrfs sub snap /var /.var/var-chr >/dev/null 2>&1")
    os.system("rm -rf /.overlays/overlay-chr/var >/dev/null 2>&1")
    os.system(f"btrfs sub snap /var /.overlays/overlay-chr/var >/dev/null 2>&1")
    os.system(f"chmod 0755 /.overlays/overlay-chr/var >/dev/null 2>&1") # For some reason the permission needs to be set here
    os.system(f"rm -rf /.overlays/overlay-chr/var/lib/pacman >/dev/null 2>&1")
    os.system(f"rm -rf /.overlays/overlay-chr/var/lib/systemd >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.var/var-{overlay}/* /.overlays/overlay-chr/var/ >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.var/var-{overlay}/* /.var/var-chr/ >/dev/null 2>&1")
    os.system(f"btrfs sub snap /.boot/boot-{overlay} /.boot/boot-chr >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.etc/etc-chr/* /.overlays/overlay-chr/etc >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.boot/boot-chr/* /.overlays/overlay-chr/boot >/dev/null 2>&1")
    os.system("mount --bind /.overlays/overlay-chr /.overlays/overlay-chr >/dev/null 2>&1") # Pacman gets weird when chroot directory is not a mountpoint, so this unusual mount is necessary

# Post transaction function, copy from chroot dirs back to read only image dir
def posttrans(overlay):
    etc = overlay
    os.system("umount /.overlays/overlay-chr >/dev/null 2>&1")
    os.system(f"btrfs sub del /.overlays/overlay-{overlay} >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.overlays/overlay-chr/etc/* /.etc/etc-chr >/dev/null 2>&1")
    os.system(f"btrfs sub del /.var/var-chr >/dev/null 2>&1")
    os.system(f"btrfs sub create /.var/var-chr >/dev/null 2>&1")
    os.system(f"mkdir -p /.var/var-chr/lib/systemd >/dev/null 2>&1")
    os.system(f"mkdir -p /.var/var-chr/lib/pacman >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.overlays/overlay-chr/var/lib/systemd/* /.var/var-chr/lib/systemd >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.overlays/overlay-chr/var/lib/pacman/* /.var/var-chr/lib/pacman >/dev/null 2>&1")
    os.system(f"cp -r --reflink=auto /.overlays/overlay-chr/boot/* /.boot/boot-chr >/dev/null 2>&1")
    os.system(f"btrfs sub del /.etc/etc-{etc} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.var/var-{etc} >/dev/null 2>&1")
    os.system(f"btrfs sub del /.boot/boot-{etc} >/dev/null 2>&1")
    os.system(f"btrfs sub snap -r /.etc/etc-chr /.etc/etc-{etc} >/dev/null 2>&1")
    os.system(f"btrfs sub create /.var/var-{etc} >/dev/null 2>&1")
    os.system(f"mkdir -p /.var/var-{etc}/lib/systemd >/dev/null 2>&1")
    os.system(f"mkdir -p /.var/var-{etc}/lib/pacman >/dev/null 2>&1")
    os.system(f"cp --reflink=auto -r /.var/var-chr/lib/systemd/* /.var/var-{etc}/lib/systemd >/dev/null 2>&1")
    os.system(f"cp --reflink=auto -r /.var/var-chr/lib/pacman/* /.var/var-{etc}/lib/pacman >/dev/null 2>&1")
    os.system(f"btrfs sub snap -r /.overlays/overlay-chr /.overlays/overlay-{overlay} >/dev/null 2>&1")
#    os.system(f"btrfs sub snap -r /.var/var-chr /.var/var-{etc} >/dev/null 2>&1")
    os.system(f"btrfs sub snap -r /.boot/boot-chr /.boot/boot-{etc} >/dev/null 2>&1")

# Upgrade overlay
def upgrade(overlay):
    if not (os.path.exists(f"/.overlays/overlay-{overlay}")):
        print("cannot upgrade, overlay doesn't exist")
    elif overlay == "0":
        print("changing base image is not allowed")
    else:
        prepare(overlay)
        os.system(f"pacman -r /.overlays/overlay-chr -Syyu")
        posttrans(overlay)

def chroot_check():
    chroot = True # When inside chroot
    with open("/proc/mounts", "r") as mounts:
        for line in mounts:
            if str("/.overlays btrfs") in str(line):
                chroot = False
    return(chroot)


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
        os.system("sed -i 's,subvol=@.overlays/overlay-tmp0,subvol=@.overlays/overlay-tmp,g' /etc/mnt/boot/grub/grub.cfg") # Overwrite grub config boot subvolume
        os.system("sed -i 's,subvol=@.overlays/overlay-tmp0,subvol=@.overlays/overlay-tmp,g' /.overlays/overlay-tmp/boot/grub/grub.cfg")
        os.system("sed -i 's,@.overlays/overlay-tmp0,@.overlays/overlay-tmp,g' /.overlays/overlay-tmp/etc/fstab") # Write fstab for new deployment
        os.system("sed -i 's,@.etc/etc-tmp0,@.etc/etc-tmp,g' /.overlays/overlay-tmp/etc/fstab")
#        os.system("sed -i 's,@.var/var-tmp0,@.var/var-tmp,g' /.overlays/overlay-tmp/etc/fstab")
        os.system("sed -i 's,@.boot/boot-tmp0,@.boot/boot-tmp,g' /.overlays/overlay-tmp/etc/fstab")
    else:
        os.system("cp --reflink=auto -r /.overlays/overlay-tmp0/boot/* /etc/mnt/boot")
        os.system("sed -i 's,subvol=@.overlays/overlay-tmp,subvol=@.overlays/overlay-tmp0,g' /etc/mnt/boot/grub/grub.cfg")
        os.system("sed -i 's,subvol=@.overlays/overlay-tmp,subvol=@.overlays/overlay-tmp0,g' /.overlays/overlay-tmp0/boot/grub/grub.cfg")
        os.system("sed -i 's,@.overlays/overlay-tmp,@.overlays/overlay-tmp0,g' /.overlays/overlay-tmp0/etc/fstab")
        os.system("sed -i 's,@.etc/etc-tmp,@.etc/etc-tmp0,g' /.overlays/overlay-tmp0/etc/fstab")
#        os.system("sed -i 's,@.var/var-tmp,@.var/var-tmp0,g' /.overlays/overlay-tmp0/etc/fstab")
        os.system("sed -i 's,@.boot/boot-tmp,@.boot/boot-tmp0,g' /.overlays/overlay-tmp0/etc/fstab")
    os.system("umount /etc/mnt/boot >/dev/null 2>&1")
#    os.system("reboot") # Enable for non-testing versions

def rswitchtmp():
    mount = get_tmp()
    part = get_part()
    os.system(f"mkdir /etc/mnt >/dev/null 2>&1")
    os.system(f"mkdir /etc/mnt/boot >/dev/null 2>&1")
    os.system(f"mount {part} -o subvol=@boot /etc/mnt/boot >/dev/null 2>&1") # Mount boot partition for writing
    if "tmp0" in mount:
        os.system("cp --reflink=auto -r /.overlays/overlay-tmp/boot/* /etc/mnt/boot >/dev/null 2>&1")
    else:
        os.system("cp --reflink=auto -r /.overlays/overlay-tmp0/boot/* /etc/mnt/boot >/dev/null 2>&1")
    os.system("umount /etc/mnt/boot >/dev/null 2>&1")
#    os.system("reboot") # Enable for non-testing versions

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

# Build image from recipe, currently completely untested, likely broken
def mk_img(imgpath):
    if not (os.path.exists(f"{imgpath}")):
        print("cannot create image, image file doesn't exist")
    else:
        i = findnew()
        new_overlay()
        prepare(i)
        os.system(f"cp -r {imgpath} /.overlays/overlay-chr/init.py >/dev/null 2>&1")
        os.system("arch-chroot /.overlays/overlay-chr python3 /init.py")
        posttrans(i)

# Main function
def main(args):
    overlay = get_overlay() # Get current overlay
    etc = overlay
    importer = DictImporter() # Dict importer
    exporter = DictExporter() # And exporter
    isChroot = chroot_check()
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
        if arg == "new-overlay" or arg == "new":
            new_overlay()
        elif arg == "boot-update" or arg == "boot":
            update_boot(args[args.index(arg)+1])
        elif arg == "chroot" or arg == "cr":
            chroot(args[args.index(arg)+1])
        elif arg == "install" or arg == "i":
            install(args[args.index(arg)+1],args[args.index(arg)+2])
        elif arg == "add-branch" or arg == "branch":
            extend_branch(args[args.index(arg)+1])
        elif arg == "clone-branch" or arg == "cbranch":
            clone_branch(args[args.index(arg)+1])
        elif arg == "clone-under" or arg == "ubranch":
            clone_under(args[args.index(arg)+1], args[args.index(arg)+2])
        elif arg == "clone" or arg == "tree-clone":
            clone_as_tree(args[args.index(arg)+1])
        elif arg == "mk-img" or arg == "img":
            mk_img(args[args.index(arg)+1])
        elif arg == "deploy":
            deploy(args[args.index(arg)+1])
        elif arg == "rollback":
            deploy(args[args.index(arg)+1])
        elif arg == "upgrade" or arg == "up":
            upgrade(args[args.index(arg)+1])
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
            args_2.remove(args_2[0])
            coverlay = args_2[0]
            args_2.remove(args_2[0])
            pac(coverlay, str(" ").join(args_2))
        elif arg == "desc" or arg == "description":
            n_lay = args[args.index(arg)+1]
            args_2 = args
            args_2.remove(args_2[0])
            args_2.remove(args_2[0])
            args_2.remove(args_2[0])
            write_desc(n_lay, str(" ").join(args_2))
        elif arg == "base-update" or arg == "bu":
            update_base()
        elif arg == "sync" or arg == "tree-sync":
            sync_tree(fstree,args[args.index(arg)+1])
        elif arg == "tree-upgrade" or arg == "tupgrade":
            update_tree(fstree,args[args.index(arg)+1])
        elif arg  == "tree":
            show_fstree()
        elif (arg == args[1]):
            print("Operation not found.")

# Call main (duh)
main(args)
