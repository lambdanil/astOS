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
    for pre, fill, node in anytree.RenderTree(tree):
        if os.path.isfile(f"/root/images/{node.name}-desc"):
            descfile = open(f"/root/images/{node.name}-desc","r")
            desc = descfile.readline()
            descfile.close()
        else:
            desc = ""
        print("%s%s - %s" % (pre, node.name, desc))

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
    par = (anytree.find(tree, filter_=lambda node: (str(node.name)+"x") in (str(id)+"x"))) # Not entirely sure how the lambda stuff here works, but it does ¯\_(ツ)_/¯
    add = anytree.Node(val, parent=par)

# Clone within node
def add_node_to_level(tree,id, val): # Broken, likely useless, probably remove later
    npar = get_parent(tree, id)
    par = (anytree.find(tree, filter_=lambda node: (str(node.name) + "x") in (str(npar) + "x"))) # Not entirely sure how the lambda stuff here works, but it does ¯\_(ツ)_/¯
    add = anytree.Node(val, parent=par)

# Remove node from tree
def remove_node(tree, id):
    par = (anytree.find(tree, filter_=lambda node: (str(node.name)+"x") in (str(id)+"x")))
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
    par = (anytree.find(tree, filter_=lambda node: (str(node.name) + "x") in (str(id) + "x")))
    return(par.parent.name)

# Return all children for node
def return_children(tree, id):
    children = []
    par = (anytree.find(tree, filter_=lambda node: (str(node.name)+"x") in (str(id)+"x")))
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
    par = (anytree.find(tree, filter_=lambda node: (str(node.name)+"x") in (str(id)+"x")))
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
    mount = str(subprocess.check_output("btrfs sub get-default /", shell=True)) # shell=True is probably not ideal? idk might fix(?) sometime
    if "tmp0" in mount:
        return("tmp0")
    else:
        return("tmp")

# Reverse tmp deploy image
def rdeploy(overlay):
    tmp = get_tmp()
    untmp()
    etc = overlay
    os.system(f"btrfs sub snap /.overlays/overlay-{overlay} /.overlays/overlay-{tmp}")
    os.system(f"btrfs sub snap /.etc/etc-{overlay} /.etc/etc-{tmp}")
    os.system(f"btrfs sub create /.var/var-{tmp}")
    os.system(f"cp --reflink=auto -r /.var/var-{etc}/* /.var/var-{tmp}")
    os.system(f"btrfs sub snap /.boot/boot-{overlay} /.boot/boot-{tmp}")
    os.system(f"mkdir /.overlays/overlay-{tmp}/etc")
    os.system(f"rm -rf /.overlays/overlay-{tmp}/var")
    os.system(f"mkdir /.overlays/overlay-{tmp}/boot")
    os.system(f"cp --reflink=auto -r /.etc/etc-{etc}/* /.overlays/overlay-{tmp}/etc")
    os.system(f"btrfs sub snap /var /.overlays/overlay-{tmp}/var")
    os.system(f"cp --reflink=auto -r /.boot/boot-{etc}/* /.overlays/overlay-{tmp}/boot")
    os.system(f"echo '{overlay}' > /.overlays/overlay-{tmp}/etc/astpk.d/astpk-coverlay")
    os.system(f"echo '{etc}' > /.overlays/overlay-{tmp}/etc/astpk.d/astpk-cetc")
    os.system(f"echo '{overlay}' > /.etc/etc-{tmp}/astpk.d/astpk-coverlay")
    os.system(f"echo '{etc}' > /.etc/etc-{tmp}/astpk.d/astpk-cetc")
    rswitchtmp()
    os.system(f"rm -rf /var/lib/pacman/*") # Clean pacman and systemd directories before copy
    os.system(f"rm -rf /var/lib/systemd/*")
    os.system(f"cp --reflink=auto -r /.var/var-{etc}/* /.overlays/overlay-{tmp}/var/")
    os.system(f"cp --reflink=auto -r /.var/var-{etc}/lib/pacman/* /var/lib/pacman/") # Copy pacman and systemd directories
    os.system(f"cp --reflink=auto -r /.var/var-{etc}/lib/systemd/* /var/lib/systemd/")
    os.system(f"btrfs sub set-default /.overlays/overlay-{tmp}") # Set default volume



# Deploy image
def deploy(overlay):
    tmp = get_tmp()
    untmp()
#    unchr()
    if "tmp0" in tmp:
        tmp = "tmp"
    else:
        tmp = "tmp0"
    etc = overlay
    os.system(f"btrfs sub snap /.overlays/overlay-{overlay} /.overlays/overlay-{tmp}")
    os.system(f"btrfs sub snap /.etc/etc-{overlay} /.etc/etc-{tmp}")
    os.system(f"btrfs sub create /.var/var-{tmp}")
    os.system(f"cp --reflink=auto -r /.var/var-{etc}/* /.var/var-{tmp}")
    os.system(f"btrfs sub snap /.boot/boot-{overlay} /.boot/boot-{tmp}")
    os.system(f"mkdir /.overlays/overlay-{tmp}/etc")
    os.system(f"rm -rf /.overlays/overlay-{tmp}/var")
    os.system(f"mkdir /.overlays/overlay-{tmp}/boot")
    os.system(f"cp --reflink=auto -r /.etc/etc-{etc}/* /.overlays/overlay-{tmp}/etc")
    os.system(f"btrfs sub snap /var /.overlays/overlay-{tmp}/var")
    os.system(f"cp --reflink=auto -r /.boot/boot-{etc}/* /.overlays/overlay-{tmp}/boot")
    os.system(f"echo '{overlay}' > /.overlays/overlay-{tmp}/etc/astpk.d/astpk-coverlay")
    os.system(f"echo '{etc}' > /.overlays/overlay-{tmp}/etc/astpk.d/astpk-cetc")
    os.system(f"echo '{overlay}' > /.etc/etc-{tmp}/astpk.d/astpk-coverlay")
    os.system(f"echo '{etc}' > /.etc/etc-{tmp}/astpk.d/astpk-cetc")
#    update_boot(overlay)
    switchtmp()
    os.system(f"rm -rf /var/lib/pacman/*") # Clean pacman and systemd directories before copy
    os.system(f"rm -rf /var/lib/systemd/*")
    os.system(f"cp --reflink=auto -r /.var/var-{etc}/* /.overlays/overlay-{tmp}/var/")
    os.system(f"cp --reflink=auto -r /.var/var-{etc}/lib/pacman/* /var/lib/pacman/") # Copy pacman and systemd directories
    os.system(f"cp --reflink=auto -r /.var/var-{etc}/lib/systemd/* /var/lib/systemd/")
    os.system(f"btrfs sub set-default /.overlays/overlay-{tmp}") # Set default volume

# Add node to branch
def extend_branch(overlay):
    i = findnew()
    os.system(f"btrfs sub snap -r /.overlays/overlay-{overlay} /.overlays/overlay-{i}")
    os.system(f"btrfs sub snap -r /.etc/etc-{overlay} /.etc/etc-{i}")
    os.system(f"btrfs sub snap -r /.var/var-{overlay} /.var/var-{i}")
    os.system(f"btrfs sub snap -r /.boot/boot-{overlay} /.boot/boot-{i}")
    add_node_to_parent(fstree,overlay,i)
    write_tree(fstree)

# Clone branch under same parent,
def clone_branch(overlay):
    i = findnew()
    os.system(f"btrfs sub snap -r /.overlays/overlay-{overlay} /.overlays/overlay-{i}")
    os.system(f"btrfs sub snap -r /.etc/etc-{overlay} /.etc/etc-{i}")
    os.system(f"btrfs sub snap -r /.var/var-{overlay} /.var/var-{i}")
    os.system(f"btrfs sub snap -r /.boot/boot-{overlay} /.boot/boot-{i}")
    add_node_to_level(fstree,overlay,i)
    write_tree(fstree)

# Sync tree and all it's overlays
def sync_tree(tree,treename):
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
        os.system(f"btrfs sub snap /.overlays/overlay-{sarg} /.overlays/overlay-chr")
        os.system(f"btrfs sub snap /.var/var-{sarg} /.var/var-chr")
        os.system(f"btrfs sub snap /.boot/boot-{sarg} /.boot/boot-chr")
        os.system(f"cp --reflink=auto -r /.var/var-{arg}/lib/pacman/local/* /.var/var-chr/lib/pacman/local/")
        os.system(f"cp --reflink=auto -r /.var/var-{arg}/lib/systemd/* /.var/var-chr/lib/systemd/")
        os.system(f"cp --reflink=auto -r /.overlays/overlay-{arg}/* /.overlays/overlay-chr/")
        os.system(f"btrfs sub del /.overlays/overlay-{sarg}")
        os.system(f"btrfs sub del /.var/var-{sarg}")
        os.system(f"btrfs sub del /.boot/boot-{sarg}")
        os.system(f"btrfs sub snap -r /.overlays/overlay-chr /.overlays/overlay-{sarg}")
        os.system(f"btrfs sub snap -r /.var/var-chr /.var/var-{sarg}")
        os.system(f"btrfs sub snap -r /.boot/boot-chr /.boot/boot-{sarg}")
        os.system(f"btrfs sub del /.overlays/overlay-chr")
        os.system(f"btrfs sub del /.var/var-chr")
        os.system(f"btrfs sub del /.boot/boot-chr")

# Clone tree
def clone_as_tree(overlay):
    i = findnew()
    os.system(f"btrfs sub snap -r /.overlays/overlay-{overlay} /.overlays/overlay-{i}")
    os.system(f"btrfs sub snap -r /.etc/etc-{overlay} /.etc/etc-{i}")
    os.system(f"btrfs sub snap -r /.var/var-{overlay} /.var/var-{i}")
    os.system(f"btrfs sub snap -r /.boot/boot-{overlay} /.boot/boot-{i}")
    append_base_tree(fstree,i)
    write_tree(fstree)

# Creates new tree from base file
def new_overlay():
    i = findnew()
    os.system(f"btrfs sub snap -r /.base/base /.overlays/overlay-{i}")
    os.system(f"btrfs sub snap -r /.etc/etc-0 /.etc/etc-{i}")
    os.system(f"btrfs sub snap -r /.var/var-0 /.var/var-{i}")
    os.system(f"btrfs sub snap -r /.boot/boot-0 /.boot/boot-{i}")
#    append_base_tree(fstree, i)
    append_base_tree(fstree,i)
    write_tree(fstree)

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
    tmp = get_tmp()
    part = get_part()
    prepare(overlay)
    os.system(f"arch-chroot /mnt grub-mkconfig {part} -o /boot/grub/grub.cfg")
    os.system(f"arch-chroot /mnt sed -i s/overlay-chr/overlay-{tmp}/g /boot/grub/grub.cfg")
    posttrans(overlay)

# Chroot into overlay
def chroot(overlay):
    prepare(overlay)
    os.system(f"arch-chroot /.overlays/overlay-chr") # Arch specific chroot command because pacman is weird without it
    posttrans(overlay)

# Clean chroot mount dirs
def unchr():
    os.system(f"btrfs sub del /.etc/etc-chr")
    os.system(f"btrfs sub del /.var/var-chr")
    os.system(f"btrfs sub del /.boot/boot-chr")
    os.system(f"btrfs sub del /.overlays/overlay-chr/*")
    os.system(f"btrfs sub del /.overlays/overlay-chr")

# Clean tmp dirs
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

# Install packages
def install(overlay,pkg):
    prepare(overlay)
    os.system(f"pacman -r /.overlays/overlay-chr -S {pkg}") # Actually doesn't chroot but uses target root instead, doesn't really make a difference, same for remove function
    posttrans(overlay)

# Remove packages
def remove(overlay,pkg):
    prepare(overlay)
    os.system(f"pacman -r /.overlays/overlay-chr -R {pkg}")
    posttrans(overlay)

# Pass arguments to pacman
def pac(overlay,arg):
    prepare(overlay)
    os.system(f"arch-chroot /.overlays/overlay-chr pacman {arg}")
    posttrans(overlay)

# Delete tree or branch
def delete(overlay):
    children = return_children(fstree,overlay)
    os.system(f"btrfs sub del /.boot/boot-{overlay}")
    os.system(f"btrfs sub del /.etc/etc-{overlay}")
    os.system(f"btrfs sub del /.var/var-{overlay}")
    os.system(f"btrfs sub del /.overlays/overlay-{overlay}")
    for child in children: # This deleted the node itself along with it's children
        os.system(f"btrfs sub del /.boot/boot-{child}")
        os.system(f"btrfs sub del /.etc/etc-{child}")
        os.system(f"btrfs sub del /.var/var-{child}")
        os.system(f"btrfs sub del /.overlays/overlay-{child}")
    remove_node(fstree,overlay) # Remove node from tree or root
    write_tree(fstree)

# Mount base to chroot dir for transaction
def prepare_base():
    unchr()
    os.system(f"btrfs sub snap /.base/base /.overlays/overlay-chr")
    os.system(f"btrfs sub snap /.base/etc /.etc/etc-chr")
    os.system(f"btrfs sub snap /var /.var/var-chr")
    os.system("rm -rf /.overlays/overlay-chr/var")
    os.system(f"btrfs sub snap /var /.overlays/overlay-chr/var")
    os.system(f"chmod 0755 /.overlays/overlay-chr/var") # For some reason the permission needs to be set here
    os.system(f"rm -rf /.overlays/overlay-chr/var/lib/pacman")
    os.system(f"rm -rf /.overlays/overlay-chr/var/lib/systemd")
    os.system(f"cp -r --reflink=auto /.base/var/* /.overlays/overlay-chr/var/")
    os.system(f"cp -r --reflink=auto /.base/var/* /.var/var-chr/")
    os.system(f"btrfs sub snap /.base/boot /.boot/boot-chr")
    os.system(f"cp -r --reflink=auto /.etc/etc-chr/* /.overlays/overlay-chr/etc")
    os.system(f"cp -r --reflink=auto /.boot/boot-chr/* /.overlays/overlay-chr/boot")
    os.system("mount --bind /.overlays/overlay-chr /.overlays/overlay-chr") # Pacman gets weird when chroot directory is not a mountpoint, so this unusual mount is necessary

# Copy base from chroot dir back to base dir
def posttrans_base():
    os.system("umount /.overlays/overlay-chr")
    os.system(f"btrfs sub del /.base/base")
    os.system(f"cp -r --reflink=auto /.overlays/overlay-chr/etc/* /.etc/etc-chr")
    os.system(f"btrfs sub del /.var/var-chr")
    os.system(f"btrfs sub create /.var/var-chr")
    os.system(f"mkdir -p /.var/var-chr/lib/systemd")
    os.system(f"mkdir -p /.var/var-chr/lib/pacman")
    os.system(f"cp -r --reflink=auto /.overlays/overlay-chr/var/lib/systemd/* /.var/var-chr/lib/systemd")
    os.system(f"cp -r --reflink=auto /.overlays/overlay-chr/var/lib/pacman/* /.var/var-chr/lib/pacman")
    os.system(f"cp -r --reflink=auto /.overlays/overlay-chr/boot/* /.boot/boot-chr")
    os.system(f"btrfs sub del /.base/etc")
    os.system(f"btrfs sub del /.base/var")
    os.system(f"btrfs sub del /.base/boot")
    os.system(f"btrfs sub snap -r /.etc/etc-chr /.base/etc")
    os.system(f"btrfs sub create /.base/var")
    os.system(f"mkdir -p /.base/var/lib/systemd")
    os.system(f"mkdir -p /.base/var/lib/pacman")
    os.system(f"cp --reflink=auto -r /.var/var-chr/lib/systemd/* /.base/var/lib/systemd")
    os.system(f"cp --reflink=auto -r /.var/var-chr/lib/pacman/* /.base/var/lib/pacman")
    os.system(f"btrfs sub snap -r /.overlays/overlay-chr /.base/base")
#    os.system(f"btrfs sub snap -r /.var/var-chr /.var/var-{etc}")
    os.system(f"btrfs sub snap -r /.boot/boot-chr /.base/boot")

# Update base
def update_base():
    prepare_base()
    os.system(f"pacman -r /.overlays/overlay-chr -Syyu")
    posttrans_base()

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
    os.system(f"btrfs sub snap /.overlays/overlay-{overlay} /.overlays/overlay-chr")
    os.system(f"btrfs sub snap /.etc/etc-{overlay} /.etc/etc-chr")
    os.system(f"btrfs sub snap /var /.var/var-chr")
    os.system("rm -rf /.overlays/overlay-chr/var")
    os.system(f"btrfs sub snap /var /.overlays/overlay-chr/var")
    os.system(f"chmod 0755 /.overlays/overlay-chr/var") # For some reason the permission needs to be set here
    os.system(f"rm -rf /.overlays/overlay-chr/var/lib/pacman")
    os.system(f"rm -rf /.overlays/overlay-chr/var/lib/systemd")
    os.system(f"cp -r --reflink=auto /.var/var-{overlay}/* /.overlays/overlay-chr/var/")
    os.system(f"cp -r --reflink=auto /.var/var-{overlay}/* /.var/var-chr/")
    os.system(f"btrfs sub snap /.boot/boot-{overlay} /.boot/boot-chr")
    os.system(f"cp -r --reflink=auto /.etc/etc-chr/* /.overlays/overlay-chr/etc")
    os.system(f"cp -r --reflink=auto /.boot/boot-chr/* /.overlays/overlay-chr/boot")
    os.system("mount --bind /.overlays/overlay-chr /.overlays/overlay-chr") # Pacman gets weird when chroot directory is not a mountpoint, so this unusual mount is necessary

# Post transaction function, copy from chroot dirs back to read only image dir
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

# Upgrade overlay
def upgrade(overlay):
    prepare(overlay)
    os.system(f"pacman -r /.overlays/overlay-chr -Syyu")
    posttrans(overlay)

# Upgrade current overlay, likely unnecessary, also broken
def cupgrade(overlay):
    i = findnew()
    prepare(overlay)
    os.system(f"pacman -r /.overlays/overlay-chr -Syyu")
    posttrans(i)
    deploy(i)

# Install inside current overlay, likely unnecessary, also broken
def cinstall(overlay,pkg):
    i = findnew()
    prepare(overlay)
    os.system(f"pacman -r /.overlays/overlay-chr -S {pkg}")
    posttrans(i)
    deploy(i)

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
    os.system(f"mkdir /etc/mnt")
    os.system(f"mkdir /etc/mnt/boot")
    os.system(f"mount {part} -o subvol=@boot /etc/mnt/boot") # Mount boot partition for writing
    if "tmp0" in mount:
        os.system("cp --reflink=auto -r /.overlays/overlay-tmp/boot/* /etc/mnt/boot")
        os.system("sed -i 's,subvol=@.overlays/overlay-tmp0,subvol=@.overlays/overlay-tmp,' /etc/mnt/boot/grub/grub.cfg") # Overwrite grub config boot subvolume
        os.system("sed -i 's,subvol=@.overlays/overlay-tmp0,subvol=@.overlays/overlay-tmp,' /.overlays/overlay-tmp/boot/grub/grub.cfg")
        os.system("sed -i 's,@.overlays/overlay-tmp0,@.overlays/overlay-tmp,' /.overlays/overlay-tmp/etc/fstab") # Write fstab for new deployment
        os.system("sed -i 's,@.etc/etc-tmp0,@.etc/etc-tmp,' /.overlays/overlay-tmp/etc/fstab")
#        os.system("sed -i 's,@.var/var-tmp0,@.var/var-tmp,' /.overlays/overlay-tmp/etc/fstab")
        os.system("sed -i 's,@.boot/boot-tmp0,@.boot/boot-tmp,' /.overlays/overlay-tmp/etc/fstab")
    else:
        os.system("cp --reflink=auto -r /.overlays/overlay-tmp0/boot/* /etc/mnt/boot")
        os.system("sed -i 's,subvol=@.overlays/overlay-tmp,subvol=@.overlays/overlay-tmp0,' /etc/mnt/boot/grub/grub.cfg")
        os.system("sed -i 's,subvol=@.overlays/overlay-tmp,subvol=@.overlays/overlay-tmp0,' /.overlays/overlay-tmp0/boot/grub/grub.cfg")
        os.system("sed -i 's,@.overlays/overlay-tmp,@.overlays/overlay-tmp0,' /.overlays/overlay-tmp0/etc/fstab")
        os.system("sed -i 's,@.etc/etc-tmp,@.etc/etc-tmp0,' /.overlays/overlay-tmp0/etc/fstab")
#        os.system("sed -i 's,@.var/var-tmp,@.var/var-tmp0,' /.overlays/overlay-tmp0/etc/fstab")
        os.system("sed -i 's,@.boot/boot-tmp,@.boot/boot-tmp0,' /.overlays/overlay-tmp0/etc/fstab")
    os.system("umount /etc/mnt/boot")
#    os.system("reboot") # Enable for non-testing versions

def rswitchtmp():
    mount = get_tmp()
    part = get_part()
    if "tmp0" in mount:
        mount = "tmp"
    else:
        mount = "tmp0"
    os.system(f"mkdir /etc/mnt")
    os.system(f"mkdir /etc/mnt/boot")
    os.system(f"mount {part} -o subvol=@boot /etc/mnt/boot") # Mount boot partition for writing
    if "tmp0" in mount:
        os.system("cp --reflink=auto -r /.overlays/overlay-tmp/boot/* /etc/mnt/boot")
        os.system("sed -i 's,subvol=@.overlays/overlay-tmp0,subvol=@.overlays/overlay-tmp,' /etc/mnt/boot/grub/grub.cfg") # Overwrite grub config boot subvolume
        os.system("sed -i 's,subvol=@.overlays/overlay-tmp0,subvol=@.overlays/overlay-tmp,' /.overlays/overlay-tmp/boot/grub/grub.cfg")
        os.system("sed -i 's,@.overlays/overlay-tmp0,@.overlays/overlay-tmp,' /.overlays/overlay-tmp/etc/fstab") # Write fstab for new deployment
        os.system("sed -i 's,@.etc/etc-tmp0,@.etc/etc-tmp,' /.overlays/overlay-tmp/etc/fstab")
#        os.system("sed -i 's,@.var/var-tmp0,@.var/var-tmp,' /.overlays/overlay-tmp/etc/fstab")
        os.system("sed -i 's,@.boot/boot-tmp0,@.boot/boot-tmp,' /.overlays/overlay-tmp/etc/fstab")
    else:
        os.system("cp --reflink=auto -r /.overlays/overlay-tmp0/boot/* /etc/mnt/boot")
        os.system("sed -i 's,subvol=@.overlays/overlay-tmp,subvol=@.overlays/overlay-tmp0,' /etc/mnt/boot/grub/grub.cfg")
        os.system("sed -i 's,subvol=@.overlays/overlay-tmp,subvol=@.overlays/overlay-tmp0,' /.overlays/overlay-tmp0/boot/grub/grub.cfg")
        os.system("sed -i 's,@.overlays/overlay-tmp,@.overlays/overlay-tmp0,' /.overlays/overlay-tmp0/etc/fstab")
        os.system("sed -i 's,@.etc/etc-tmp,@.etc/etc-tmp0,' /.overlays/overlay-tmp0/etc/fstab")
#        os.system("sed -i 's,@.var/var-tmp,@.var/var-tmp0,' /.overlays/overlay-tmp0/etc/fstab")
        os.system("sed -i 's,@.boot/boot-tmp,@.boot/boot-tmp0,' /.overlays/overlay-tmp0/etc/fstab")
    os.system("umount /etc/mnt/boot")
#    os.system("reboot") # Enable for non-testing versions

# List overlays, quite unnecessary with the tree now :)
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
    i = findnew()
    new_overlay()
    prepare(i)
    os.system(f"cp -r {imgpath} /.overlays/overlay-chr/init.py")
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
        elif arg == "cinstall" or arg == "ci":
            cinstall(overlay,args[args.index(arg)+1])
        elif arg == "add-branch" or arg == "branch":
            extend_branch(args[args.index(arg)+1])
        elif arg == "clone-branch" or arg == "cbranch":
            clone_branch(args[args.index(arg)+1])
        elif arg == "clone" or arg == "tree-clone":
            clone_as_tree(args[args.index(arg)+1])
        elif arg == "list" or arg == "l":
            ls_overlay()
        elif arg == "mk-img" or arg == "img":
            mk_img(args[args.index(arg)+1])
        elif arg == "deploy":
            deploy(args[args.index(arg)+1])
        elif arg == "rdeploy" or arg == "rescue-deploy":
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
        elif arg  == "tree":
            show_fstree()
        elif (arg == args[1]):
            print("Operation not found.")

# Call main (duh)
main(args)
