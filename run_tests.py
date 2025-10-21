#!/usr/bin/env python3
"""
Test runner script for BNR Exchange Rate Monitor.
Provides different test execution modes for development and CI/CD.
"""
import sys
import subprocess
import argparse
import os
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(command)}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, check=True, capture_output=False)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed with exit code {e.returncode}")
        return False


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="BNR Exchange Rate Monitor Test Runner")
    parser.add_argument(
        "--mode",
        choices=["unit", "integration", "performance", "all", "ci"],
        default="all",
        help="Test execution mode"
    )
    parser.add_argument(
        "--coverage",
        action="store_true",
        help="Generate coverage report"
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate HTML test report"
    )
    parser.add_argument(
        "--parallel",
        type=int,
        default=1,
        help="Number of parallel workers"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    args = parser.parse_args()
    
    # Base pytest command
    base_cmd = ["python3", "-m", "pytest"]
    
    if args.verbose:
        base_cmd.append("-v")
    
    if args.parallel > 1:
        base_cmd.extend(["-n", str(args.parallel)])
    
    if args.coverage:
        base_cmd.extend(["--cov=main", "--cov-report=html", "--cov-report=term"])
    
    if args.html:
        base_cmd.extend(["--html=test-results.html", "--self-contained-html"])
    
    # Test mode specific commands
    if args.mode == "unit":
        cmd = base_cmd + ["tests/unit/", "-m", "unit"]
        success = run_command(cmd, "Unit Tests")
        
    elif args.mode == "integration":
        cmd = base_cmd + ["tests/integration/", "-m", "integration"]
        success = run_command(cmd, "Integration Tests")
        
    elif args.mode == "performance":
        cmd = base_cmd + ["tests/performance/", "-m", "performance"]
        success = run_command(cmd, "Performance Tests")
        
    elif args.mode == "ci":
        # CI mode: run all tests with full reporting
        cmd = base_cmd + [
            "tests/",
            "--cov=main",
            "--cov-report=xml",
            "--cov-report=html",
            "--cov-report=term-missing",
            "--cov-fail-under=80",
            "--html=test-results.html",
            "--self-contained-html",
            "--json-report",
            "--json-report-file=test-results.json",
            "--junitxml=test-results.xml"
        ]
        success = run_command(cmd, "CI Test Suite")
        
    else:  # all
        cmd = base_cmd + ["tests/"]
        success = run_command(cmd, "All Tests")
    
    # Additional quality checks
    if success and args.mode in ["all", "ci"]:
        print(f"\n{'='*60}")
        print("Running Code Quality Checks")
        print(f"{'='*60}")
        
        # Run linting
        lint_cmd = ["python3", "-m", "flake8", "main.py", "tests/"]
        run_command(lint_cmd, "Code Linting (flake8)")
        
        # Run type checking
        type_cmd = ["python3", "-m", "mypy", "main.py"]
        run_command(type_cmd, "Type Checking (mypy)")
        
        # Run code formatting check
        format_cmd = ["python3", "-m", "black", "--check", "main.py", "tests/"]
        run_command(format_cmd, "Code Formatting Check (black)")
    
    # Summary
    print(f"\n{'='*60}")
    if success:
        print("🎉 All tests completed successfully!")
        print("📊 Check htmlcov/ for coverage report")
        print("📋 Check test-results.html for detailed test report")
    else:
        print("❌ Some tests failed. Check output above for details.")
        sys.exit(1)
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
