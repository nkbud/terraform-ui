#!/usr/bin/env python3
"""
Terraform File Collection Pipeline - Clone Stage

This script performs sparse clones of Git repositories and checks out only .tf files.

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


def get_repo_path(base_dir, project, repo):
    """Get the path where repository should be cloned."""
    return os.path.join(base_dir, "repos", project, repo)


def clone_repository(git_url, base_dir, rate_limit=0.1):
    """Clone a single repository with sparse checkout for .tf files."""
    logger = logging.getLogger(__name__)
    
    project, repo = extract_repo_info(git_url)
    if not project or not repo:
        return False
    
    repo_path = get_repo_path(base_dir, project, repo)
    
    try:
        logger.info(f"Cloning {git_url}")
        
        # Create directory if it doesn't exist
        os.makedirs(repo_path, exist_ok=True)
        
        # Clone with sparse checkout enabled from the start
        git_repo = git.Repo.clone_from(
            git_url,
            repo_path,
            no_checkout=True,
            depth=1,
            filter='tree:0'
        )
        
        # Configure sparse checkout for .tf files only
        logger.info(f"Setting sparse checkout for {project}/{repo} to *.tf files")
        git_repo.git.sparse_checkout('set', '--no-cone', '*.tf', '**/*.tf')
        
        # Checkout the files
        git_repo.git.checkout()
        
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
    
    # Get base directory for cloning
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Track results
    successful_clones = []
    failed_clones = []
    retry_queue = []
    
    # First pass: clone all repositories
    for repo_url in repositories:
        if clone_repository(repo_url, script_dir, rate_limit):
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
            if clone_repository(repo_url, script_dir, rate_limit):
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