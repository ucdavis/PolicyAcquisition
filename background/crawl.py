## Methods for getting documents to index, generally by crawling a website and extracting the relevant information
# Will call the appropriate method based on the source name and return a list of PolicyDetails objects

from db import SourceName
from download_academic_affairs import get_apm_links, get_apm_url
from download_ucop_policies import get_ucop_links, get_ucop_policies_url
from logger import setup_logger
from policy_details import PolicyDetails
from shared import get_driver

logger = setup_logger()


def get_source_policy_list(source_name: str) -> list[PolicyDetails] | None:
    """
    Get the list of policies to index for the given source
    """
    if source_name == SourceName.UCOP.value:
        return get_ucop_policies()
    elif source_name == SourceName.UCDAPM.value:
        return get_academic_affairs_apm()
    else:
        logger.error(f"Unknown source name {source_name}")
        return None


def get_ucop_policies() -> list[PolicyDetails]:
    """
    Get the list of UCOP policies to index
    """
    driver = get_driver()

    url = get_ucop_policies_url()

    logger.info(f"Getting UCOP policy info from {url}")

    policy_details_list = get_ucop_links(driver, url)

    logger.info(f"Found {len(policy_details_list)} UCOP policies")

    driver.quit()

    return policy_details_list


def get_fake_policies() -> list[PolicyDetails]:
    """
    fake policies so we don't have to scrape the web during testing
    """

    # create 2 fake policies
    policy1 = PolicyDetails(
        title="Fake Policy 1",
        url="https://css4.pub/2017/newsletter/drylab.pdf",
    )

    policy2 = PolicyDetails(
        title="Fake Policy 2",
        url="https://css4.pub/2015/usenix/example.pdf",
    )

    return [policy1, policy2]


def get_academic_affairs_apm() -> list[PolicyDetails]:
    """
    Get the list of Academic Affairs policies to index
    """
    driver = get_driver()

    url = get_apm_url()

    logger.info(f"Getting academic affairs policy info from {url}")

    policy_details_list = get_apm_links(driver, url)

    logger.info(f"Found {len(policy_details_list)} academic affairs policies")

    driver.quit()

    return policy_details_list
