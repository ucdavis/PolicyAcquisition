from datetime import datetime
import logging
from typing import List
from urllib.parse import urljoin, urlparse
from dotenv import load_dotenv

from bs4 import BeautifulSoup

from background.ingest import request_with_retry
from background.models.policy_details import PolicyDetails

load_dotenv()  # This loads the environment variables from .env

logger = logging.getLogger(__name__)

user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"


def get_sitemap_links(sitemap_url):
    """
    Given a sitemap.xml URL, read the urls and return a list of PolicyDetails objects
    """
    headers = {"User-Agent": user_agent}
    response = request_with_retry(
        sitemap_url, headers=headers, allow_redirects=True, timeout=60
    )

    response.raise_for_status()

    if response is None:
        logger.error(f"Failed to fetch sitemap {sitemap_url}")
        return []

    policy_details_list: List[PolicyDetails] = []

    soup = BeautifulSoup(response.content, "html.parser")

    url_tags = soup.find_all("url")

    for url_tag in url_tags:
        loc_tag = url_tag.find("loc")
        lastmod_tag = url_tag.find("lastmod")

        if loc_tag:
            url = _ensure_absolute_url(sitemap_url, loc_tag.text)

            if lastmod_tag and lastmod_tag.text:
                try:
                    lastmod_date = datetime.fromisoformat(lastmod_tag.text)
                except ValueError:
                    lastmod_date = None
            else:
                lastmod_date = None

            policy_details = PolicyDetails(
                url=url, effective_date=lastmod_date, issuance_date=lastmod_date
            )
            policy_details_list.append(policy_details)

    if len(policy_details) == 0 and len(soup.find_all("urlset")) == 0:
        # the given url doesn't look like a sitemap
        logger.error(
            f"No URLs found in sitemap {sitemap_url}. Check URL and ensure it's a valid sitemap.xml"
        )
        return []

    if len(policy_details) == 0:
        raise ValueError(f"No URLs found in sitemap {sitemap_url}")

    return policy_details_list


def _ensure_absolute_url(source_url: str, maybe_relative_url: str) -> str:
    if not urlparse(maybe_relative_url).netloc:
        return urljoin(source_url, maybe_relative_url)
    return maybe_relative_url
