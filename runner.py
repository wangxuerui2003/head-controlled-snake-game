import os
import subprocess

devnull = open(
    os.devnull, "w"
)  # os.devnull is 'nul' on Windows and '/dev/null' on Unix

# Run both scripts in background
subprocess.Popen(["python", "snake.py"])
subprocess.Popen(["python", "detect.py"], stderr=devnull)
