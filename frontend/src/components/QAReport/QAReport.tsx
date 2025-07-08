// frontend/src/components/QAReport/QAReport.tsx
import React, { useState, useEffect } from 'react';
import './QAReport.css'; // Import the CSS file

// Define interfaces for the report data structures (based on API placeholders)
interface QATestSummary {
    total_tests?: number;
    passed?: number;
    failed?: number;
    overall_quality_score?: number;
    [key: string]: any; // For other summary fields
}

interface QAReportData {
    report_id?: string;
    task_id?: string;
    conversion_id?: string;
    generated_at?: string;
    overall_quality_score?: number;
    summary?: QATestSummary;
    functional_tests?: any; // Define more specific types later
    performance_tests?: any;
    compatibility_tests?: any;
    recommendations?: string[];
    severity_ratings?: Record<string, number>;
    [key: string]: any; // Allow other top-level fields
}

interface QAReportProps {
    taskId: string; // Task ID to fetch the report for
    apiBaseUrl?: string; // Optional base URL for the API
}

const QAReport: React.FC<QAReportProps> = ({ taskId, apiBaseUrl = '/api/qa' }) => {
    const [report, setReport] = useState<QAReportData | null>(null);
    const [loading, setLoading] = useState<boolean>(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchReport = async () => {
            setLoading(true);
            setError(null);
            try {
                // In a real app, this would use the actual API endpoint function `get_qa_report`
                // For now, it simulates fetching based on the structure of backend/src/api/qa.py
                // const response = await fetch(`${apiBaseUrl}/report/${taskId}?format=json`); // Example fetch

                // Simulate API call based on the mock structure in qa.py
                // This is a mock fetch, replace with actual API call to backend/src/api/qa.py::get_qa_report
                // For demonstration, we'll use a timeout and mock data.
                console.log(`Fetching QA report for task ID: ${taskId} from ${apiBaseUrl}/report/${taskId}`);

                // Mocking the API call delay
                await new Promise(resolve => setTimeout(resolve, 1000));

                // Mocked response structure, similar to what get_qa_report in qa.py might return
                // This should align with the 'mock_report_content' in qa.py's get_qa_report
                const mockApiResponse = {
                    success: true,
                    report_format: "json",
                    report: {
                        report_id: `report_${taskId}`,
                        task_id: taskId,
                        conversion_id: `conv_for_${taskId}`,
                        generated_at: new Date().toISOString(),
                        overall_quality_score: Math.random() * (0.98 - 0.75) + 0.75, // Random score between 0.75 and 0.98
                        summary: {
                            total_tests: 100,
                            passed: Math.floor(Math.random() * 20) + 75, // 75 to 95 passed
                            // 'failed' would be total_tests - passed
                            performance_score: Math.random(),
                            compatibility_score: Math.random(),
                        },
                        functional_tests: { passed: 40, failed: 1, skipped: 1, details: [{name: "Test A", status: "passed"}, {name: "Test B", status: "failed"}] },
                        performance_tests: { cpu_avg: "20%", memory_peak: "250MB", details: [{name: "Load Test", metrics: "OK"}] },
                        compatibility_tests: { versions_tested: ["1.19.0", "1.20.0"], issues: 0, details: [{name: "Version X", status: "passed"}]},
                        recommendations: ["Review item placement logic.", "Optimize texture loading for 'custom_block_A'."],
                        severity_ratings: { critical: 0, major: 1, minor: 2, cosmetic: 1 }
                    }
                };

                if (mockApiResponse.success && mockApiResponse.report) {
                    setReport(mockApiResponse.report);
                } else {
                    // setError(mockApiResponse.error || 'Failed to fetch report');
                    setError('Failed to fetch report (mock error). Task might not be completed or found.');
                }
            } catch (e) {
                console.error("Error fetching QA report:", e);
                setError(e instanceof Error ? e.message : 'An unknown error occurred.');
            } finally {
                setLoading(false);
            }
        };

        if (taskId) {
            fetchReport();
        } else {
            setError("Task ID is required to fetch a QA report.");
            setLoading(false);
        }
    }, [taskId, apiBaseUrl]);

    if (loading) {
        return <div className="qa-report-loading">Loading QA Report for Task ID: {taskId}...</div>;
    }

    if (error) {
        return <div className="qa-report-error">Error: {error}</div>;
    }

    if (!report) {
        return <div className="qa-report-empty">No report data available for Task ID: {taskId}.</div>;
    }

    // Basic rendering of the report
    return (
        <div className="qa-report-container">
            <h2>QA Report (Task ID: {report.task_id})</h2>
            <p><strong>Report ID:</strong> {report.report_id}</p>
            <p><strong>Conversion ID:</strong> {report.conversion_id}</p>
            <p><strong>Generated At:</strong> {new Date(report.generated_at || Date.now()).toLocaleString()}</p>

            <div className="qa-section overall-summary">
                <h3>Overall Summary</h3>
                <p><strong>Overall Quality Score:</strong> {report.overall_quality_score?.toFixed(2) ?? 'N/A'}</p>
                <p>Total Tests: {report.summary?.total_tests ?? 'N/A'}</p>
                <p>Passed: {report.summary?.passed ?? 'N/A'}</p>
                <p>Failed: {report.summary?.total_tests && report.summary?.passed ? report.summary.total_tests - report.summary.passed : 'N/A'}</p>
            </div>

            <div className="qa-section functional-tests">
                <h3>Functional Tests</h3>
                {/* Render more details from report.functional_tests */}
                <pre>{JSON.stringify(report.functional_tests, null, 2)}</pre>
            </div>

            <div className="qa-section performance-tests">
                <h3>Performance Tests</h3>
                {/* Render more details from report.performance_tests */}
                <pre>{JSON.stringify(report.performance_tests, null, 2)}</pre>
            </div>

            <div className="qa-section compatibility-tests">
                <h3>Compatibility Tests</h3>
                {/* Render more details from report.compatibility_tests */}
                <pre>{JSON.stringify(report.compatibility_tests, null, 2)}</pre>
            </div>

            <div className="qa-section recommendations">
                <h3>Recommendations</h3>
                <ul>
                    {report.recommendations?.map((rec, index) => (
                        <li key={index}>{rec}</li>
                    ))}
                </ul>
            </div>

            <div className="qa-section severity-ratings">
                <h3>Issue Severity</h3>
                {/* Render more details from report.severity_ratings */}
                <pre>{JSON.stringify(report.severity_ratings, null, 2)}</pre>
            </div>
        </div>
    );
};

export default QAReport;
