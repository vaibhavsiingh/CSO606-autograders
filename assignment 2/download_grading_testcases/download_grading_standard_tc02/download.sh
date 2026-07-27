#!/bin/bash

# Autograder - Download Script
# Usage: ./download.sh <link to directory> <cut-dirs argument>
# Downloads directory structure from URL and saves as mock_grading

if [ $# -ne 2 ]; then
    echo "Usage: ./download.sh <link to directory> <cut-dirs argument>"
    exit 1
fi

LINK="$1"
CUT_DIRS="$2"

# Download the directory recursively using wget
# -r: recursive
# -np: no parent (don't go to parent directories)
# -R: reject specified files (index.html and .tmp files)
# -q: quiet mode
# --cut-dirs: cut specified number of directory levels
# -nH: don't create host directory

wget -r \
    -np \
    -R "index.html,*.tmp" \
    -q \
    --cut-dirs="$CUT_DIRS" \
    -nH \
    "$LINK"

# Extract the directory name from the URL (last part before the trailing slash)
REMOTE_DIR_NAME=$(echo "$LINK" | sed 's|/$||' | xargs basename)

# Find what was actually downloaded (look for directories at the top level)
# After wget with cut-dirs, the downloaded content should be in a directory
# We need to find it and rename it to mock_grading if it has a different name

# The downloaded directory will be the first directory created
DOWNLOADED_DIR=$(find . -maxdepth 1 -type d ! -name "." | head -1)

if [ -n "$DOWNLOADED_DIR" ] && [ "$DOWNLOADED_DIR" != "./mock_grading" ]; then
    # Check if the directory name is not mock_grading, then rename it
    CURRENT_NAME=$(basename "$DOWNLOADED_DIR")
    if [ "$CURRENT_NAME" != "mock_grading" ]; then
        mv "$DOWNLOADED_DIR" mock_grading
    fi
fi

# Ensure the directory is named mock_grading
if [ ! -d "mock_grading" ]; then
    # If still not found, try to find the directory with expected contents
    if [ -d "bash-assignment" ]; then
        mv "bash-assignment" mock_grading
    fi
fi
