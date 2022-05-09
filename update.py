#!/usr/bin/python3
import os
import time
import subprocess

overlay = subprocess.check_output("/usr/bin/ast c", shell=True)
while True:
    if os.path.exists(f"/.overlays/overlay-chr{overlay}"):
        time.sleep(20)
    else:
        os.system("/usr/bin/ast clone $(/usr/bin/ast c)")
        os.system("/usr/bin/ast auto-upgrade")
        break

upstate = open("/var/astpk/upstate")
line = upstate.readline()
upstate.close()
if "1" not in line:
    os.system("/usr/bin/ast deploy $(/usr/bin/ast c)")
