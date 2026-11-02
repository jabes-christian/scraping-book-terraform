import os
import sys

from book_monitor.runner import run

if __name__ == "__main__":
    sys.exit(run(os.environ))
