#!/usr/bin/python3
import os

USER = "jan"


#os.system("sudo -u jan DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus notify-send astUpdate 'System upgrade is being installed...' -u critical")

while True:
    if os.path.exists("/var/astpk/lock"):
        time.sleep(20)
    else:
        os.system("/usr/bin/ast auto-upgrade")
        break

upstate = open("/var/astpk/upstate")
line = upstate.readline()
upstate.close()
if "0" in line:
#    os.system("sudo -u jan DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus notify-send astUpdate 'System has been upgraded succesfully' -u critical")
    os.system("/usr/bin/ast deploy $(ast c)")
else:
#    os.system("sudo -u jan DISPLAY=:0 DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/1000/bus notify-send astUpdate 'System upgrade failed' -u critical")
    print()
