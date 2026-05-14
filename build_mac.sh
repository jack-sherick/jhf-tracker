#!/bin/bash
set -e

pyinstaller -y jhf-tracker.spec

MACOS_DIR="dist/jhf-tracker.app/Contents/MacOS"
BINARY="$MACOS_DIR/jhf-tracker"

mv "$BINARY" "$MACOS_DIR/jhf-tracker-bin"

cat > "$BINARY" << 'EOF'
#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
osascript -e "tell application \"Terminal\" to activate" \
          -e "tell application \"Terminal\" to do script \"$DIR/jhf-tracker-bin\""
EOF

chmod +x "$BINARY"
echo "Done"
