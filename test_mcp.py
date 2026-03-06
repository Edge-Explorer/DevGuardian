import subprocess
import sys

cmd = [r"C:\Users\ASUS\OneDrive\Desktop\DevGuardian\.venv\Scripts\devguardian.exe"]
try:
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=r"C:\Users\ASUS\OneDrive\Desktop\DevGuardian"
    )
    # Wait a bit to see if it crashes
    try:
        stdout, stderr = process.communicate(timeout=3)
        print("STDOUT:", stdout)
        print("STDERR:", stderr)
    except subprocess.TimeoutExpired:
        print("Process still running (this is good for MCP)")
        process.terminate()
except Exception as e:
    print(f"Failed to run: {e}")
