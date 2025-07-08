import React from 'react';

interface ComparisonReportPageProps {
  fullReport: any; // Replace 'any' with the main ComparisonResult type
}

const ComparisonReportPage: React.FC<ComparisonReportPageProps> = ({ fullReport }) => {
  return (
    <div>
      <h2>Full Comparison Report (ComparisonReportPage)</h2>
      <p>A comprehensive summary of the entire comparison.</p>
      <pre>{JSON.stringify(fullReport, null, 2)}</pre>
    </div>
  );
};

export default ComparisonReportPage;
