#!/usr/bin/env python3
"""
Terraform File Collection Pipeline - Clone Stage

This script performs shallow clones of Git repositories and checks out only .tf files
using sparse checkout. Each repository is cloned into its own directory under repos/.

Usage:
    python clone.py [config.yaml]
    
Environment Variables:
    LOG_LEVEL - Set to DEBUG or INFO for different verbosity levels
"""

import os
import sys
import yaml
import subprocess
import logging
import time
import platform
from pathlib import Path
from urllib.parse import urlparse


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


def extract_repo_name(git_url):
    """Extract repository name from Git SSH URL."""
    # Handle git@github.com:org/repo.git format
    if git_url.startswith('git@'):
        # Extract the part after the colon
        path_part = git_url.split(':')[1]
        # Remove .git suffix if present
        if path_part.endswith('.git'):
            path_part = path_part[:-4]
        # Return just the repo name (last part after /)
        return path_part.split('/')[-1]
    else:
        logging.error(f"Unsupported URL format: {git_url}. Only SSH URLs are supported.")
        return None


def run_command(cmd, cwd=None, check=True):
    """Run a shell command and return the result."""
    logger = logging.getLogger(__name__)
    logger.debug(f"Running command: {' '.join(cmd)} in {cwd or 'current directory'}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check
        )
        if result.stdout:
            logger.debug(f"Command output: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {' '.join(cmd)}")
        logger.error(f"Error: {e.stderr}")
        raise


def setup_sparse_checkout(repo_dir):
    """Configure sparse checkout to only include .tf files."""
    logger = logging.getLogger(__name__)
    
    try:
        # Enable sparse checkout
        run_command(['git', 'config', 'core.sparseCheckout', 'true'], cwd=repo_dir)
        
        # Create sparse-checkout file
        sparse_checkout_path = os.path.join(repo_dir, '.git', 'info', 'sparse-checkout')
        os.makedirs(os.path.dirname(sparse_checkout_path), exist_ok=True)
        
        with open(sparse_checkout_path, 'w') as f:
            f.write('*.tf\n')
            f.write('**/*.tf\n')
        
        # Apply sparse checkout
        run_command(['git', 'read-tree', '-m', '-u', 'HEAD'], cwd=repo_dir)
        
        logger.debug(f"Sparse checkout configured for {repo_dir}")
        
    except Exception as e:
        logger.error(f"Failed to setup sparse checkout: {e}")
        raise


def clone_repository(git_url, repos_base_dir, rate_limit=0.1):
    """Clone a single repository with shallow clone and sparse checkout."""
    logger = logging.getLogger(__name__)
    
    repo_name = extract_repo_name(git_url)
    if not repo_name:
        return False
    
    repo_dir = os.path.join(repos_base_dir, repo_name)
    
    # Remove existing directory if it exists
    if os.path.exists(repo_dir):
        logger.info(f"Removing existing directory: {repo_dir}")
        import shutil
        shutil.rmtree(repo_dir)
    
    try:
        logger.info(f"Cloning {git_url} to {repo_dir}")
        
        # Shallow clone with depth 1
        run_command([
            'git', 'clone',
            '--depth', '1',
            '--no-checkout',
            git_url,
            repo_dir
        ])
        
        # Setup sparse checkout for .tf files only
        setup_sparse_checkout(repo_dir)
        
        logger.info(f"Successfully cloned {repo_name}")
        
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
    
    # Ensure repos directory exists
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repos_base_dir = os.path.join(script_dir, 'repos')
    os.makedirs(repos_base_dir, exist_ok=True)
    
    # Track results
    successful_clones = []
    failed_clones = []
    retry_queue = []
    
    # First pass: clone all repositories
    for repo_url in repositories:
        if clone_repository(repo_url, repos_base_dir, rate_limit):
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
            if clone_repository(repo_url, repos_base_dir, rate_limit):
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