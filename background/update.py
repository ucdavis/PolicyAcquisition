import logging
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

from db import IndexAttempt, IndexStatus, RefreshFrequency, Source
from mongoengine.queryset.visitor import Q

logger = logging.getLogger(__name__)

# Set up logging, just for development purposes for now
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)  # Set the logging level

load_dotenv()  # This loads the environment variables from .env


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
        if source.name == "UCOP":
            # download UCOP
            pass
        elif source.name == "UCD":
            # download UCD
            pass
        else:
            logger.error(f"Source {source.name} not recognized")
            attempt.status = IndexStatus.FAILURE
            attempt.error_details = f"Source {source.name} not recognized"
            attempt.save()
            return

        logger.info(f"Indexing source {source.name} successful.")
        # End timing the indexing attempt
        end_time = datetime.now(timezone.utc)

        # Record a successful index attempt
        attempt.status = IndexStatus.SUCCESS
        attempt.end_time = end_time
        attempt.duration = (end_time - start_time).total_seconds()
        attempt.num_docs_indexed = 0  # TODO: update with actual counts
        attempt.num_new_docs = 0  # TODO: update with actual counts
        attempt.num_docs_removed = 0  # TODO: update with actual counts

        source.last_updated = datetime.now(timezone.utc)

        attempt.save()
        source.save()
    except Exception as e:
        # End timing the indexing attempt in case of an error
        end_time = datetime.now(timezone.utc)

        # Record a failed index attempt
        attempt.status = IndexStatus.FAILURE
        attempt.error_details = str(e)
        attempt.end_time = end_time

        attempt.save()
        logger.warning(f"Indexing failed for source: {source.name} due to {e}")


def update_loop(delay: int = 60) -> None:
    while True:
        start = time.time()
        start_time_utc = datetime.fromtimestamp(start).strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Running update, current UTC time: {start_time_utc}")

        # get all sources that need to be updated (daily and last updated more than 1 day ago)
        one_day_ago = datetime.now() - timedelta(days=1)

        sources_to_index = Source.objects(
            Q(refresh_frequency=RefreshFrequency.DAILY)
            & Q(last_updated__lte=one_day_ago)
        )

        if not sources_to_index:
            logger.info("No sources to update. Sleeping.")
            time.sleep(delay)
            continue

        # otherwise, we have sources to index, get the first
        source = sources_to_index[0]

        # Perform indexing
        index_documents(source)


def tmp_create_source():
    ## if there are no sources, create one to play with
    sources = Source.objects()

    if len(sources) == 0:
        # create a source
        source = Source(
            name="UCOP",
            url="https://policy.ucop.edu/policy/",
            refresh_frequency="daily",
            last_updated=datetime.now(timezone.utc),
        )
        source.save()

    ## delete all existing index attempts so we have a clean slate
    IndexAttempt.objects().delete()


def update__main() -> None:
    logger.info("Starting Indexing Loop")
    tmp_create_source()
    update_loop()


if __name__ == "__main__":
    update__main()
