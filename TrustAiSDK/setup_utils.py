#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import shutil

def clean():
    """Clean build artifacts"""
    for dir_name in ['build', 'dist', 'ai_asset_obfuscate.egg-info']:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)

def parse_mode():
    """Parse mode and version from command line"""
    mode = "zh"
    version = "1.0.0"
    for arg in sys.argv:
        if arg.startswith('--mode='):
            mode = arg.split('=')[1]
        elif arg.startswith('--version='):
            version = arg.split('=')[1]
    return mode, version

def get_setup_config(mode, version):
    """Get setup configuration"""
    from setuptools import find_packages
    
    config = {
        'name': "ai_asset_obfuscate",
        'version': version,
        'packages': find_packages(),
        'include_package_data': True,
        'description': "Trust AI SDK for model and data asset obfuscation",
        'author': "Huawei Technologies Co., Ltd",
        'author_email': "",
        'classifiers': [
            "Programming Language :: Python :: 3",
            "Operating System :: OS Independent",
        ],
        'python_requires': '>=3.11',
    }
    return config