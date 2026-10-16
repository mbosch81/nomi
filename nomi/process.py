"""Keep owned command-line helpers invisible in the Windows desktop app."""
import os
import subprocess

def process_options():
    return {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
