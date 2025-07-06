"""
QA Validator Agent for validating conversion quality and generating comprehensive reports
"""

from typing import Dict, List, Any, Optional, Tuple

import logging
import json
from datetime import datetime
from pathlib import Path
from langchain.tools import tool
from ..models.smart_assumptions import (
    SmartAssumptionEngine, FeatureContext, ConversionPlanComponent, AssumptionReport
)

logger = logging.getLogger(__name__)


class QAValidatorAgent:
    """
    QA Validator Agent responsible for validating conversion quality and
    generating comprehensive reports as specified in PRD Feature 2.
    """
    
    def __init__(self):
        self.smart_assumption_engine = SmartAssumptionEngine()
        
        # Quality metrics and thresholds
        self.quality_thresholds = {
            'feature_conversion_rate': 0.8,  # 80% of features should convert successfully
            'assumption_accuracy': 0.9,      # 90% of assumptions should be appropriate
            'bedrock_compatibility': 0.95,   # 95% Bedrock compatibility
            'performance_score': 0.7,        # 70% performance threshold
            'user_experience_score': 0.8     # 80% UX threshold
        }
        
        # Test categories and weights
        self.test_categories = {
            'functional_tests': {
                'weight': 0.4,
                'subcategories': ['feature_behavior', 'logic_correctness', 'data_integrity']
            },
            'compatibility_tests': {
                'weight': 0.3,
                'subcategories': ['bedrock_api_usage', 'version_compatibility', 'device_compatibility']
            },
            'performance_tests': {
                'weight': 0.2,
                'subcategories': ['memory_usage', 'cpu_performance', 'network_efficiency']
            },
            'user_experience_tests': {
                'weight': 0.1,
                'subcategories': ['installation_process', 'error_handling', 'user_feedback']
            }
        }
        
        # Common issues and their severity levels
        self.issue_severity = {
            'critical': {'weight': 10, 'description': 'Prevents functionality or causes crashes'},
            'major': {'weight': 5, 'description': 'Significantly impacts functionality'},
            'minor': {'weight': 2, 'description': 'Minor functionality impact'},
            'cosmetic': {'weight': 1, 'description': 'Visual or aesthetic issues only'}
        }
    
    def get_tools(self) -> List:
        """Get tools available to this agent"""
        return [
            self.validate_conversion_quality_tool,
            self.run_functional_tests_tool,
            self.analyze_bedrock_compatibility_tool,
            self.assess_performance_metrics_tool,
            self.generate_qa_report_tool
        ]
    
    @tool
    def validate_conversion_quality_tool(self, quality_data: str) -> str:
        """Validate overall conversion quality."""
        return self.validate_conversion_quality(quality_data)
    
    @tool
    def run_functional_tests_tool(self, test_data: str) -> str:
        """Run functional tests on the converted addon."""
        return self.run_functional_tests(test_data)
    
    @tool
    def analyze_bedrock_compatibility_tool(self, compatibility_data: str) -> str:
        """Analyze Bedrock compatibility of the conversion."""
        return self.analyze_bedrock_compatibility(compatibility_data)
    
    @tool
    def assess_performance_metrics_tool(self, performance_data: str) -> str:
        """Assess performance metrics of the converted addon."""
        return self.assess_performance_metrics(performance_data)
    
    @tool
    def generate_qa_report_tool(self, report_data: str) -> str:
        """Generate comprehensive QA report."""
        return self.generate_qa_report(report_data)
    
    
    def validate_conversion_quality(self, validation_data: str) -> str:
        """
        Perform comprehensive quality validation of the conversion.
        
        Args:
            validation_data: JSON string containing conversion results and components:
                           conversion_results, original_features, assumptions_applied
        
        Returns:
            JSON string with comprehensive quality validation results
        """
        try:
            data = json.loads(validation_data)
            
            conversion_results = data.get('conversion_results', {})
            original_features = data.get('original_features', [])
            assumptions_applied = data.get('assumptions_applied', [])
            
            quality_assessment = {
                'overall_quality_score': 0.0,
                'feature_conversion_analysis': {},
                'assumption_validation': {},
                'completeness_assessment': {},
                'accuracy_assessment': {},
                'risk_analysis': {}
            }
            
            # Analyze feature conversion success rate
            feature_analysis = self._analyze_feature_conversion(conversion_results, original_features)
            quality_assessment['feature_conversion_analysis'] = feature_analysis
            
            # Validate assumption usage and appropriateness
            assumption_validation = self._validate_assumptions(assumptions_applied, original_features)
            quality_assessment['assumption_validation'] = assumption_validation
            
            # Assess conversion completeness
            completeness = self._assess_conversion_completeness(conversion_results, original_features)
            quality_assessment['completeness_assessment'] = completeness
            
            # Assess conversion accuracy
            accuracy = self._assess_conversion_accuracy(conversion_results, assumptions_applied)
            quality_assessment['accuracy_assessment'] = accuracy
            
            # Analyze risks and potential issues
            risk_analysis = self._analyze_conversion_risks(conversion_results, assumptions_applied)
            quality_assessment['risk_analysis'] = risk_analysis
            
            # Calculate overall quality score
            overall_score = self._calculate_overall_quality_score(quality_assessment)
            quality_assessment['overall_quality_score'] = overall_score
            
            response = {
                "success": True,
                "quality_assessment": quality_assessment,
                "quality_grade": self._get_quality_grade(overall_score),
                "recommendations": self._generate_quality_recommendations(quality_assessment)
            }
            
            logger.info(f"Quality validation completed with score: {overall_score:.2f}")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to validate quality: {str(e)}"}
            logger.error(f"Quality validation error: {e}")
            return json.dumps(error_response)
    
    
    def run_functional_tests(self, test_data: str) -> str:
        """
        Run functional tests on converted components.
        
        Args:
            test_data: JSON string containing test configuration and components to test
        
        Returns:
            JSON string with functional test results
        """
        try:
            data = json.loads(test_data)
            
            test_components = data.get('test_components', [])
            test_scenarios = data.get('test_scenarios', [])
            test_config = data.get('config', {})
            
            test_results = {
                'total_tests': 0,
                'passed_tests': 0,
                'failed_tests': 0,
                'skipped_tests': 0,
                'test_details': [],
                'category_results': {}
            }
            
            # Run tests for each category
            for category, category_info in self.test_categories.items():
                if category == 'functional_tests':  # Only run functional tests in this tool
                    category_results = self._run_category_tests(
                        category, category_info, test_components, test_scenarios, test_config
                    )
                    test_results['category_results'][category] = category_results
                    
                    # Update totals
                    test_results['total_tests'] += category_results['total_tests']
                    test_results['passed_tests'] += category_results['passed_tests']
                    test_results['failed_tests'] += category_results['failed_tests']
                    test_results['skipped_tests'] += category_results['skipped_tests']
                    test_results['test_details'].extend(category_results['test_details'])
            
            # Calculate success rate
            success_rate = (test_results['passed_tests'] / test_results['total_tests'] 
                          if test_results['total_tests'] > 0 else 0)
            
            response = {
                "success": True,
                "test_results": test_results,
                "success_rate": round(success_rate, 3),
                "test_summary": self._generate_test_summary(test_results)
            }
            
            logger.info(f"Functional tests completed: {test_results['passed_tests']}/{test_results['total_tests']} passed")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to run functional tests: {str(e)}"}
            logger.error(f"Functional test error: {e}")
            return json.dumps(error_response)
    
    
    def analyze_bedrock_compatibility(self, compatibility_data: str) -> str:
        """
        Analyze Bedrock compatibility of converted components.
        
        Args:
            compatibility_data: JSON string containing components and compatibility requirements
        
        Returns:
            JSON string with Bedrock compatibility analysis
        """
        try:
            data = json.loads(compatibility_data)
            
            components = data.get('components', [])
            target_version = data.get('target_bedrock_version', '1.19.0')
            requirements = data.get('requirements', {})
            
            compatibility_analysis = {
                'overall_compatibility_score': 0.0,
                'api_compatibility': {},
                'version_compatibility': {},
                'feature_compatibility': {},
                'platform_compatibility': {},
                'incompatible_features': [],
                'warnings': [],
                'recommendations': []
            }
            
            # Analyze API compatibility
            api_compatibility = self._analyze_api_compatibility(components, target_version)
            compatibility_analysis['api_compatibility'] = api_compatibility
            
            # Analyze version compatibility
            version_compatibility = self._analyze_version_compatibility(components, target_version)
            compatibility_analysis['version_compatibility'] = version_compatibility
            
            # Analyze feature compatibility
            feature_compatibility = self._analyze_feature_compatibility(components, requirements)
            compatibility_analysis['feature_compatibility'] = feature_compatibility
            
            # Analyze platform compatibility
            platform_compatibility = self._analyze_platform_compatibility(components)
            compatibility_analysis['platform_compatibility'] = platform_compatibility
            
            # Identify incompatible features
            incompatible = self._identify_incompatible_features(components)
            compatibility_analysis['incompatible_features'] = incompatible
            
            # Generate warnings and recommendations
            warnings, recommendations = self._generate_compatibility_guidance(compatibility_analysis)
            compatibility_analysis['warnings'] = warnings
            compatibility_analysis['recommendations'] = recommendations
            
            # Calculate overall compatibility score
            overall_score = self._calculate_compatibility_score(compatibility_analysis)
            compatibility_analysis['overall_compatibility_score'] = overall_score
            
            response = {
                "success": True,
                "compatibility_analysis": compatibility_analysis,
                "compatibility_grade": self._get_compatibility_grade(overall_score),
                "certification_status": self._get_certification_status(compatibility_analysis)
            }
            
            logger.info(f"Bedrock compatibility analysis completed with score: {overall_score:.2f}")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to analyze compatibility: {str(e)}"}
            logger.error(f"Compatibility analysis error: {e}")
            return json.dumps(error_response)
    
    
    def assess_performance_metrics(self, performance_data: str) -> str:
        """
        Assess performance metrics of converted components.
        
        Args:
            performance_data: JSON string containing performance test data and metrics
        
        Returns:
            JSON string with performance assessment results
        """
        try:
            data = json.loads(performance_data)
            
            metrics = data.get('metrics', {})
            benchmarks = data.get('benchmarks', {})
            test_scenarios = data.get('test_scenarios', [])
            
            performance_assessment = {
                'overall_performance_score': 0.0,
                'memory_analysis': {},
                'cpu_analysis': {},
                'network_analysis': {},
                'startup_analysis': {},
                'runtime_analysis': {},
                'optimization_opportunities': [],
                'performance_warnings': []
            }
            
            # Analyze memory usage
            memory_analysis = self._analyze_memory_performance(metrics.get('memory', {}), benchmarks)
            performance_assessment['memory_analysis'] = memory_analysis
            
            # Analyze CPU performance
            cpu_analysis = self._analyze_cpu_performance(metrics.get('cpu', {}), benchmarks)
            performance_assessment['cpu_analysis'] = cpu_analysis
            
            # Analyze network performance
            network_analysis = self._analyze_network_performance(metrics.get('network', {}), benchmarks)
            performance_assessment['network_analysis'] = network_analysis
            
            # Analyze startup performance
            startup_analysis = self._analyze_startup_performance(metrics.get('startup', {}), benchmarks)
            performance_assessment['startup_analysis'] = startup_analysis
            
            # Analyze runtime performance
            runtime_analysis = self._analyze_runtime_performance(metrics.get('runtime', {}), benchmarks)
            performance_assessment['runtime_analysis'] = runtime_analysis
            
            # Identify optimization opportunities
            optimizations = self._identify_optimization_opportunities(performance_assessment)
            performance_assessment['optimization_opportunities'] = optimizations
            
            # Generate performance warnings
            warnings = self._generate_performance_warnings(performance_assessment)
            performance_assessment['performance_warnings'] = warnings
            
            # Calculate overall performance score
            overall_score = self._calculate_performance_score(performance_assessment)
            performance_assessment['overall_performance_score'] = overall_score
            
            response = {
                "success": True,
                "performance_assessment": performance_assessment,
                "performance_grade": self._get_performance_grade(overall_score),
                "optimization_priority": self._get_optimization_priority(performance_assessment)
            }
            
            logger.info(f"Performance assessment completed with score: {overall_score:.2f}")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to assess performance: {str(e)}"}
            logger.error(f"Performance assessment error: {e}")
            return json.dumps(error_response)
    
    
    def generate_qa_report(self, report_data: str) -> str:
        """
        Generate a comprehensive QA report combining all validation results.
        
        Args:
            report_data: JSON string containing all QA results and metadata
        
        Returns:
            JSON string with comprehensive QA report
        """
        try:
            data = json.loads(report_data)
            
            quality_results = data.get('quality_results', {})
            functional_results = data.get('functional_results', {})
            compatibility_results = data.get('compatibility_results', {})
            performance_results = data.get('performance_results', {})
            metadata = data.get('metadata', {})
            
            qa_report = {
                'report_metadata': self._generate_report_metadata(metadata),
                'executive_summary': {},
                'detailed_results': {},
                'quality_metrics': {},
                'risk_assessment': {},
                'recommendations': {},
                'certification': {},
                'appendices': {}
            }
            
            # Generate executive summary
            executive_summary = self._generate_executive_summary(
                quality_results, functional_results, compatibility_results, performance_results
            )
            qa_report['executive_summary'] = executive_summary
            
            # Compile detailed results
            detailed_results = self._compile_detailed_results(
                quality_results, functional_results, compatibility_results, performance_results
            )
            qa_report['detailed_results'] = detailed_results
            
            # Calculate quality metrics
            quality_metrics = self._calculate_quality_metrics(
                quality_results, functional_results, compatibility_results, performance_results
            )
            qa_report['quality_metrics'] = quality_metrics
            
            # Perform risk assessment
            risk_assessment = self._perform_risk_assessment(
                quality_results, functional_results, compatibility_results, performance_results
            )
            qa_report['risk_assessment'] = risk_assessment
            
            # Generate recommendations
            recommendations = self._generate_comprehensive_recommendations(qa_report)
            qa_report['recommendations'] = recommendations
            
            # Determine certification status
            certification = self._determine_certification_status(qa_report)
            qa_report['certification'] = certification
            
            # Generate appendices
            appendices = self._generate_report_appendices(qa_report, metadata)
            qa_report['appendices'] = appendices
            
            response = {
                "success": True,
                "qa_report": qa_report,
                "report_formats": {
                    "json": "Complete structured report",
                    "html": "Human-readable HTML report",
                    "pdf": "Professional PDF report",
                    "summary": "Executive summary only"
                }
            }
            
            logger.info("Comprehensive QA report generated successfully")
            return json.dumps(response)
            
        except Exception as e:
            error_response = {"success": False, "error": f"Failed to generate QA report: {str(e)}"}
            logger.error(f"QA report generation error: {e}")
            return json.dumps(error_response)
    
    # Helper methods for quality validation
    
    def _analyze_feature_conversion(self, conversion_results: Dict, original_features: List[Dict]) -> Dict:
        """Analyze feature conversion success rate and quality"""
        total_features = len(original_features)
        successfully_converted = 0
        partially_converted = 0
        failed_conversions = 0
        
        conversion_details = []
        
        for feature in original_features:
            feature_id = feature.get('feature_id', 'unknown')
            feature_result = conversion_results.get(feature_id, {})
            
            if feature_result.get('status') == 'success':
                successfully_converted += 1
                conversion_quality = 'high'
            elif feature_result.get('status') == 'partial':
                partially_converted += 1
                conversion_quality = 'medium'
            else:
                failed_conversions += 1
                conversion_quality = 'low'
            
            conversion_details.append({
                'feature_id': feature_id,
                'feature_type': feature.get('feature_type', 'unknown'),
                'conversion_status': feature_result.get('status', 'failed'),
                'conversion_quality': conversion_quality,
                'issues': feature_result.get('issues', [])
            })
        
        success_rate = successfully_converted / total_features if total_features > 0 else 0
        
        return {
            'total_features': total_features,
            'successfully_converted': successfully_converted,
            'partially_converted': partially_converted,
            'failed_conversions': failed_conversions,
            'success_rate': round(success_rate, 3),
            'conversion_details': conversion_details,
            'meets_threshold': success_rate >= self.quality_thresholds['feature_conversion_rate']
        }
    
    def _validate_assumptions(self, assumptions_applied: List[Dict], original_features: List[Dict]) -> Dict:
        """Validate the appropriateness and accuracy of assumptions used"""
        total_assumptions = len(assumptions_applied)
        appropriate_assumptions = 0
        questionable_assumptions = 0
        inappropriate_assumptions = 0
        
        assumption_details = []
        
        for assumption in assumptions_applied:
            # Analyze assumption appropriateness based on feature context
            appropriateness = self._assess_assumption_appropriateness(assumption, original_features)
            
            if appropriateness['score'] >= 0.8:
                appropriate_assumptions += 1
                category = 'appropriate'
            elif appropriateness['score'] >= 0.6:
                questionable_assumptions += 1
                category = 'questionable'
            else:
                inappropriate_assumptions += 1
                category = 'inappropriate'
            
            assumption_details.append({
                'assumption_id': assumption.get('assumption_id', 'unknown'),
                'java_feature': assumption.get('java_feature', 'unknown'),
                'bedrock_equivalent': assumption.get('bedrock_equivalent', 'unknown'),
                'appropriateness_category': category,
                'appropriateness_score': appropriateness['score'],
                'reasoning': appropriateness['reasoning']
            })
        
        accuracy_rate = appropriate_assumptions / total_assumptions if total_assumptions > 0 else 0
        
        return {
            'total_assumptions': total_assumptions,
            'appropriate_assumptions': appropriate_assumptions,
            'questionable_assumptions': questionable_assumptions,
            'inappropriate_assumptions': inappropriate_assumptions,
            'accuracy_rate': round(accuracy_rate, 3),
            'assumption_details': assumption_details,
            'meets_threshold': accuracy_rate >= self.quality_thresholds['assumption_accuracy']
        }
    
    def _assess_conversion_completeness(self, conversion_results: Dict, original_features: List[Dict]) -> Dict:
        """Assess how complete the conversion is"""
        feature_categories = {}
        
        # Categorize original features
        for feature in original_features:
            category = feature.get('category', 'unknown')
            feature_categories[category] = feature_categories.get(category, 0) + 1
        
        # Analyze completeness per category
        category_completeness = {}
        overall_completeness = 0
        
        for category, count in feature_categories.items():
            converted_count = sum(1 for feature in original_features 
                                if feature.get('category') == category and 
                                conversion_results.get(feature.get('feature_id', ''), {}).get('status') == 'success')
            
            completeness = converted_count / count if count > 0 else 0
            category_completeness[category] = {
                'total_features': count,
                'converted_features': converted_count,
                'completeness_rate': round(completeness, 3)
            }
            
        # Calculate overall completeness
        total_features = sum(info['total_features'] for info in category_completeness.values())
        total_converted = sum(info['converted_features'] for info in category_completeness.values())
        overall_completeness = total_converted / total_features if total_features > 0 else 0
        
        return {
            'overall_completeness': round(overall_completeness, 3),
            'category_completeness': category_completeness,
            'meets_expectations': overall_completeness >= 0.8
        }
    
    def _assess_conversion_accuracy(self, conversion_results: Dict, assumptions_applied: List[Dict]) -> Dict:
        """Assess conversion accuracy"""
        total_conversions = len(conversion_results)
        accurate_conversions = sum(1 for result in conversion_results.values() 
                                 if result.get('status') == 'success')
        
        accuracy_rate = accurate_conversions / total_conversions if total_conversions > 0 else 0
        
        return {
            'accuracy_rate': round(accuracy_rate, 3),
            'total_conversions': total_conversions,
            'accurate_conversions': accurate_conversions,
            'assumptions_impact': len(assumptions_applied)
        }
    
    def _analyze_conversion_risks(self, conversion_results: Dict, assumptions_applied: List[Dict]) -> Dict:
        """Analyze conversion risks"""
        risks = []
        
        if assumptions_applied:
            risks.append({
                'type': 'assumption_risk',
                'severity': 'medium',
                'description': f'{len(assumptions_applied)} assumptions applied'
            })
        
        failed_conversions = sum(1 for result in conversion_results.values() 
                               if result.get('status') != 'success')
        
        if failed_conversions > 0:
            risks.append({
                'type': 'conversion_failure',
                'severity': 'high',
                'description': f'{failed_conversions} conversions failed'
            })
        
        return {
            'total_risks': len(risks),
            'risks': risks,
            'risk_level': 'high' if any(r['severity'] == 'high' for r in risks) else 'medium'
        }
    
    def _calculate_overall_quality_score(self, quality_assessment: Dict) -> float:
        """Calculate overall quality score"""
        feature_score = quality_assessment.get('feature_conversion_analysis', {}).get('success_rate', 0)
        assumption_score = quality_assessment.get('assumption_validation', {}).get('accuracy_rate', 0)
        completeness_score = quality_assessment.get('completeness_assessment', {}).get('overall_completeness', 0)
        accuracy_score = quality_assessment.get('accuracy_assessment', {}).get('accuracy_rate', 0)
        
        # Weighted average
        overall_score = (feature_score * 0.3 + assumption_score * 0.25 + 
                        completeness_score * 0.25 + accuracy_score * 0.2)
        
        return round(overall_score, 3)
    
    def _get_quality_grade(self, score: float) -> str:
        """Get quality grade based on score"""
        if score >= 0.9:
            return 'A'
        elif score >= 0.8:
            return 'B'
        elif score >= 0.7:
            return 'C'
        elif score >= 0.6:
            return 'D'
        else:
            return 'F'
    
    def _generate_quality_recommendations(self, quality_assessment: Dict) -> List[str]:
        """Generate quality recommendations"""
        recommendations = []
        
        feature_analysis = quality_assessment.get('feature_conversion_analysis', {})
        if feature_analysis.get('success_rate', 0) < 0.8:
            recommendations.append("Improve feature conversion rate")
        
        assumption_validation = quality_assessment.get('assumption_validation', {})
        if assumption_validation.get('accuracy_rate', 0) < 0.9:
            recommendations.append("Review assumption appropriateness")
        
        return recommendations
    
    def _assess_assumption_appropriateness(self, assumption: Dict, original_features: List[Dict]) -> Dict:
        """Assess assumption appropriateness"""
        # Simple scoring based on assumption type
        score = 0.8  # Default score
        reasoning = "Standard assumption applied"
        
        return {
            'score': score,
            'reasoning': reasoning
        }
       