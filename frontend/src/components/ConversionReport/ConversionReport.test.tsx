import { render, screen, fireEvent, waitFor } from '@testing-library/react'; // Added fireEvent, waitFor
import '@testing-library/jest-dom'; // For extended matchers like .toBeInTheDocument()
import { ConversionReport } from './ConversionReport';
import { InteractiveReport, FeedbackResponse } from '../../types/api'; // Added FeedbackResponse
// Import mock data from stories. Note: Path might need adjustment if stories are elsewhere.
// Assuming stories export named objects like 'successfulConversion' which have an 'args' property.
import { Successful, Failed } from './ConversionReport.stories';
import { submitFeedback as mockSubmitFeedback } from '../../services/api'; // Import the actual function to be mocked

// Mock the API service
jest.mock('../../services/api', () => ({
  ...jest.requireActual('../../services/api'), // Import and retain default exports
  submitFeedback: jest.fn(), // Mock only submitFeedback
}));

// Cast the mock for type safety in tests
const mockedSubmitFeedback = submitFeedback as jest.MockedFunction<typeof mockSubmitFeedback>;


const minimalMockReport: InteractiveReport = {
  job_id: 'test-job-123',
  report_generation_date: new Date().toISOString(),
  summary: {
    overall_success_rate: 100,
    total_features: 10,
    converted_features: 10,
    partially_converted_features: 0,
    failed_features: 0,
    assumptions_applied_count: 1,
    processing_time_seconds: 60,
    download_url: '/download/test-job-123.zip',
    quick_statistics: {},
  },
  converted_mods: [],
  failed_mods: [],
};


describe('ConversionReport Component', () => {
    beforeEach(() => {
        // Clear mock call history before each test
        mockedSubmitFeedback.mockClear();
    });

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

describe('Feedback Functionality in ConversionReport', () => {
    test('renders feedback UI elements', () => {
        render(<ConversionReport conversionResult={minimalMockReport} />);

        expect(screen.getByText('Rate this Conversion')).toBeInTheDocument();
        expect(screen.getByTitle('Thumbs Up')).toBeInTheDocument(); // Using title for emoji buttons
        expect(screen.getByTitle('Thumbs Down')).toBeInTheDocument();
        expect(screen.getByPlaceholderText('Optional: Add any comments here...')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: 'Submit Feedback' })).toBeInTheDocument();
    });

    test('feedback type selection works correctly', () => {
        render(<ConversionReport conversionResult={minimalMockReport} />);

        const thumbsUpButton = screen.getByTitle('Thumbs Up');
        const thumbsDownButton = screen.getByTitle('Thumbs Down');

        // Initially, neither should be "pressed" (or have specific styling indicating selection)
        // This test relies on the styling added in the component:
        // border: feedbackType === 'thumbs_up' ? '2px solid #2563eb' : '1px solid #ccc'
        expect(thumbsUpButton).toHaveStyle('border: 1px solid #ccc');
        expect(thumbsDownButton).toHaveStyle('border: 1px solid #ccc');

        fireEvent.click(thumbsUpButton);
        expect(thumbsUpButton).toHaveStyle('border: 2px solid #2563eb');
        expect(thumbsDownButton).toHaveStyle('border: 1px solid #ccc');

        fireEvent.click(thumbsDownButton);
        expect(thumbsDownButton).toHaveStyle('border: 2px solid #ef4444');
        expect(thumbsUpButton).toHaveStyle('border: 1px solid #ccc');

        // Test deselecting
        fireEvent.click(thumbsDownButton);
        expect(thumbsDownButton).toHaveStyle('border: 1px solid #ccc');
    });

    test('submit feedback success flow', async () => {
        const mockSuccessResponse: FeedbackResponse = {
            id: 'fb-1', job_id: minimalMockReport.job_id, feedback_type: 'thumbs_up', comment: 'Great!', created_at: new Date().toISOString()
        };
        mockedSubmitFeedback.mockResolvedValueOnce(mockSuccessResponse);

        render(<ConversionReport conversionResult={minimalMockReport} />);

        fireEvent.click(screen.getByTitle('Thumbs Up'));
        fireEvent.change(screen.getByPlaceholderText('Optional: Add any comments here...'), {
            target: { value: 'Great!' },
        });
        fireEvent.click(screen.getByRole('button', { name: 'Submit Feedback' }));

        expect(mockedSubmitFeedback).toHaveBeenCalledWith({
            job_id: minimalMockReport.job_id,
            feedback_type: 'thumbs_up',
            comment: 'Great!',
            user_id: undefined, // Assuming user_id is not implemented/passed yet
        });

        await waitFor(() => {
            expect(screen.getByText('Thank you for your feedback!')).toBeInTheDocument();
        });
        // Check if form is hidden or submit button is gone
        expect(screen.queryByRole('button', { name: 'Submit Feedback' })).not.toBeInTheDocument();
        expect(screen.queryByTitle('Thumbs Up')).not.toBeInTheDocument();
    });

    test('submit feedback API error flow', async () => {
        const errorMessage = 'Failed to submit feedback due to server issue';
        mockedSubmitFeedback.mockRejectedValueOnce(new Error(errorMessage));

        render(<ConversionReport conversionResult={minimalMockReport} />);

        fireEvent.click(screen.getByTitle('Thumbs Down'));
        fireEvent.click(screen.getByRole('button', { name: 'Submit Feedback' }));

        expect(mockedSubmitFeedback).toHaveBeenCalledTimes(1);

        await waitFor(() => {
            expect(screen.getByText(`Error: ${errorMessage}`)).toBeInTheDocument();
        });
        // Form should still be visible for retry
        expect(screen.getByRole('button', { name: 'Submit Feedback' })).toBeInTheDocument();
    });

    test('submit button is disabled until a feedback type is selected', () => {
        render(<ConversionReport conversionResult={minimalMockReport} />);

        const submitButton = screen.getByRole('button', { name: 'Submit Feedback' });
        expect(submitButton).toBeDisabled();

        fireEvent.click(screen.getByTitle('Thumbs Up'));
        expect(submitButton).not.toBeDisabled();

        fireEvent.click(screen.getByTitle('Thumbs Up')); // Deselect
        expect(submitButton).toBeDisabled();

        fireEvent.click(screen.getByTitle('Thumbs Down'));
        expect(submitButton).not.toBeDisabled();
    });

    test('submit feedback fails if no feedback type is selected (client-side check)', () => {
        render(<ConversionReport conversionResult={minimalMockReport} />);

        const submitButton = screen.getByRole('button', { name: 'Submit Feedback' });
        fireEvent.click(submitButton); // Try to submit without selection

        // Check for client-side message if implemented, or just that API wasn't called
        expect(mockedSubmitFeedback).not.toHaveBeenCalled();
        // The component's internal handler should set a message
        expect(screen.getByText('Please select thumbs up or thumbs down.')).toBeInTheDocument();
    });
});
