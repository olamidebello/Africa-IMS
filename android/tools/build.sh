#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
: "${ANDROID_HOME:?Set ANDROID_HOME to an Android SDK with platform 35 and build-tools 35.0.0}"
: "${AIMS_KEYSTORE:?Set AIMS_KEYSTORE to a persistent signing key}"
: "${AIMS_KEY_PASSWORD:?Set signing password in environment}"
AIMS_KEY_ALIAS=${AIMS_KEY_ALIAS:-aims}
TOOLS="$ANDROID_HOME/build-tools/35.0.0"
BUILD="$ROOT/build"
mkdir -p "$BUILD/gen" "$BUILD/classes" "$BUILD/dex" "$ROOT/dist"
python3 - "$ROOT" "$BUILD" <<'PYMANIFEST'
import pathlib,sys
root,build=map(pathlib.Path,sys.argv[1:])
s=(root/'app/src/main/AndroidManifest.xml').read_text().replace('<manifest ', '<manifest package="world.africandroid.aims" ',1)
(build/'AndroidManifest.xml').write_text(s)
PYMANIFEST
"$TOOLS/aapt" package -f -M "$BUILD/AndroidManifest.xml" -S "$ROOT/app/src/main/res" -I "$ANDROID_HOME/platforms/android-35/android.jar" -J "$BUILD/gen" -F "$BUILD/resources.apk"
find "$ROOT/app/src/main/java" "$BUILD/gen" -name '*.java' > "$BUILD/sources.txt"
if command -v javac >/dev/null 2>&1; then
  javac -source 8 -target 8 -bootclasspath "$ANDROID_HOME/platforms/android-35/android.jar" -d "$BUILD/classes" @"$BUILD/sources.txt"
else
  : "${AIMS_ECJ_JAR:?Install a JDK or provide the Eclipse Java compiler JAR}"
  java -jar "$AIMS_ECJ_JAR" -source 8 -target 8 -bootclasspath "$ANDROID_HOME/platforms/android-35/android.jar" -d "$BUILD/classes" @"$BUILD/sources.txt"
fi
python3 - "$BUILD" <<'PYZIP'
import sys,zipfile,pathlib
b=pathlib.Path(sys.argv[1])
with zipfile.ZipFile(b/'classes.jar','w',zipfile.ZIP_DEFLATED) as z:
    for f in (b/'classes').rglob('*.class'): z.write(f,f.relative_to(b/'classes'))
PYZIP
"$TOOLS/d8" --min-api 26 --lib "$ANDROID_HOME/platforms/android-35/android.jar" --output "$BUILD/dex" "$BUILD/classes.jar"
cp "$BUILD/resources.apk" "$BUILD/unsigned.apk"
(cd "$BUILD/dex" && "$TOOLS/aapt" add "$BUILD/unsigned.apk" classes.dex)
"$TOOLS/zipalign" -f -p 4 "$BUILD/unsigned.apk" "$BUILD/aligned.apk"
"$TOOLS/apksigner" sign --ks "$AIMS_KEYSTORE" --ks-key-alias "$AIMS_KEY_ALIAS" --ks-pass env:AIMS_KEY_PASSWORD --key-pass env:AIMS_KEY_PASSWORD --out "$ROOT/dist/AIMS.apk" "$BUILD/aligned.apk"
"$TOOLS/apksigner" verify --verbose "$ROOT/dist/AIMS.apk"
"$TOOLS/aapt" dump badging "$ROOT/dist/AIMS.apk" | head -1
(cd "$ROOT/dist" && sha256sum AIMS.apk > AIMS.apk.sha256)
