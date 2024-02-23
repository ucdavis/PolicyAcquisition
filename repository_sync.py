import os
import shutil
import tempfile

from dotenv import load_dotenv
from git import Repo, exc
from datetime import datetime

from convert_pdfs import convert_pdfs

### Used to sync the content folder to the https://github.com/ucdavis/policy repo

load_dotenv()  # This loads the environment variables from .env

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
    Clears the content folder by deleting all files and subdirectories, except for the .git directory.

    Raises:
        OSError: If there is an error deleting files.
    """
    try:
        for item in os.listdir(directory):
            item_path = os.path.join(directory, item)
            if os.path.isfile(item_path):
                os.remove(item_path)
            elif os.path.isdir(item_path) and item != ".git":
                shutil.rmtree(item_path)
    except OSError as e:
        print(f"Error deleting files: {e}")
        exit(1)

def sync_policies(update_progress):
    """
    Synchronizes the policies by performing the following steps:
    1. Initialize or Open the Repo & Ensure "[branch_name]" Branch
    2. Pull/Fetch to Update Local Data. Reset to Remote State
    3. Update the Content
        a. Convert the PDFs to Text
        b. Copy text files over
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
        print(f'Temporary directory: {temp_dir}')

        # Step 1: Initialize the Repo & Ensure "[branch_name]" Branch
        try:
            # Clone the repo
            repo = Repo.clone_from(remote_url, temp_dir)

            # Ensure "main" branch is checked out
            if repo.active_branch.name != branch_name:
                repo.git.checkout(branch_name)

            # Make sure the remote URL is updated (in case the token has changed)
            if remote_name in repo.remotes:
                remote = repo.remotes[remote_name]
                remote.set_url(remote_url)
            else:
                remote = repo.create_remote(remote_name, url=remote_url)

        except Exception as e:
            print(f"Error initializing repo: {e}")
            exit(1)

        # Step 2: Pull/Fetch to Update Local Data. Reset to Remote State
        try:
            repo.git.fetch("--all")
            repo.git.reset("--hard", f"{remote_name}/{branch_name}")
        except exc.GitCommandError as e:
            print(f"Error updating local branch: {e}")
            exit(1)

        # Remove all files so we can replace with the new content
        clear_content_folder(temp_dir)

        # Step 3: Update the Content
            
        # Step 3a: Convert the PDFs to Text
        convert_pdfs(update_progress, output_directory=temp_dir)

        # Step 3b: Copy text files over
        ### TODO

        # Step 4: Commit and Push the Changes
        try:
            repo.git.add(A=True)
            repo.index.commit("Automated commit message")
            repo.git.push(remote_name, branch_name)
            print("Changes have been pushed successfully.")
        except exc.GitCommandError as e:
            print(f"Error during commit/push: {e}")
            exit(1)

        update_progress("Sync complete at " + datetime.now().isoformat())
