import os, sys
import subprocess

python_exe = "C:\\Users\\japeltom\\PycharmProjects\\stgem\\venv\\Scripts\\python.exe"

if len(sys.argv) < 2:
    raise Exception("Please specify the number of replicas as a command line argument.")
N = int(sys.argv[1])
identifier = sys.argv[2] if len(sys.argv) > 2 else None

if not os.path.exists(python_exe):
    raise Exception("No Python executable {}.".format(python_exe))

def run_on_powershell(python_exe, seed, identifier=None):
    python_exe = python_exe.strip()
    if identifier is None:
        command = "{} sbst.py 1 {}".format(python_exe, seed)
    else:
        command = "{} sbst.py 1 {} {}".format(python_exe, seed, identifier)
    p = subprocess.Popen(["powershell.exe", command], stdout=sys.stdout)
    p.communicate()

for i in range(N):
    run_on_powershell(python_exe, i, identifier)
