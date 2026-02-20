import * as monaco from 'monaco-editor';
import bedrockBlockSchema from '../schemas/bedrock_block_schema.json';

export interface SchemaDefinition {
  uri: string;
  schema: any;
  fileMatch?: string[];
}

export class BedrockSchemaLoader {
  private schemas: Map<string, SchemaDefinition> = new Map();

  constructor() {
    this.registerDefaultSchemas();
  }

  private registerDefaultSchemas() {
    // Bedrock Block Schema
    this.registerSchema({
      uri: 'schemas/bedrock_block_schema.json',
      schema: bedrockBlockSchema,
      fileMatch: ['blocks/*.json', '*/blocks/*.json']
    });

    // Additional schemas can be loaded from AI engine or external sources
    this.registerRemoteSchema('schemas/bedrock_item_schema.json', '/api/v1/schemas/bedrock_item_schema.json', [
      'items/*.json',
      '*/items/*.json'
    ]);

    this.registerRemoteSchema('schemas/bedrock_recipe_schema.json', '/api/v1/schemas/bedrock_recipe_schema.json', [
      'recipes/*.json',
      '*/recipes/*.json'
    ]);

    this.registerRemoteSchema('schemas/bedrock_loot_table_schema.json', '/api/v1/schemas/bedrock_loot_table_schema.json', [
      'loot_tables/*.json',
      '*/loot_tables/*.json'
    ]);

    this.registerRemoteSchema('schemas/bedrock_entity_schema.json', '/api/v1/schemas/bedrock_entity_schema.json', [
      'entities/*.json',
      '*/entities/*.json'
    ]);
  }

  registerSchema(definition: SchemaDefinition) {
    this.schemas.set(definition.uri, definition);
    monaco.languages.json.jsonDefaults.setDiagnosticsOptions({
      validate: true,
      schemas: this.getSchemaDefinitions()
    });
  }

  private async registerRemoteSchema(
    uri: string,
    url: string,
    fileMatch: string[]
  ): Promise<void> {
    try {
      const response = await fetch(url);
      if (response.ok) {
        const schema = await response.json();
        this.registerSchema({ uri, schema, fileMatch });
      }
    } catch (error) {
      console.warn(`Failed to load schema from ${url}:`, error);
      // Register a basic placeholder schema
      this.registerSchema({
        uri,
        schema: this.createPlaceholderSchema(),
        fileMatch
      });
    }
  }

  private createPlaceholderSchema() {
    return {
      $schema: 'http://json-schema.org/draft-07/schema#',
      title: 'Bedrock JSON File',
      description: 'A Bedrock Edition behavior file',
      type: 'object',
      properties: {
        format_version: {
          type: 'string',
          description: 'Format version'
        }
      }
    };
  }

  getSchemaDefinitions(): monaco.languages.json.SchemaAdditions {
    const additions: monaco.languages.json.SchemaAdditions = [];
    this.schemas.forEach(definition => {
      additions.push({
        uri: definition.uri,
        fileMatch: definition.fileMatch || [],
        schema: definition.schema
      });
    });
    return additions;
  }

  getSchemaForFile(filePath: string): any | null {
    for (const [uri, definition] of this.schemas.entries()) {
      if (definition.fileMatch) {
        for (const pattern of definition.fileMatch) {
          if (this.matchPattern(filePath, pattern)) {
            return definition.schema;
          }
        }
      }
    }
    return null;
  }

  private matchPattern(filePath: string, pattern: string): boolean {
    // Convert glob pattern to regex
    const regexPattern = pattern
      .replace(/\*/g, '.*')
      .replace(/\?/g, '.');
    const regex = new RegExp(regexPattern, 'i');
    return regex.test(filePath);
  }

  setupAutoCompletion(monacoInstance: typeof monaco) {
    // Bedrock block property completions
    monacoInstance.languages.registerCompletionItemProvider('json', {
      provideCompletionItems: (model, position) => {
        const textUntilPosition = model.getValueInRange({
          startLineNumber: 1,
          startColumn: 1,
          endLineNumber: position.lineNumber,
          endColumn: position.column
        });

        // Block component completions
        if (textUntilPosition.includes('"components"')) {
          return {
            suggestions: this.getBlockComponentSuggestions()
          };
        }

        return { suggestions: [] };
      }
    });
  }

  private getBlockComponentSuggestions(): monaco.languages.CompletionItem[] {
    return [
      {
        label: 'minecraft:display_name',
        kind: monaco.languages.CompletionItemKind.Property,
        insertText: '"minecraft:display_name": {\n  "value": ""\n}',
        documentation: 'Display name for the block'
      },
      {
        label: 'minecraft:destroy_time',
        kind: monaco.languages.CompletionItemKind.Property,
        insertText: '"minecraft:destroy_time": 0',
        documentation: 'Block hardness in seconds'
      },
      {
        label: 'minecraft:explosion_resistance',
        kind: monaco.languages.CompletionItemKind.Property,
        insertText: '"minecraft:explosion_resistance": 0',
        documentation: 'Explosion resistance'
      },
      {
        label: 'minecraft:friction',
        kind: monaco.languages.CompletionItemKind.Property,
        insertText: '"minecraft:friction": 0.6',
        documentation: 'Slipperiness (0-1)'
      },
      {
        label: 'minecraft:light_emission',
        kind: monaco.languages.CompletionItemKind.Property,
        insertText: '"minecraft:light_emission": 0',
        documentation: 'Light level emitted (0-15)'
      },
      {
        label: 'minecraft:material',
        kind: monaco.languages.CompletionItemKind.Property,
        insertText: '"minecraft:material": "stone"',
        documentation: 'Material type'
      },
      {
        label: 'minecraft:geometry',
        kind: monaco.languages.CompletionItemKind.Property,
        insertText: '"minecraft:geometry": ""',
        documentation: 'Geometry identifier'
      }
    ];
  }

  // Static instance for singleton access
  private static instance: BedrockSchemaLoader;

  static getInstance(): BedrockSchemaLoader {
    if (!BedrockSchemaLoader.instance) {
      BedrockSchemaLoader.instance = new BedrockSchemaLoader();
    }
    return BedrockSchemaLoader.instance;
  }
}

// Initialize schema loader when module is imported
export const bedrockSchemaLoader = BedrockSchemaLoader.getInstance();
