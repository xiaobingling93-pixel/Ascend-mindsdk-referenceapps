#!/bin/bash
# -*- coding:utf-8 -*-
# Copyright 2025 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

set -e  # 遇到错误立即退出

echo "=========================================="
echo "begin to build ai_asset_obfuscate"
echo "=========================================="

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
echo "Script directory: ${SCRIPT_DIR}"

# 切换到脚本目录
cd "${SCRIPT_DIR}"

# Parse command line arguments
ARCH="x86_64"  # Default architecture is x86_64

# Process command line arguments
for arg in "$@" ; do
    case $arg in
        --arch=*)
            ARCH="${arg#*=}"
            ;;
        --help)
            echo "Usage: $0 [--arch=x86_64|aarch64]"
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg"
            exit 1
            ;;
    esac
done

echo "Building for architecture: $ARCH"

# Set platform name based on architecture
if [ "$ARCH" == "aarch64" ]; then
    PLATFORM="linux_aarch64"
    # Set cross-compilation environment variables
    export CC=aarch64-linux-gnu-gcc
    export CXX=aarch64-linux-gnu-g++
    export LDSHARED="aarch64-linux-gnu-gcc -shared"
    export _CROSS_COMPILE_AARCH64=1
    export _PYTHON_HOST_PLATFORM="linux_aarch64"
    
    # Check if cross-compiler is installed
    if ! command -v aarch64-linux-gnu-gcc &> /dev/null; then
        echo "❌ aarch64-linux-gnu-gcc not found!"
        echo "Please install cross-compilation toolchain:"
        echo "  sudo apt-get install gcc-aarch64-linux-gnu g++-aarch64-linux-gnu"
        exit 1
    fi
else
    PLATFORM="linux_x86_64"
    unset _CROSS_COMPILE_AARCH64
    unset _PYTHON_HOST_PLATFORM
fi

echo "Building for platform: $PLATFORM"

# Download and extract architecture-specific so files
BASE_URL="https://ascend-repo.obs.cn-east-2.myhuaweicloud.com/libs/ai_asset_obfuscate"
if [ "$ARCH" == "aarch64" ]; then
    URL="${BASE_URL}/ai_asset_obfuscate_libs_aarch64.zip"
else
    URL="${BASE_URL}/ai_asset_obfuscate_libs_x86_64.zip"
fi

# Create output directory (using relative path)
OUTPUT_DIR="./output"
mkdir -p "${OUTPUT_DIR}"
echo "Output directory: ${OUTPUT_DIR}"

# Clean up old temporary directories if they exist
if [ -d "./tmp" ]; then
    echo "Cleaning up old temporary directories..."
    rm -rf "./tmp/*"
fi

# Create temporary directory
TMP_DIR="./tmp/ai_asset_obfuscate_build_$(date +%Y%m%d_%H%M%S)"
mkdir -p "${TMP_DIR}"
echo "Temporary directory: ${TMP_DIR}"

# Create a temporary copy of the project
TMP_PROJECT_DIR="${TMP_DIR}/project"
mkdir -p "${TMP_PROJECT_DIR}"

# Copy all project files to temporary directory (excluding unnecessary files)
echo "Copying project files to temporary directory..."
rsync -av --exclude='__pycache__' \
          --exclude='*.pyc' \
          --exclude='.git' \
          --exclude='output' \
          --exclude='dist' \
          --exclude='build' \
          --exclude='*.egg-info' \
          --exclude='tmp' \
          "${SCRIPT_DIR}/" "${TMP_PROJECT_DIR}/"

# Create libs directory
LIBS_DIR="${TMP_PROJECT_DIR}/ai_asset_obfuscate/libs"
mkdir -p "${LIBS_DIR}"

# Download the zip file
echo "Downloading $ARCH so files from $URL"
if ! wget -q --show-progress -O "${TMP_DIR}/ai_asset_obfuscate_libs.zip" "$URL"; then
    echo "❌ Failed to download from $URL"
    exit 1
fi

# Extract the zip file
echo "Extracting so files..."
unzip -q -o "${TMP_DIR}/ai_asset_obfuscate_libs.zip" -d "${TMP_DIR}/"

# Copy so files to libs directory
echo "Copying so files to libs directory..."
find "${TMP_DIR}" -name "*.so" -type f -exec cp -v {} "${LIBS_DIR}/" \;

# Verify so files were copied
SO_COUNT=$(find "${LIBS_DIR}" -name "*.so" | wc -l)
echo "Copied $SO_COUNT .so files to ${LIBS_DIR}"

# Create version file if it doesn't exist
if [ ! -f "${TMP_PROJECT_DIR}/version" ]; then
    echo "1.0.0" > "${TMP_PROJECT_DIR}/version"
    echo "Created version file with default version 1.0.0"
fi

# Clean up zip file
rm -f "${TMP_DIR}/ai_asset_obfuscate_libs.zip"

# Build wheel package
echo ""
echo "=========================================="
echo "Building wheel package for $PLATFORM"
echo "=========================================="

cd "${TMP_PROJECT_DIR}"

# Clean any existing build artifacts
rm -rf build dist *.egg-info

# Print Python version and environment
echo "Python version:"
python3 --version
echo "Pip version:"
pip3 --version

# Install build dependencies
echo "Installing build dependencies..."
pip3 install --upgrade pip setuptools wheel

# Build wheel with explicit platform specification
echo "Running setup.py bdist_wheel --plat-name=$PLATFORM"
python3 setup.py bdist_wheel --plat-name="$PLATFORM"

# Check if wheel was created
if [ ! -d "dist" ] || [ -z "$(ls -A dist)" ]; then
    echo "❌ No wheel file created in dist directory"
    echo "Build output:"
    ls -la
    exit 1
fi

# Find the wheel file
echo ""
echo "=========================================="
echo "Finding wheel file"
echo "=========================================="
WHL_FILE=$(find dist -name "*.whl" -type f | head -1)

if [ -z "$WHL_FILE" ]; then
    echo "❌ No wheel file found in dist directory"
    echo "Contents of dist:"
    ls -la dist/
    exit 1
fi

WHL_FILENAME=$(basename "$WHL_FILE")

echo "Found wheel file: $WHL_FILENAME"
echo "Full path: $WHL_FILE"

# Copy wheel file to output directory
echo ""
echo "=========================================="
echo "Copying wheel file to output directory"
echo "=========================================="
# Get the full path to the wheel file
WHEEL_FULL_PATH="$(pwd)/${WHL_FILE}"
# Use the SCRIPT_DIR variable defined at the beginning of the script
OUTPUT_FULL_PATH="${SCRIPT_DIR}/${OUTPUT_DIR}"

# Ensure output directory exists
mkdir -p "${OUTPUT_FULL_PATH}"

# Copy wheel file to output directory
cp -v "${WHEEL_FULL_PATH}" "${OUTPUT_FULL_PATH}/${WHL_FILENAME}"

# Verify the copy
if [ -f "${OUTPUT_FULL_PATH}/${WHL_FILENAME}" ]; then
    echo "✅ Successfully copied to: ${OUTPUT_FULL_PATH}/${WHL_FILENAME}"
    ls -la "${OUTPUT_FULL_PATH}/${WHL_FILENAME}"
else
    echo "❌ Failed to copy wheel file"
    exit 1
fi

# Verify wheel platform tag
echo ""
echo "=========================================="
echo "Verifying wheel platform tag"
echo "=========================================="
if command -v wheel &> /dev/null; then
    wheel tags "${OUTPUT_FULL_PATH}/${WHL_FILENAME}"
else
    unzip -p "${OUTPUT_FULL_PATH}/${WHL_FILENAME}" "*/WHEEL" | grep -E "Tag|Root-Is-Purelib"
fi

# Clean up temporary directory
echo ""
echo "=========================================="
echo "Cleaning up temporary directory"
echo "=========================================="

# Switch back to script directory before cleanup
cd "${SCRIPT_DIR}"

rm -rf "${TMP_DIR}"
echo "Temporary directory removed"

# Remove tmp directory completely
if [ -d "./tmp" ]; then
    rm -rf ./tmp
    echo "tmp directory removed"
fi

echo ""
echo "=========================================="
echo "✅ Build completed successfully!"
echo "=========================================="
echo "Generated wheel file: ${OUTPUT_FULL_PATH}/${WHL_FILENAME}"
echo "File size: $(du -h ${OUTPUT_FULL_PATH}/${WHL_FILENAME} | cut -f1)"
echo ""
echo "To install the wheel:"
echo "  pip install ${OUTPUT_FULL_PATH}/${WHL_FILENAME}"
echo ""
echo "finish build ai_asset_obfuscate"