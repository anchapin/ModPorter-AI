import React, { useState, useMemo } from 'react';
import {
  Typography,
  TextField,
  InputAdornment,
  Tabs,
  Tab,
  List,
  ListItemButton,
  ListItemText,
  Collapse,
  Chip,
  IconButton,
  Tooltip,
  Divider,
} from '@mui/material';
import {
  Search,
  ExpandMore,
  ExpandLess,
  ContentCopy,
  Book,
  Code,
  Extension,
  Inventory,
} from '@mui/icons-material';
import './BedrockDocsPanel.css';

// Types for Bedrock API documentation
interface BedrockDocItem {
  id: string;
  title: string;
  description: string;
  category: 'entity' | 'block' | 'item' | 'recipe' | 'loot_table' | 'component' | 'event';
  syntax?: string;
  example?: string;
  properties?: Record<string, string>;
  related?: string[];
}

interface BedrockDocsPanelProps {
  className?: string;
  onInsertSnippet?: (snippet: string) => void;
}

// Comprehensive Bedrock API documentation data
const bedrockDocs: BedrockDocItem[] = [
  // Entity Components
  {
    id: 'entity-identifier',
    title: 'minecraft:identifier',
    description: 'Defines the entity\'s unique identifier used to spawn it in-game.',
    category: 'entity',
    syntax: '"minecraft:identifier": { "id": "<namespace>:<name>" }',
    example: '"minecraft:identifier": { "id": "minecraft:creeper" }',
    properties: {
      'id': 'The unique identifier (e.g., "minecraft:zombie")',
    },
    related: ['minecraft:spawn_entity', 'minecraft:entity'],
  },
  {
    id: 'entity-health',
    title: 'minecraft:health',
    description: 'Sets the entity\'s health value and maximum health.',
    category: 'entity',
    syntax: '"minecraft:health": { "value": <number>, "max": <number> }',
    example: '"minecraft:health": { "value": 20, "max": 20 }',
    properties: {
      'value': 'Current health value',
      'max': 'Maximum health value',
    },
    related: ['minecraft:damage', 'minecraft:heal'],
  },
  {
    id: 'entity-movement',
    title: 'minecraft:movement',
    description: 'Defines the entity\'s movement speed.',
    category: 'entity',
    syntax: '"minecraft:movement": { "value": <number> }',
    example: '"minecraft:movement": { "value": 0.25 }',
    properties: {
      'value': 'Movement speed (0.0-1.0)',
    },
    related: ['minecraft:movement.basic', 'minecraft:movement.jump'],
  },
  {
    id: 'entity-collision',
    title: 'minecraft:collision_box',
    description: 'Defines the entity\'s collision box size.',
    category: 'entity',
    syntax: '"minecraft:collision_box": { "width": <number>, "height": <number> }',
    example: '"minecraft:collision_box": { "width": 0.6, "height": 1.8 }',
    properties: {
      'width': 'Width of collision box',
      'height': 'Height of collision box',
    },
    related: ['minecraft:physics'],
  },
  // Block Components
  {
    id: 'block-identifier',
    title: 'minecraft:identifier',
    description: 'Defines the block\'s unique identifier.',
    category: 'block',
    syntax: '"minecraft:identifier": "<namespace>:<name>"',
    example: '"minecraft:identifier": "minecraft:diamond_block"',
    properties: {
      'id': 'The unique identifier (e.g., "minecraft:stone")',
    },
    related: ['minecraft:block', 'minecraft:block_light_absorption'],
  },
  {
    id: 'block-hardness',
    title: 'minecraft:blast_resistance',
    description: 'Defines the block\'s blast resistance value.',
    category: 'block',
    syntax: '"minecraft:blast_resistance": <number>',
    example: '"minecraft:blast_resistance": 30',
    properties: {
      'value': 'Blast resistance (higher = more resistant)',
    },
    related: ['minecraft:hardness'],
  },
  {
    id: 'block-loot',
    title: 'minecraft:loot',
    description: 'Defines the loot table used when the block is broken.',
    category: 'block',
    syntax: '"minecraft:loot": "loot_tables/<path>.json"',
    example: '"minecraft:loot": "loot_tables/blocks/diamond_ore.json"',
    properties: {
      'table': 'Path to loot table file',
    },
    related: ['minecraft:pick_loot'],
  },
  {
    id: 'block-crafting',
    title: 'minecraft:crafting_table',
    description: 'Defines crafting recipes for the block.',
    category: 'block',
    syntax: '"minecraft:crafting_table": { "recipes": [...] }',
    example: '"minecraft:crafting_table": { "recipes": [{ "result": "minecraft:diamond_sword", "count": 1 }] }',
    properties: {
      'recipes': 'Array of recipe definitions',
    },
    related: ['minecraft:recipe'],
  },
  // Item Components
  {
    id: 'item-identifier',
    title: 'minecraft:icon',
    description: 'Defines the item\'s icon texture.',
    category: 'item',
    syntax: '"minecraft:icon": "<texture_name>"',
    example: '"minecraft:icon": "diamond_sword"',
    properties: {
      'texture': 'Name of the texture without extension',
    },
    related: ['minecraft:display_name', 'minecraft:stack_size'],
  },
  {
    id: 'item-stack',
    title: 'minecraft:stack_size',
    description: 'Defines the maximum stack size for the item.',
    category: 'item',
    syntax: '"minecraft:stack_size": <number>',
    example: '"minecraft:stack_size": 64',
    properties: {
      'size': 'Maximum stack size (1-64)',
    },
    related: ['minecraft:max_damage', 'minecraft:durability'],
  },
  // Component References
  {
    id: 'component-annotation',
    title: 'minecraft:annotation',
    description: 'Attaches text annotations to entities for AI sensing.',
    category: 'component',
    syntax: '"minecraft:annotation": { "value": "<text>" }',
    example: '"minecraft:annotation": { "value": "A friendly creeper" }',
    properties: {
      'value': 'The annotation text',
    },
    related: ['minecraft:sensor', 'minecraft:behavior'],
  },
  // Events
  {
    id: 'event-entity',
    title: 'minecraft:entity',
    description: 'Base event namespace for entity events.',
    category: 'event',
    syntax: 'minecraft:entity.<event_name>',
    example: 'minecraft:entity.spawned',
    properties: {
      'spawned': 'Triggered when entity spawns',
      'died': 'Triggered when entity dies',
      'hurt': 'Triggered when entity takes damage',
    },
    related: ['minecraft:player', 'minecraft:ageable'],
  },
  {
    id: 'event-component',
    title: 'minecraft:component',
    description: 'Event to add or remove components dynamically.',
    category: 'event',
    syntax: 'minecraft:component.<action>_<component_name>',
    example: 'minecraft:component.health.set_value',
    properties: {
      'add': 'Add a component',
      'remove': 'Remove a component',
      'set': 'Set component value',
    },
    related: ['minecraft:entity'],
  },
];

// Group docs by category
const categorizeDocs = (docs: BedrockDocItem[]) => {
  const categories: Record<string, BedrockDocItem[]> = {};
  docs.forEach((doc) => {
    if (!categories[doc.category]) {
      categories[doc.category] = [];
    }
    categories[doc.category].push(doc);
  });
  return categories;
};

// Category display info
const categoryInfo: Record<string, { label: string; icon: React.ReactNode }> = {
  entity: { label: 'Entities', icon: <Extension /> },
  block: { label: 'Blocks', icon: <Inventory /> },
  item: { label: 'Items', icon: <Inventory /> },
  recipe: { label: 'Recipes', icon: <Book /> },
  loot_table: { label: 'Loot Tables', icon: <Book /> },
  component: { label: 'Components', icon: <Code /> },
  event: { label: 'Events', icon: <Extension /> },
};

export const BedrockDocsPanel: React.FC<BedrockDocsPanelProps> = ({
  className = '',
  onInsertSnippet,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [activeTab, setActiveTab] = useState(0);
  const [expandedCategory, setExpandedCategory] = useState<string | null>('entity');
  const [expandedDoc, setExpandedDoc] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);

  // Filter docs based on search query
  const filteredDocs = useMemo(() => {
    if (!searchQuery) return bedrockDocs;
    const query = searchQuery.toLowerCase();
    return bedrockDocs.filter(
      (doc) =>
        doc.title.toLowerCase().includes(query) ||
        doc.description.toLowerCase().includes(query) ||
        doc.syntax?.toLowerCase().includes(query) ||
        doc.category.toLowerCase().includes(query)
    );
  }, [searchQuery]);

  // Group filtered docs by category
  const groupedDocs = useMemo(() => categorizeDocs(filteredDocs), [filteredDocs]);

  // Handle copy to clipboard
  const handleCopy = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // Handle insert snippet
  const handleInsert = (snippet: string) => {
    if (onInsertSnippet) {
      onInsertSnippet(snippet);
    }
  };

  // Toggle category expansion
  const toggleCategory = (category: string) => {
    setExpandedCategory(expandedCategory === category ? null : category);
  };

  // Toggle doc expansion
  const toggleDoc = (docId: string) => {
    setExpandedDoc(expandedDoc === docId ? null : docId);
  };

  return (
    <div className={`bedrock-docs-panel ${className}`}>
      {/* Header */}
      <div className="docs-panel-header">
        <Typography variant="h6" className="docs-title">
          <Book className="docs-icon" />
          Bedrock API Docs
        </Typography>
      </div>

      {/* Search */}
      <div className="docs-search">
        <TextField
          fullWidth
          size="small"
          placeholder="Search documentation..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <Search />
              </InputAdornment>
            ),
          }}
        />
      </div>

      {/* Category Tabs */}
      <Tabs
        value={activeTab}
        onChange={(_, newValue) => setActiveTab(newValue)}
        variant="scrollable"
        scrollButtons="auto"
        className="docs-tabs"
      >
        <Tab label="All" />
        <Tab label="Entities" />
        <Tab label="Blocks" />
        <Tab label="Items" />
        <Tab label="Components" />
        <Tab label="Events" />
      </Tabs>

      {/* Documentation List */}
      <div className="docs-content">
        {Object.entries(groupedDocs).map(([category, docs]) => {
          const tabCategories: Record<number, string[]> = {
            0: ['entity', 'block', 'item', 'recipe', 'loot_table', 'component', 'event'],
            1: ['entity'],
            2: ['block'],
            3: ['item'],
            4: ['component'],
            5: ['event'],
          };

          if (!tabCategories[activeTab]?.includes(category)) {
            return null;
          }

          return (
            <div key={category} className="docs-category">
              <ListItemButton
                className="category-header"
                onClick={() => toggleCategory(category)}
              >
                {categoryInfo[category]?.icon}
                <ListItemText
                  primary={categoryInfo[category]?.label || category}
                  secondary={`${docs.length} items`}
                />
                {expandedCategory === category ? <ExpandLess /> : <ExpandMore />}
              </ListItemButton>

              <Collapse in={expandedCategory === category}>
                <List dense className="docs-list">
                  {docs.map((doc) => (
                    <React.Fragment key={doc.id}>
                      <ListItemButton
                        className="doc-item"
                        onClick={() => toggleDoc(doc.id)}
                      >
                        <ListItemText
                          primary={doc.title}
                          secondary={
                            <Typography
                              variant="body2"
                              className="doc-description"
                              noWrap
                            >
                              {doc.description}
                            </Typography>
                          }
                        />
                        {expandedDoc === doc.id ? <ExpandLess /> : <ExpandMore />}
                      </ListItemButton>

                      <Collapse in={expandedDoc === doc.id}>
                        <div className="doc-details">
                          {/* Syntax */}
                          {doc.syntax && (
                            <div className="doc-section">
                              <Typography variant="subtitle2" className="section-label">
                                Syntax:
                              </Typography>
                              <div className="code-block">
                                <code>{doc.syntax}</code>
                                <Tooltip title="Copy syntax">
                                  <IconButton
                                    size="small"
                                    onClick={() => handleCopy(doc.syntax!, `${doc.id}-syntax`)}
                                  >
                                    {copiedId === `${doc.id}-syntax` ? (
                                      <ContentCopy fontSize="small" />
                                    ) : (
                                      <ContentCopy fontSize="small" />
                                    )}
                                  </IconButton>
                                </Tooltip>
                              </div>
                            </div>
                          )}

                          {/* Example */}
                          {doc.example && (
                            <div className="doc-section">
                              <Typography variant="subtitle2" className="section-label">
                                Example:
                              </Typography>
                              <div className="code-block">
                                <code>{doc.example}</code>
                                <Tooltip title="Copy example">
                                  <IconButton
                                    size="small"
                                    onClick={() => handleCopy(doc.example!, `${doc.id}-example`)}
                                  >
                                    {copiedId === `${doc.id}-example` ? (
                                      <ContentCopy fontSize="small" />
                                    ) : (
                                      <ContentCopy fontSize="small" />
                                    )}
                                  </IconButton>
                                </Tooltip>
                              </div>
                            </div>
                          )}

                          {/* Properties */}
                          {doc.properties && Object.keys(doc.properties).length > 0 && (
                            <div className="doc-section">
                              <Typography variant="subtitle2" className="section-label">
                                Properties:
                              </Typography>
                              <div className="properties-list">
                                {Object.entries(doc.properties).map(([key, value]) => (
                                  <Chip
                                    key={key}
                                    label={`${key}: ${value}`}
                                    size="small"
                                    className="property-chip"
                                  />
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Related */}
                          {doc.related && doc.related.length > 0 && (
                            <div className="doc-section">
                              <Typography variant="subtitle2" className="section-label">
                                Related:
                              </Typography>
                              <div className="related-list">
                                {doc.related.map((rel) => (
                                  <Chip
                                    key={rel}
                                    label={rel}
                                    size="small"
                                    variant="outlined"
                                    className="related-chip"
                                  />
                                ))}
                              </div>
                            </div>
                          )}

                          {/* Insert Button */}
                          {onInsertSnippet && (
                            <div className="doc-actions">
                              <Chip
                                label="Insert to Editor"
                                onClick={() => handleInsert(doc.example || doc.syntax || '')}
                                color="primary"
                                size="small"
                                className="insert-chip"
                              />
                            </div>
                          )}
                        </div>
                      </Collapse>
                    </React.Fragment>
                  ))}
                </List>
              </Collapse>

              <Divider />
            </div>
          );
        })}

        {filteredDocs.length === 0 && (
          <div className="docs-empty">
            <Typography variant="body2" color="text.secondary">
              No documentation found for "{searchQuery}"
            </Typography>
          </div>
        )}
      </div>
    </div>
  );
};

export default BedrockDocsPanel;
