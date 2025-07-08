import React from 'react';
import { useEditorContext } from '../../../context/EditorContext';
import './BlockList.css';

export const BlockList: React.FC = () => {
  const { addonData, selectedBlockId, setSelectedBlockId, isLoading } = useEditorContext();

  if (isLoading && !addonData) { // Show loading only if addonData is not yet available
    return <div className="block-list-loading">Loading blocks...</div>;
  }

  if (!addonData || !addonData.blocks || addonData.blocks.length === 0) {
    return <div className="block-list-empty">No blocks found in this addon.</div>;
  }

  return (
    <div className="block-list-container">
      <h3>Blocks</h3>
      <ul className="block-list">
        {addonData.blocks.map((block) => (
          <li
            key={block.id}
            className={`block-list-item ${selectedBlockId === block.id ? 'selected' : ''}`}
            onClick={() => setSelectedBlockId(block.id)}
            role="button" // Make it accessible
            tabIndex={0} // Make it focusable
            onKeyPress={(e) => { if (e.key === 'Enter' || e.key === ' ') setSelectedBlockId(block.id);}} // Keyboard accessible
          >
            {block.identifier || `Block ID: ${block.id.substring(0,8)}...`}
          </li>
        ))}
      </ul>
    </div>
  );
};
