#!/usr/bin/env python3
"""
Terraform File Collection Pipeline - Override Stage

This script copies override .tf files from configurable source directories
into the root of each cloned repository directory.

Usage:
    python override.py [config.yaml]
    
Environment Variables:
    LOG_LEVEL - Set to DEBUG or INFO for different verbosity levels
"""

import os
import sys
import yaml
import logging
import shutil
import platform
from pathlib import Path
from glob import glob


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


def get_override_sources(config):
    """Get override source directories from config or use defaults."""
    default_sources = [
        './aws_deployment_overrides',
        './k8s/deployment/overrides'
    ]
    
    return config.get('override_sources', default_sources)


def find_tf_files(directory):
    """Find all .tf files in a directory."""
    logger = logging.getLogger(__name__)
    
    if not os.path.exists(directory):
        logger.debug(f"Override directory does not exist: {directory}")
        return []
    
    tf_files = glob(os.path.join(directory, '*.tf'))
    logger.debug(f"Found {len(tf_files)} .tf files in {directory}")
    
    return tf_files


def copy_override_files(source_dirs, repo_dir):
    """Copy override .tf files from source directories to repo directory."""
    logger = logging.getLogger(__name__)
    copied_files = []
    
    for source_dir in source_dirs:
        # Convert relative paths to absolute paths from script location
        if not os.path.isabs(source_dir):
            script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            source_dir = os.path.join(script_dir, source_dir)
        
        tf_files = find_tf_files(source_dir)
        
        for tf_file in tf_files:
            filename = os.path.basename(tf_file)
            dest_path = os.path.join(repo_dir, filename)
            
            try:
                shutil.copy2(tf_file, dest_path)
                logger.debug(f"Copied {tf_file} to {dest_path}")
                copied_files.append(filename)
            except Exception as e:
                logger.error(f"Failed to copy {tf_file} to {dest_path}: {e}")
    
    return copied_files


def process_repository(repo_dir, override_sources):
    """Process a single repository by copying override files."""
    logger = logging.getLogger(__name__)
    
    repo_name = os.path.basename(repo_dir)
    
    if not os.path.exists(repo_dir):
        logger.warning(f"Repository directory does not exist: {repo_dir}")
        return False
    
    logger.info(f"Processing repository: {repo_name}")
    
    try:
        copied_files = copy_override_files(override_sources, repo_dir)
        
        if copied_files:
            logger.info(f"Copied {len(copied_files)} override files to {repo_name}: {copied_files}")
        else:
            logger.info(f"No override files found to copy to {repo_name}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to process repository {repo_name}: {e}")
        return False


def main():
    """Main function to orchestrate the override process."""
    logger = setup_logging()
    
    # Get config file path from command line or use default
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.yaml'
    
    logger.info("Starting Terraform file collection - Override stage")
    logger.info(f"Platform: {platform.system()}")
    
    # Load configuration
    config = load_config(config_path)
    override_sources = get_override_sources(config)
    
    logger.info(f"Override sources: {override_sources}")
    
    # Find repos directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repos_base_dir = os.path.join(script_dir, 'repos')
    
    if not os.path.exists(repos_base_dir):
        logger.error(f"Repos directory does not exist: {repos_base_dir}")
        logger.error("Please run clone.py first to clone repositories")
        sys.exit(1)
    
    # Find all repository directories
    repo_dirs = [
        os.path.join(repos_base_dir, d) 
        for d in os.listdir(repos_base_dir) 
        if os.path.isdir(os.path.join(repos_base_dir, d)) and not d.startswith('.')
    ]
    
    if not repo_dirs:
        logger.warning(f"No repository directories found in {repos_base_dir}")
        logger.info("Override stage completed with no repositories to process")
        return
    
    logger.info(f"Found {len(repo_dirs)} repositories to process")
    
    # Track results
    successful_overrides = []
    failed_overrides = []
    retry_queue = []
    
    # First pass: process all repositories
    for repo_dir in repo_dirs:
        if process_repository(repo_dir, override_sources):
            successful_overrides.append(os.path.basename(repo_dir))
        else:
            failed_overrides.append(os.path.basename(repo_dir))
            retry_queue.append(repo_dir)
    
    # Retry failed overrides once
    if retry_queue:
        logger.info(f"Retrying {len(retry_queue)} failed repositories")
        retry_failed = []
        
        for repo_dir in retry_queue:
            repo_name = os.path.basename(repo_dir)
            logger.info(f"Retrying {repo_name}")
            if process_repository(repo_dir, override_sources):
                successful_overrides.append(repo_name)
                failed_overrides.remove(repo_name)
            else:
                retry_failed.append(repo_name)
    
    # Summary
    logger.info(f"Override stage completed:")
    logger.info(f"  Successful: {len(successful_overrides)}")
    logger.info(f"  Failed: {len(failed_overrides)}")
    
    if failed_overrides:
        logger.warning(f"Failed to process: {failed_overrides}")
        sys.exit(1)
    else:
        logger.info("All repositories processed successfully")


if __name__ == '__main__':
    main()