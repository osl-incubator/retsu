from __future__ import annotations


class CollectorBase:
    def get_docs_ids(self, query: str) -> list[str]:
        """Get a list of document IDs."""
        raise Exception("Not implemented yet")

    def get_docs_metadata(self, doc_id: str) -> list[dict[str, str]]:
        """Get a list of document metadata."""
        raise Exception("Not implemented yet")

    def get_doc_metadata(self, doc_id: str) -> dict[str, str]:
        """Get a document metadata."""
        raise Exception("Not implemented yet")
