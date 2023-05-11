import os, sys
import subprocess

#python_exe = "C:\\Users\\japeltom\\PycharmProjects\\stgem\\venv\\Scripts\\python.exe"
python_exe = "C:\\Users\\japeltom\\AppData\\Local\\Programs\\Python\\Python37\\python.exe"

if len(sys.argv) < 2:
    raise Exception("Please specify the number of replicas as a command line argument.")
N = int(sys.argv[1])
identifier = sys.argv[2] if len(sys.argv) > 2 else None

if not os.path.exists(python_exe):
    raise Exception(f"No Python executable {python_exe}.")

def run_on_powershell(python_exe, seed, identifier=None):
    python_exe = python_exe.strip()
    if identifier is None:
        command = f"{python_exe} sbst.py 1 {seed}"
    else:
        command = f"{python_exe} sbst.py 1 {seed} {identifier}"
    p = subprocess.Popen(["powershell.exe", command], stdout=sys.stdout)
    p.communicate()

for i in range(N):
    run_on_powershell(python_exe, i, identifier)
