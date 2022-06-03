#!/usr/bin/python3
import os
import time
import subprocess

snapshot = subprocess.check_output("/usr/local/sbin/ast c", shell=True)
while True:
    if os.path.exists(f"/.snapshots/rootfs/snapshot-chr{snapshot}"):
        time.sleep(20)
    else:
        os.system("/usr/local/sbin/ast clone $(/usr/local/sbin/ast c)")
        os.system("/usr/local/sbin/ast auto-upgrade")
        os.system("/usr/local/sbin/ast base-update")
        break

upstate = open("/var/astpk/upstate")
line = upstate.readline()
upstate.close()
if "1" not in line:
    os.system("/usr/local/sbin/ast deploy $(/usr/local/sbin/ast c)")
