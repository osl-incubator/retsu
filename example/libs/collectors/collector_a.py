"""Collector A."""

from __future__ import annotations

from datetime import datetime

from .collector_base import CollectorBase
from .utils import df_from_raw_csv

COLLECTOR_A_DB = df_from_raw_csv(
    """
id,title,abstract,published_at
1,"article a 1","my abstract 1","2023-01-01"
2,"article a 2","my abstract 2","2023-02-01"
3,"article a 3","my abstract 3","2023-03-01"
4,"article a 4","my abstract 4","2023-04-01"
5,"article a 5","my abstract 5","2023-05-01"
6,"article a 6","my abstract 6","2023-06-01"
7,"article a 7","my abstract 7","2023-07-01"
8,"article a 8","my abstract 8","2023-08-01"
9,"article a 9","my abstract 9","2023-09-01"
10,"article a 10","my abstract 10","2023-10-01"
    """
)


class CollectorA(CollectorBase):
    """Collector A."""

    def get_docs_ids(self, query: str) -> list[str]:
        """Get a list of document IDs."""
        str_dt_start, str_dt_end = query.split(",")
        dt_start = datetime.strptime(str_dt_start, "%Y-%m-%d")
        dt_end = datetime.strptime(str_dt_end, "%Y-%m-%d")
        data = DB[
            (DB["published"] >= dt_start) and (DB["published"] <= dt_end)
        ]
        return data["id"].to_list()

    def get_docs_metadata(self, docs_ids: list[str]) -> list[dict[str, str]]:
        """Get a list of document metadata."""
        return [self.get_single_doc_metadata(idx) for idx in docs_ids]

    def get_single_doc_metadata(self, doc_id: str) -> dict[str, str]:
        """Get a document metadata."""
        return DB[DB["id"] == doc_id].to_dict("records")[0]
