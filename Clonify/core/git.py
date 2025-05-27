import asyncio
import shlex
from typing import Tuple

from git import Repo, exc as git_exc # Import specific exceptions from git.exc
# from git.exc import GitCommandError, InvalidGitRepositoryError # Original imports

import config

# Assuming LOGGER is initialized in the parent package or a shared logging module
from ..logging import LOGGER
_log = LOGGER(__name__)


def install_req(cmd: str) -> Tuple[str, str, int, int]:
    _log.info(f"Attempting to install requirements with command: '{cmd}'")
    
    async def install_requirements_async(): # Renamed for clarity
        args = shlex.split(cmd)
        process = await asyncio.create_subprocess_exec(
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()
        return (
            stdout.decode("utf-8", "replace").strip(),
            stderr.decode("utf-8", "replace").strip(),
            process.returncode,
            process.pid,
        )

    try:
        # Ensure an event loop is available. If this function is called from a sync context
        # without a running loop, this might be an issue.
        # loop = asyncio.get_event_loop() # This might be needed if no loop is running
        # stdout, stderr, returncode, pid = loop.run_until_complete(install_requirements_async())
        # However, the original code `asyncio.get_event_loop().run_until_complete` suggests it's okay.
        stdout, stderr, returncode, pid = asyncio.get_event_loop().run_until_complete(install_requirements_async())

        if returncode == 0:
            _log.info(f"Successfully installed requirements. PID: {pid}. Command: '{cmd}'")
            if stdout: _log.debug(f"Install stdout:\n{stdout}")
        else:
            _log.error(
                f"Failed to install requirements. PID: {pid}. Return Code: {returncode}. Command: '{cmd}'\n"
                f"Stderr:\n{stderr}\n"
                f"Stdout (if any):\n{stdout}"
            )
        return stdout, stderr, returncode, pid
    except FileNotFoundError as fnf_error: # If the command itself (e.g. pip3) is not found
        _log.critical(f"Install command '{cmd.split()[0]}' not found. Ensure it's in PATH. Error: {fnf_error}", exc_info=True)
        return "", str(fnf_error), -1, -1 # Return dummy values indicating critical failure
    except Exception as e:
        _log.critical(f"Exception during requirements installation with command '{cmd}': {e}", exc_info=True)
        return "", str(e), -1, -1 # Return dummy values


def git_repo_setup(): # Renamed from 'git()' to be more descriptive
    _log.info("Setting up Git repository...")
    if not config.UPSTREAM_REPO:
        _log.warning("UPSTREAM_REPO not configured. Skipping Git setup.")
        return

    repo_link_for_logging = config.UPSTREAM_REPO.split("://")[1] if "://" in config.UPSTREAM_REPO else config.UPSTREAM_REPO
    
    actual_upstream_repo = config.UPSTREAM_REPO
    if config.GIT_TOKEN:
        if "github.com" not in config.UPSTREAM_REPO: # Basic check
            _log.error("GIT_TOKEN is provided, but UPSTREAM_REPO does not seem to be a GitHub link. Cannot construct authenticated URL safely.")
            # Fallback to unauthenticated, or skip if auth is mandatory
        else:
            git_username_match = re.search(r"github\.com/([^/]+)/", config.UPSTREAM_REPO) # More robust extraction
            if git_username_match:
                git_username = git_username_match.group(1)
                temp_repo = config.UPSTREAM_REPO.split("https://")[1]
                actual_upstream_repo = f"https://{git_username}:{config.GIT_TOKEN}@{temp_repo}"
                _log.info(f"Using authenticated Git remote for user '{git_username}' on {repo_link_for_logging}.")
            else:
                _log.error("Could not extract GitHub username from UPSTREAM_REPO to use with GIT_TOKEN. Using unauthenticated URL.")
    else:
        _log.info(f"Using unauthenticated Git remote: {repo_link_for_logging}")

    try:
        repo = Repo()
        _log.info(f"Git repository found at current location: {repo.working_dir}")
        
        # Check if origin matches configured upstream
        if "origin" in repo.remotes:
            origin_url = repo.remotes.origin.url
            # Normalize URLs for comparison (e.g. removing .git suffix, http vs https if not using token)
            normalized_origin = origin_url.replace(".git", "").rstrip("/")
            normalized_upstream = actual_upstream_repo.replace(".git", "").rstrip("/")
            
            if config.GIT_TOKEN not in origin_url and config.GIT_TOKEN: # If token is used, URL must contain it
                 _log.warning(f"Origin URL '{normalized_origin}' does not match expected authenticated upstream. Attempting to set URL.")
                 repo.remotes.origin.set_url(actual_upstream_repo)
            elif normalized_origin != normalized_upstream and not config.GIT_TOKEN:
                 _log.warning(f"Origin URL '{normalized_origin}' does not match configured UPSTREAM_REPO '{normalized_upstream}'. Attempting to set URL.")
                 repo.remotes.origin.set_url(actual_upstream_repo)

        else: # No origin remote
            _log.info("No 'origin' remote found. Creating one.")
            repo.create_remote("origin", actual_upstream_repo)
        
        # Fetch from the configured branch
        _log.info(f"Fetching updates from remote 'origin', branch '{config.UPSTREAM_BRANCH}'...")
        repo.remotes.origin.fetch(config.UPSTREAM_BRANCH, progress=GitProgressPrinter()) # Added progress printer

    except git_exc.InvalidGitRepositoryError:
        _log.info(f"No existing Git repository found. Initializing a new one for {actual_upstream_repo}.")
        repo = Repo.init()
        origin = repo.create_remote("origin", actual_upstream_repo)
        origin.fetch(progress=GitProgressPrinter()) # Fetch all branches initially
        
        try:
            repo.create_head(config.UPSTREAM_BRANCH, origin.refs[config.UPSTREAM_BRANCH])
            repo.heads[config.UPSTREAM_BRANCH].set_tracking_branch(origin.refs[config.UPSTREAM_BRANCH])
            repo.heads[config.UPSTREAM_BRANCH].checkout(True)
            _log.info(f"Checked out branch '{config.UPSTREAM_BRANCH}' and set to track origin.")
        except IndexError: # Branch might not exist on remote
             _log.error(f"Specified UPSTREAM_BRANCH '{config.UPSTREAM_BRANCH}' not found on remote repository {actual_upstream_repo}. Please check branch name.")
             return # Cannot proceed without a valid branch
        except Exception as e_checkout:
            _log.error(f"Error during initial branch setup for '{config.UPSTREAM_BRANCH}': {e_checkout}", exc_info=True)
            return

    except git_exc.GitCommandError as e_git_cmd:
        _log.error(f"Git command error during setup: {e_git_cmd}", exc_info=True)
        return # Cannot proceed
    except Exception as e_other_init:
        _log.critical(f"Unexpected error during Git repository initialization: {e_other_init}", exc_info=True)
        return

    # At this point, repo object should be valid and origin set.
    try:
        _log.info(f"Attempting to pull updates for branch '{config.UPSTREAM_BRANCH}'...")
        repo.remotes.origin.pull(config.UPSTREAM_BRANCH, progress=GitProgressPrinter())
        _log.info(f"Successfully pulled updates for branch '{config.UPSTREAM_BRANCH}'.")
    except git_exc.GitCommandError as e_pull: # Common if local changes conflict
        _log.warning(f"Git pull failed for branch '{config.UPSTREAM_BRANCH}'. Error: {e_pull}. Attempting hard reset to FETCH_HEAD.")
        try:
            repo.git.reset("--hard", "FETCH_HEAD")
            _log.info("Successfully performed a hard reset to FETCH_HEAD after failed pull.")
        except git_exc.GitCommandError as e_reset:
            _log.error(f"Failed to hard reset to FETCH_HEAD. Error: {e_reset}. Manual intervention may be required.", exc_info=True)
            return # Avoid installing reqs if repo state is uncertain
    except Exception as e_pull_generic:
        _log.error(f"Unexpected error during git pull: {e_pull_generic}", exc_info=True)
        return

    # Install requirements after ensuring repo is up-to-date
    _log.info("Installing/updating Python package requirements from requirements.txt...")
    # Consider making the command/path configurable if not always in root
    install_req("pip3 install --no-cache-dir -r requirements.txt") 
    _log.info("Git repository setup and requirements installation process completed.")

# Helper class for git progress logging (optional, but nice for long operations)
import re # Ensure re is imported if not already for git_repo_setup
from git import RemoteProgress

class GitProgressPrinter(RemoteProgress):
    def update(self, op_code, cur_count, max_count=None, message=''):
        if message:
            # Clean up progress messages for cleaner logs
            cleaned_message = re.sub(r'\s*\(\d+/\d+\)\s*|\s*\d+%\s*', '', message).strip()
            if cleaned_message: # Log only if there's meaningful text after cleaning
                 _log.debug(f"Git operation progress: {cleaned_message} ({cur_count}" + (f"/{max_count}" if max_count else "") + ")")

# Call the setup function if this script is executed, or it can be called from app startup.
# if __name__ == "__main__": # Example of how it might be run
#    git_repo_setup()
