import unittest
from typing import cast
# Assuming execution from backend/ directory or PYTHONPATH includes backend/
from src.services.report_generator import ConversionReportGenerator, MOCK_CONVERSION_RESULT_SUCCESS, MOCK_CONVERSION_RESULT_FAILURE
from src.services.report_models import (
    FeatureConversionDetail, AssumptionDetail
)

class TestConversionReportGenerator(unittest.TestCase):
    def setUp(self):
        self.generator = ConversionReportGenerator()
        self.success_data = MOCK_CONVERSION_RESULT_SUCCESS
        self.failure_data = MOCK_CONVERSION_RESULT_FAILURE

    def test_generate_summary_report_success(self):
        summary = self.generator.generate_summary_report(self.success_data)
        self.assertIsInstance(summary, dict)
        self.assertEqual(summary['overall_success_rate'], self.success_data['overall_success_rate'])
        self.assertEqual(summary['total_features'], self.success_data['total_features'])
        self.assertTrue('download_url' in summary)
        self.assertEqual(summary['download_url'], self.success_data['download_url'])

    def test_generate_summary_report_failure(self):
        summary = self.generator.generate_summary_report(self.failure_data)
        self.assertEqual(summary['overall_success_rate'], self.failure_data['overall_success_rate'])
        # Current generator behavior: if input 'download_url' is None, output is None.
        # This is now consistent with SummaryReport's 'download_url: Optional[str]' type hint.
        self.assertEqual(summary['download_url'], self.failure_data.get('download_url')) # Expecting None here based on mock

    def test_generate_feature_analysis(self):
        analysis = self.generator.generate_feature_analysis(self.success_data['features_data'])
        self.assertIsInstance(analysis, dict)
        self.assertTrue(len(analysis['per_feature_status']) > 0)
        # Example check on one field of the first feature
        if analysis['per_feature_status']: # Check if list is not empty
            first_feature = cast(FeatureConversionDetail, analysis['per_feature_status'][0])
            self.assertEqual(first_feature['feature_name'], self.success_data['features_data'][0]['feature_name'])

    def test_generate_assumptions_report(self):
        assumptions = self.generator.generate_assumptions_report(self.success_data['assumptions_detail_data'])
        self.assertIsInstance(assumptions, dict)
        self.assertTrue(len(assumptions['assumptions']) > 0)
        if assumptions['assumptions']: # Check if list is not empty
            first_assumption = cast(AssumptionDetail, assumptions['assumptions'][0])
            self.assertEqual(first_assumption['assumption_id'], self.success_data['assumptions_detail_data'][0]['assumption_id'])

    def test_generate_developer_log(self):
        dev_log = self.generator.generate_developer_log(self.success_data['developer_logs_data'])
        self.assertIsInstance(dev_log, dict)
        self.assertTrue(len(dev_log['code_translation_details']) > 0)
        self.assertEqual(dev_log['performance_metrics']['total_time_seconds'], self.success_data['developer_logs_data']['performance']['total_time_seconds'])

    def test_create_interactive_report_success(self):
        job_id = self.success_data['job_id']
        report = self.generator.create_interactive_report(self.success_data, job_id)
        self.assertIsInstance(report, dict)
        self.assertEqual(report['job_id'], job_id)
        self.assertIsInstance(report['summary'], dict)
        self.assertIsInstance(report['feature_analysis'], dict)
        self.assertIsInstance(report['smart_assumptions_report'], dict)
        self.assertIsInstance(report['developer_log'], dict)
        self.assertEqual(report['summary']['overall_success_rate'], self.success_data['overall_success_rate'])
        self.assertTrue(len(report['converted_mods']) > 0)

    def test_create_interactive_report_failure(self):
        job_id = self.failure_data['job_id']
        report = self.generator.create_interactive_report(self.failure_data, job_id)
        self.assertEqual(report['job_id'], job_id)
        self.assertEqual(report['summary']['overall_success_rate'], self.failure_data['overall_success_rate'])
        self.assertTrue(len(report['failed_mods']) > 0)

    def test_create_full_conversion_report_prd_style(self):
        report = self.generator.create_full_conversion_report_prd_style(self.success_data)
        self.assertIsInstance(report, dict)
        self.assertIsInstance(report['summary'], dict)
        self.assertTrue(isinstance(report['smart_assumptions'], list))
        if self.success_data.get('smart_assumptions_data'):
            self.assertEqual(len(report['smart_assumptions']), len(self.success_data['smart_assumptions_data']))
        self.assertIsInstance(report['developer_log'], dict)

if __name__ == '__main__':
    unittest.main()
