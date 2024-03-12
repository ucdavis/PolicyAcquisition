import logging
import os
import shutil
import tempfile

from dotenv import load_dotenv
from git import Repo, exc
from datetime import datetime

### Used to sync the content folder to the https://github.com/ucdavis/policy repo

load_dotenv()  # This loads the environment variables from .env

file_storage_path_base = os.getenv("FILE_STORAGE_PATH", "./output")

logger = logging.getLogger(__name__)

remote_name = "origin"
branch_name = "sync"
github_token = os.getenv("GITHUB_TOKEN")

if not github_token:
    raise EnvironmentError(
        "GitHub Token not found. Please set the GITHUB_TOKEN environment variable."
    )

github_repo = "ucdavis/policy"
remote_url = f"https://{github_token}:x-oauth-basic@github.com/{github_repo}.git"


def clear_content_folder(directory):
    """
    Clears the content folder by deleting all files and subdirectories
    Leaves .git and the README file in place.
    Raises:
        OSError: If there is an error deleting files.
    """
    try:
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path):
                # Don't delete the README file
                if item != "README.md":
                    os.remove(item_path)
            elif os.path.isdir(item_path) and item != ".git":
                shutil.rmtree(item_path)
    except OSError as e:
        logger.error(f"Error deleting files: {e}")
        exit(1)


import os
import shutil


def copy_content_to_existing_dir(src, dst):
    """
    Copy the contents of the source directory to the destination directory.
    If a directory already exists in the destination, it will be overwritten.

    Args:
        src (str): The path to the source directory.
        dst (str): The path to the destination directory.

    Returns:
        None
    """
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            shutil.copytree(s, d, dirs_exist_ok=True)
        else:
            shutil.copy2(s, d)


def reset_file_storage_folder():
    """
    clear everything out of the file_storage_path_base directory.

    Returns:
        None
    """
    os.system(f"rm -rf {file_storage_path_base}/*")


def sync_policies(update_progress):
    """
    Synchronizes the policies by performing the following steps:
    1. Initialize or Open the Repo & Ensure "[branch_name]" Branch
    2. Clear the Content Folder but leave the git history
    3. Copy the new content to the folder
    4. Commit and Push the Changes

    Args:
        update_progress: A callback function to update the progress of the synchronization.

    Returns:
        None
    """

    update_progress("Starting sync at " + datetime.now().isoformat())

    # first, create a temporary directory to store the content
    # Create a temporary directory using the context manager
    with tempfile.TemporaryDirectory() as temp_dir:
        logger.info(f"Temporary directory: {temp_dir}")

        # Step 1: Initialize the Repo & Ensure "[branch_name]" Branch
        try:
            # Clone the repo with depth 1 (shallow clone, no need to download the entire history)
            repo = Repo.clone_from(remote_url, temp_dir, depth=1)

            update_progress("Repo cloned")

            # Ensure the needed branch is checked out
            if repo.active_branch.name != branch_name:
                # fetch the remote branch
                repo.git.fetch("origin", branch_name + ":" + branch_name, depth=1)
                repo.git.checkout(branch_name)

            update_progress("Branch checked out")

            # Make sure the remote URL is updated (in case the token has changed)
            if remote_name in repo.remotes:
                remote = repo.remotes[remote_name]
                remote.set_url(remote_url)
            else:
                remote = repo.create_remote(remote_name, url=remote_url)

        except Exception as e:
            logger.error(f"Error initializing repo: {e}")
            exit(1)

        update_progress("Local data fetched and reset to remote state.")

        # Step 2: Remove all files so we can replace with the new content
        clear_content_folder(temp_dir)

        update_progress("Content folder cleared.")

        # Step 3: Update the Content from the file_storage_path_base content directory
        copy_content_to_existing_dir(
            os.path.join(file_storage_path_base, "content"), temp_dir
        )

        update_progress("text output copied to the content folder.")

        # Content should be updated at this point, let's double check that there are folders in here now
        if not os.listdir(temp_dir):
            logger.error("Content directory is empty. No changes to push.")
            exit(1)

        update_progress("Ready to commit and push.")

        # Step 4: Commit and Push the Changes
        try:
            repo.git.add(A=True)
            commit_message = "Policy Update " + datetime.now().strftime("%Y-%m-%d")
            repo.index.commit(commit_message)
            repo.git.push(remote_name, branch_name)
            logger.info("Changes have been pushed successfully.")
            update_progress("Changes have been pushed successfully.")
        except exc.GitCommandError as e:
            logger.error(f"Error during commit/push: {e}")
            exit(1)

        update_progress("Sync complete at " + datetime.now().isoformat())
