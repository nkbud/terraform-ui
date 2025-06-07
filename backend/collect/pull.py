#!/usr/bin/env python3
"""
Terraform File Collection Pipeline - Pull Stage

This script runs 'terraform init' and 'terraform state pull' on each repository
directory to fetch and save .tfstate files locally.

Usage:
    python pull.py [config.yaml]
    
Environment Variables:
    LOG_LEVEL - Set to DEBUG or INFO for different verbosity levels
    
Prerequisites:
    - terraform must be available in PATH
    - git must be available in PATH
    - Valid terraform configuration in each repository
"""

import os
import sys
import yaml
import subprocess
import logging
import platform
from pathlib import Path


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


def check_prerequisites():
    """Check if required tools are available in PATH."""
    logger = logging.getLogger(__name__)
    
    required_tools = ['terraform', 'git']
    missing_tools = []
    
    for tool in required_tools:
        try:
            subprocess.run([tool, '--version'], 
                         capture_output=True, 
                         check=True,
                         timeout=10)
            logger.debug(f"{tool} is available")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            missing_tools.append(tool)
    
    if missing_tools:
        logger.error(f"Missing required tools: {missing_tools}")
        logger.error("Please ensure terraform and git are installed and available in PATH")
        logger.error("See README.md for installation instructions")
        return False
    
    return True


def run_command(cmd, cwd=None, check=True, timeout=300):
    """Run a shell command and return the result."""
    logger = logging.getLogger(__name__)
    logger.debug(f"Running command: {' '.join(cmd)} in {cwd or 'current directory'}")
    
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=check,
            timeout=timeout
        )
        if result.stdout:
            logger.debug(f"Command output: {result.stdout.strip()}")
        return result
    except subprocess.CalledProcessError as e:
        logger.error(f"Command failed: {' '.join(cmd)}")
        logger.error(f"Error: {e.stderr}")
        raise
    except subprocess.TimeoutExpired:
        logger.error(f"Command timed out: {' '.join(cmd)}")
        raise


def has_terraform_files(repo_dir):
    """Check if repository has .tf files to process."""
    tf_files = []
    for root, dirs, files in os.walk(repo_dir):
        # Skip .git directory
        if '.git' in dirs:
            dirs.remove('.git')
        tf_files.extend([f for f in files if f.endswith('.tf')])
    
    return len(tf_files) > 0


def terraform_init(repo_dir):
    """Run terraform init in the repository directory."""
    logger = logging.getLogger(__name__)
    
    try:
        logger.debug(f"Running terraform init in {repo_dir}")
        run_command(['terraform', 'init', '-backend=false'], cwd=repo_dir)
        return True
    except Exception as e:
        logger.error(f"terraform init failed in {repo_dir}: {e}")
        return False


def terraform_state_pull(repo_dir):
    """Run terraform state pull and save to .tfstate file."""
    logger = logging.getLogger(__name__)
    
    try:
        logger.debug(f"Running terraform state pull in {repo_dir}")
        result = run_command(['terraform', 'state', 'pull'], cwd=repo_dir, check=False)
        
        # Save state to file even if command returns non-zero (might be empty state)
        tfstate_path = os.path.join(repo_dir, 'terraform.tfstate')
        with open(tfstate_path, 'w') as f:
            f.write(result.stdout)
        
        # Check if we got actual state data
        if result.stdout.strip():
            logger.debug(f"State data written to {tfstate_path}")
            return True
        else:
            logger.info(f"No state data available for {os.path.basename(repo_dir)}")
            return True  # This is not an error - some repos might not have remote state
            
    except Exception as e:
        logger.error(f"terraform state pull failed in {repo_dir}: {e}")
        return False


def process_repository(repo_dir):
    """Process a single repository: init and state pull."""
    logger = logging.getLogger(__name__)
    
    repo_name = os.path.basename(repo_dir)
    
    if not os.path.exists(repo_dir):
        logger.warning(f"Repository directory does not exist: {repo_dir}")
        return False
    
    if not has_terraform_files(repo_dir):
        logger.info(f"No .tf files found in {repo_name}, skipping")
        return True
    
    logger.info(f"Processing repository: {repo_name}")
    
    try:
        # Step 1: terraform init
        if not terraform_init(repo_dir):
            return False
        
        # Step 2: terraform state pull
        if not terraform_state_pull(repo_dir):
            return False
        
        logger.info(f"Successfully processed {repo_name}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to process repository {repo_name}: {e}")
        return False


def main():
    """Main function to orchestrate the terraform state pull process."""
    logger = setup_logging()
    
    # Get config file path from command line or use default
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.yaml'
    
    logger.info("Starting Terraform file collection - Pull stage")
    logger.info(f"Platform: {platform.system()}")
    
    # Check prerequisites
    if not check_prerequisites():
        sys.exit(1)
    
    # Load configuration (mainly for consistency, we might add pull-specific config later)
    config = load_config(config_path)
    
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
        logger.info("Pull stage completed with no repositories to process")
        return
    
    logger.info(f"Found {len(repo_dirs)} repositories to process")
    
    # Track results
    successful_pulls = []
    failed_pulls = []
    retry_queue = []
    
    # First pass: process all repositories
    for repo_dir in repo_dirs:
        if process_repository(repo_dir):
            successful_pulls.append(os.path.basename(repo_dir))
        else:
            failed_pulls.append(os.path.basename(repo_dir))
            retry_queue.append(repo_dir)
    
    # Retry failed pulls once
    if retry_queue:
        logger.info(f"Retrying {len(retry_queue)} failed repositories")
        retry_failed = []
        
        for repo_dir in retry_queue:
            repo_name = os.path.basename(repo_dir)
            logger.info(f"Retrying {repo_name}")
            if process_repository(repo_dir):
                successful_pulls.append(repo_name)
                failed_pulls.remove(repo_name)
            else:
                retry_failed.append(repo_name)
    
    # Summary
    logger.info(f"Pull stage completed:")
    logger.info(f"  Successful: {len(successful_pulls)}")
    logger.info(f"  Failed: {len(failed_pulls)}")
    
    if failed_pulls:
        logger.warning(f"Failed to process: {failed_pulls}")
        sys.exit(1)
    else:
        logger.info("All repositories processed successfully")


if __name__ == '__main__':
    main()