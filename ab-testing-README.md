# A/B Testing Infrastructure

This directory contains the implementation of the A/B testing infrastructure for ModPorter AI agent strategy optimization.

## Components

1. **Database Schema** - Defined in `database/schema.sql` with tables for experiments, variants, and results
2. **Backend API** - Located in `backend/src/api/experiments.py` with endpoints for managing experiments
3. **Database Models** - Defined in `backend/src/db/models.py` with SQLAlchemy models for A/B testing
4. **CRUD Operations** - Implemented in `backend/src/db/crud.py` for database interactions
5. **AI Engine Integration** - Located in `ai-engine/agents/variant_loader.py` for loading variant configurations
6. **Frontend UI** - Implemented in `frontend/src/pages/ExperimentsPage.tsx` and `frontend/src/pages/ExperimentResultsPage.tsx`
7. **Tests** - Located in `tests/test_ab_testing.py` for verifying functionality
8. **Documentation** - Detailed documentation in `docs/ab-testing.md`

## Getting Started

1. Ensure the database schema is updated with the A/B testing tables
2. Start the backend service to access the experiment management API
3. Use the frontend UI to create experiments and variants
4. Configure agent strategies in the variant configuration files
5. Run experiments and monitor results through the dashboard

## Key Features

- Create and manage A/B testing experiments
- Define multiple variants with different agent configurations
- Automatically route conversion requests to experiment variants
- Record and analyze key performance indicators (KPIs)
- Compare variant performance with statistical analysis
- Visualize results through dashboards

## API Endpoints

- `/api/v1/experiments/experiments` - Experiment management
- `/api/v1/experiments/experiments/{id}/variants` - Variant management
- `/api/v1/experiments/experiment_results` - Result recording and retrieval

## Testing

Run the A/B testing tests with:
```
pytest tests/test_ab_testing.py
```

## Documentation

For detailed documentation, see `docs/ab-testing.md`.