## Methods for getting documents to index, generally by crawling a website and extracting the relevant information
# Will call the appropriate method based on the source name and return a list of PolicyDetails objects

from db import SourceName
from logger import setup_logger

from sources.apm import get_apm_links, get_apm_url
from sources.cb import get_uc_collective_bargaining_links
from sources.ucd import get_ucd_policy_binders, get_ucd_policy_links
from sources.ucop import get_ucop_links, get_ucop_policies_url
from sources.shared import get_driver
from models.policy_details import PolicyDetails

logger = setup_logger()


def get_source_policy_list(source_name: str) -> list[PolicyDetails] | None:
    """
    Get the list of policies to index for the given source
    """
    if source_name == SourceName.UCOP.value:
        return get_ucop_policies()
    elif source_name == SourceName.UCDAPM.value:
        return get_academic_affairs_apm()
    elif source_name == SourceName.UCDPOLICY.value:
        return get_ucdavis_policies()
    elif source_name == SourceName.UCCOLLECTIVEBARGAINING.value:
        return get_uc_collective_bargaining_policies()
    else:
        logger.error(f"Unknown source name {source_name}")
        return None


def get_uc_collective_bargaining_policies() -> list[PolicyDetails]:
    """
    Get the list of UC Collective Bargaining policies to index
    """
    driver = get_driver()

    policy_details_list = get_uc_collective_bargaining_links(driver)

    logger.info(f"Found {len(policy_details_list)} UC Collective Bargaining documents")

    driver.quit()

    return policy_details_list


def get_ucdavis_policies() -> list[PolicyDetails]:
    """
    Get the list of UC Davis policies to index
    A little tricky because:
    - The policies are organized by binders
    - Each policy URL has the actualy policy inside an iframe, so we can't just download the PDF directly
    """
    driver = get_driver()

    binders = get_ucd_policy_binders()

    policy_details_list = []

    for binder in binders:
        # each binder is a tuple of (binder_name, binder_url)
        binder_name, binder_url = binder

        logger.info(
            f"Getting UC Davis policy info from {binder_url} for binder {binder_name}"
        )

        binder_links = get_ucd_policy_links(driver, binder_url)

        policy_details_list.extend(binder_links)

        logger.info(
            f"Found {len(binder_links)} UC Davis policies for binder {binder_name}"
        )

    driver.quit()

    return policy_details_list


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
