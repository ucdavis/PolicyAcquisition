from enum import Enum
import os
from typing import Any, Dict, List
from dotenv import load_dotenv
import pymongo
from pymongo import MongoClient
from datetime import datetime, timedelta
from bson.objectid import ObjectId
from dataclasses import dataclass

load_dotenv()

MONGO_CONNECTION = os.getenv("MONGO_CONNECTION")
MONGO_DB = os.getenv("MONGO_DB")


@dataclass
class Source:
    _id: ObjectId
    name: str
    url: str
    last_updated: datetime
    refresh_frequency: str


@dataclass
class Document:
    _id: ObjectId
    url: str  # treated as the unique identifier for a web document
    filename: str
    title: str
    last_updated: datetime
    source_id: ObjectId
    metadata: Dict[str, Any]  # TODO: might want to define a dataclass for this


class IndexStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


@dataclass
class IndexAttempt:
    _id: ObjectId
    source_id: ObjectId
    status: IndexStatus
    num_docs_indexed: int
    num_new_docs: int
    num_docs_removed: int
    start_time: datetime
    end_time: datetime
    duration: int
    error_details: str = ""


class SourceRepository:
    def __init__(self, db):
        self.collection = db.sources

    def create_index(self):
        self.collection.create_index([("last_updated", 1)])

    def get_all_sources_to_index(self) -> List[Source]:
        now = datetime.utcnow()
        result = self.collection.find(
            {
                "refresh_frequency": "daily",
                "last_updated": {"$lt": now - timedelta(days=1)},
            }
        )
        return [Source(**source) for source in result]

    def update_last_updated(self, source_id: str, last_updated: datetime) -> None:
        self.collection.update_one(
            {"_id": ObjectId(source_id)}, {"$set": {"last_updated": last_updated}}
        )


class DocumentRepository:
    def __init__(self, db):
        self.collection = db.documents

    def create_index(self):
        self.collection.create_index([("source_id", 1)])

    def get_docs_within_source(self, source_id: str) -> List[Document]:
        result = self.collection.find({"source_id": ObjectId(source_id)})
        return [Document(**doc) for doc in result]

    def insert_document(self, document: Document) -> ObjectId:
        document = {
            "url": document.url,
            "filename": document.filename,
            "source_id": ObjectId(document.source_id),
            "metadata": document.metadata,
            "title": document.title,
            "last_updated": document.last_updated,
        }
        return self.collection.insert_one(document).inserted_id


class IndexAttemptRepository:
    def __init__(self, db):
        self.collection = db.index_attempts

    def create_index(self):
        self.collection.create_index([("source_id", 1)])

    def add_index_attempt(self, attempt: IndexAttempt) -> ObjectId:
        index_attempt = {
            "source_id": attempt.source_id,
            "num_docs_indexed": attempt.num_docs_indexed,
            "num_new_docs": attempt.num_new_docs,
            "num_docs_removed": attempt.num_docs_removed,
            "start_time": attempt.start_time,
            "end_time": attempt.end_time,
            "duration": attempt.duration,
            "status": attempt.status.value,
            "error_details": attempt.error_details,
        }
        return self.collection.insert_one(index_attempt).inserted_id

    def get_index_attempts(self) -> List[IndexAttempt]:
        result = self.collection.find()
        return [
            IndexAttempt(**attempt, status=IndexStatus(attempt["status"]))
            for attempt in result
        ]


class PolicyDB:
    def __init__(self, uri: str, db_name: str):
        self.client = MongoClient(uri)
        self.db = self.client[db_name]

        # collections
        self.sources = SourceRepository(self.db)
        self.documents = DocumentRepository(self.db)
        self.index_attempts = IndexAttemptRepository(self.db)

        # Create indexes if they do not exist
        self._create_indexes()

    def _create_indexes(self) -> None:
        self.sources.create_index()
        self.documents.create_index()
        self.index_attempts.create_index()


def get_database():
    return PolicyDB(MONGO_CONNECTION, MONGO_DB)
