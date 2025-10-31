"""
Artifact Smoke Test - Verify Generated Test Files

Run this to check generated test artifacts.
"""
import pathlib
import sys


def check_artifacts():
    """Check if test artifacts were generated successfully."""
    artifacts_dir = pathlib.Path("generated_tests")

    print("📁 Checking Generated Test Artifacts")
    print(f"   Directory: {artifacts_dir.absolute()}")
    print()

    # Check if directory exists
    if not artifacts_dir.exists():
        print("❌ Artifacts directory does not exist")
        print()
        print("💡 Troubleshooting:")
        print("   1. Run a test first: python run_e2e_headed.py")
        print("   2. Check if Generator agent ran successfully")
        return 1

    # List artifacts
    artifacts = list(artifacts_dir.glob("*.py"))

    print(f"📄 Found {len(artifacts)} test file(s):")
    print()

    if not artifacts:
        print("   (no files found)")
        print()
        print("❌ No test artifacts generated")
        print()
        print("💡 Troubleshooting:")
        print("   1. Check if test run completed: grep 'Generated Test Artifact' out_*.txt")
        print("   2. Review Generator agent logs")
        print("   3. Verify verdict was computed (pass/fail/partial)")
        return 1

    total_size = 0
    for f in sorted(artifacts, key=lambda x: x.stat().st_mtime, reverse=True):
        size = f.stat().st_size
        total_size += size
        modified = f.stat().st_mtime

        # Try to read first few lines
        try:
            with open(f, 'r', encoding='utf-8') as file:
                lines = file.readlines()
                first_line = lines[0].strip() if lines else "(empty)"
        except Exception:
            first_line = "(unable to read)"

        print(f"   ✅ {f.name}")
        print(f"      Size: {size:,} bytes")
        print(f"      First line: {first_line[:60]}...")
        print()

    print(f"📊 Summary:")
    print(f"   Total files: {len(artifacts)}")
    print(f"   Total size: {total_size:,} bytes")
    print()

    # Validate Python syntax
    print("🔍 Validating Python syntax...")
    invalid_files = []

    for f in artifacts:
        try:
            with open(f, 'r', encoding='utf-8') as file:
                compile(file.read(), f.name, 'exec')
            print(f"   ✅ {f.name} - Valid Python")
        except SyntaxError as e:
            invalid_files.append((f.name, str(e)))
            print(f"   ❌ {f.name} - Syntax Error: {e}")

    print()

    if invalid_files:
        print(f"❌ {len(invalid_files)} file(s) have syntax errors")
        return 1

    print("🎉 All test artifacts are VALID")
    return 0


if __name__ == "__main__":
    sys.exit(check_artifacts())
