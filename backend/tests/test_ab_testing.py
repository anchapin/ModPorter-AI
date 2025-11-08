"""
Test suite for A/B testing infrastructure
"""

import pytest
import uuid
from db import crud


@pytest.mark.asyncio
async def test_experiment_lifecycle(db_session):
    """Test the full lifecycle of an experiment"""
    # Create experiment
    experiment = await crud.create_experiment(
        db_session,
        name="Test Experiment",
        description="A test experiment for A/B testing",
        status="active",
        traffic_allocation=50
    )

    assert experiment.id is not None
    assert experiment.name == "Test Experiment"
    assert experiment.status == "active"
    assert experiment.traffic_allocation == 50

    # Get experiment
    retrieved_experiment = await crud.get_experiment(db_session, experiment.id)
    assert retrieved_experiment is not None
    assert retrieved_experiment.name == "Test Experiment"

    # Update experiment
    updated_experiment = await crud.update_experiment(
        db_session,
        experiment.id,
        status="paused"
    )

    assert updated_experiment.status == "paused"

    # List experiments
    experiments = await crud.list_experiments(db_session, status="paused")
    assert len(experiments) >= 1
    assert any(exp.id == experiment.id for exp in experiments)

    # Delete experiment
    result = await crud.delete_experiment(db_session, experiment.id)
    assert result is True

    # Verify deletion
    deleted_experiment = await crud.get_experiment(db_session, experiment.id)
    assert deleted_experiment is None


@pytest.mark.asyncio
async def test_experiment_variant_lifecycle(db_session):
    """Test the full lifecycle of an experiment variant"""
    # Create experiment first
    experiment = await crud.create_experiment(
        db_session,
        name="Variant Test Experiment",
        description="Experiment for testing variants",
        status="active"
    )

    # Create variant
    variant = await crud.create_experiment_variant(
        db_session,
        experiment_id=experiment.id,
        name="Test Variant",
        description="A test variant",
        is_control=True,
        strategy_config={"test": "config"}
    )

    assert variant.id is not None
    assert variant.name == "Test Variant"
    assert variant.is_control is True
    assert variant.strategy_config == {"test": "config"}

    # Get variant
    retrieved_variant = await crud.get_experiment_variant(db_session, variant.id)
    assert retrieved_variant is not None
    assert retrieved_variant.name == "Test Variant"

    # List variants
    variants = await crud.list_experiment_variants(db_session, experiment.id)
    assert len(variants) == 1
    assert variants[0].id == variant.id

    # Update variant
    updated_variant = await crud.update_experiment_variant(
        db_session,
        variant.id,
        name="Updated Variant",
        is_control=False
    )

    assert updated_variant.name == "Updated Variant"
    assert updated_variant.is_control is False

    # Delete variant
    result = await crud.delete_experiment_variant(db_session, variant.id)
    assert result is True

    # Verify deletion
    deleted_variant = await crud.get_experiment_variant(db_session, variant.id)
    assert deleted_variant is None

    # Clean up experiment
    await crud.delete_experiment(db_session, experiment.id)


@pytest.mark.asyncio
async def test_experiment_results(db_session):
    """Test recording and retrieving experiment results"""
    # Create experiment and variant first
    experiment = await crud.create_experiment(
        db_session,
        name="Results Test Experiment",
        description="Experiment for testing results",
        status="active"
    )

    variant = await crud.create_experiment_variant(
        db_session,
        experiment_id=experiment.id,
        name="Results Test Variant",
        is_control=True
    )

    # Create result
    session_id = uuid.uuid4()
    result = await crud.create_experiment_result(
        db_session,
        variant_id=variant.id,
        session_id=session_id,
        kpi_quality=95.5,
        kpi_speed=1200,
        kpi_cost=0.5,
        user_feedback_score=4.5,
        user_feedback_text="Great conversion!",
        result_metadata={"test": "data"}
    )

    assert result.id is not None
    assert result.variant_id == variant.id
    assert result.session_id == session_id
    assert result.kpi_quality == 95.5
    assert result.kpi_speed == 1200
    assert result.kpi_cost == 0.5
    assert result.user_feedback_score == 4.5
    assert result.user_feedback_text == "Great conversion!"
    assert result.result_asset_metadata == {"test": "data"}

    # Get result
    retrieved_result = await crud.get_experiment_result(db_session, result.id)
    assert retrieved_result is not None
    assert retrieved_result.kpi_quality == 95.5

    # List results
    results = await crud.list_experiment_results(db_session, variant_id=variant.id)
    assert len(results) == 1
    assert results[0].id == result.id

    results = await crud.list_experiment_results(db_session, session_id=session_id)
    assert len(results) == 1
    assert results[0].id == result.id

    # Clean up
    await crud.delete_experiment_variant(db_session, variant.id)
    await crud.delete_experiment(db_session, experiment.id)


@pytest.mark.asyncio
async def test_control_variant_uniqueness(db_session):
    """Test that only one control variant exists per experiment"""
    # Create experiment
    experiment = await crud.create_experiment(
        db_session,
        name="Control Test Experiment",
        description="Experiment for testing control variant uniqueness",
        status="active"
    )

    # Create first control variant
    control_variant1 = await crud.create_experiment_variant(
        db_session,
        experiment_id=experiment.id,
        name="Control Variant 1",
        is_control=True
    )

    # Create second control variant - this should make the first one not control
    control_variant2 = await crud.create_experiment_variant(
        db_session,
        experiment_id=experiment.id,
        name="Control Variant 2",
        is_control=True
    )

    # Verify first variant is no longer control
    updated_variant1 = await crud.get_experiment_variant(db_session, control_variant1.id)
    assert updated_variant1 is not None
    assert updated_variant1.is_control is False

    # Verify second variant is control
    retrieved_variant2 = await crud.get_experiment_variant(db_session, control_variant2.id)
    assert retrieved_variant2 is not None
    assert retrieved_variant2.is_control is True

    # Update first variant to be control - this should make the second one not control
    updated_variant1 = await crud.update_experiment_variant(
        db_session,
        control_variant1.id,
        is_control=True
    )

    assert updated_variant1.is_control is True

    # Verify second variant is no longer control
    updated_variant2 = await crud.get_experiment_variant(db_session, control_variant2.id)
    assert updated_variant2 is not None
    assert updated_variant2.is_control is False

    # Clean up
    await crud.delete_experiment_variant(db_session, control_variant1.id)
    await crud.delete_experiment_variant(db_session, control_variant2.id)
    await crud.delete_experiment(db_session, experiment.id)
