import React from 'react';

interface AssumptionTrackerProps {
  assumptions: any[]; // Replace 'any' with a specific type for assumptions
}

const AssumptionTracker: React.FC<AssumptionTrackerProps> = ({ assumptions }) => {
  return (
    <div>
      <h2>Smart Assumptions Applied (AssumptionTracker)</h2>
      <p>Details about applied smart assumptions will be shown here.</p>
      <ul>
        {assumptions.map((assumption, index) => (
          <li key={index}>{JSON.stringify(assumption)}</li>
        ))}
      </ul>
    </div>
  );
};

export default AssumptionTracker;
