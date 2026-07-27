#!/bin/bash

# Autograder - Organise Script
# Usage: ./organise.sh
# Creates organised directory with student folders and symbolic links to submitted files

# Create the organised directory
mkdir -p organised

# Read the roll list from mock_grading/roll_list
if [ ! -f "mock_grading/roll_list" ]; then
    echo "Error: mock_grading/roll_list not found"
    exit 1
fi

# For each roll number in the roll_list
while IFS= read -r ROLL_NO; do
    # Skip empty lines
    [ -z "$ROLL_NO" ] && continue
    
    # Create a directory for each student
    mkdir -p "organised/$ROLL_NO"
    
    # Find all files that start with this roll number in the submissions directory
    for file in mock_grading/submissions/${ROLL_NO}*; do
        if [ -f "$file" ]; then
            # Get the filename (not the full path)
            filename=$(basename "$file")
            
            # Create a symbolic link from the student's directory to their file
            # Using relative paths: from organised/ROLL_NO/filename to ../../mock_grading/submissions/filename
            ln -sf "../../mock_grading/submissions/$filename" "organised/$ROLL_NO/$filename"
        fi
    done
done < mock_grading/roll_list
