# Utils package for ModPorter AI Engine

from .vector_db_client import VectorDBClient

_vector_db_client_instance = None

def get_vector_db_client() -> VectorDBClient:
    """
    Returns a shared instance of the VectorDBClient.
    Initializes it if it doesn't exist yet.
    """
    global _vector_db_client_instance
    if _vector_db_client_instance is None:
        _vector_db_client_instance = VectorDBClient()
    return _vector_db_client_instance

# It might also be useful to expose the class directly if users
# want to create instances with custom configurations.
__all__ = ["VectorDBClient", "get_vector_db_client"]