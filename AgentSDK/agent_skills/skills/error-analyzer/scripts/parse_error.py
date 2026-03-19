#!/usr/bin/env python3
"""
Error Parser Script for Error Analyzer - Ascend NPU

Parses error logs and extracts structured information for analysis.
Supports multiple output formats: JSON, Markdown, and Summary.
"""

import argparse
import json
import logging
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Constants for duplicate string literals
_KEY_ENVIRONMENT = 'environment'
_FORMAT_JSON = 'json'


# Common error patterns for categorization
ERROR_CATEGORIES = {
    'npu': [
        r'NPU out of memory',
        r'ascend.*error',
        r'ACL error',
        r'CANN',
        r'NPU error',
        r'hiai.*error',
        r'ascend.*initialize',
    ],
    'multimodal': [
        r'mm\..*error',
        r'MultimodalSDK',
        r'AdapterError',
        r'TensorError',
    ],
    'vision': [
        r'mxvision',
        r'mxstream',
        r'Image.*decode.*error',
        r'Video.*decode.*error',
    ],
    'network': [
        r'socket\.gaierror',
        r'ConnectionError',
        r'Connection refused',
        r'TimeoutError',
        r'Name or service not known',
    ],
    'import': [
        r'ImportError',
        r'ModuleNotFoundError',
        r'cannot import',
    ],
    'memory': [
        r'OutOfMemoryError',
        r'OOM',
        r'MemoryError',
        r'Cannot allocate memory',
    ],
    'permission': [
        r'Permission denied',
        r'PermissionError',
        r'No such file or directory',
    ],
    'configuration': [
        r'KeyError',
        r'ValueError',
        r'yaml.*error',
        r'Configuration',
    ],
    'distributed': [
        r'distributed.*error',
        r'NCCL',
        r'RayTaskError',
        r'ProcessGroup',
    ],
}


def categorize_error(error_message: str) -> List[str]:
    """Categorize error based on patterns."""
    categories = []
    error_lower = error_message.lower()
    
    for category, patterns in ERROR_CATEGORIES.items():
        for pattern in patterns:
            if re.search(pattern, error_lower, re.IGNORECASE):
                if category not in categories:
                    categories.append(category)
                break
    
    return categories if categories else ['unknown']


def extract_error_type(error_message: str) -> str:
    """Extract the main error type from the message."""
    # Common error type patterns
    patterns = [
        r'(\w+Error)',
        r'(\w+Exception)',
        r'(RuntimeError)',
        r'(Process.*(?:exited|killed))',
        r'(Failed.*?:)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, error_message, re.IGNORECASE)
        if match:
            return match.group(1)
    
    # Default to first significant word
    words = error_message.split()
    return words[0] if words else 'UnknownError'


def extract_file_paths(traceback: str) -> List[Dict[str, Any]]:
    """Extract file paths and line numbers from traceback."""
    paths = []
    # Pattern: File "path", line N
    pattern = r'File "([^"]+)", line (\d+)'
    
    for match in re.finditer(pattern, traceback):
        paths.append({
            'file': match.group(1),
            'line': int(match.group(2))
        })
    
    return paths


def extract_npu_info(environment: str) -> Dict[str, str]:
    """Extract NPU-related information from environment string."""
    npu_info = {}
    
    # CANN version
    cann_match = re.search(r'CANN\s*(\d+\.\d+)', environment, re.IGNORECASE)
    if cann_match:
        npu_info['cann_version'] = cann_match.group(1)
    
    # NPU device
    npu_match = re.search(r'NPU\s*(\d+)', environment, re.IGNORECASE)
    if npu_match:
        npu_info['npu_device'] = npu_match.group(1)
    
    # Ascend
    ascend_match = re.search(r'Ascend\s*(\w+)', environment, re.IGNORECASE)
    if ascend_match:
        npu_info['ascend_type'] = ascend_match.group(1)
    
    # Device ID
    device_id_match = re.search(r'device[_\s]?id\s*[=:]?\s*(\d+)', environment, re.IGNORECASE)
    if device_id_match:
        npu_info['device_id'] = device_id_match.group(1)
    
    return npu_info


def extract_python_info(environment: str) -> Dict[str, str]:
    """Extract Python and package information from environment string."""
    info = {}
    
    # Python version
    py_match = re.search(r'Python\s*(\d+\.\d+)', environment, re.IGNORECASE)
    if py_match:
        info['python_version'] = py_match.group(1)
    
    # Common packages
    packages = ['torch', 'tensorflow', 'mmcv', 'pillow', 'numpy', 'transformers']
    for pkg in packages:
        pkg_match = re.search(rf'{pkg}[-_]?(\d+\.\d+(?:\.\d+)?)', environment, re.IGNORECASE)
        if pkg_match:
            info[f'{pkg}_version'] = pkg_match.group(1)
    
    return info


def parse_error_log(error_log: str, environment: str = "", context: str = "") -> Dict[str, Any]:
    """Parse error log and extract structured information."""
    
    # Clean up the error log
    error_log = error_log.strip()
    
    # Extract main error message (first line or error: portion)
    lines = error_log.split('\n')
    main_error = lines[0] if lines else error_log
    
    # Extract traceback if present
    traceback = ""
    if 'Traceback' in error_log:
        tb_start = error_log.find('Traceback')
        traceback = error_log[tb_start:]
    
    # Parse components
    result = {
        'error_type': extract_error_type(main_error),
        'error_message': main_error,
        'full_error': error_log,
        'categories': categorize_error(main_error),
        'traceback': traceback,
        'file_paths': extract_file_paths(traceback),
        _KEY_ENVIRONMENT: {
            'raw': environment,
            'npu_info': extract_npu_info(environment),
            'python_info': extract_python_info(environment),
        },
        'context': context,
        'npu_specific': 'npu' in categorize_error(main_error) or 
                       'multimodal' in categorize_error(main_error) or 
                       'vision' in categorize_error(main_error),
    }
    
    return result


def format_json(data: Dict[str, Any]) -> str:
    """Format output as JSON."""
    return json.dumps(data, indent=2, ensure_ascii=False)


def format_markdown(data: Dict[str, Any]) -> str:
    """Format output as Markdown."""
    lines = [
        "# Error Analysis",
        "",
        "## Error Information",
        f"**Type**: {data['error_type']}",
        f"**Message**: {data['error_message']}",
        "",
        f"**Categories**: {', '.join(data['categories'])}",
        "",
    ]
    
    if data['file_paths']:
        lines.append("## File Locations")
        for path in data['file_paths'][:5]:  # Limit to 5
            lines.append(f"- `{path['file']}` line {path['line']}")
        lines.append("")
    
    if data[_KEY_ENVIRONMENT]['npu_info']:
        lines.append("## NPU Information")
        for key, value in data[_KEY_ENVIRONMENT]['npu_info'].items():
            lines.append(f"- **{key}**: {value}")
        lines.append("")
    
    if data[_KEY_ENVIRONMENT]['python_info']:
        lines.append("## Python Environment")
        for key, value in data[_KEY_ENVIRONMENT]['python_info'].items():
            lines.append(f"- **{key}**: {value}")
        lines.append("")
    
    if data['traceback']:
        lines.append("## Traceback")
        lines.append("```")
        lines.append(data['traceback'][:500])  # Limit traceback length
        lines.append("```")
        lines.append("")
    
    if data['context']:
        lines.append(f"**Context**: {data['context']}")
    
    return '\n'.join(lines)


def format_summary(data: Dict[str, Any]) -> str:
    """Format output as short summary."""
    npu_info = data[_KEY_ENVIRONMENT]['npu_info']
    npu_str = ""
    if npu_info:
        npu_str = f" [NPU: {npu_info.get('cann_version', 'unknown')}]"
    
    return f"[{data['error_type']}] {data['error_message'][:100]}{npu_str} ({', '.join(data['categories'])})"


def main():
    parser = argparse.ArgumentParser(
        description='Parse error logs and extract structured information'
    )
    parser.add_argument('input', nargs='?', help='Error log text or file path (use -f for file)')
    parser.add_argument('-f', '--file', help='Read error from file')
    parser.add_argument('-e', '--env', '--environment', help='Environment information')
    parser.add_argument('-c', '--context', help='Context information')
    parser.add_argument('-o', '--output', choices=[_FORMAT_JSON, 'markdown', 'summary'], 
                        default=_FORMAT_JSON, help='Output format')
    parser.add_argument('-i', '--interactive', action='store_true',
                        help='Interactive mode')
    
    args = parser.parse_args()
    
    # Handle interactive mode
    if args.interactive:
        logger.info("Error Analyzer - Interactive Mode")
        logger.info("=" * 40)
        error_log = input("\nEnter error message/log (Ctrl+D to finish):\n")
        try:
            error_log += "\n" + sys.stdin.read()
        except (EOFError, KeyboardInterrupt):
            pass
        
        environment = input("\nEnter environment info (or press Enter to skip):\n")
        context = input("\nEnter context (or press Enter to skip):\n")
    elif args.file:
        error_log = Path(args.file).read_text()
        environment = args.env or ""
        context = args.context or ""
    elif args.input:
        # Check if input is a file path
        if Path(args.input).exists():
            error_log = Path(args.input).read_text()
        else:
            error_log = args.input
        environment = args.env or ""
        context = args.context or ""
    else:
        parser.print_help()
        return 1
    
    # Parse error
    result = parse_error_log(error_log, environment, context)
    
    # Format output
    if args.output == _FORMAT_JSON:
        logger.info(format_json(result))
    elif args.output == 'markdown':
        logger.info(format_markdown(result))
    else:
        logger.info(format_summary(result))
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
