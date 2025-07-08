import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import DiffViewer from './DiffViewer';
import FeatureMapper from './FeatureMapper';
import AssumptionTracker from './AssumptionTracker';

// Interface matching the backend response structure for a single comparison result
interface FeatureMappingData {
  id: string;
  java_feature: string;
  bedrock_equivalent: string;
  mapping_type: string;
  confidence_score: number | null;
}

interface ComparisonData {
  id: string; // Changed from comparison_id to id to match backend response
  conversion_id: string;
  structural_diff: { files_added: string[]; files_removed: string[]; files_modified: string[] } | null;
  code_diff: any; // Define more specifically later
  asset_diff: any; // Define more specifically later
  assumptions_applied: any[] | null; // Define more specifically later
  confidence_scores: any | null; // Define more specifically later
  created_at: string | null;
  feature_mappings: FeatureMappingData[] | null;
}

const ComparisonView: React.FC = () => {
  const { comparisonId } = useParams<{ comparisonId: string }>();
  const [data, setData] = useState<ComparisonData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (comparisonId) {
      setLoading(true);
      fetch(`/api/v1/comparisons/${comparisonId}`) // Use the actual API endpoint
        .then(res => {
          if (!res.ok) {
            return res.text().then(text => {
              let detail = text;
              try {
                const errJson = JSON.parse(text);
                detail = errJson.detail || text;
              } catch {
                /* ignore parsing error, use text */
              }
              throw new Error(`Failed to fetch comparison data: ${res.status} ${res.statusText} - ${detail}`);
            });
          }
          return res.json();
        })
        .then((fetchedData: ComparisonData) => { // Type the fetched data
          setData(fetchedData);
          setError(null);
        })
        .catch(err => {
          console.error("Error fetching comparison data:", err);
          setError(err.message);
          setData(null);
        })
        .finally(() => {
          setLoading(false);
        });
    } else {
      setError("No comparison ID provided in the URL.");
      setLoading(false);
    }
  }, [comparisonId]);

  if (loading) return <div>Loading comparison data for ID: {comparisonId}...</div>;
  if (error) return <div>Error: {error}</div>;
  if (!data) return <div>No comparison data found for ID: {comparisonId}.</div>;

  return (
    <div>
      <h1>Comparison Report for ID: {data.id}</h1>
      <p>Conversion ID: {data.conversion_id}</p>
      <p>Report Generated At: {data.created_at ? new Date(data.created_at).toLocaleString() : 'N/A'}</p>

      <section>
        <h2>Structural Changes</h2>
        {data.structural_diff ? (
          <pre>{JSON.stringify(data.structural_diff, null, 2)}</pre>
        ) : <p>No structural diff data.</p>}
      </section>

      {/* Pass data to FeatureMapper; it expects an array. */}
      <FeatureMapper features={data.feature_mappings || []} />

      {/* Pass data to DiffViewer */}
      <DiffViewer codeDiff={data.code_diff || { summary: "No code diff data available." }} />

      {/* Pass data to AssumptionTracker; it expects an array. */}
      <AssumptionTracker assumptions={data.assumptions_applied || []} />

      {/* Pass full data to ComparisonReportPage */}
      {/* <ComparisonReportPage fullReport={data} /> */} {/* This might be too much for one page, or could be a separate view */}

      {/* Example of displaying other top-level fields */}
      <section>
        <h2>Confidence Scores</h2>
        {data.confidence_scores ? (
          <pre>{JSON.stringify(data.confidence_scores, null, 2)}</pre>
        ) : <p>No confidence scores.</p>}
      </section>

    </div>
  );
};

export default ComparisonView;
