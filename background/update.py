import gc
import time
from datetime import datetime, timedelta, timezone
import traceback
from dotenv import load_dotenv

from ingest import ingest_documents, ingest_kb_documents
from crawl import get_source_policy_list
from db import (
    IndexAttempt,
    IndexStatus,
    IndexedDocument,
    RefreshFrequency,
    Source,
    SourceName,
    SourceStatus,
)
from mongoengine.queryset.visitor import Q

from logger import setup_logger

logger = setup_logger()

load_dotenv()  # This loads the environment variables from .env

# TODO: load from env
MAX_SOURCE_FAILURES = 3


def index_documents(source: Source) -> None:
    start_time = datetime.now(timezone.utc)

    # create new index attempt
    attempt = IndexAttempt(
        source_id=source._id,
        status=IndexStatus.INPROGRESS,
        num_docs_indexed=0,
        num_new_docs=0,
        num_docs_removed=0,
        start_time=start_time,
        duration=0,
        end_time=None,
        error_details=None,
    )

    attempt.save()

    ## TODO: each source should return a list of PolicyDetails objects from their respective functions
    ## then common code to loop through each, save to db, download files, convert to text, vectorize and save to db
    ## want to check if the policy already exists in the db, if so, update the metadata and text, if not, create a new one.  use hash to check if file has changed
    ## then when all are done, update the source last_updated field and update the attempt with the final counts
    ## OPTIONAL: eventually, we could add a check to see if the policy has been removed from the source, and if so, remove it from the db

    try:
        policy_details = get_source_policy_list(source.name)

        if policy_details is None:
            logger.error(f"Source {source.name} not recognized")

            # automatically fail the attempt, save error details and disable the source
            attempt.status = IndexStatus.FAILURE
            attempt.error_details = f"Source {source.name} not recognized"
            attempt.save()

            source.status = SourceStatus.FAILED
            source.last_failed = datetime.now(timezone.utc)
            source.failure_count += 1
            source.save()

            return

        logger.info(
            f"Found {len(policy_details)} documents from source {source.name}. Ingesting..."
        )

        # if we have no documents, raise an error
        if len(policy_details) == 0:
            raise ValueError(f"No documents found for source {source.name}")

        # loop through each policy, download files, convert to text, vectorize and save to db
        if source.name == SourceName.UCDKB.value:
            # KB is a special case, we have the data in a JSON file
            ingest_result = ingest_kb_documents(source, policy_details)
        else:
            ingest_result = ingest_documents(source, policy_details)

        logger.info(f"Indexing source {source.name} successful.")

        # End timing the indexing attempt
        end_time = datetime.now(timezone.utc)

        # Record a successful index attempt
        attempt.status = IndexStatus.SUCCESS
        attempt.end_time = end_time
        attempt.duration = (end_time - start_time).total_seconds()
        attempt.num_docs_indexed = ingest_result.num_docs_indexed
        attempt.num_new_docs = ingest_result.num_new_docs
        attempt.num_docs_removed = 0  # TODO: update with actual counts

        source.last_updated = datetime.now(timezone.utc)
        source.failure_count = 0
        source.last_failed = None

        attempt.save()
        source.save()
    except Exception as e:
        # End timing the indexing attempt in case of an error
        end_time = datetime.now(timezone.utc)

        # Record a failed index attempt
        attempt.status = IndexStatus.FAILURE
        attempt.error_details = traceback.format_exc()  # Get full traceback
        attempt.end_time = end_time

        attempt.save()
        logger.warning(f"Indexing failed for source: {source.name} due to {e}")

        ## register failed attempts.  If too many failed attempts, disable the source
        source.last_failed = datetime.now(timezone.utc)
        source.failure_count += 1

        if source.failure_count >= MAX_SOURCE_FAILURES:
            logger.error(
                f"Source {source.name} has failed {source.failure_count} times. Disabling."
            )
            source.status = SourceStatus.FAILED


def cleanup_old_attempts():
    """Set to failed any index_attempts that are INPROGRESS and started more than 1 day ago"""
    one_day_ago = datetime.now(timezone.utc) - timedelta(days=1)
    IndexAttempt.objects(
        Q(status=IndexStatus.INPROGRESS) & Q(start_time__lte=one_day_ago)
    ).update(
        status=IndexStatus.FAILURE,
        error_details="Indexing attempt took too long or was interrupted",
    )


def update_loop(delay: int = 60) -> None:
    while True:
        start = time.time()
        start_time_utc = datetime.fromtimestamp(start).strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Running update, current UTC time: {start_time_utc}")

        # get all sources that might need to be updated (daily and last updated more than 1 day ago)
        one_day_ago = datetime.now() - timedelta(days=1)

        sources_to_index = Source.objects(
            Q(refresh_frequency=RefreshFrequency.DAILY)
            & Q(last_updated__lte=one_day_ago)
            & Q(status=SourceStatus.ACTIVE)
        )

        # we don't want to index any sources that have failed recently
        filtered_sources = []
        current_time = datetime.now()

        for source in sources_to_index:
            if (
                not source.last_failed
            ):  # if the source has never failed, add it to the list
                filtered_sources.append(source)
            else:  # if the source has failed, check if it has been long enough to try again
                allowable_failure_time = source.last_failed + timedelta(
                    hours=source.failure_count * 6
                )
                if allowable_failure_time <= current_time:
                    filtered_sources.append(source)

        if not filtered_sources:
            logger.info("No sources to update. Sleeping.")
            time.sleep(delay)
            continue

        # we have valid sources in need up update, get the first
        source = filtered_sources[0]

        # Perform indexing
        index_documents(source)

        gc.collect()  # clean up memory after each indexing run


def tmp_reset_db():
    # delete all sources and index attempts and documents
    Source.objects().delete()
    IndexAttempt.objects().delete()
    IndexedDocument.objects().delete()

    # create a source that needs to be updated
    source = Source(
        name=SourceName.UCDAPM.value,
        url="https://policy.ucop.edu/",
        refresh_frequency=RefreshFrequency.DAILY,
        last_updated=datetime.now(timezone.utc) - timedelta(days=30),
        status=SourceStatus.ACTIVE,
    )
    source.save()

    ## delete all existing index attempts so we have a clean slate
    IndexAttempt.objects().delete()


def ensure_default_source():
    # make sure we have the APM source setup
    source = Source.objects(name=SourceName.UCDAPM.value).first()

    if not source:
        source = Source(
            name=SourceName.UCDAPM.value,
            url="https://policy.ucop.edu/",
            refresh_frequency=RefreshFrequency.DAILY,
            last_updated=datetime.now(timezone.utc) - timedelta(days=30),
            status=SourceStatus.ACTIVE,
        )
        source.save()


def update__main() -> None:
    logger.info("Starting Indexing Loop")
    cleanup_old_attempts()
    ensure_default_source()  # TMP: don't delete anything but make sure the APM source is in there
    update_loop()


if __name__ == "__main__":
    update__main()
