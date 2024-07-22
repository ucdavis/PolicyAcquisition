import os
from bson import ObjectId
from enum import Enum
from dotenv import load_dotenv
from mongoengine import (
    Document,
    StringField,
    DateTimeField,
    ObjectIdField,
    DictField,
    IntField,
    EnumField,
    connect,
)

load_dotenv()

MONGO_CONNECTION = os.getenv("MONGO_CONNECTION")
MONGO_DB = os.getenv("MONGO_DB")

connect(db=MONGO_DB, host=MONGO_CONNECTION)


class RefreshFrequency(Enum):
    DAILY = "DAILY"


class SourceStatus(Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    FAILED = "FAILED"


class SourceName(Enum):
    UCOP = "UCOP"
    UCCOLLECTIVEBARGAINING = "UCCOLLECTIVEBARGAINING"
    UCDAPM = "UCDAPM"
    UCDPOLICY = "UCDPOLICY"
    UCDKB = "UCDKB"


class SourceType(Enum):
    CUSTOM = "CUSTOM"  # Custom source (ex: ucop, ellucid)
    RECURSIVE = "RECURSIVE"  # Given a base site, index everything under that path
    SITEMAP = "SITEMAP"  # Given a sitemap.xml URL, parse all the pages in it
    SINGLE = "SINGLE"  # Given a URL, index only the given page (unsupported)


class Source(Document):
    name = StringField(required=True)
    url = StringField(required=True)
    type = EnumField(SourceType, required=True)
    last_updated = DateTimeField(required=True)
    last_failed = DateTimeField(required=False)
    refresh_frequency = EnumField(RefreshFrequency, required=True)
    failure_count = IntField(default=0)
    status = EnumField(SourceStatus, required=True)
    _id = ObjectIdField(default=ObjectId, primary_key=True)

    meta = {"collection": "sources"}


class IndexedDocument(Document):
    url = StringField(required=True, unique=True)  # url is the unique identifier
    filename = StringField(required=True)
    title = StringField(required=True)
    last_updated = DateTimeField(required=True)
    source_id = ObjectIdField(required=True)
    metadata = DictField(required=True)
    _id = ObjectIdField(default=ObjectId, primary_key=True)

    meta = {"collection": "documents"}


class IndexStatus(Enum):
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    INPROGRESS = "INPROGRESS"


class IndexAttempt(Document):
    source_id = ObjectIdField(required=True)
    status = EnumField(IndexStatus, required=True)
    num_docs_indexed = IntField(required=True)
    num_new_docs = IntField(required=True)
    num_docs_removed = IntField(required=True)
    start_time = DateTimeField(required=True)
    end_time = DateTimeField(required=False)
    duration = IntField(required=True)
    error_details = StringField(default="")
    _id = ObjectIdField(default=ObjectId, primary_key=True)

    meta = {"collection": "index_attempts"}
