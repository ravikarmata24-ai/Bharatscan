#!/usr/bin/env bash
set -e

# Install ZBar system library (needed for pyzbar barcode scanning)
apt-get update && apt-get install -y libzbar0 libzbar-dev

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt