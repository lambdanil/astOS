#!/usr/bin/python3
import os
import time

while True:
    if os.path.exists("/var/astpk/lock"):
        time.sleep(20)
    else:
        os.system("/usr/bin/ast auto-upgrade")
        break

upstate = open("/var/astpk/upstate")
line = upstate.readline()
upstate.close()
if "127" not in line:
    os.system("/usr/bin/ast deploy $(ast c)")
