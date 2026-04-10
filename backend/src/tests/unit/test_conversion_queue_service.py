import pytest
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from services.conversion_queue import ConversionJobQueue


@pytest.fixture
def mock_redis():
    redis = AsyncMock()
    redis.hset = AsyncMock()
    redis.zadd = AsyncMock()
    redis.zpopmax = AsyncMock()
    redis.hgetall = AsyncMock()
    redis.hget = AsyncMock()
    redis.zcard = AsyncMock()
    redis.close = AsyncMock()
    return redis


@pytest.fixture
def queue(mock_redis):
    q = ConversionJobQueue(redis_url="redis://localhost:6379")
    q._redis = mock_redis
    return q


@pytest.mark.asyncio
async def test_enqueue_job_success(queue, mock_redis):
    user_id = "user-1"
    java_code = "public class Test {}"
    mod_info = {"name": "test"}
    options = {"target": "bedrock"}

    job_id = await queue.enqueue_job(user_id, java_code, mod_info, options)

    assert job_id is not None
    assert isinstance(uuid.UUID(job_id), uuid.UUID)

    # Check if hset was called with job data
    mock_redis.hset.assert_called()
    call_args = mock_redis.hset.call_args_list[0][1]
    assert call_args["mapping"]["job_id"] == job_id
    assert call_args["mapping"]["user_id"] == user_id
    assert call_args["mapping"]["status"] == "queued"

    # Check if zadd was called for priority queue
    mock_redis.zadd.assert_called_with(queue.QUEUE_KEY, {job_id: 0})


@pytest.mark.asyncio
async def test_dequeue_job_success(queue, mock_redis):
    job_id = "job-123"
    job_data = {
        "job_id": job_id,
        "user_id": "user-1",
        "status": "queued",
        "mod_info": json.dumps({"name": "test"}),
        "options": json.dumps({}),
    }

    mock_redis.zpopmax.return_value = [(job_id, 0)]
    mock_redis.hgetall.return_value = job_data

    result = await queue.dequeue_job()

    assert result["job_id"] == job_id
    assert result["mod_info"]["name"] == "test"
    # Check status was updated
    mock_redis.hset.assert_called()


@pytest.mark.asyncio
async def test_dequeue_job_empty(queue, mock_redis):
    mock_redis.zpopmax.return_value = []

    result = await queue.dequeue_job()

    assert result is None


@pytest.mark.asyncio
async def test_update_progress(queue, mock_redis):
    job_id = "job-123"
    await queue.update_progress(job_id, 50, "parsing", "Parsing files...")

    # Check progress hash update
    mock_redis.hset.assert_called()
    # Find call for progress key
    progress_call = next(
        c for c in mock_redis.hset.call_args_list if f"{queue.PROGRESS_KEY}:{job_id}" in c[0][0]
    )
    assert progress_call[1]["mapping"]["progress"] == 50
    assert progress_call[1]["mapping"]["current_stage"] == "parsing"


@pytest.mark.asyncio
async def test_complete_job(queue, mock_redis):
    job_id = "job-123"
    result_meta = {"status": "success"}
    bedrock_code = "// bedrock"

    await queue.complete_job(job_id, result_meta, bedrock_code)

    # Check results hash update
    results_call = next(
        c for c in mock_redis.hset.call_args_list if f"{queue.RESULTS_KEY}:{job_id}" in c[0][0]
    )
    assert results_call[1]["mapping"]["bedrock_code"] == bedrock_code

    # Check job status update
    job_call = next(
        c for c in mock_redis.hset.call_args_list if f"{queue.JOBS_KEY}:{job_id}" in c[0][0]
    )
    assert job_call[1]["mapping"]["status"] == "completed"


@pytest.mark.asyncio
async def test_fail_job(queue, mock_redis):
    job_id = "job-123"
    error = "Something went wrong"

    await queue.fail_job(job_id, error)

    job_call = next(
        c for c in mock_redis.hset.call_args_list if f"{queue.JOBS_KEY}:{job_id}" in c[0][0]
    )
    assert job_call[1]["mapping"]["status"] == "failed"
    assert job_call[1]["mapping"]["error_message"] == error


@pytest.mark.asyncio
async def test_get_job_result_success(queue, mock_redis):
    job_id = "job-123"
    mock_redis.hgetall.return_value = {
        "job_id": job_id,
        "result": json.dumps({"ok": True}),
        "bedrock_code": "code",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }

    result = await queue.get_job_result(job_id)
    assert result["job_id"] == job_id
    assert result["result"]["ok"] is True
    assert result["bedrock_code"] == "code"


@pytest.mark.asyncio
async def test_get_job_result_not_found(queue, mock_redis):
    mock_redis.hgetall.return_value = {}

    result = await queue.get_job_result("unknown")
    assert result is None


@pytest.mark.asyncio
async def test_close(queue, mock_redis):
    await queue.close()
    mock_redis.close.assert_called_once()
    assert queue._redis is None
