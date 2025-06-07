#!/usr/bin/env python3
"""
Terraform File Collection Pipeline - Main Orchestrator

This script orchestrates the complete pipeline by running clone, override, and pull stages in sequence.

Usage:
    python main.py [config.yaml]
    
Environment Variables:
    LOG_LEVEL - Set to DEBUG or INFO for different verbosity levels
"""

import os
import sys
import logging
import subprocess


def setup_logging():
    """Configure logging based on LOG_LEVEL environment variable."""
    log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
    logging.basicConfig(
        level=getattr(logging, log_level, logging.INFO),
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger(__name__)


def run_stage(stage_script, config_path):
    """Run a pipeline stage script."""
    logger = logging.getLogger(__name__)
    
    script_path = os.path.join(os.path.dirname(__file__), stage_script)
    cmd = [sys.executable, script_path, config_path]
    
    logger.info(f"Running {stage_script}...")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            logger.info(f"{stage_script} output: {result.stdout.strip()}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"{stage_script} failed: {e}")
        if e.stderr:
            logger.error(f"{stage_script} stderr: {e.stderr}")
        return False


def main():
    """Main function to orchestrate the complete pipeline."""
    logger = setup_logging()
    
    # Get config file path from command line or use default
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.yaml'
    
    logger.info("Starting Terraform File Collection Pipeline")
    
    # Pipeline stages in order
    stages = [
        'clone.py',
        'override.py', 
        'pull.py'
    ]
    
    for stage in stages:
        if not run_stage(stage, config_path):
            logger.error(f"Pipeline failed at stage: {stage}")
            sys.exit(1)
    
    logger.info("Terraform File Collection Pipeline completed successfully")


if __name__ == '__main__':
    main()