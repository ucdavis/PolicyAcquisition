## Methods for getting documents to index, generally by crawling a website and extracting the relevant information
# Will call the appropriate method based on the source name and return a list of PolicyDetails objects

import sys  ## eventually we want to move the crawl functions inside the background folder but for now let's just also check parent

sys.path.append("..")

from download_academic_affairs import get_apm_links, get_apm_url
from logger import setup_logger
from policy_details import PolicyDetails
from shared import get_driver

logger = setup_logger()


def get_ucop_policies() -> list[PolicyDetails]:
    """
    Get the list of UCOP policies to index
    """
    pass


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


def get_academic_affairs_policies() -> list[PolicyDetails]:
    """
    Get the list of Academic Affairs policies to index
    """
    driver = get_driver()
    url = get_apm_url()

    logger.info(f"Getting academic affairs policy info from {url}")

    policy_details_list = get_apm_links(driver, url)

    logger.info(f"Found {len(policy_details_list)} academic affairs policies")

    return policy_details_list
