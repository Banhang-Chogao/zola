#!/usr/bin/env python3
"""Unit tests for experience logger."""

import json
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock
import sys
import tempfile
import shutil

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.log_experience import ExperienceLogger


class TestExperienceLogger(unittest.TestCase):
    """Test the ExperienceLogger class."""

    def setUp(self):
        """Create temporary directory for test files."""
        self.temp_dir = tempfile.mkdtemp()
        self.original_repo_root = None

    def tearDown(self):
        """Clean up temporary files."""
        if self.temp_dir and Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir)

    @patch('scripts.log_experience.Path')
    def test_ensure_file_exists_creates_initial_file(self, mock_path):
        """Test that ensure_file_exists creates the initial file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_file = Path(tmpdir) / '.github' / 'preflight_experiences.json'

            logger = ExperienceLogger.__new__(ExperienceLogger)
            logger.repo_root = Path(tmpdir)
            logger.experience_file = exp_file

            logger.ensure_file_exists()

            assert exp_file.exists()
            data = json.loads(exp_file.read_text())
            assert data['version'] == '1.0'
            assert data['total_experiences'] == 0
            assert data['statistics']['auto_resolved'] == 0

    def test_get_conflict_patterns(self):
        """Test conflict pattern detection."""
        logger = ExperienceLogger.__new__(ExperienceLogger)

        files = [
            'package.json',
            'package-lock.json',
            'data/seo-qa-scores.json',
            'templates/base.html',
            'sass/_footer.scss'
        ]

        patterns = logger.get_conflict_patterns(files)

        assert patterns['package_json'] == 1
        assert patterns['lock_file'] == 1
        assert patterns['scores_json'] == 1
        assert patterns['template_style'] == 2

    def test_log_experience_updates_statistics(self):
        """Test that logging experience updates statistics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_file = Path(tmpdir) / '.github' / 'preflight_experiences.json'

            logger = ExperienceLogger.__new__(ExperienceLogger)
            logger.repo_root = Path(tmpdir)
            logger.experience_file = exp_file

            logger.ensure_file_exists()

            # Mock git command
            with patch('scripts.log_experience.subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(stdout='package.json\npackage-lock.json\n', returncode=0)

                exp = logger.log_experience(123, 'feature/xyz', 'auto-resolved', 'auto')

            # Verify experience was logged
            assert exp['pr_number'] == 123
            assert exp['branch'] == 'feature/xyz'
            assert exp['status'] == 'auto-resolved'
            assert exp['method'] == 'auto'
            assert exp['success'] is True

            # Verify file was updated
            data = json.loads(exp_file.read_text())
            assert data['total_experiences'] == 1
            assert data['statistics']['auto_resolved'] == 1

    def test_log_experience_by_file_type(self):
        """Test statistics tracking by file type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_file = Path(tmpdir) / '.github' / 'preflight_experiences.json'

            logger = ExperienceLogger.__new__(ExperienceLogger)
            logger.repo_root = Path(tmpdir)
            logger.experience_file = exp_file

            logger.ensure_file_exists()

            with patch('scripts.log_experience.subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(
                    stdout='package.json\ndata/seo-qa-scores.json\n',
                    returncode=0
                )

                logger.log_experience(123, 'feature/xyz', 'auto-resolved', 'auto')

            data = json.loads(exp_file.read_text())
            assert data['statistics']['by_file_type']['package_json'] == 1
            assert data['statistics']['by_file_type']['scores_json'] == 1

    def test_multiple_experiences_in_history(self):
        """Test that multiple experiences are tracked."""
        with tempfile.TemporaryDirectory() as tmpdir:
            exp_file = Path(tmpdir) / '.github' / 'preflight_experiences.json'

            logger = ExperienceLogger.__new__(ExperienceLogger)
            logger.repo_root = Path(tmpdir)
            logger.experience_file = exp_file

            logger.ensure_file_exists()

            with patch('scripts.log_experience.subprocess.run') as mock_run:
                mock_run.return_value = MagicMock(stdout='file1.json\n', returncode=0)

                # Log first experience
                logger.log_experience(123, 'feature/xyz', 'auto-resolved', 'auto')
                # Log second experience
                logger.log_experience(124, 'feature/abc', 'manual', 'manual')

            data = json.loads(exp_file.read_text())
            assert len(data['experiences']) == 2
            assert data['total_experiences'] == 2
            assert data['statistics']['auto_resolved'] == 1
            assert data['statistics']['manual_resolved'] == 1


if __name__ == '__main__':
    unittest.main()
