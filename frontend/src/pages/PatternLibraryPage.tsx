import React from 'react';
import { PatternLibrary } from '../components/PatternLibrary';
import './PatternLibraryPage.css';

const PatternLibraryPage: React.FC = () => {
  const handlePatternSelect = (pattern: any) => {
    console.log('Pattern selected:', pattern);
  };

  const handlePatternUse = (pattern: any) => {
    console.log('Pattern used:', pattern);
    // Navigate to editor or apply pattern
  };

  return (
    <div className="pattern-library-page">
      <PatternLibrary
        onPatternSelect={handlePatternSelect}
        onPatternUse={handlePatternUse}
      />
    </div>
  );
};

export default PatternLibraryPage;
