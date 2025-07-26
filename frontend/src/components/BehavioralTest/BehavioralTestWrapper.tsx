import React from 'react';
import { useParams } from 'react-router-dom';
import { BehavioralTest } from './BehavioralTest';

export const BehavioralTestWrapper: React.FC = () => {
  const { conversionId } = useParams<{ conversionId: string }>();
  
  if (!conversionId) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-md">
        <p className="text-red-700">Error: No conversion ID provided</p>
      </div>
    );
  }

  return <BehavioralTest conversionId={conversionId} />;
};