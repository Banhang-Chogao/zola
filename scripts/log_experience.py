#!/usr/bin/env python3
"""Log conflict resolution experiences into Merge Conflict Preflight knowledge base.

Usage:
    python3 scripts/log_experience.py --pr 123 --branch feature/xyz --status resolved --method auto
    python3 scripts/log_experience.py --pr 123 --branch feature/xyz --status auto-resolved --method auto --files package.json,package-lock.json
"""

import json
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
import subprocess
import hashlib


class ExperienceLogger:
    def __init__(self):
        self.repo_root = Path(__file__).resolve().parent.parent
        self.experience_file = self.repo_root / '.github' / 'preflight_experiences.json'
        self.ensure_file_exists()

    def ensure_file_exists(self):
        """Create experience file if it doesn't exist."""
        if not self.experience_file.exists():
            self.experience_file.parent.mkdir(parents=True, exist_ok=True)
            initial_data = {
                "version": "1.0",
                "total_experiences": 0,
                "experiences": [],
                "statistics": {
                    "auto_resolved": 0,
                    "manual_resolved": 0,
                    "failed": 0,
                    "by_file_type": {}
                }
            }
            with open(self.experience_file, 'w') as f:
                json.dump(initial_data, f, indent=2, ensure_ascii=False)

    def load_experiences(self) -> dict:
        """Load existing experiences."""
        with open(self.experience_file) as f:
            return json.load(f)

    def save_experiences(self, data: dict):
        """Save experiences."""
        with open(self.experience_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def get_conflict_files(self) -> list:
        """Get list of conflicted files from git."""
        result = subprocess.run(
            ['git', 'diff', '--name-only', '--diff-filter=U'],
            capture_output=True,
            text=True,
            cwd=self.repo_root
        )
        return [f.strip() for f in result.stdout.splitlines() if f.strip()]

    def get_conflict_patterns(self, files: list) -> dict:
        """Analyze conflict patterns by file type."""
        patterns = {}
        for file in files:
            # Categorize by file type
            if 'package.json' in file:
                patterns['package_json'] = patterns.get('package_json', 0) + 1
            elif 'lock' in file:
                patterns['lock_file'] = patterns.get('lock_file', 0) + 1
            elif file.endswith('.data.json'):
                patterns['data_json'] = patterns.get('data_json', 0) + 1
            elif 'registry.json' in file:
                patterns['registry'] = patterns.get('registry', 0) + 1
            elif 'CHANGELOG.md' in file:
                patterns['changelog'] = patterns.get('changelog', 0) + 1
            elif file.endswith('-report.json'):
                patterns['report_json'] = patterns.get('report_json', 0) + 1
            elif file.endswith('-state.json'):
                patterns['state_json'] = patterns.get('state_json', 0) + 1
            elif file.endswith('-scores.json'):
                patterns['scores_json'] = patterns.get('scores_json', 0) + 1
            elif file.endswith('.md'):
                patterns['markdown'] = patterns.get('markdown', 0) + 1
            elif file.endswith(('.html', '.scss', '.css')):
                patterns['template_style'] = patterns.get('template_style', 0) + 1
            elif file.endswith(('.py', '.js', '.toml')):
                patterns['code_config'] = patterns.get('code_config', 0) + 1
            else:
                patterns['other'] = patterns.get('other', 0) + 1
        return patterns

    def log_experience(self, pr_number: int, branch: str,
                      status: str, method: str, files: list = None):
        """Log a conflict resolution experience."""
        data = self.load_experiences()

        # Get current timestamp
        timestamp = datetime.now().isoformat()

        # Get conflict files if not provided
        if files is None:
            files = self.get_conflict_files()

        # Analyze patterns
        patterns = self.get_conflict_patterns(files)

        # Create experience entry
        experience = {
            "id": hashlib.md5(f"{pr_number}{timestamp}".encode()).hexdigest()[:8],
            "timestamp": timestamp,
            "pr_number": pr_number,
            "branch": branch,
            "status": status,  # resolved, auto-resolved, failed, manual
            "method": method,  # auto, manual, hybrid
            "conflict_files": files,
            "conflict_patterns": patterns,
            "file_count": len(files),
            "success": status in ['resolved', 'auto-resolved']
        }

        # Add to experiences
        data['experiences'].append(experience)
        data['total_experiences'] = len(data['experiences'])

        # Update statistics
        if method == 'auto':
            data['statistics']['auto_resolved'] += 1
        elif method == 'manual':
            data['statistics']['manual_resolved'] += 1
        else:
            data['statistics']['failed'] += 1

        # Update file type statistics
        for file_type, count in patterns.items():
            if file_type in data['statistics']['by_file_type']:
                data['statistics']['by_file_type'][file_type] += count
            else:
                data['statistics']['by_file_type'][file_type] = count

        # Save experiences
        self.save_experiences(data)

        # Print summary
        print(f"✅ Experience logged:")
        print(f"   PR: #{pr_number}")
        print(f"   Branch: {branch}")
        print(f"   Status: {status}")
        print(f"   Method: {method}")
        print(f"   Files: {len(files)}")
        if patterns:
            pattern_str = ', '.join(f"{k}:{v}" for k, v in sorted(patterns.items()))
            print(f"   Patterns: {pattern_str}")

        return experience


def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument('--pr', type=int, required=True, help='PR number')
    parser.add_argument('--branch', required=True, help='Branch name')
    parser.add_argument('--status', required=True,
                       choices=['resolved', 'auto-resolved', 'failed', 'manual'],
                       help='Resolution status')
    parser.add_argument('--method', required=True,
                       choices=['auto', 'manual', 'hybrid'],
                       help='Resolution method')
    parser.add_argument('--files', help='Comma-separated list of conflicted files')

    args = parser.parse_args()

    logger = ExperienceLogger()

    files = [f.strip() for f in args.files.split(',')] if args.files else None

    try:
        logger.log_experience(
            args.pr,
            args.branch,
            args.status,
            args.method,
            files
        )
    except Exception as e:
        print(f"❌ Error logging experience: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
