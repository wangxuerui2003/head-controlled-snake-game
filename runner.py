import subprocess

# Run snake.py in the background
subprocess.Popen(["python", "snake.py"])

# Run detect.py in the background, suppressing stderr
with open("/dev/null", "w") as devnull:
    subprocess.Popen(["python", "detect.py"], stderr=devnull)
