#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
from setuptools import setup, find_packages, Extension
from setuptools.command.build_ext import build_ext
from setuptools.command.bdist_wheel import bdist_wheel
import sys
import os
import shutil
import platform
import glob
import warnings
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s]: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Filter out the license warning
warnings.filterwarnings("ignore", message="File '.*LICENSE' cannot be found")

SOURCE_CODE_URL = "https://gitcode.com/Ascend/mindsdk-referenceapps"

# 自定义版本号处理类，确保版本号不被规范化
class NonNormalizingVersion:
    """Custom version class that preserves the original version string"""
    def __init__(self, version_str):
        self.version_str = version_str
    
    def __str__(self):
        return self.version_str
    
    def __repr__(self):
        return f"NonNormalizingVersion('{self.version_str}')"
    
    def __eq__(self, other):
        if isinstance(other, NonNormalizingVersion):
            return self.version_str == other.version_str
        return self.version_str == str(other)
    
    def __ne__(self, other):
        return not self.__eq__(other)


class CrossBuildExt(build_ext):
    """Custom build_ext command for cross compilation"""
    
    def build_extensions(self):
        """Handle cross compilation settings"""
        
        # Check if we're cross-compiling for aarch64 on x86_64
        is_cross_compile = (
            platform.machine() in ['x86_64', 'amd64'] and 
            any(arg.startswith('--plat-name=') and 'aarch64' in arg for arg in sys.argv)
        )
        
        if is_cross_compile:
            logger.info("=" * 60)
            logger.info("Cross-compiling for aarch64 on x86_64 platform")
            logger.info("=" * 60)
            
            # Set cross-compilation environment variables
            os.environ.setdefault('CC', 'aarch64-linux-gnu-gcc')
            os.environ.setdefault('CXX', 'aarch64-linux-gnu-g++')
            os.environ.setdefault('AR', 'aarch64-linux-gnu-ar')
            os.environ.setdefault('LD', 'aarch64-linux-gnu-ld')
            os.environ.setdefault('STRIP', 'aarch64-linux-gnu-strip')
            
            # Set compilation flags for aarch64
            cflags = os.environ.get('CFLAGS', '')
            cxxflags = os.environ.get('CXXFLAGS', '')
            ldflags = os.environ.get('LDFLAGS', '')
            
            # Add architecture-specific flags
            os.environ['CFLAGS'] = f'-target aarch64-linux-gnu -march=armv8-a {cflags}'
            os.environ['CXXFLAGS'] = f'-target aarch64-linux-gnu -march=armv8-a {cxxflags}'
            os.environ['LDFLAGS'] = f'-target aarch64-linux-gnu {ldflags}'
            
            # Check if cross-compiler is available
            if not shutil.which('aarch64-linux-gnu-gcc'):
                logger.warning("aarch64 cross-compiler not found!")
                logger.warning("Please install the cross-compilation toolchain:")
                logger.warning("  Ubuntu/Debian: sudo apt-get install gcc-aarch64-linux-gnu g++-aarch64-linux-gnu")
                logger.warning("  CentOS/RHEL:   sudo yum install gcc-aarch64-linux-gnu gcc-c++-aarch64-linux-gnu")
        
        # Build extensions
        build_ext.build_extensions(self)


class CrossBdistWheel(bdist_wheel):
    """Custom bdist_wheel command for cross compilation with proper platform tags"""
    
    def finalize_options(self):
        """Handle platform name for cross compilation"""
        # Call parent class finalize_options first
        super().finalize_options()
        
        # If we're cross-compiling, set the platform name to manylinux2014_aarch64
        if self.plat_name is None:
            # Check if we're cross-compiling based on environment
            is_cross_compile = (
                platform.machine() in ['x86_64', 'amd64'] and 
                os.environ.get('_CROSS_COMPILE_AARCH64') == '1'
            )
            
            if is_cross_compile:
                self.plat_name = 'manylinux2014_aarch64'
                logger.info(f"Setting platform name to: {self.plat_name} (compatible with PyPI)")
    
    def get_tag(self):
        """Return the wheel tag with proper platform tag for PyPI compatibility"""
        python_tag, abi_tag, plat_tag = super().get_tag()
        
        # 处理所有 linux_ 开头的平台标签
        if plat_tag.startswith('linux_'):
            # 检查是否应该使用 manylinux 标签
            use_manylinux = os.environ.get('USE_MANYLINUX', '1') == '1'
            
            if use_manylinux:
                # 确定 manylinux 版本
                manylinux_version = os.environ.get('MANYLINUX_VERSION', '2014')
                i686 = "i686"
                # 架构映射
                arch_map = {
                    'x86_64': 'x86_64',
                    'aarch64': 'aarch64',
                    i686: i686,
                    'i386': i686
                }
                
                # 确定架构
                arch = None
                for key in arch_map:
                    if key in plat_tag:
                        arch = arch_map[key]
                        break
                
                if arch:
                    # 生成 manylinux 标签
                    if manylinux_version == '2010':
                        new_plat_tag = f'manylinux2010_{arch}'
                    elif manylinux_version == '2014':
                        new_plat_tag = f'manylinux2014_{arch}'
                    elif manylinux_version == '2_24':
                        new_plat_tag = f'manylinux_2_24_{arch}'
                    elif manylinux_version == '2_28':
                        new_plat_tag = f'manylinux_2_28_{arch}'
                    else:
                        new_plat_tag = f'manylinux2014_{arch}'  # 默认
                    logger.info(f"Converting {arch} platform tag from '{plat_tag}' to '{new_plat_tag}' for PyPI compatibility")
                else:
                    # 其他架构，保留原标签并给出警告
                    logger.warning(f"Unknown architecture in platform tag '{plat_tag}', keeping as is")
                    new_plat_tag = plat_tag
                
                plat_tag = new_plat_tag
        
        return (python_tag, abi_tag, plat_tag)


def clean():
    """Clean build artifacts"""
    dirs_to_clean = ['build', 'dist', 'ai_asset_obfuscate.egg-info']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            logger.info(f"Cleaning {dir_name}...")
            shutil.rmtree(dir_name)


def parse_mode():
    """Parse mode and version from command line"""
    mode = "zh"
    version = "1.0.0"
    
    # First read version from version file if it exists
    version_file = os.path.join(os.path.dirname(__file__), 'version')
    if os.path.exists(version_file):
        with open(version_file, 'r') as f:
            version = f.read().strip()
    
    # Process command line arguments
    args_to_remove = []
    for arg in sys.argv[:]:
        if arg.startswith('--mode='):
            mode = arg.split('=')[1]
            args_to_remove.append(arg)
        elif arg.startswith('--version='):
            version = arg.split('=')[1]
            args_to_remove.append(arg)
    
    # Remove processed args to avoid confusing setuptools
    for arg in args_to_remove:
        sys.argv.remove(arg)
    
    return mode, version


def find_package_data():
    """Find all package data files"""
    package_data = {}
    
    # Find all packages
    packages = find_packages()
    
    for package in packages:
        package_data[package] = []
        package_dir = package.replace('.', '/')
        
        # Common data file patterns
        data_patterns = [
            'conf/**/*',
            'libs/**/*',
            'data/**/*',
            'resources/**/*',
            '*.so',
            '*.dll',
            '*.dylib',
            '*.bin',
            '*.model',
            '*.pb',
            '*.onnx',
        ]
        
        # Check if directories exist and add files
        for pattern in data_patterns:
            search_pattern = os.path.join(package_dir, pattern)
            matched_files = glob.glob(search_pattern, recursive=True)
            for file in matched_files:
                if os.path.isfile(file):
                    # Get the path relative to the package
                    rel_path = os.path.relpath(file, package_dir)
                    if rel_path not in package_data[package]:
                        package_data[package].append(rel_path)
    
    return package_data


def get_long_description():
    """Get long description from README file"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Try different README file names
    readme_names = ['README.md', 'README.rst', 'README.txt', 'README']
    for readme_name in readme_names:
        readme_path = os.path.join(current_dir, readme_name)
        if os.path.exists(readme_path):
            with open(readme_path, 'r', encoding='utf-8') as f:
                return f.read()
    
    # Return empty string if no README found
    return ""


def get_setup_config(mode, version):
    """Get setup configuration"""
    # Get package data
    package_data = find_package_data()
    packages = find_packages()
    
    # 确保版本号保持原始形式
    original_version = version
    
    # Basic configuration - avoid using fields that might conflict with pyproject.toml
    config = {
        'name': "ai-asset-obfuscate",
        'version': original_version,
        'packages': packages,
        'package_dir': {'': '.'},
        'include_package_data': True,
        'package_data': package_data,
        'exclude_package_data': {
            '': ['tests/*', 'test/*', 'examples/*', 'docs/*', 'build/*'],
        },
        'author': "Huawei Technologies Co., Ltd",
        'author_email': "",
        'url': SOURCE_CODE_URL,
        'project_urls': {
            'Documentation': SOURCE_CODE_URL,
            'Source Code': SOURCE_CODE_URL,
        },
        'license': "Apache License 2.0",
        'classifiers': [
            "Development Status :: 5 - Production/Stable",
            "Intended Audience :: Developers",
            "Topic :: Software Development :: Build Tools",
            "License :: OSI Approved :: Apache Software License",
            "Programming Language :: Python :: 3",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Programming Language :: Python :: 3.13",
            "Operating System :: POSIX :: Linux",
            "Operating System :: MacOS :: MacOS X",
            "Operating System :: Microsoft :: Windows",
        ],
        'python_requires': '>=3.8',
        'install_requires': [],
        'extras_require': {
            'dev': [
                'pytest>=6.0',
                'pytest-cov>=2.0',
                'flake8>=3.0',
                'black>=22.0',
            ],
            'test': [
                'pytest>=6.0',
                'pytest-cov>=2.0',
            ],
        },
        'ext_modules': [],
        'cmdclass': {
            'build_ext': CrossBuildExt,
            'bdist_wheel': CrossBdistWheel,
        },
        'zip_safe': False,
    }
    
    # Only add description and long_description if we have them
    description = "Trust AI SDK for model and data asset obfuscation"
    config['description'] = description
    
    long_desc = get_long_description()
    if long_desc:
        config['long_description'] = long_desc
        config['long_description_content_type'] = 'text/markdown'
    
    return config


def create_license_file_if_needed():
    """Create a LICENSE file from outer License.md if it exists"""
    # Read from the outer License.md
    outer_license_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'License.md')
    license_path = os.path.join(os.path.dirname(__file__), 'LICENSE')
    
    if os.path.exists(outer_license_path):
        logger.info(f"Reading license from outer License.md: {outer_license_path}")
        with open(outer_license_path, 'r') as f:
            license_content = f.read()
        with open(license_path, 'w') as f:
            f.write(license_content)
    else:
        logger.info(f"Outer License.md not found at: {outer_license_path}")
        logger.info("LICENSE file will not be created")


def create_version_file_if_needed():
    """Create a basic version file if it doesn't exist"""
    version_path = os.path.join(os.path.dirname(__file__), 'version')
    if not os.path.exists(version_path):
        logger.info("Creating version file...")
        with open(version_path, 'w') as f:
            f.write("1.0.0")


def main():
    """Main entry point"""
    # Create required files if they don't exist
    create_version_file_if_needed()
    create_license_file_if_needed()
    
    # Print build information
    logger.info("="*60)
    logger.info("AI Asset Obfuscate Package Builder")
    logger.info("="*60)
    logger.info(f"Python version: {platform.python_version()}")
    logger.info(f"Platform: {platform.machine()} ({platform.system()})")
    logger.info(f"Current directory: {os.getcwd()}")
    
    # Clean build artifacts
    clean()
    
    # Parse command line arguments
    mode, version = parse_mode()
    logger.info(f"Mode: {mode}")
    logger.info(f"Version: {version}")
    
    # Get platform name from arguments
    plat_name = None
    
    for arg in sys.argv[:]:
        if arg.startswith('--plat-name='):
            plat_name = arg.split('=')[1]
            logger.info(f"Building for platform: {plat_name}")
            
            # Set environment variable for cross compilation detection
            if 'aarch64' in plat_name:
                os.environ['_CROSS_COMPILE_AARCH64'] = '1'
            
            # ===== 更新点：为 x86_64 添加警告信息 =====
            if plat_name == 'linux_x86_64':
                logger.warning("'linux_x86_64' platform tag is not accepted by PyPI!")
                logger.warning("The wheel will be built with 'manylinux2014_x86_64' tag for PyPI compatibility.")
                logger.warning("To use a different manylinux version, set the MANYLINUX_VERSION environment variable.")
                logger.warning("  export MANYLINUX_VERSION=2014  (for manylinux2014_x86_64)")
                logger.warning("  export MANYLINUX_VERSION=2_24  (for manylinux_2_24_x86_64)")
                logger.warning("  export MANYLINUX_VERSION=2_28  (for manylinux_2_28_x86_64)")
            
            elif plat_name == 'linux_aarch64':
                logger.warning("'linux_aarch64' platform tag is not accepted by PyPI!")
                logger.warning("The wheel will be built with 'manylinux2014_aarch64' tag for PyPI compatibility.")
                logger.warning("To use a different manylinux version, set the MANYLINUX_VERSION environment variable.")
                logger.warning("  export MANYLINUX_VERSION=2014  (for manylinux2014_aarch64)")
                logger.warning("  export MANYLINUX_VERSION=2_24  (for manylinux_2_24_aarch64)")
                logger.warning("  export MANYLINUX_VERSION=2_28  (for manylinux_2_28_aarch64)")
            
            # Remove the argument
            sys.argv.remove(arg)
            break
    
    # Get configuration
    config = get_setup_config(mode, version)
    
    # Call setup with explicit platform specification
    try:
        if plat_name:
            logger.info(f"Creating wheel with platform tag: {plat_name}")
            
            # Create options dictionary for bdist_wheel
            bdist_wheel_options = {'plat_name': plat_name}
            
            # Call setup with options
            setup(**config, options={'bdist_wheel': bdist_wheel_options})
        else:
            logger.info("Creating wheel for native platform")
            setup(**config)
        
        logger.info("Build completed successfully!")
        dist = "dist"
        # Show output files
        if os.path.exists(dist):
            logger.info("Generated wheel files:")
            for file in os.listdir(dist):
                if file.endswith('.whl'):
                    file_size = os.path.getsize(os.path.join(dist, file))
                    size_str = f"{file_size / 1024:.2f} KB"
                    if file_size > 1024 * 1024:
                        size_str = f"{file_size / (1024 * 1024):.2f} MB"
                    logger.info(f"  {file} ({size_str})")
                    
    except Exception as e:
        logger.error(f"Build failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()