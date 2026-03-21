import os
import sys
from contextlib import contextmanager


class _TeeStream:
    """Write text to both terminal and a log file."""

    def __init__(self, terminal_stream, log_file):
        self._terminal_stream = terminal_stream
        self._log_file = log_file

    def write(self, data):
        self._terminal_stream.write(data)
        self._log_file.write(data)
        # Ensure the progress file is updated while the pipeline is running.
        self._log_file.flush()
        self._terminal_stream.flush()
        return len(data)

    def flush(self):
        self._terminal_stream.flush()
        self._log_file.flush()


@contextmanager
def tee_streams(log_path: str):
    """Temporarily mirror stdout/stderr to a run-specific progress log file."""
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    original_stdout = sys.stdout
    original_stderr = sys.stderr

    # Use line buffering so newline-terminated prints are pushed out quickly.
    with open(log_path, "a", encoding="utf-8", buffering=1) as log_file:
        sys.stdout = _TeeStream(original_stdout, log_file)
        sys.stderr = _TeeStream(original_stderr, log_file)
        try:
            yield
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr
