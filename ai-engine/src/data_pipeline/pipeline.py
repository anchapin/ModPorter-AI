from typing import List
from .document import Document
from .document_loader import DocumentLoader
from .text_splitter import TextSplitter

class IngestionPipeline:
    def __init__(self, document_loader: DocumentLoader, text_splitter: TextSplitter):
        self.document_loader = document_loader
        self.text_splitter = text_splitter

    def process(self, file_path: str) -> List[Document]:
        '''
        Processes a single file:
        1. Loads the document using the document loader.
        2. For each loaded document (some loaders might return multiple docs from one file),
           splits it into chunks using the text splitter.
        3. Returns a flat list of all chunked documents.
        '''
        loaded_documents = self.document_loader.load(file_path)

        all_chunks: List[Document] = []
        for doc in loaded_documents:
            chunks = self.text_splitter.split_text(doc)
            all_chunks.extend(chunks)

        return all_chunks

    def process_batch(self, file_paths: List[str]) -> List[Document]:
        '''
        Processes a batch of files.
        1. Iterates through each file path.
        2. Calls the process method for each file.
        3. Aggregates and returns all chunks from all processed files.
        '''
        all_processed_chunks: List[Document] = []
        for file_path in file_paths:
            # Here we could add error handling for individual file processing if needed
            chunks_from_file = self.process(file_path)
            all_processed_chunks.extend(chunks_from_file)
        return all_processed_chunks
