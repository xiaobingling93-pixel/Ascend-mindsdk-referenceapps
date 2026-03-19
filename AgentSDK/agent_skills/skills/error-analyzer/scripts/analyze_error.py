#!/usr/bin/env python3
"""
Advanced Error Analysis Script for Error Analyzer - Ascend NPU

Provides deeper error analysis with optional repository context.
Can search source code for error strings and related patterns.
"""

import argparse
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Constants for duplicate string literals
_KEY_LIKELY_CAUSE = 'likely_cause'
_KEY_SOLUTIONS = 'solutions'
_MARKDOWN_CODE_BLOCK = '```'
_KEY_CATEGORIES = 'categories'


def search_repository(repo_path: str, error_message: str) -> Dict[str, Any]:
    """Search repository for error-related code."""
    results = {
        'files_matched': [],
        'error_strings_found': [],
        'config_files': [],
    }
    
    if not os.path.exists(repo_path):
        return results
    
    # Extract key error phrases
    phrases = re.findall(r'"([^"]+)"', error_message)
    phrases.extend(re.findall(r"'([^']+)'", error_message))
    phrases = [p for p in phrases if len(p) > 5][:5]
    
    # Search for error strings
    for root, dirs, files in os.walk(repo_path):
        dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv']]
        
        for file in files:
            if not file.endswith(('.py', '.yaml', '.yml', '.json', '.md')):
                continue
            
            file_path = os.path.join(root, file)
            
            try:
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    
                    # Check for error string matches
                    for phrase in phrases:
                        if phrase.lower() in content.lower():
                            line_num = content.lower().count(phrase.lower(), 0, content.lower().find(phrase.lower()) + len(phrase))
                            results['error_strings_found'].append({
                                'file': file_path,
                                'phrase': phrase,
                            })
                    
                    # Check for config files
                    if file in ['config.yaml', 'config.yml', 'settings.py', 'config.py']:
                        results['config_files'].append(file_path)
                        
            except IOError as e:
                logger.debug("Failed to read %s: %s", file_path, e)
    
    return results


def analyze_npu_error(error_message: str, environment: str) -> Dict[str, Any]:
    """Analyze NPU-specific errors."""
    analysis = {
        _KEY_LIKELY_CAUSE: '',
        _KEY_SOLUTIONS: [],
        'npu_checks': [],
    }
    
    error_lower = error_message.lower()
    
    # NPU Memory errors
    if 'npu out of memory' in error_lower or 'npu oom' in error_lower:
        analysis[_KEY_LIKELY_CAUSE] = 'NPU device memory exhausted'
        analysis[_KEY_SOLUTIONS] = [
            'Reduce batch size',
            'Enable memory optimization (gradient checkpointing)',
            'Use mixed precision training',
            'Clear NPU cache: npu-smi -r',
        ]
        analysis['npu_checks'] = [
            'Check NPU memory: npu-smi info',
            'Monitor memory during execution',
        ]
    
    # CANN errors
    elif 'cann' in error_lower or 'acl' in error_lower or 'ascend' in error_lower:
        if 'import' in error_lower or 'not found' in error_lower:
            analysis[_KEY_LIKELY_CAUSE] = 'CANN not properly installed or environment not set'
            analysis[_KEY_SOLUTIONS] = [
                'Source CANN environment: source /usr/local/Ascend/ascend-toolkit/set_env.sh',
                'Verify CANN installation: npu-smi info',
                'Reinstall CANN if needed',
            ]
        elif 'initialize' in error_lower:
            analysis[_KEY_LIKELY_CAUSE] = 'NPU initialization failed'
            analysis[_KEY_SOLUTIONS] = [
                'Check NPU device status: npu-smi info',
                'Verify driver installation',
                'Check device permissions',
            ]
        else:
            analysis[_KEY_LIKELY_CAUSE] = 'CANN runtime error'
            analysis[_KEY_SOLUTIONS] = [
                'Check CANN version compatibility',
                'Verify NPU device is available',
            ]
    
    # MultimodalSDK errors
    elif 'mm.' in error_lower or 'multimodalsdk' in error_lower:
        analysis[_KEY_LIKELY_CAUSE] = 'MultimodalSDK processing error'
        analysis[_KEY_SOLUTIONS] = [
            'Verify MultimodalSDK installation',
            'Check CANN compatibility',
            'Verify input data format',
        ]
    
    return analysis


def generate_response(error_info: Dict[str, Any], analysis: Dict[str, Any], 
                    repo_results: Dict[str, Any], output_format: str) -> str:
    """Generate customer-friendly response."""
    
    if output_format == 'json':
        return json.dumps({
            'error': error_info,
            'analysis': analysis,
            'repository': repo_results,
        }, indent=2)
    
    # Markdown format
    lines = [
        "# Error Analysis Result",
        "",
        f"**Error Type**: {error_info.get('error_type', 'Unknown')}",
        f"**Categories**: {', '.join(error_info.get(_KEY_CATEGORIES, []))}",
        "",
        "## Error Message",
        _MARKDOWN_CODE_BLOCK,
        error_info.get('error_message', '')[:200],
        _MARKDOWN_CODE_BLOCK,
        "",
    ]
    
    if analysis.get(_KEY_LIKELY_CAUSE):
        lines.extend([
            "## Root Cause Analysis",
            f"**Likely Cause**: {analysis[_KEY_LIKELY_CAUSE]}",
            "",
        ])
    
    if analysis.get(_KEY_SOLUTIONS):
        lines.extend([
            "## Suggested Solutions",
        ])
        for i, sol in enumerate(analysis[_KEY_SOLUTIONS], 1):
            lines.append(f"{i}. {sol}")
        lines.append("")
    
    if analysis.get('npu_checks'):
        lines.extend([
            "## NPU Diagnostic Commands",
            "```bash",
        ])
        for check in analysis['npu_checks']:
            lines.append(check)
        lines.extend([
            _MARKDOWN_CODE_BLOCK,
            "",
        ])
    
    if repo_results.get('error_strings_found'):
        lines.extend([
            "## Repository References",
        ])
        for ref in repo_results['error_strings_found'][:5]:
            lines.append(f"- Found in: `{ref['file']}`")
        lines.append("")
    
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='Advanced error analysis with repository context'
    )
    parser.add_argument('--error-log', required=True, help='Error log file or text')
    parser.add_argument('--env-info', help='Environment information')
    parser.add_argument('--repo-path', help='Path to repository for source code search')
    parser.add_argument('--output', choices=['json', 'markdown'], default='markdown')
    parser.add_argument('-o', '--out-file', help='Output file (default: stdout)')
    
    args = parser.parse_args()
    
    # Read error log
    if os.path.exists(args.error_log):
        error_log = Path(args.error_log).read_text()
    else:
        error_log = args.error_log
    
    env_info = args.env_info or ""
    
    # Basic error parsing
    error_info = {
        'error_type': 'Unknown',
        'error_message': error_log.strip().split('\n')[0],
        _KEY_CATEGORIES: [],
    }
    
    # Categorize
    error_lower = error_log.lower()
    if 'npu' in error_lower or 'ascend' in error_lower:
        error_info[_KEY_CATEGORIES].append('npu')
    if 'cann' in error_lower or 'acl' in error_lower:
        error_info[_KEY_CATEGORIES].append('cann')
    if 'mm.' in error_lower:
        error_info[_KEY_CATEGORIES].append('multimodal')
    if 'vision' in error_lower or 'mxv' in error_lower:
        error_info[_KEY_CATEGORIES].append('vision')
    
    # Analyze
    analysis = analyze_npu_error(error_log, env_info)
    
    # Search repository if provided
    repo_results = {}
    if args.repo_path:
        repo_results = search_repository(args.repo_path, error_log)
    
    # Generate response
    response = generate_response(error_info, analysis, repo_results, args.output)
    
    # Output
    if args.out_file:
        Path(args.out_file).write_text(response)
        logger.info(f"Analysis written to: {args.out_file}")
    else:
        logger.info(response)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
