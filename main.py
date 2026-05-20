import sys

import config
import listener
import updater

print(f"[jhf-tracker] v{config.VERSION}")

if getattr(sys, "frozen", False):
    try:
        updater.check_and_update()
    except Exception as e:
        import traceback
        traceback.print_exc()
        input("[updater] Press Enter to continue...")

listener.run()
