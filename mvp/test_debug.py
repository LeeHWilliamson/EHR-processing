import sys

def test_debug():
    print("\nExecutable:", sys.executable)
    print("\nSys.path:")
    for p in sys.path:
        print(" ", p)