#!/usr/bin/env python3
"""
AI Content Verifier
"""

import re
import sys
import json
import socket
import logging
import asyncio
import argparse
from typing import List, Dict, Any

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    import httpx
except ImportError as e:
    logger.error("Error: httpx library is required. Install with: pip install httpx")
    raise ImportError("httpx library is required. Install with: pip install httpx") from e

# patterns for compile https/doi/pip/install/code
URL_PATTERN = re.compile(
    r'https?://[^\s<>\"\')}\]，。、；！？\uff08\uff09\u3002\uff0c\uff1b\uff01\uff1f\u3010\u3011\u300a\u300b]+',
    re.IGNORECASE,
)

DOI_PATTERN = re.compile(
    r'\b(10\.\d{4,9}/[^\s<>\"\')}\]，。、；！？\uff08\uff09\u3002\uff0c\uff1b\uff01\uff1f\u3010\u3011\u300a\u300b]+)',
    re.IGNORECASE,
)

PIP_INSTALL_PATTERN = re.compile(
    r'pip\s+install\s+([A-Za-z0-9_][A-Za-z0-9._-]*)',
    re.IGNORECASE,
)

NPM_INSTALL_PATTERN = re.compile(
    r'(?:npm|yarn|pnpm)\s+(?:install|add)\s+(?:-[A-Za-z]+\s+)*(@?[A-Za-z0-9._][A-Za-z0-9._/-]*)',
    re.IGNORECASE,
)

CODE_BLOCK_PATTERN = re.compile(
    r'```[\s\S]*?```',
    re.MULTILINE,
)


def extract_urls(text: str) -> List[str]:
    seen = set()
    results = []
    for match in URL_PATTERN.findall(text):
        url = match.rstrip('.,;:!?)')
        if url not in seen:
            seen.add(url)
            results.append(url)
    return results


def extract_dois(text: str) -> List[str]:
    seen = set()
    results = []
    for match in DOI_PATTERN.findall(text):
        doi = match.rstrip('.,;:!?)')
        if doi not in seen:
            seen.add(doi)
            results.append(doi)
    return results


def extract_packages(text: str) -> Dict[str, List[str]]:
    pip_names = set()
    npm_names = set()

    for match in PIP_INSTALL_PATTERN.findall(text):
        pip_names.add(match)

    for match in NPM_INSTALL_PATTERN.findall(text):
        npm_names.add(match)

    for block in CODE_BLOCK_PATTERN.findall(text):
        for m in PIP_INSTALL_PATTERN.findall(block):
            pip_names.add(m)
        for m in NPM_INSTALL_PATTERN.findall(block):
            npm_names.add(m)

    return {
        "pip": sorted(pip_names),
        "npm": sorted(npm_names),
    }


# verify url/doi/pypi/npm
TIMEOUT = 10
USER_AGENT = "ai-content-verifier/1.0"


async def _check_url_async(client: httpx.AsyncClient, url: str) -> Dict[str, Any]:
    result = {
        "url": url,
        "accessible": False,
        "status_code": None,
        "content_type": None,
        "error": None,
    }
    try:
        response = await client.head(url, follow_redirects=True, timeout=TIMEOUT)
        result["status_code"] = response.status_code
        result["content_type"] = response.headers.get("Content-Type", "")
        if response.status_code < 400:
            result["accessible"] = True
        else:
            result["accessible"] = False
            result["error"] = f"HTTP {response.status_code}"
    except httpx.HTTPStatusError as exc:
        result["status_code"] = exc.response.status_code
        result["error"] = f"HTTP {exc.response.status_code}"
    except httpx.RequestError as exc:
        result["error"] = str(exc)
    except asyncio.TimeoutError:
        result["error"] = "Timeout"
    except Exception as exc:
        result["error"] = str(exc)

    return result


def _check_url(url: str) -> Dict[str, Any]:
    return asyncio.run(_check_url_async(httpx.Client(verify=False), url))


def _check_doi(doi: str) -> Dict[str, Any]:
    url = f"https://doi.org/{doi}"
    return _check_url(url)


def _check_pypi(package: str) -> Dict[str, Any]:
    url = f"https://pypi.org/project/{package}/"
    result = _check_url(url)
    result["package"] = package
    result["registry"] = "pypi"
    return result


def _check_npm(package: str) -> Dict[str, Any]:
    url = f"https://www.npmjs.com/package/{package}"
    result = _check_url(url)
    result["package"] = package
    result["registry"] = "npm"
    return result


# Concurrent Detection
async def verify_urls_async(urls: List[str], workers: int = 8) -> List[Dict[str, Any]]:
    if not urls:
        return []

    async with httpx.AsyncClient(verify=False, timeout=TIMEOUT) as client:
        tasks = [_check_url_async(client, url) for url in urls]
        results = await asyncio.gather(*tasks)

    url_order = {url: i for i, url in enumerate(urls)}
    sorted_results = sorted(results, key=lambda r: url_order.get(r["url"], 999))
    return sorted_results


def verify_urls(urls: List[str], workers: int = 8) -> List[Dict[str, Any]]:
    if not urls:
        return []
    return asyncio.run(verify_urls_async(urls, workers))


async def verify_dois_async(dois: List[str], workers: int = 4) -> List[Dict[str, Any]]:
    if not dois:
        return []

    async with httpx.AsyncClient(verify=False, timeout=TIMEOUT) as client:
        tasks = [_check_url_async(client, f"https://doi.org/{doi}") for doi in dois]
        results = await asyncio.gather(*tasks)

    for i, doi in enumerate(dois):
        results[i]["doi"] = doi
    return results


def verify_dois(dois: List[str], workers: int = 4) -> List[Dict[str, Any]]:
    if not dois:
        return []
    return asyncio.run(verify_dois_async(dois, workers))


async def verify_packages_async(
        packages: Dict[str, List[str]], workers: int = 4
) -> Dict[str, List[Dict[str, Any]]]:
    results: Dict[str, List[Dict[str, Any]]] = {"pip": [], "npm": []}

    all_checks = []
    for pkg in packages.get("pip", []):
        all_checks.append(("pip", pkg, f"https://pypi.org/project/{pkg}/"))
    for pkg in packages.get("npm", []):
        all_checks.append(("npm", pkg, f"https://www.npmjs.com/package/{pkg}"))

    if not all_checks:
        return results

    async with httpx.AsyncClient(verify=False, timeout=TIMEOUT) as client:
        tasks = [_check_url_async(client, url) for _, _, url in all_checks]
        task_results = await asyncio.gather(*tasks)

        for i, (registry, pkg, _) in enumerate(all_checks):
            task_results[i]["package"] = pkg
            task_results[i]["registry"] = registry
            results[registry].append(task_results[i])

    return results


def verify_packages(
        packages: Dict[str, List[str]], workers: int = 4
) -> Dict[str, List[Dict[str, Any]]]:
    return asyncio.run(verify_packages_async(packages, workers))


# main analyze
def analyze(text: str) -> Dict[str, Any]:
    urls = extract_urls(text)
    dois = extract_dois(text)
    packages = extract_packages(text)

    url_results = verify_urls(urls)
    doi_results = verify_dois(dois)
    pkg_results = verify_packages(packages)

    accessible_urls = sum(1 for r in url_results if r["accessible"])
    accessible_dois = sum(1 for r in doi_results if r["accessible"])

    return {
        "summary": {
            "urls_found": len(urls),
            "urls_accessible": accessible_urls,
            "dois_found": len(dois),
            "dois_accessible": accessible_dois,
            "pip_packages": len(packages["pip"]),
            "npm_packages": len(packages["npm"]),
        },
        "urls": url_results,
        "dois": doi_results,
        "packages": pkg_results,
    }


def format_report(data: Dict[str, Any]) -> str:
    lines = []
    s = data["summary"]
    lines.append("## 🔗 Resource Verification\n")
    lines.append(f"| Metric | Count |")
    lines.append(f"|--------|-------|")
    lines.append(f"| URLs found | {s['urls_found']} |")
    lines.append(f"| URLs accessible | {s['urls_accessible']} |")
    lines.append(f"| DOIs found | {s['dois_found']} |")
    lines.append(f"| DOIs accessible | {s['dois_accessible']} |")
    lines.append(f"| pip packages | {s['pip_packages']} |")
    lines.append(f"| npm packages | {s['npm_packages']} |")
    lines.append("")

    if data["urls"]:
        lines.append("### URLs\n")
        lines.append("| URL | Status | Code | Error |")
        lines.append("|-----|--------|------|-------|")
        for r in data["urls"]:
            status = "✅" if r["accessible"] else "❌"
            code = r.get("status_code", "-") or "-"
            err = r.get("error", "-") or "-"
            lines.append(f"| {r['url']} | {status} | {code} | {err} |")
        lines.append("")

    if data["dois"]:
        lines.append("### DOIs\n")
        lines.append("| DOI | Status | Code | Error |")
        lines.append("|-----|--------|------|-------|")
        for r in data["dois"]:
            status = "✅" if r["accessible"] else "❌"
            code = r.get("status_code", "-") or "-"
            err = r.get("error", "-") or "-"
            lines.append(f"| {r.get('doi', r['url'])} | {status} | {code} | {err} |")
        lines.append("")

    for registry in ("pip", "npm"):
        if data["packages"].get(registry):
            lines.append(f"### {registry.upper()} Packages\n")
            lines.append("| Package | Status | Code | Error |")
            lines.append("|---------|--------|------|-------|")
            for r in data["packages"][registry]:
                status = "✅" if r["accessible"] else "❌"
                code = r.get("status_code", "-") or "-"
                err = r.get("error", "-") or "-"
                lines.append(f"| {r['package']} | {status} | {code} | {err} |")
            lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="AI Content Verifier - Extract and verify URLs, DOIs, and package references from text",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s document.txt              # Analyze resources in a file
  %(prog)s --text "text with URLs"   # Analyze directly provided text

Output formats:
  - JSON format verification results
  - Markdown format report
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "file",
        nargs="?",
        help="Path to the file to analyze"
    )

    group.add_argument(
        "--text",
        metavar="TEXT",
        help="Directly provide the text content to analyze"
    )

    parser.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        help="Save JSON results to specified file (default: output to console)"
    )

    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Only output JSON results, don't show Markdown report"
    )

    args = parser.parse_args()
    if args.text:
        text = args.text
        logger.info("Analyzing directly provided text...")
    else:
        filepath = args.file
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                text = f.read()
            logger.info(f"Reading file: {filepath}")
        except FileNotFoundError:
            logger.error(f"Error: File not found: {filepath}")
            raise
        except Exception as file_error:
            logger.error(f"Error reading file: {file_error}")
            raise

    logger.info("Extracting resources...")
    result = analyze(text)

    json_output = json.dumps(result, indent=2, ensure_ascii=False)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(json_output)
            logger.info(f"JSON results saved to: {args.output}")
        except Exception as save_error:
            logger.error(f"Error saving file: {save_error}")
            raise
    else:
        logger.info(json_output)

    if not args.json_only:
        logger.info("\n--- Markdown Report ---\n")
        logger.info(format_report(result))


if __name__ == "__main__":
    try:
        main()
        sys.exit(0)
    except Exception as main_error:
        logger.error(f"Error: {main_error}")
        sys.exit(1)
