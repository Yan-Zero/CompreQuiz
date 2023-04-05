#!/bin/bash

# Delete the existing weights.yaml files and create new empty ones
find ./Data/* -name weights.yaml -delete
for dir in ./Data/*; do
    touch "$dir"/weights.yaml
done
# Add the files to the Git repository
git add ./Data/*/weights.yaml
# Mark the files as unchanged
git update-index --assume-unchanged ./Data/*/weights.yaml

