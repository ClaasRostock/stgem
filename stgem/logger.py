# Multiprocessing does not support Python's logging module as concurrent
# handling of log file writes is complex. Thus we need our own logger. We use
# a very simple approach without continuous logging to files.

class Logger:

    def __init__(self):
        self.silent = False

    def __call__(self, name, log):
        if not self.silent:
            print(f"{name}: {log}")

