#!/usr/bin/env bash
set -euo pipefail

# Scan iOS project — source files, deps, storyboards, stats.
# Emits: <signal:ready>path</signal:ready>
# Output: $PILOT_CONFIG_DIR/$PILOT_INVENTORY

IOS_DIR="$PILOT_CONFIG_DIR/../../$PILOT_IOS_DIR"
OUT="$PILOT_CONFIG_DIR/$PILOT_INVENTORY"

if [ ! -d "$IOS_DIR" ]; then
  echo "<signal:failed>iOS project not found at $IOS_DIR</signal:failed>"
  exit 0
fi

echo "<signal:update>scanning $PILOT_IOS_DIR</signal:update>"

# Find all source files
SWIFT_FILES=$(find "$IOS_DIR" -name '*.swift' -not -path '*/Pods/*' -not -path '*/.build/*' -not -path '*/DerivedData/*' | sort)
OBJC_M_FILES=$(find "$IOS_DIR" -name '*.m' -not -path '*/Pods/*' -not -path '*/.build/*' | sort)
OBJC_H_FILES=$(find "$IOS_DIR" -name '*.h' -not -path '*/Pods/*' -not -path '*/.build/*' | sort)
STORYBOARDS=$(find "$IOS_DIR" -name '*.storyboard' -not -path '*/Pods/*' | sort)
XIBS=$(find "$IOS_DIR" -name '*.xib' -not -path '*/Pods/*' | sort)
PLISTS=$(find "$IOS_DIR" -name 'Info.plist' -not -path '*/Pods/*' | sort)

# Count
N_SWIFT=$(echo "$SWIFT_FILES" | grep -c . || true)
N_OBJC_M=$(echo "$OBJC_M_FILES" | grep -c . || true)
N_OBJC_H=$(echo "$OBJC_H_FILES" | grep -c . || true)
N_STORYBOARDS=$(echo "$STORYBOARDS" | grep -c . || true)
N_XIBS=$(echo "$XIBS" | grep -c . || true)

# LOC (Swift + Obj-C)
SWIFT_LOC=0
if [ -n "$SWIFT_FILES" ]; then
  SWIFT_LOC=$(echo "$SWIFT_FILES" | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}' || echo 0)
fi
OBJC_LOC=0
if [ -n "$OBJC_M_FILES" ]; then
  OBJC_LOC=$(echo "$OBJC_M_FILES" | xargs wc -l 2>/dev/null | tail -1 | awk '{print $1}' || echo 0)
fi

# Dependencies — CocoaPods
PODS="[]"
PODFILE="$IOS_DIR/Podfile"
if [ -f "$PODFILE" ]; then
  PODS=$(grep -E "^\s*pod\s+" "$PODFILE" | sed "s/.*pod\s*['\"]//;s/['\"].*//" | jq -R . | jq -s . 2>/dev/null || echo "[]")
fi

# Dependencies — SPM
SPM="[]"
PACKAGE_SWIFT="$IOS_DIR/Package.swift"
if [ -f "$PACKAGE_SWIFT" ]; then
  SPM=$(grep -E '\.package\(' "$PACKAGE_SWIFT" | sed 's/.*url:\s*"//;s/".*//' | jq -R . | jq -s . 2>/dev/null || echo "[]")
fi

# Xcode project name
PROJECT_NAME=""
XCODEPROJ=$(find "$IOS_DIR" -maxdepth 2 -name '*.xcodeproj' -print -quit 2>/dev/null || true)
if [ -n "$XCODEPROJ" ]; then
  PROJECT_NAME=$(basename "$XCODEPROJ" .xcodeproj)
fi

# Make paths relative to iOS dir
make_relative() {
  while IFS= read -r f; do
    [ -z "$f" ] && continue
    echo "$f" | sed "s|^$IOS_DIR/||"
  done
}

# Build JSON
cat > "$OUT" <<INVENTORY
{
  "project_name": "$(echo "$PROJECT_NAME" | jq -R .)",
  "ios_dir": "$PILOT_IOS_DIR",
  "swift_files": $(echo "$SWIFT_FILES" | make_relative | jq -R . | jq -s .),
  "objc_m_files": $(echo "$OBJC_M_FILES" | make_relative | jq -R . | jq -s .),
  "objc_h_files": $(echo "$OBJC_H_FILES" | make_relative | jq -R . | jq -s .),
  "storyboards": $(echo "$STORYBOARDS" | make_relative | jq -R . | jq -s .),
  "xibs": $(echo "$XIBS" | make_relative | jq -R . | jq -s .),
  "cocoapods": $PODS,
  "spm_packages": $SPM,
  "stats": {
    "swift_files": $N_SWIFT,
    "objc_m_files": $N_OBJC_M,
    "objc_h_files": $N_OBJC_H,
    "storyboards": $N_STORYBOARDS,
    "xibs": $N_XIBS,
    "swift_loc": $SWIFT_LOC,
    "objc_loc": $OBJC_LOC,
    "total_loc": $((SWIFT_LOC + OBJC_LOC))
  }
}
INVENTORY

echo "Project: $PROJECT_NAME"
echo "Swift: $N_SWIFT files ($SWIFT_LOC LOC), Obj-C: $N_OBJC_M files ($OBJC_LOC LOC)"
echo "Storyboards: $N_STORYBOARDS, XIBs: $N_XIBS"
echo "CocoaPods: $(echo "$PODS" | jq length), SPM: $(echo "$SPM" | jq length)"
echo "<signal:ready>$PILOT_IOS_DIR</signal:ready>"
