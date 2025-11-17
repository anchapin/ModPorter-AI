import pytest
import pytest_asyncio
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from db import crud
from src.db.base import AsyncSessionLocal


@pytest_asyncio.fixture
async def async_session():
    """Create an async database session for testing."""
    async with AsyncSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def sample_conversion_job(async_session: AsyncSession):
    """Create a sample conversion job for testing."""
    job = await crud.create_job(
        async_session,
        file_id=str(uuid.uuid4()),
        original_filename="test_mod.jar",
        target_version="1.20.0",
        options={}
    )
    yield job

    # Cleanup - delete the job (cascade will handle behavior files)
    try:
        await async_session.delete(job)
        await async_session.commit()
    except Exception:
        pass  # Job might already be deleted


@pytest.mark.asyncio
class TestBehaviorFilesCRUD:
    """Test behavior files CRUD operations."""

    async def test_create_behavior_file(self, async_session: AsyncSession, sample_conversion_job):
        """Test creating a behavior file."""
        behavior_file = await crud.create_behavior_file(
            async_session,
            conversion_id=str(sample_conversion_job.id),
            file_path="behaviors/entities/test_entity.json",
            file_type="entity_behavior",
            content='{"minecraft:entity": {"description": {"identifier": "test:entity"}}}'
        )

        assert behavior_file.id is not None
        assert behavior_file.conversion_id == sample_conversion_job.id
        assert behavior_file.file_path == "behaviors/entities/test_entity.json"
        assert behavior_file.file_type == "entity_behavior"
        assert "test:entity" in behavior_file.content
        assert behavior_file.created_at is not None
        assert behavior_file.updated_at is not None

    async def test_get_behavior_file(self, async_session: AsyncSession, sample_conversion_job):
        """Test retrieving a behavior file by ID."""
        # Create a behavior file
        created_file = await crud.create_behavior_file(
            async_session,
            conversion_id=str(sample_conversion_job.id),
            file_path="behaviors/blocks/test_block.json",
            file_type="block_behavior",
            content='{"minecraft:block": {"description": {"identifier": "test:block"}}}'
        )

        # Retrieve it
        retrieved_file = await crud.get_behavior_file(async_session, str(created_file.id))

        assert retrieved_file is not None
        assert retrieved_file.id == created_file.id
        assert retrieved_file.file_path == "behaviors/blocks/test_block.json"
        assert retrieved_file.file_type == "block_behavior"
        assert "test:block" in retrieved_file.content

    async def test_get_behavior_files_by_conversion(self, async_session: AsyncSession, sample_conversion_job):
        """Test retrieving all behavior files for a conversion."""
        # Create multiple behavior files
        files_data = [
            {
                "file_path": "behaviors/entities/zombie.json",
                "file_type": "entity_behavior",
                "content": '{"minecraft:entity": {"description": {"identifier": "test:zombie"}}}'
            },
            {
                "file_path": "behaviors/blocks/stone.json",
                "file_type": "block_behavior",
                "content": '{"minecraft:block": {"description": {"identifier": "test:stone"}}}'
            },
            {
                "file_path": "scripts/main.js",
                "file_type": "script",
                "content": 'console.log("Hello World");'
            }
        ]

        created_files = []
        for file_data in files_data:
            behavior_file = await crud.create_behavior_file(
                async_session,
                conversion_id=str(sample_conversion_job.id),
                **file_data
            )
            created_files.append(behavior_file)

        # Retrieve all files
        retrieved_files = await crud.get_behavior_files_by_conversion(
            async_session, str(sample_conversion_job.id)
        )

        assert len(retrieved_files) == 3

        # Check that files are ordered by file_path
        file_paths = [f.file_path for f in retrieved_files]
        assert file_paths == sorted(file_paths)

        # Check file types are correct
        file_types = {f.file_path: f.file_type for f in retrieved_files}
        assert file_types["behaviors/entities/zombie.json"] == "entity_behavior"
        assert file_types["behaviors/blocks/stone.json"] == "block_behavior"
        assert file_types["scripts/main.js"] == "script"

    async def test_update_behavior_file_content(self, async_session: AsyncSession, sample_conversion_job):
        """Test updating behavior file content."""
        # Create a behavior file
        behavior_file = await crud.create_behavior_file(
            async_session,
            conversion_id=str(sample_conversion_job.id),
            file_path="recipes/test_recipe.json",
            file_type="recipe",
            content='{"minecraft:recipe_shaped": {"description": {"identifier": "test:recipe_old"}}}'
        )

        original_updated_at = behavior_file.updated_at

        # Update the content
        new_content = '{"minecraft:recipe_shaped": {"description": {"identifier": "test:recipe_new"}}}'
        updated_file = await crud.update_behavior_file_content(
            async_session, str(behavior_file.id), new_content
        )

        assert updated_file is not None
        assert updated_file.content == new_content
        assert "test:recipe_new" in updated_file.content
        assert updated_file.updated_at > original_updated_at

    async def test_get_behavior_files_by_type(self, async_session: AsyncSession, sample_conversion_job):
        """Test retrieving behavior files by type."""
        # Create files of different types
        entity_files = [
            ("behaviors/entities/cow.json", "entity_behavior", "cow"),
            ("behaviors/entities/pig.json", "entity_behavior", "pig"),
        ]

        block_files = [
            ("behaviors/blocks/dirt.json", "block_behavior", "dirt"),
        ]

        script_files = [
            ("scripts/utils.js", "script", "utils"),
        ]

        all_files = entity_files + block_files + script_files

        for file_path, file_type, identifier in all_files:
            await crud.create_behavior_file(
                async_session,
                conversion_id=str(sample_conversion_job.id),
                file_path=file_path,
                file_type=file_type,
                content=f'{{"identifier": "test:{identifier}"}}'
            )

        # Test getting entity behaviors
        entity_behaviors = await crud.get_behavior_files_by_type(
            async_session, str(sample_conversion_job.id), "entity_behavior"
        )
        assert len(entity_behaviors) == 2
        assert all(f.file_type == "entity_behavior" for f in entity_behaviors)

        # Test getting block behaviors
        block_behaviors = await crud.get_behavior_files_by_type(
            async_session, str(sample_conversion_job.id), "block_behavior"
        )
        assert len(block_behaviors) == 1
        assert block_behaviors[0].file_type == "block_behavior"

        # Test getting scripts
        scripts = await crud.get_behavior_files_by_type(
            async_session, str(sample_conversion_job.id), "script"
        )
        assert len(scripts) == 1
        assert scripts[0].file_type == "script"

    async def test_delete_behavior_file(self, async_session: AsyncSession, sample_conversion_job):
        """Test deleting a behavior file."""
        # Create a behavior file
        behavior_file = await crud.create_behavior_file(
            async_session,
            conversion_id=str(sample_conversion_job.id),
            file_path="temp/test_file.json",
            file_type="script",
            content='{"temp": "file"}'
        )

        file_id = str(behavior_file.id)

        # Verify it exists
        retrieved_file = await crud.get_behavior_file(async_session, file_id)
        assert retrieved_file is not None

        # Delete it
        success = await crud.delete_behavior_file(async_session, file_id)
        assert success is True

        # Verify it's gone
        deleted_file = await crud.get_behavior_file(async_session, file_id)
        assert deleted_file is None

    async def test_invalid_conversion_id(self, async_session: AsyncSession):
        """Test behavior with invalid conversion ID."""
        invalid_id = str(uuid.uuid4())

        # This should not raise an error, but return empty list
        files = await crud.get_behavior_files_by_conversion(async_session, invalid_id)
        assert files == []

        # Creating with invalid conversion_id should raise an error due to foreign key constraint
        with pytest.raises(Exception):  # Could be IntegrityError or similar
            await crud.create_behavior_file(
                async_session,
                conversion_id=invalid_id,
                file_path="invalid/test.json",
                file_type="test",
                content="test"
            )

    async def test_invalid_file_id_format(self, async_session: AsyncSession):
        """Test behavior with invalid file ID format."""
        # Test with non-UUID string
        result = await crud.get_behavior_file(async_session, "not-a-uuid")
        assert result is None

        result = await crud.update_behavior_file_content(async_session, "not-a-uuid", "content")
        assert result is None

        success = await crud.delete_behavior_file(async_session, "not-a-uuid")
        assert success is False
