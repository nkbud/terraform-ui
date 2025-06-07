#!/usr/bin/env python3
"""
Terraform File Collection Pipeline - Clone Stage

This script performs sparse clones of Git repositories and checks out only .tf files
using the GitCliClient implementation with efficient sparse checkout.

Usage:
    python clone.py [config.yaml]
    
Environment Variables:
    LOG_LEVEL - Set to DEBUG or INFO for different verbosity levels
"""

import os
import sys
import yaml
import logging
import time
import platform
import git


def setup_logging():
    """Configure logging based on LOG_LEVEL environment variable."""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def load_config(config_path='config.yaml'):
    """Load configuration from YAML file."""
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        logging.error(f"Configuration file {config_path} not found")
        sys.exit(1)
    except yaml.YAMLError as e:
        logging.error(f"Error parsing YAML config: {e}")
        sys.exit(1)


class GitCliClient:
    def __init__(self, clone_location, clone_dir_name="repos"):
        self.clone_dir_name = clone_dir_name
        self.clone_location = os.path.join(clone_location, self.clone_dir_name)
        if not os.path.exists(self.clone_location):
            os.makedirs(self.clone_location)

    def clone_repo(self, project: str, repo: str, ssh_ref: str) -> None:
        self.create_repo_path(project, repo)
        try:
            print(f"Cloning repository ssh ref '{project}/{repo}: {ssh_ref}'")
            git.Repo.clone_from(
                ssh_ref,
                self.get_repo_path(project, repo),
                no_checkout=True,
                depth=1,
                filter='tree:0'
            )
        except Exception as e:
            print(f"Error cloning repository '{project}/{repo}': {e}")

    def update_repo(self, project: str, repo: str) -> None:
        try:
            print(f"Updating existing repository '{project}/{repo}'")
            git_repo = git.Repo(self.get_repo_path(project, repo))
            git_repo.git.fetch('--depth', '1', '--filter', 'tree:0')
            default_branch = git_repo.git.symbolic_ref('refs/remotes/origin/HEAD').split('/')[-1]
            git_repo.git.update_ref(f'refs/heads/{default_branch}', f'origin/{default_branch}')
            git_repo.git.checkout(default_branch)
            git_repo.git.reset('--hard', 'HEAD')
        except Exception as e:
            print(f"Error updating repository '{project}/{repo}': {e}")

    def set_sparse_checkout(self, project: str, repo: str, repo_files: list[str]) -> None:
        repo_path = self.get_repo_path(project, repo)
        if not os.path.exists(repo_path):
            return
        try:
            git_repo = git.Repo(repo_path)
            if repo_files:
                print(f"Setting sparse checkout for '{project}/{repo}' to {repo_files}")
                git_repo.git.sparse_checkout('set', '--no-cone', *repo_files)
            else:
                print(f"Setting sparse checkout for '{project}/{repo}' to empty")
                git_repo.git.sparse_checkout('set', '--no-cone', '--sparse-index', '')
                git_repo.git.checkout()
        except Exception as e:
            print(f"Error setting sparse checkout for '{project}/{repo}': {e}")

    def disable_sparse_checkout(self, project: str, repo: str) -> None:
        repo_path = self.get_repo_path(project, repo)
        if not os.path.exists(repo_path):
            return
        try:
            git_repo = git.Repo(repo_path)
            print(f"Disabling sparse checkout for '{project}/{repo}'")
            git_repo.git.sparse_checkout('disable')
            git_repo.git.checkout()
        except Exception as e:
            print(f"Error disabling sparse checkout for '{project}/{repo}': {e}")

    def get_repo_path(self, project: str, repo: str) -> str:
        return os.path.join(self.clone_location, project, repo)

    def create_repo_path(self, project: str, repo: str) -> None:
        repo_path = self.get_repo_path(project, repo)
        if not os.path.exists(repo_path):
            os.makedirs(repo_path)


def extract_repo_info(git_url):
    """Extract project and repository name from Git SSH URL."""
    # Handle git@github.com:org/repo.git format
    if git_url.startswith('git@'):
        # Extract the part after the colon
        path_part = git_url.split(':')[1]
        # Remove .git suffix if present
        if path_part.endswith('.git'):
            path_part = path_part[:-4]
        # Split into project and repo
        parts = path_part.split('/')
        if len(parts) >= 2:
            project = parts[0]
            repo = parts[1]
            return project, repo
        else:
            logging.error(f"Invalid URL format: {git_url}")
            return None, None
    else:
        logging.error(f"Unsupported URL format: {git_url}. Only SSH URLs are supported.")
        return None, None


def clone_repository(git_client, git_url, rate_limit=0.1):
    """Clone a single repository with sparse checkout for .tf files."""
    logger = logging.getLogger(__name__)
    
    project, repo = extract_repo_info(git_url)
    if not project or not repo:
        return False
    
    try:
        logger.info(f"Cloning {git_url}")
        
        # Clone the repository
        git_client.clone_repo(project, repo, git_url)
        
        # Set sparse checkout for .tf files only
        tf_patterns = ['*.tf', '**/*.tf']
        git_client.set_sparse_checkout(project, repo, tf_patterns)
        
        logger.info(f"Successfully cloned {project}/{repo} with sparse checkout for .tf files")
        
        # Rate limiting
        if rate_limit > 0:
            logger.debug(f"Rate limiting: waiting {rate_limit} seconds")
            time.sleep(rate_limit)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to clone {git_url}: {e}")
        return False


def main():
    """Main function to orchestrate the cloning process."""
    logger = setup_logging()
    
    # Get config file path from command line or use default
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.yaml'
    
    logger.info("Starting Terraform file collection - Clone stage")
    logger.info(f"Platform: {platform.system()}")
    
    # Load configuration
    config = load_config(config_path)
    
    if 'repositories' not in config:
        logger.error("No 'repositories' section found in config")
        sys.exit(1)
    
    repositories = config['repositories']
    rate_limit = config.get('rate_limit', 0.1)
    
    logger.info(f"Found {len(repositories)} repositories to clone")
    
    # Initialize Git client
    script_dir = os.path.dirname(os.path.abspath(__file__))
    git_client = GitCliClient(script_dir)
    
    # Track results
    successful_clones = []
    failed_clones = []
    retry_queue = []
    
    # First pass: clone all repositories
    for repo_url in repositories:
        if clone_repository(git_client, repo_url, rate_limit):
            successful_clones.append(repo_url)
        else:
            failed_clones.append(repo_url)
            retry_queue.append(repo_url)
    
    # Retry failed clones once
    if retry_queue:
        logger.info(f"Retrying {len(retry_queue)} failed repositories")
        retry_failed = []
        
        for repo_url in retry_queue:
            logger.info(f"Retrying {repo_url}")
            if clone_repository(git_client, repo_url, rate_limit):
                successful_clones.append(repo_url)
                failed_clones.remove(repo_url)
            else:
                retry_failed.append(repo_url)
    
    # Summary
    logger.info(f"Clone stage completed:")
    logger.info(f"  Successful: {len(successful_clones)}")
    logger.info(f"  Failed: {len(failed_clones)}")
    
    if failed_clones:
        logger.warning(f"Failed to clone: {failed_clones}")
        sys.exit(1)
    else:
        logger.info("All repositories cloned successfully")


if __name__ == '__main__':
    main()