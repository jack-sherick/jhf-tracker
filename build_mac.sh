#!/bin/bash
set -e

pip install icnsutil pyobjc-core pyobjc-framework-Cocoa
python scripts/generate_icon.py --icns
pyinstaller -y jhf-tracker.spec
echo "Done"
