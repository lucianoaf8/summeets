#!/usr/bin/env python3
"""
Comprehensive test runner for Summeets project.
Provides various test execution modes and reporting options.
"""
import subprocess
import sys
import argparse
from pathlib import Path
import time
from datetime import datetime
import os
import re


class SummeetsTestRunner:
    """Test runner for Summeets with different execution modes."""
    
    def __init__(self):
        self.project_root = Path(__file__).parent
        self.tests_dir = self.project_root / "tests"
        self.reports_dir = self.tests_dir / "reports"
        self.reports_dir.mkdir(exist_ok=True)
    
    def run_unit_tests(self, verbose=False, coverage=True):
        """Run unit tests only."""
        print("[UNIT] Running unit tests...")
        
        cmd = ["python", "-m", "pytest", "tests/unit/"]
        
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd.extend(["--cov=core", "--cov=cli", "--cov-report=term-missing"])
        
        return self._execute_command(cmd, test_type="unit")
    
    def run_integration_tests(self, verbose=False):
        """Run integration tests."""
        print("🔗 Running integration tests...")
        
        cmd = ["python", "-m", "pytest", "tests/integration/", "--run-integration"]
        
        if verbose:
            cmd.append("-v")
        
        return self._execute_command(cmd, test_type="integration")
    
    def run_e2e_tests(self, verbose=False):
        """Run end-to-end tests."""
        print("🎯 Running end-to-end tests...")
        
        cmd = ["python", "-m", "pytest", "tests/e2e/", "--run-e2e"]
        
        if verbose:
            cmd.append("-v")
        
        return self._execute_command(cmd, test_type="e2e")
    
    def run_performance_tests(self, verbose=False):
        """Run performance tests."""
        print("⚡ Running performance tests...")
        
        cmd = ["python", "-m", "pytest", "tests/performance/", "--run-performance"]
        
        if verbose:
            cmd.append("-v")
        
        return self._execute_command(cmd, test_type="performance")
    
    def run_all_tests(self, verbose=False, coverage=True):
        """Run all tests (unit, integration, e2e)."""
        print("🚀 Running all tests...")
        
        cmd = ["python", "-m", "pytest", "tests/"]
        cmd.extend(["--run-integration", "--run-e2e"])
        
        if verbose:
            cmd.append("-v")
        
        if coverage:
            cmd.extend([
                "--cov=core", 
                "--cov=cli", 
                "--cov-branch",
                "--cov-report=term-missing",
                "--cov-report=html:tests/reports/htmlcov"
            ])
        
        return self._execute_command(cmd, test_type="all")
    
    def run_smoke_tests(self, verbose=False):
        """Run smoke test suite (critical path validation)."""
        print("[SMOKE] Running smoke tests...")
        
        # Run a small subset of critical tests for quick validation
        cmd = [
            "python", "-m", "pytest", 
            "tests/unit/test_models.py",
            "tests/unit/test_workflow_engine.py",
            "tests/unit/test_validation.py",
            "tests/unit/test_audio_processing.py",
            "-m", "not slow",
            "--tb=short"
        ]
        
        if verbose:
            cmd.append("-v")
        
        return self._execute_command(cmd, test_type="smoke")
    
    def run_quick_tests(self, verbose=False):
        """Run quick test suite (unit tests only, no slow tests)."""
        print("⚡ Running quick test suite...")
        
        cmd = ["python", "-m", "pytest", "tests/unit/", "-m", "not slow"]
        
        if verbose:
            cmd.append("-v")
        
        return self._execute_command(cmd, test_type="quick")
    
    def run_specific_test(self, test_path, verbose=False):
        """Run a specific test file or test function."""
        print(f"🎯 Running specific test: {test_path}")
        
        cmd = ["python", "-m", "pytest", test_path]
        
        if verbose:
            cmd.append("-v")
        
        return self._execute_command(cmd, test_type="specific")
    
    def run_with_profile(self, verbose=False):
        """Run tests with profiling."""
        print("📊 Running tests with profiling...")
        
        cmd = ["python", "-m", "pytest", "tests/unit/", "--profile"]
        
        if verbose:
            cmd.append("-v")
        
        return self._execute_command(cmd, test_type="profile")
    
    def run_parallel_tests(self, num_workers=None, verbose=False):
        """Run tests in parallel using pytest-xdist."""
        if num_workers is None:
            import multiprocessing
            num_workers = multiprocessing.cpu_count()
        
        print(f"🏃‍♂️ Running tests in parallel with {num_workers} workers...")
        
        cmd = ["python", "-m", "pytest", "tests/unit/", f"-n{num_workers}"]
        
        if verbose:
            cmd.append("-v")
        
        return self._execute_command(cmd, test_type="parallel")
    
    def check_test_coverage(self):
        """Generate and display test coverage report."""
        print("[COVERAGE] Generating coverage report...")
        
        # Run tests with coverage
        cmd = [
            "python", "-m", "pytest", "tests/unit/",
            "--cov=core", "--cov=cli", 
            "--cov-branch",
            "--cov-report=term-missing",
            "--cov-report=html:tests/reports/htmlcov",
            "--cov-report=xml:tests/reports/coverage.xml"
        ]
        
        result = self._execute_command(cmd, test_type="coverage")
        
        if result == 0:
            print("\n[SUCCESS] Coverage report generated:")
            print("   - Terminal: displayed above")
            print("   - HTML: tests\\reports\\htmlcov\\index.html")
            print("   - XML: tests\\reports\\coverage.xml")
        
        return result
    
    def lint_and_format_check(self):
        """Run linting and format checks."""
        print("🔍 Running linting and format checks...")
        
        success = True
        
        # Check with ruff
        print("  Running ruff...")
        result = self._execute_command(["ruff", "check", "core/", "cli/", "tests/"])
        if result != 0:
            success = False
        
        # Check with mypy
        print("  Running mypy...")
        result = self._execute_command(["mypy", "core/", "cli/"])
        if result != 0:
            success = False
        
        # Check with black (format check)
        print("  Checking code formatting with black...")
        result = self._execute_command(["black", "--check", "core/", "cli/", "tests/"])
        if result != 0:
            success = False
        
        return 0 if success else 1
    
    def run_security_scan(self):
        """Run security scan with bandit."""
        print("🔒 Running security scan...")
        
        cmd = ["bandit", "-r", "core/", "cli/", "-f", "json", "-o", "security-report.json"]
        result = self._execute_command(cmd)
        
        if result == 0:
            print("   Security report generated: security-report.json")
        
        return result
    
    def clean_test_artifacts(self):
        """Clean up test artifacts and cache files."""
        print("[CLEAN] Cleaning test artifacts...")
        
        artifacts = [
            ".pytest_cache",
            "tests/reports/htmlcov",
            "tests/reports/coverage.xml",
            ".coverage",
            "tests.log",
            "__pycache__",
            "*.pyc"
        ]
        
        for artifact in artifacts:
            # Use PowerShell commands for Windows compatibility
            if artifact in ["tests/reports/htmlcov", "tests/reports/coverage.xml", ".coverage", "tests.log"]:
                cmd = ["powershell.exe", "-Command", f"Remove-Item -Path '{artifact}' -Recurse -Force -ErrorAction SilentlyContinue"]
                self._execute_command(cmd, capture_output=True)
            else:
                cmd = ["powershell.exe", "-Command", f"Get-ChildItem -Path . -Name '{artifact}' -Recurse | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue"]
                self._execute_command(cmd, capture_output=True)
        
        print("   Test artifacts cleaned")
        return 0
    
    def validate_test_structure(self):
        """Validate test structure and completeness."""
        print("📋 Validating test structure...")
        
        required_dirs = [
            "tests/unit",
            "tests/integration", 
            "tests/e2e",
            "tests/fixtures",
            "tests/performance"
        ]
        
        required_files = [
            "tests/conftest.py",
            "tests/__init__.py",
            "pytest.ini"
        ]
        
        missing_items = []
        
        for directory in required_dirs:
            if not (self.project_root / directory).exists():
                missing_items.append(f"Missing directory: {directory}")
        
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                missing_items.append(f"Missing file: {file_path}")
        
        if missing_items:
            print("   ❌ Test structure validation failed:")
            for item in missing_items:
                print(f"      {item}")
            return 1
        else:
            print("   ✅ Test structure validation passed")
            return 0
    
    def _generate_report_filename(self, test_type):
        """Generate report filename with test type and timestamp."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"test_report_{test_type}_{timestamp}.md"
    
    def _format_output_for_markdown(self, text, max_lines=500):
        """Format terminal output for markdown with syntax highlighting."""
        if not text:
            return ""
        
        lines = text.split('\n')
        
        # Truncate very long output for readability
        if len(lines) > max_lines:
            truncated_lines = lines[:max_lines//2] + [
                "",
                f"... [TRUNCATED: {len(lines) - max_lines} lines hidden for readability] ...",
                ""
            ] + lines[-max_lines//2:]
            text = '\n'.join(truncated_lines)
        
        # For better readability, wrap the entire output in a code block
        # with ansi color preservation
        formatted_text = f"```ansi\n{text}\n```"
        
        return formatted_text
    
    def _add_color_coding_legend(self):
        """Add a legend for color coding in the markdown report."""
        return """
## Color Coding Legend

- 🟢 **GREEN**: Successful tests, passed operations
- 🔴 **RED**: Failed tests, errors
- 🟡 **YELLOW**: Warnings, skipped tests
- 🔵 **BLUE**: Information, test names
- 🟣 **PURPLE**: File paths, module names
- ⚪ **WHITE**: General output, statistics

"""
    
    def _extract_test_summary(self, stdout_text):
        """Extract test summary information from pytest output."""
        if not stdout_text:
            return {}
        
        lines = stdout_text.split('\n')
        summary = {}
        
        # Extract test counts from final summary line
        for line in lines:
            if " failed" in line and " passed" in line:
                # Parse line like "37 failed, 120 passed in 6.59s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "failed,":
                        summary['failed'] = int(parts[i-1])
                    elif part == "passed":
                        summary['passed'] = int(parts[i-1])
                    elif part.startswith("in") and "s" in part:
                        summary['duration'] = parts[i+1]
            elif " passed in" in line and "failed" not in line:
                # Parse line like "120 passed in 6.59s"
                parts = line.split()
                for i, part in enumerate(parts):
                    if part == "passed":
                        summary['passed'] = int(parts[i-1])
                        summary['failed'] = 0
                    elif part.startswith("in") and "s" in part:
                        summary['duration'] = parts[i+1]
        
        # Extract coverage percentage if present
        for line in lines:
            if "TOTAL" in line and "%" in line:
                parts = line.split()
                for part in parts:
                    if "%" in part:
                        summary['coverage'] = part
                        break
        
        return summary
    
    def _write_test_summary(self, file_handle, stdout_text):
        """Write a concise test summary section."""
        summary = self._extract_test_summary(stdout_text)
        
        if summary:
            file_handle.write("## Test Results Summary\n\n")
            
            if 'passed' in summary:
                file_handle.write(f"- **Passed**: {summary['passed']} tests\n")
            if 'failed' in summary:
                file_handle.write(f"- **Failed**: {summary['failed']} tests\n")
            if 'duration' in summary:
                file_handle.write(f"- **Duration**: {summary['duration']}\n")
            if 'coverage' in summary:
                file_handle.write(f"- **Coverage**: {summary['coverage']}\n")
            
            # Calculate success rate
            if 'passed' in summary and 'failed' in summary:
                total = summary['passed'] + summary['failed']
                success_rate = (summary['passed'] / total * 100) if total > 0 else 0
                file_handle.write(f"- **Success Rate**: {success_rate:.1f}%\n")
            
            file_handle.write("\n")
    
    def _execute_command(self, cmd, capture_output=False, test_type=None):
        """Execute a command and return the exit code, optionally saving output to report."""
        try:
            # Use PowerShell wrapper for Windows compatibility
            if cmd[0] in ['python', 'pytest', 'mypy', 'ruff', 'black', 'bandit']:
                powershell_cmd = ['powershell.exe', '-Command'] + cmd
            else:
                powershell_cmd = cmd
            
            if test_type:
                # Capture output for reporting
                result = subprocess.run(powershell_cmd, capture_output=True, text=True)
                
                # Generate report
                report_filename = self._generate_report_filename(test_type)
                report_path = self.reports_dir / report_filename
                
                # Write report with test details in Markdown format
                with open(report_path, 'w', encoding='utf-8') as f:
                    # Write markdown header
                    f.write(f"# Summeets Test Report - {test_type.upper()}\n\n")
                    
                    # Test execution metadata
                    f.write("## Test Execution Details\n\n")
                    f.write(f"- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"- **Test Type**: {test_type.upper()}\n")
                    f.write(f"- **Command**: `{' '.join(powershell_cmd)}`\n")
                    f.write(f"- **Exit Code**: {result.returncode} {'[SUCCESS]' if result.returncode == 0 else '[FAILED]'}\n")
                    f.write(f"- **Status**: {'SUCCESS' if result.returncode == 0 else 'FAILED'}\n\n")
                    
                    # Add test summary (extracted from output)
                    if result.stdout:
                        self._write_test_summary(f, result.stdout)
                    
                    # Add color coding legend
                    f.write(self._add_color_coding_legend())
                    
                    # Test output section
                    if result.stdout:
                        f.write("## Test Output (STDOUT)\n\n")
                        formatted_stdout = self._format_output_for_markdown(result.stdout)
                        f.write(formatted_stdout)
                        f.write("\n\n")
                    
                    # Error output section
                    if result.stderr:
                        f.write("## Error Output (STDERR)\n\n")
                        formatted_stderr = self._format_output_for_markdown(result.stderr)
                        f.write(formatted_stderr)
                        f.write("\n\n")
                    
                    # Execution summary section
                    f.write("## Execution Summary\n\n")
                    if result.returncode == 0:
                        f.write("[SUCCESS] **Test execution completed successfully**\n\n")
                        f.write("All tests passed without errors.\n")
                    else:
                        f.write("[FAILED] **Test execution failed**\n\n")
                        f.write("Please review the error output above for details.\n")
                    
                    # Footer
                    f.write(f"\n---\n*Report generated by Summeets Test Runner on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*\n")
                
                # Display output to terminal (same as before)
                if result.stdout:
                    print(result.stdout)
                if result.stderr:
                    print(result.stderr)
                
                print(f"\n[REPORT] Test report saved: {report_path}")
                return result.returncode
            else:
                # Original behavior for non-test commands
                if capture_output:
                    result = subprocess.run(powershell_cmd, capture_output=True, text=True)
                else:
                    result = subprocess.run(powershell_cmd)
                return result.returncode
                
        except FileNotFoundError:
            error_msg = f"   [ERROR] Command not found: {cmd[0]}"
            print(error_msg)
            
            if test_type:
                # Save error to report
                report_filename = self._generate_report_filename(test_type)
                report_path = self.reports_dir / report_filename
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Summeets Test Report - {test_type.upper()} (ERROR)\n\n")
                    f.write("## Test Execution Details\n\n")
                    f.write(f"- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"- **Test Type**: {test_type.upper()}\n")
                    f.write(f"- **Command**: `{' '.join(powershell_cmd)}`\n")
                    f.write(f"- **Status**: COMMAND ERROR [FAILED]\n\n")
                    f.write("## Error Details\n\n")
                    f.write(f"```\n{error_msg}\n```\n")
                    f.write(f"\n---\n*Report generated by Summeets Test Runner on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*\n")
            
            return 1
        except Exception as e:
            error_msg = f"   [ERROR] Error executing command: {e}"
            print(error_msg)
            
            if test_type:
                # Save error to report
                report_filename = self._generate_report_filename(test_type)
                report_path = self.reports_dir / report_filename
                with open(report_path, 'w', encoding='utf-8') as f:
                    f.write(f"# Summeets Test Report - {test_type.upper()} (ERROR)\n\n")
                    f.write("## Test Execution Details\n\n")
                    f.write(f"- **Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"- **Test Type**: {test_type.upper()}\n")
                    f.write(f"- **Command**: `{' '.join(powershell_cmd)}`\n")
                    f.write(f"- **Status**: COMMAND ERROR [FAILED]\n\n")
                    f.write("## Error Details\n\n")
                    f.write(f"```\n{error_msg}\n```\n")
                    f.write(f"\n---\n*Report generated by Summeets Test Runner on {datetime.now().strftime('%Y-%m-%d at %H:%M:%S')}*\n")
            
            return 1


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(
        description="Comprehensive test runner for Summeets project",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_tests.py                         # Run smoke tests (default)
  python run_tests.py smoke                   # Run smoke tests (critical path)
  python run_tests.py unit                    # Run unit tests
  python run_tests.py all -v                  # Run all tests verbosely
  python run_tests.py quick                   # Run quick test suite
  python run_tests.py coverage                # Generate coverage report
  python run_tests.py validate                # Validate test structure
  python run_tests.py specific tests/unit/test_models.py  # Run specific test
        """
    )
    
    parser.add_argument(
        "mode",
        nargs="?",
        default="smoke",
        choices=[
            "unit", "integration", "e2e", "performance", 
            "all", "quick", "smoke", "specific", "parallel",
            "coverage", "lint", "security", "clean", 
            "validate", "profile"
        ],
        help="Test execution mode (default: smoke)"
    )
    
    parser.add_argument(
        "test_path",
        nargs="?",
        help="Specific test path (for 'specific' mode)"
    )
    
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    parser.add_argument(
        "--no-coverage",
        action="store_true",
        help="Disable coverage reporting"
    )
    
    parser.add_argument(
        "-j", "--workers",
        type=int,
        help="Number of parallel workers (for 'parallel' mode)"
    )
    
    args = parser.parse_args()
    
    runner = SummeetsTestRunner()
    
    print("[TEST] Summeets Test Runner")
    print(f"[INFO] Project root: {runner.project_root}")
    print(f"[MODE] Mode: {args.mode}")
    print("=" * 50)
    
    start_time = time.time()
    
    # Execute based on mode
    if args.mode == "smoke":
        result = runner.run_smoke_tests(verbose=args.verbose)
    elif args.mode == "unit":
        result = runner.run_unit_tests(
            verbose=args.verbose, 
            coverage=not args.no_coverage
        )
    elif args.mode == "integration":
        result = runner.run_integration_tests(verbose=args.verbose)
    elif args.mode == "e2e":
        result = runner.run_e2e_tests(verbose=args.verbose)
    elif args.mode == "performance":
        result = runner.run_performance_tests(verbose=args.verbose)
    elif args.mode == "all":
        result = runner.run_all_tests(
            verbose=args.verbose,
            coverage=not args.no_coverage
        )
    elif args.mode == "quick":
        result = runner.run_quick_tests(verbose=args.verbose)
    elif args.mode == "specific":
        if not args.test_path:
            print("❌ Test path required for 'specific' mode")
            return 1
        result = runner.run_specific_test(args.test_path, verbose=args.verbose)
    elif args.mode == "parallel":
        result = runner.run_parallel_tests(
            num_workers=args.workers,
            verbose=args.verbose
        )
    elif args.mode == "coverage":
        result = runner.check_test_coverage()
    elif args.mode == "lint":
        result = runner.lint_and_format_check()
    elif args.mode == "security":
        result = runner.run_security_scan()
    elif args.mode == "clean":
        result = runner.clean_test_artifacts()
    elif args.mode == "validate":
        result = runner.validate_test_structure()
    elif args.mode == "profile":
        result = runner.run_with_profile(verbose=args.verbose)
    else:
        print(f"[ERROR] Unknown mode: {args.mode}")
        return 1
    
    # Report results
    elapsed_time = time.time() - start_time
    print("=" * 50)
    
    if result == 0:
        print(f"[SUCCESS] Tests completed successfully in {elapsed_time:.2f}s")
    else:
        print(f"[FAILED] Tests failed in {elapsed_time:.2f}s")
    
    return result


if __name__ == "__main__":
    sys.exit(main())