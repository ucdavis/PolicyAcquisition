import logging
import os
import sys
import time
from datetime import datetime
from dotenv import load_dotenv

from db import Source, get_database, PolicyDB

logger = logging.getLogger(__name__)

# Set up logging, just for development purposes for now
handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)  # Set the logging level

load_dotenv()  # This loads the environment variables from .env


def index_documents(source: Source, db: PolicyDB) -> None:
    start_time = datetime.utcnow()

    try:
        if source.name == "UCOP":
            # download UCOP
            pass
        elif source.name == "UCD":
            # download UCD
            pass
        else:
            logger.error(f"Source {source.name} not recognized")
            return
    except Exception as e:
        # End timing the indexing attempt in case of an error
        end_time = datetime.utcnow()

        # Record a failed index attempt
        db.add_index_attempt(
            str(source.source_id), "FAILURE", 0, 0, 0, start_time, end_time, str(e)
        )
        logger.warning(f"Indexing failed for source: {source.name} due to {e}")


def update_loop(delay: int = 60) -> None:
    db = get_database()

    while True:
        start = time.time()
        start_time_utc = datetime.fromtimestamp(start).strftime("%Y-%m-%d %H:%M:%S")
        logger.info(f"Running update, current UTC time: {start_time_utc}")

        sources_to_index = db.sources.get_all_sources_to_index()

        if not sources_to_index:
            logger.info("No sources to update. Sleeping.")
            time.sleep(delay)
            continue

        # otherwise, we have sources to index, get the first
        source = sources_to_index[0]

        # Perform indexing
        index_documents(source, db)


def update__main() -> None:
    logger.info("Starting Indexing Loop")
    update_loop()


if __name__ == "__main__":
    update__main()
