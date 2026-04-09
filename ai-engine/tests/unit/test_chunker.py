
from utils.chunker import Chunker

class TestChunker:
    def test_chunk_document_basic(self):
        document = "abcdefghij"
        chunk_size = 4
        overlap = 2
        # Calculation:
        # 1. start=0, end=4 -> "abcd", next start = 4-2 = 2
        # 2. start=2, end=6 -> "cdef", next start = 6-2 = 4
        # 3. start=4, end=8 -> "efgh", next start = 8-2 = 6
        # 4. start=6, end=10 -> "ghij", next start = 10-2 = 8
        # 5. start=8, end=12 -> "ij", next start = 12-2 = 10
        # Loop ends as 10 < 10 is false
        chunks = Chunker.chunk_document(document, chunk_size, overlap)
        assert chunks == ["abcd", "cdef", "efgh", "ghij", "ij"]

    def test_chunk_document_no_overlap(self):
        document = "abcdefghij"
        chunk_size = 4
        overlap = 0
        # Expected:
        # 1. 0:4 -> "abcd"
        # 2. 4:8 -> "efgh"
        # 3. 8:12 -> "ij"
        chunks = Chunker.chunk_document(document, chunk_size, overlap)
        assert chunks == ["abcd", "efgh", "ij"]

    def test_chunk_document_large_chunk(self):
        document = "abc"
        chunk_size = 10
        overlap = 2
        chunks = Chunker.chunk_document(document, chunk_size, overlap)
        assert chunks == ["abc"]

    def test_chunk_document_empty(self):
        assert Chunker.chunk_document("", 10, 2) == []
        assert Chunker.chunk_document(None, 10, 2) == []

    def test_chunk_document_invalid_type(self):
        assert Chunker.chunk_document(123, 10, 2) == []

    def test_chunk_document_overlap_larger_than_size(self):
        # This tests the infinite loop prevention
        document = "abcdef"
        chunk_size = 4
        overlap = 6
        chunks = Chunker.chunk_document(document, chunk_size, overlap)
        # Should behave like overlap = 0 (no overlap) if it would loop infinitely
        assert chunks == ["abcd", "ef"]
