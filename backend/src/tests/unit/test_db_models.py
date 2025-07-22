from db import models


def test_model_tablenames() -> None:
    assert models.ConversionJob.__tablename__ == "conversion_jobs"
    assert models.ConversionResult.__tablename__ == "conversion_results"
    assert models.JobProgress.__tablename__ == "job_progress"
