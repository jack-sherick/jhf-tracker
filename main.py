import sys

import listener
import updater

if getattr(sys, "frozen", False):
    try:
        updater.check_and_update()
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("[updater] Press Enter to continue...")

listener.run()
