import sys

import listener
import updater

if getattr(sys, "frozen", False):
    updater.check_and_update()

listener.run()
