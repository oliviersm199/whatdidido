#!/usr/bin/env python3
"""
Smoke test to verify the package is functional after building.

This test is run in the CI/CD pipeline after building the package
to ensure no critical files are missing and basic functionality works.
"""

import subprocess
import sys


def test_cli_help():
    """Test that the CLI entry point works."""
    print("Testing CLI entry point...")

    try:
        # Run the CLI with --help flag
        result = subprocess.run(
            ["whatdidido", "--help"], capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0:
            print("  ✓ CLI entry point works")
            # Verify expected commands are in help output
            expected_commands = [
                "connect",
                "sync",
                "config",
                "clean",
                "report",
                "disconnect",
            ]
            for cmd in expected_commands:
                if cmd not in result.stdout:
                    print(f"  ✗ Expected command '{cmd}' not found in help output")
                    return False
            print("  ✓ All expected commands present")
            return True
        else:
            print(f"  ✗ CLI failed with return code {result.returncode}")
            print(f"  stderr: {result.stderr}")
            return False

    except subprocess.TimeoutExpired:
        print("  ✗ CLI command timed out")
        return False
    except Exception as e:
        print(f"  ✗ CLI test failed: {e}")
        return False


def main():
    """Run all smoke tests."""
    print("Running smoke tests...\n")

    tests = [
        test_cli_help,
    ]

    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
            print()
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}\n")
            results.append(False)

    # Summary
    passed = sum(results)
    total = len(results)
    print(f"Results: {passed}/{total} tests passed")

    if all(results):
        print("\n✓ All smoke tests passed!")
        sys.exit(0)
    else:
        print("\n✗ Some smoke tests failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
