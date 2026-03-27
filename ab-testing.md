# A/B Testing Infrastructure Documentation

## Overview

The A/B testing infrastructure allows ModPorter AI to compare different AI agent strategies and measure their performance. This system enables data-driven decisions about which agent configurations produce the best results for mod conversion.

## Architecture

The A/B testing system consists of three main components:

1. **Database Schema** - Tables for storing experiments, variants, and results
2. **Backend API** - Endpoints for managing experiments and recording results
3. **AI Engine Integration** - Support for loading different agent configurations based on experiment variants
4. **Frontend UI** - Interfaces for creating experiments and viewing results

## Database Schema

### experiments
Stores information about each A/B test.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Unique identifier |
| name | VARCHAR(255) | Experiment name |
| description | TEXT | Description of the experiment |
| start_date | TIMESTAMP | When the experiment starts |
| end_date | TIMESTAMP | When the experiment ends |
| status | VARCHAR(20) | Draft, active, paused, or completed |
| traffic_allocation | INTEGER | Percentage of traffic (0-100) |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

### experiment_variants
Stores different strategies/variants within an experiment.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Unique identifier |
| experiment_id | UUID | Foreign key to experiments |
| name | VARCHAR(255) | Variant name |
| description | TEXT | Description of the variant |
| is_control | BOOLEAN | Whether this is the control group |
| strategy_config | JSONB | Configuration for agent strategies |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

### experiment_results
Records the outcomes of conversion runs for analysis.

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Unique identifier |
| variant_id | UUID | Foreign key to experiment_variants |
| session_id | UUID | Link to conversion session |
| kpi_quality | DECIMAL(5,2) | Quality score (0-100) |
| kpi_speed | INTEGER | Execution time in milliseconds |
| kpi_cost | DECIMAL(10,2) | Computational cost |
| user_feedback_score | DECIMAL(3,2) | User feedback (1-5) |
| user_feedback_text | TEXT | Optional text feedback |
| metadata | JSONB | Additional metadata |
| created_at | TIMESTAMP | Creation timestamp |

## Backend API

### Experiment Management
- `POST /api/v1/experiments/experiments` - Create a new experiment
- `GET /api/v1/experiments/experiments` - List experiments
- `GET /api/v1/experiments/experiments/{id}` - Get experiment details
- `PUT /api/v1/experiments/experiments/{id}` - Update an experiment
- `DELETE /api/v1/experiments/experiments/{id}` - Delete an experiment

### Variant Management
- `POST /api/v1/experiments/experiments/{experiment_id}/variants` - Create a variant
- `GET /api/v1/experiments/experiments/{experiment_id}/variants` - List variants
- `GET /api/v1/experiments/experiments/{experiment_id}/variants/{id}` - Get variant details
- `PUT /api/v1/experiments/experiments/{experiment_id}/variants/{id}` - Update a variant
- `DELETE /api/v1/experiments/experiments/{experiment_id}/variants/{id}` - Delete a variant

### Result Recording
- `POST /api/v1/experiments/experiment_results` - Record experiment results
- `GET /api/v1/experiments/experiment_results` - List experiment results

## AI Engine Integration

The AI engine supports different agent configurations based on experiment variants:

1. When a conversion request includes an `experiment_variant` parameter, the engine initializes the conversion crew with that variant
2. The `VariantLoader` class loads configuration files based on the variant ID
3. Agent configurations can specify different models, temperatures, and other parameters
4. The system automatically falls back to default configurations if a variant config is not found

## Frontend UI

### Experiments Page
Located at `/experiments`, this page allows users to:
- Create and manage experiments
- Define experiment variants
- Control experiment status (draft, active, paused, completed)
- Set traffic allocation percentages

### Results Page
Located at `/experiment-results`, this page displays:
- Summary statistics for experiments
- Detailed results tables
- Performance comparisons between variants

## Key Performance Indicators (KPIs)

The system tracks several KPIs to measure variant performance:

1. **Quality** - How accurate or effective is the conversion (0-100 score)
2. **Speed** - How long does the agent take to complete the conversion (milliseconds)
3. **Cost** - Computational cost (e.g., token usage)
4. **User Feedback** - User rating of the output (1-5 scale)

## Implementation Example

To create and run an A/B test:

1. Create an experiment through the frontend or API
2. Define variants with different agent configurations
3. Set the experiment to "active" status
4. The backend will automatically route a percentage of conversion requests to each variant
5. Results are automatically recorded after each conversion
6. View results in the dashboard to determine the best-performing variant

## Best Practices

1. Always have a control variant for comparison
2. Run experiments long enough to gather statistically significant data
3. Monitor results regularly to detect issues early
4. Document the purpose and expected outcomes of each experiment
5. Clean up completed experiments to maintain database performance