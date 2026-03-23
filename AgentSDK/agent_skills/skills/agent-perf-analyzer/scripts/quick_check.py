"""
Quick Check Module - Fast validation for CI/CD integration.

This module provides a quick check that can be run before commits
to catch critical precision and performance issues early.
"""

import sys
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)

# Add parent directory to path (using append to avoid index issues)
_SCRIPT_DIR = Path(__file__).parent
_PARENT_DIR = str(_SCRIPT_DIR.parent)
if _PARENT_DIR not in sys.path:
    sys.path.append(_PARENT_DIR)

from analyze_precision import PrecisionAnalyzer
from analyze_performance import PerformanceAnalyzer


class QuickChecker:
    """Fast checker for critical issues."""
    
    # Critical patterns that should fail the check
    CRITICAL_PATTERNS = [
        "dtype=torch.float64",  # Should not use float64 in training
        ".to(torch.float32)",   # Check for conversion
        "ray.get(",             # Check for blocking
        "gc.collect()",         # Check for GC
    ]
    
    def __init__(self, target_path: str, fail_on_error: bool = True):
        """Initialize quick checker."""
        self.target_path = Path(target_path)
        self.fail_on_error = fail_on_error
        self.issues_found = 0
        
    def run(self) -> bool:
        """Run quick check and return True if passed."""
        logger.info(f"Running quick check on: {self.target_path}")
        logger.info("-" * 50)
        
        # Run precision check
        precision_analyzer = PrecisionAnalyzer(str(self.target_path))
        precision_report = precision_analyzer.run()
        
        # Check for critical issues
        critical_issues = [i for i in precision_report.issues 
                         if i.severity in ("critical", "high")]
        
        if critical_issues:
            logger.info(f"\n[ERROR] Found {len(critical_issues)} critical precision issues:")
            for issue in critical_issues[:5]:  # Show first 5
                logger.info(f"  - {issue.file}:{issue.line} [{issue.severity}] {issue.category}")
                logger.info(f"    {issue.description[:80]}")
            self.issues_found += len(critical_issues)
        
        # Run performance check
        perf_analyzer = PerformanceAnalyzer(str(self.target_path))
        perf_report = perf_analyzer.run()
        
        # Check for critical bottlenecks
        critical_bottlenecks = [b for b in perf_report.bottlenecks 
                              if b.severity == "high"]
        
        if critical_bottlenecks:
            logger.info(f"\n[WARNING] Found {len(critical_bottlenecks)} high-impact performance issues:")
            for bottleneck in critical_bottlenecks[:5]:  # Show first 5
                logger.info(f"  - {bottleneck.file}:{bottleneck.line} [{bottleneck.category}]")
                logger.info(f"    {bottleneck.description[:80]}")
            self.issues_found += len(critical_bottlenecks)
        
        # Summary
        logger.info("\n" + "-" * 50)
        if self.issues_found > 0:
            logger.info(f"RESULT: FAILED ({self.issues_found} issues)")
            if self.fail_on_error:
                return False
        else:
            logger.info("RESULT: PASSED")
            
        return True


def main():
    """Command-line interface."""
    parser = argparse.ArgumentParser(description="Quick check for critical issues")
    parser.add_argument("target_path", help="Path to check")
    parser.add_argument("--no-fail", action="store_true", 
                       help="Don't fail on errors, just report")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Verbose output")
    
    args = parser.parse_args()
    
    checker = QuickChecker(args.target_path, fail_on_error=not args.no_fail)
    success = checker.run()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
