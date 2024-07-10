#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -e

# Update package lists and install Graphviz
apt-get update && apt-get install -y graphviz

# Install Python dependencies
pip install -r requirements.txt
