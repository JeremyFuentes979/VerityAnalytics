import csv
import json
import os
import shutil
import tempfile
import unittest

from agents.analyst.analyst import run_analysis
from agents.auditor.auditor import Auditor


class WorkflowContractsTests(unittest.TestCase):
    def setUp(self):
        self.workdir = tempfile.mkdtemp(prefix='quorum-contract-')
        self.session_dir = os.path.join(self.workdir, 'demo-session')
        os.makedirs(self.session_dir, exist_ok=True)

        os.makedirs(os.path.join(self.session_dir, 'raw'), exist_ok=True)
        with open(os.path.join(self.session_dir, 'profile.json'), 'w') as f:
            json.dump({"raw_data_file": 'data.csv'}, f)

        with open(os.path.join(self.session_dir, 'raw', 'data.csv'), 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['customer', 'amount', 'status'])
            writer.writerow(['A', '100', 'paid'])
            writer.writerow(['A', '100', 'paid'])
            writer.writerow(['B', '-50', 'pending'])
            writer.writerow(['C', '200', 'paid'])

    def tearDown(self):
        shutil.rmtree(self.workdir)

    def test_analyst_produces_manager_compatible_keys(self):
        run_analysis(self.session_dir)
        with open(os.path.join(self.session_dir, 'analysis.json')) as f:
            analysis = json.load(f)
        self.assertIn('key_metrics', analysis)
        self.assertIn('patterns', analysis)
        self.assertIn('recommendations', analysis)
        self.assertIn('data_quality', analysis)

    def test_auditor_writes_manager_compatible_outputs(self):
        run_analysis(self.session_dir)
        os.makedirs(os.path.join(self.session_dir, 'raw'), exist_ok=True)

        auditor = Auditor(self.session_dir)
        auditor.validate_and_clean()

        self.assertTrue(os.path.exists(os.path.join(self.session_dir, 'cleaned_data.csv')))
        self.assertTrue(os.path.exists(os.path.join(self.session_dir, 'audit_trail.json')))

        with open(os.path.join(self.session_dir, 'audit_trail.json')) as f:
            trail = json.load(f)
        self.assertIn('corrections', trail)
        self.assertIn('data_quality_issues', trail)


if __name__ == '__main__':
    unittest.main()
