import React, { useState, useEffect } from 'react';
import { useEditorContext } from '../../../context/EditorContext';
import { getPropertyByPath } from '../../../utils/objectUtils'; // Import the utility
// AddonBlock type is implicitly available via selectedBlock from addonData.blocks
import './PropertiesPanel.css';

export const PropertiesPanel: React.FC = () => {
  const { addonData, selectedBlockId, updateBlockProperty } = useEditorContext();

  // Local state for textareas to allow typing before JSON parsing
  const [propertiesJsonString, setPropertiesJsonString] = useState<string>('');
  const [behaviorDataJsonString, setBehaviorDataJsonString] = useState<string>('');
  const [propertiesError, setPropertiesError] = useState<string | null>(null);
  const [behaviorError, setBehaviorError] = useState<string | null>(null);

  const selectedBlock = React.useMemo(() => {
    return addonData?.blocks.find(block => block.id === selectedBlockId);
  }, [addonData, selectedBlockId]);

  useEffect(() => {
    // Defer state updates to avoid setting state directly in effect
    setTimeout(() => {
      if (selectedBlock?.properties) {
        setPropertiesJsonString(JSON.stringify(selectedBlock.properties, null, 2));
        setPropertiesError(null);
      } else {
        setPropertiesJsonString('{}'); // Default to empty JSON object
      }
      if (selectedBlock?.behavior?.data) {
        setBehaviorDataJsonString(JSON.stringify(selectedBlock.behavior.data, null, 2));
        setBehaviorError(null);
      } else {
        setBehaviorDataJsonString('{}'); // Default for new/empty behavior data
      }
    }, 0);
  }, [selectedBlock]);


  const handleInputChange = (propertyPath: string, value: any) => {
    if (selectedBlockId) {
      updateBlockProperty(selectedBlockId, propertyPath, value);
    }
  };

  const handleJsonChange = (
    e: React.ChangeEvent<HTMLTextAreaElement>,
    setter: React.Dispatch<React.SetStateAction<string>>
  ) => {
    setter(e.target.value);
  };

  const handleJsonBlur = (
    propertyPath: string,
    jsonString: string,
    errorSetter: React.Dispatch<React.SetStateAction<string | null>>
  ) => {
    if (selectedBlockId) {
      try {
        const parsedValue = JSON.parse(jsonString);
        updateBlockProperty(selectedBlockId, propertyPath, parsedValue);
        errorSetter(null); // Clear error on successful parse
      } catch (err) {
        console.error(`Error parsing JSON for ${propertyPath}:`, err);
        errorSetter("Invalid JSON format.");
      }
    }
  };

  if (!selectedBlockId) {
    return <div className="properties-panel-empty">Select a block to see its properties.</div>;
  }
  if (!selectedBlock) {
    return <div className="properties-panel-empty">Selected block not found (this may be a brief state during updates).</div>;
  }

  return (
    <div className="properties-panel-container">
      <h3>Block: {selectedBlock.identifier}</h3>
      <div className="properties-grid">
        <div className="property-item">
          <label htmlFor="blockId" className="property-label">ID:</label>
          <input
            id="blockId"
            type="text"
            className="property-value"
            value={selectedBlock.id}
            readOnly // ID is not editable
          />
        </div>
        <div className="property-item">
          <label htmlFor="blockIdentifier" className="property-label">Identifier:</label>
          <input
            id="blockIdentifier"
            type="text"
            className="property-value"
            value={selectedBlock.identifier}
            onChange={(e) => handleInputChange("identifier", e.target.value)}
          />
        </div>

        <div className="property-section">
          <h4>Custom Properties (JSON):</h4>
          <textarea
            className={`property-value json-textarea ${propertiesError ? 'json-error' : ''}`}
            value={propertiesJsonString}
            onChange={(e) => handleJsonChange(e, setPropertiesJsonString)}
            onBlur={() => handleJsonBlur("properties", propertiesJsonString, setPropertiesError)}
            rows={8}
          />
          {propertiesError && <small className="json-error-message">{propertiesError}</small>}
        </div>

        <div className="property-section">
          <h4>Behavior Data (JSON):</h4>
          {selectedBlock.behavior ? (
            <>
              <div className="property-item">
                <label htmlFor="behaviorId" className="property-label">Behavior ID:</label>
                <input id="behaviorId" type="text" className="property-value" value={selectedBlock.behavior.id} readOnly />
              </div>

              {/* Dedicated input for custom:is_explosive */}
              <div className="property-item">
                <label htmlFor="isExplosive" className="property-label">Is Explosive (custom):</label>
                <input
                  id="isExplosive"
                  type="checkbox"
                  className="property-value-checkbox"
                  checked={getPropertyByPath(selectedBlock, "behavior.data.custom:is_explosive") === true}
                  onChange={(e) => handleInputChange("behavior.data.custom:is_explosive", e.target.checked)}
                />
              </div>

              {/* Dedicated input for custom:destroy_on_use */}
              <div className="property-item">
                <label htmlFor="destroyOnUse" className="property-label">Destroy on Use (custom):</label>
                <input
                  id="destroyOnUse"
                  type="checkbox"
                  className="property-value-checkbox"
                  checked={getPropertyByPath(selectedBlock, "behavior.data.custom:destroy_on_use") === true}
                  onChange={(e) => handleInputChange("behavior.data.custom:destroy_on_use", e.target.checked)}
                />
              </div>

              <label htmlFor="behaviorDataJson" className="property-label-fullwidth">Raw Behavior Data (JSON):</label>
              <textarea
                id="behaviorDataJson"
                className={`property-value json-textarea ${behaviorError ? 'json-error' : ''}`}
                value={behaviorDataJsonString}
                onChange={(e) => handleJsonChange(e, setBehaviorDataJsonString)}
                onBlur={() => handleJsonBlur("behavior.data", behaviorDataJsonString, setBehaviorError)}
                rows={10}
              />
              {behaviorError && <small className="json-error-message">{behaviorError}</small>}
            </>
          ) : (
             <div className="property-item">
                <span className="property-label">Behavior:</span>
                <span className="property-value">
                  No behavior defined.
                  {/* TODO: Add button to create behavior object */}
                </span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
