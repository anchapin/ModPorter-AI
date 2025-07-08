import React from 'react';

interface DiffViewerProps {
  codeDiff: any; // Replace 'any' with a more specific type for code differences
}

const DiffViewer: React.FC<DiffViewerProps> = ({ codeDiff }) => {
  return (
    <div>
      <h2>Code Differences (DiffViewer)</h2>
      <p>Interactive diff view will be implemented here.</p>
      <pre>{JSON.stringify(codeDiff, null, 2)}</pre>
    </div>
  );
};

export default DiffViewer;
