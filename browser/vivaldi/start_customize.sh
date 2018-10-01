#!/usr/bin/env bash
SRC=$(dirname "$0")
VIVALDI="/Applications/Vivaldi.app"
VFRAMEWORK=$(find "$VIVALDI" -name Vivaldi\ Framework.framework)
echo "Starting customization..."
cp "$SRC/vivaldi-custom.css" "$VFRAMEWORK/Resources/vivaldi/style/"
echo "vivaldi-custom.css copied"
browserHtml=$VFRAMEWORK/Resources/vivaldi/browser.html
sed 's|  </head>|    <link rel="stylesheet" href="style/vivaldi-custom.css" /></head>|' "$browserHtml" > "$browserHtml.temp"
echo "Generated new browser.html"
cp "$browserHtml" "$browserHtml.backup"
echo "Original browser.html moved to $browserHtml.backup"
mv "$browserHtml.temp" "$browserHtml"
echo "browser.html patched"
