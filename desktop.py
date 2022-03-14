import os

user="jan"
packages = ["xorg", "xorg-xinit", "sddm", "sddm-kcm", "sudo", "xorg-xrandr", "neofetch", "mate", "mate-terminal", "flatpak", "materia-kde", "materia-gtk-theme"]
 
pkglist = str(" ".join(packages))
os.system(f"pacman -S {pkglist}")

os.system(f"useradd {user}")
os.system(f"usermod -aG wheel,audio,video,input {user}")
os.system(f"mkdir /home/{user}")
os.system(f"chown -R {user} /home/{user}")
os.system(f"passwd -l root")
os.system(f"chmod +w /etc/sudoers")
os.system(f"echo '%wheel ALL=(ALL:ALL) ALL' > /etc/sudoers")
os.system(f"chmod -x /etc/sudoers")

os.system(f"systemctl enable sddm")

os.system(f"echo '[Theme]' > /etc/sddm.conf")
os.system(f"echo 'Current=materia-dark' >> /etc/sddm.conf")
os.system(f"echo '[General]' >> /etc/sddm.conf")
os.system(f"echo 'EnableHiDPI=false' >> /etc/sddm.conf")
os.system(f"echo 'setxkbmap cz' >> /usr/share/sddm/scripts/Xsetup")
os.system(f"echo 'xrandr --output Virtual-1 --mode 1920x1080' >> /usr/share/sddm/scripts/Xsetup")

print("set password")
os.system(f"passwd {user}")
