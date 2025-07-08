import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom'; // For extended matchers like .toBeInTheDocument()
import { ConversionReport } from './ConversionReport';
import { InteractiveReport } from '../../types/api';
// Import mock data from stories. Note: Path might need adjustment if stories are elsewhere.
// Assuming stories export named objects like 'successfulConversion' which have an 'args' property.
import { Successful, Failed } from './ConversionReport.stories';

describe('ConversionReport Component', () => {
    test('renders successful conversion report correctly', () => {
        // Storybook's 'Successful' export is an object with an 'args' property
        // which contains 'conversionResult'.
        const mockSuccessReport = Successful.args?.conversionResult as InteractiveReport | undefined;

        if (!mockSuccessReport) {
            throw new Error("Mock data for successfulConversion is not correctly loaded from stories.");
        }

        render(<ConversionReport conversionResult={mockSuccessReport} jobStatus="completed" />);

        // Check for high-level summary elements
        // The main title text might vary based on jobStatus prop, let's check for key elements.
        // Example: if jobStatus="completed", title might be "Conversion Report"
        expect(screen.getByText(/Conversion Report/i)).toBeInTheDocument();

        expect(screen.getByText("Overall Success Rate:")).toBeInTheDocument();
        expect(screen.getByText(mockSuccessReport.summary.overall_success_rate.toFixed(1) + "%")).toBeInTheDocument();

        if (mockSuccessReport.summary.download_url) {
            expect(screen.getByRole('link', { name: /Download .mcaddon/i })).toHaveAttribute('href', mockSuccessReport.summary.download_url);
        }

        if (mockSuccessReport.converted_mods && mockSuccessReport.converted_mods.length > 0) {
            expect(screen.getByText(new RegExp("Converted Mods \\(" + mockSuccessReport.converted_mods.length + "\\)", "i"))).toBeInTheDocument();
            // Check for the first converted mod's name (should appear at least once)
            expect(screen.getAllByText(new RegExp(mockSuccessReport.converted_mods[0].name, "i"))[0]).toBeInTheDocument();
        }

        if (mockSuccessReport.smart_assumptions_report && mockSuccessReport.smart_assumptions_report.assumptions.length > 0) {
            expect(screen.getByText(/Detailed Smart Assumptions/i)).toBeInTheDocument();
        }
        if (mockSuccessReport.feature_analysis) {
            expect(screen.getByText(/Detailed Feature Analysis/i)).toBeInTheDocument();
        }
        if (mockSuccessReport.developer_log) {
            expect(screen.getByText(/Developer Technical Log/i)).toBeInTheDocument();
        }
    });

    test('renders failed conversion report correctly', () => {
        const mockFailedReport = Failed.args?.conversionResult as InteractiveReport | undefined;

        if (!mockFailedReport) {
            throw new Error("Mock data for failedConversion is not correctly loaded from stories.");
        }

        render(<ConversionReport conversionResult={mockFailedReport} jobStatus="failed" />);

        expect(screen.getByText(/Conversion Failed/i)).toBeInTheDocument();
        // For failed reports, success rate might still be displayed
        expect(screen.getByText("Overall Success Rate:")).toBeInTheDocument();
        expect(screen.getByText(mockFailedReport.summary.overall_success_rate.toFixed(1) + "%")).toBeInTheDocument();

        if (mockFailedReport.failed_mods && mockFailedReport.failed_mods.length > 0) {
            expect(screen.getByText(new RegExp("Failed Mods \\(" + mockFailedReport.failed_mods.length + "\\)", "i"))).toBeInTheDocument();
            // Check for the first failed mod's name
            expect(screen.getAllByText(new RegExp(mockFailedReport.failed_mods[0].name, "i"))[0]).toBeInTheDocument();
            // And its first error, if available
            if (mockFailedReport.failed_mods[0].errors && mockFailedReport.failed_mods[0].errors.length > 0) {
                 // The error message might be long, so we test for a substring or use a flexible matcher
                 // For simplicity, let's assume the error message itself is not too complex for getByText
                 // or use a custom text matcher if needed.
                 // This test will be sensitive to the exact error message in mock data.
                 expect(screen.getByText(mockFailedReport.failed_mods[0].errors[0])).toBeInTheDocument();
            }
        }

        if (mockFailedReport.summary.download_url) {
             expect(screen.getByRole('link', { name: /Download .mcaddon/i })).toBeInTheDocument();
        } else {
             expect(screen.queryByRole('link', { name: /Download .mcaddon/i })).not.toBeInTheDocument();
        }
    });

    test('displays developer log content if available', () => {
        const mockReportWithDevLog = Successful.args?.conversionResult as InteractiveReport | undefined;

        if (!mockReportWithDevLog) {
            throw new Error("Mock data for successfulConversion (for dev log test) is not correctly loaded.");
        }

        if (!mockReportWithDevLog.developer_log ||
            !mockReportWithDevLog.developer_log.performance_metrics ||
            mockReportWithDevLog.developer_log.performance_metrics.total_time_seconds === undefined) {
            console.warn("Skipping dev log content test: mock data for performance_metrics.total_time_seconds is incomplete or undefined.");
            // Optionally, make the test fail if the mock data isn't as expected for this specific test
            // fail("Mock data for developer_log.performance_metrics.total_time_seconds is missing.");
            return;
        }

        render(<ConversionReport conversionResult={mockReportWithDevLog} jobStatus="completed" />);

        // The <details> tag for Developer Log should be present
        const devLogDetailsSummary = screen.getByText(/Developer Technical Log/i);
        expect(devLogDetailsSummary).toBeInTheDocument();

        // Check for a specific metric (e.g. total_time_seconds)
        // The current component implementation stringifies performance_metrics.
        // We need to find the text within the <pre> block.
        const perfMetricsPreElement = screen.getByText((content, element) => {
            return element?.tagName.toLowerCase() === 'pre' && content.includes('"total_time_seconds"');
        });
        expect(perfMetricsPreElement).toBeInTheDocument();
        expect(perfMetricsPreElement.textContent).toContain(`"total_time_seconds": ${mockReportWithDevLog.developer_log.performance_metrics.total_time_seconds}`);

        // Check for a log entry message if available
        if (mockReportWithDevLog.developer_log.code_translation_details && mockReportWithDevLog.developer_log.code_translation_details.length > 0) {
            expect(screen.getByText(new RegExp(mockReportWithDevLog.developer_log.code_translation_details[0].message, "i"))).toBeInTheDocument();
        }
    });
});
