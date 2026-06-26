#!/usr/bin/env python3
"""
Push to remote with exponential backoff retry.

Handles transient network/API failures with smart retry logic:
- Detects transient errors (rate limit, temporary network failure)
- Exponential backoff: 2s, 4s, 8s, 16s, 32s (max 5 attempts)
- Aborts immediately on permanent errors (auth, non-fast-forward)
- Logs each attempt for debugging
"""

import argparse
import subprocess
import sys
import time
from pathlib import Path

class PushRetry:
    def __init__(self, max_retries=5, verbose=False):
        self.max_retries = max_retries
        self.verbose = verbose
        self.attempt = 0

    def log(self, msg: str):
        if self.verbose:
            print(f"[push-retry] {msg}")

    def run_cmd(self, cmd: list) -> tuple[int, str, str]:
        """Run command and return (returncode, stdout, stderr)."""
        result = subprocess.run(cmd, capture_output=True, text=True)
        return result.returncode, result.stdout, result.stderr

    def is_transient_error(self, stderr: str) -> bool:
        """Check if error is transient (retry-able)."""
        transient_patterns = [
            'rate limit',
            'api rate limit',
            'temporarily unavailable',
            'connection timeout',
            'broken pipe',
            'reset by peer',
            'connection refused',
            'temporary failure',
            'try again',
            'timed out',
            'too many requests',
        ]
        stderr_lower = stderr.lower()
        return any(pattern in stderr_lower for pattern in transient_patterns)

    def is_permanent_error(self, stderr: str) -> bool:
        """Check if error is permanent (don't retry)."""
        permanent_patterns = [
            'permission denied',
            'fatal: authentication failed',
            'fatal: could not read',
            'invalid credentials',
            'no such file',
            'merge conflict',
            'non-fast-forward',
        ]
        stderr_lower = stderr.lower()
        return any(pattern in stderr_lower for pattern in permanent_patterns)

    def push(self, branch: str, remote: str = 'origin') -> bool:
        """Push branch with retries. Returns True on success."""
        cmd = ['git', 'push', remote, f'HEAD:{branch}']

        for attempt in range(1, self.max_retries + 1):
            self.attempt = attempt
            print(f"\n📤 Push attempt {attempt}/{self.max_retries}")
            print(f"   Command: {' '.join(cmd)}")

            returncode, stdout, stderr = self.run_cmd(cmd)

            if returncode == 0:
                print(f"✅ Push successful on attempt {attempt}")
                return True

            # Analyze error
            if self.is_permanent_error(stderr):
                print(f"\n❌ Permanent error (not retrying):")
                print(stderr)
                return False

            if not self.is_transient_error(stderr):
                print(f"\n⚠️  Unexpected error:")
                print(stderr)
                if attempt == self.max_retries:
                    return False
                # Still retry on unexpected errors

            # Calculate backoff
            if attempt < self.max_retries:
                backoff = 2 ** (attempt - 1)  # 2, 4, 8, 16, 32
                print(f"⏳ Waiting {backoff}s before retry...")
                time.sleep(backoff)
            else:
                print(f"\n❌ Failed after {self.max_retries} attempts")
                return False

        return False

def main():
    parser = argparse.ArgumentParser(description='Push with exponential backoff retry')
    parser.add_argument('--branch', required=True, help='Branch to push')
    parser.add_argument('--remote', default='origin', help='Remote name (default: origin)')
    parser.add_argument('--max-retries', type=int, default=5, help='Max retry attempts')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    args = parser.parse_args()

    pusher = PushRetry(max_retries=args.max_retries, verbose=args.verbose)
    success = pusher.push(args.branch, args.remote)

    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())
