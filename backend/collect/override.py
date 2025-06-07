#!/usr/bin/env python3
"""
Terraform File Collection Pipeline - Override Stage

This script copies override .tf files from fixed directories into each cloned 
repository directory, replicating the work that the CI/CD pipeline normally does.

Usage:
    python override.py [config.yaml]
    
Environment Variables:
    LOG_LEVEL - Set to DEBUG or INFO for different verbosity levels
"""

import os
import sys
import logging
import shutil
import platform
from glob import glob


def setup_logging():
    """Configure logging based on LOG_LEVEL environment variable."""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def copy_tf_files(source_dir, dest_dir):
    """Copy all .tf files from source directory to destination directory."""
    logger = logging.getLogger(__name__)
    copied_files = []
    
    if not os.path.exists(source_dir):
        logger.debug(f"Source directory does not exist: {source_dir}")
        return copied_files
    
    tf_files = glob(os.path.join(source_dir, '*.tf'))
    
    for tf_file in tf_files:
        filename = os.path.basename(tf_file)
        dest_path = os.path.join(dest_dir, filename)
        
        try:
            shutil.copy2(tf_file, dest_path)
            logger.debug(f"Copied {tf_file} to {dest_path}")
            copied_files.append(filename)
        except Exception as e:
            logger.error(f"Failed to copy {tf_file} to {dest_path}: {e}")
    
    return copied_files


def process_repository(repo_dir):
    """Process a single repository by copying override files."""
    logger = logging.getLogger(__name__)
    
    repo_name = os.path.basename(repo_dir)
    
    if not os.path.exists(repo_dir):
        logger.warning(f"Repository directory does not exist: {repo_dir}")
        return False
    
    logger.info(f"Processing repository: {repo_name}")
    
    try:
        # Get project root directory (two levels up from backend/collect)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Copy from aws_deployment_overrides
        aws_overrides_dir = os.path.join(project_root, 'aws_deployment_overrides')
        aws_copied = copy_tf_files(aws_overrides_dir, repo_dir)
        
        # Copy from k8s_deployment_overrides  
        k8s_overrides_dir = os.path.join(project_root, 'k8s_deployment_overrides')
        k8s_copied = copy_tf_files(k8s_overrides_dir, repo_dir)
        
        total_copied = len(aws_copied) + len(k8s_copied)
        
        if total_copied > 0:
            logger.info(f"Copied {total_copied} override files to {repo_name}")
            if aws_copied:
                logger.debug(f"AWS overrides: {aws_copied}")
            if k8s_copied:
                logger.debug(f"K8s overrides: {k8s_copied}")
        else:
            logger.info(f"No override files found to copy to {repo_name}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to process repository {repo_name}: {e}")
        return False


def main():
    """Main function to orchestrate the override process."""
    logger = setup_logging()
    
    logger.info("Starting Terraform file collection - Override stage")
    logger.info(f"Platform: {platform.system()}")
    
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
    
    # Process all repositories
    for repo_dir in repo_dirs:
        if process_repository(repo_dir):
            successful_overrides.append(os.path.basename(repo_dir))
        else:
            failed_overrides.append(os.path.basename(repo_dir))
    
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