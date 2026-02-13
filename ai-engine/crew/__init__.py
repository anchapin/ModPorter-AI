# Lazy import to avoid CrewAI import errors when crewai package is not available
# This can happen in test environments or when dependencies aren't fully installed
_RAGTasks = None
_RAGCrew = None

def RAGTasks(*args, **kwargs):
    """Lazy factory function for RAGTasks."""
    global _RAGTasks
    if _RAGTasks is None:
        from .rag_crew import RAGTasks as _RAGTasksClass
        _RAGTasks = _RAGTasksClass
    return _RAGTasks(*args, **kwargs)

def RAGCrew(*args, **kwargs):
    """Lazy factory function for RAGCrew."""
    global _RAGCrew
    if _RAGCrew is None:
        from .rag_crew import RAGCrew as _RAGCrewClass
        _RAGCrew = _RAGCrewClass
    return _RAGCrew(*args, **kwargs)

__all__ = ["RAGTasks", "RAGCrew"]
