#!/usr/bin/env python3
"""
Terraform File Collection Pipeline - Repository Discovery

This script discovers repositories from Bitbucket Server and Bitbucket Cloud
using project/workspace names and regex patterns, then generates a repos.yaml
file with SSH clone URLs for use by the clone.py script.

Usage:
    python repos.py [config.yaml]
    
Configuration format:
    bitbucket:
      server:
        url: "https://bitbucket.example.com"
        username: "your-username"
        password: "your-app-password"
        projects:
          - name: "PROJECT_KEY"
            repo_pattern: "terraform-.*"
      cloud:
        username: "your-username" 
        app_password: "your-app-password"
        workspaces:
          - name: "workspace-name"
            repo_pattern: "terraform-.*"

Environment Variables:
    LOG_LEVEL - Set to DEBUG or INFO for different verbosity levels
    BITBUCKET_SERVER_PASSWORD - Password for Bitbucket Server
    BITBUCKET_CLOUD_APP_PASSWORD - App password for Bitbucket Cloud
"""

import os
import sys
import yaml
import logging
import re
import requests
from urllib.parse import urljoin
from requests.auth import HTTPBasicAuth


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


class BitbucketServerClient:
    """Client for Bitbucket Server API."""
    
    def __init__(self, base_url, username, password):
        self.base_url = base_url.rstrip('/')
        self.auth = HTTPBasicAuth(username, password)
        self.session = requests.Session()
        self.session.auth = self.auth
        
    def get_project_repos(self, project_key, repo_pattern=None):
        """Get repositories from a Bitbucket Server project."""
        logger = logging.getLogger(__name__)
        repos = []
        
        url = f"{self.base_url}/rest/api/1.0/projects/{project_key}/repos"
        
        try:
            logger.info(f"Fetching repositories from project: {project_key}")
            
            start = 0
            limit = 100
            
            while True:
                params = {'start': start, 'limit': limit}
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                for repo in data['values']:
                    repo_name = repo['name']
                    
                    # Apply regex filter if provided
                    if repo_pattern and not re.match(repo_pattern, repo_name):
                        logger.debug(f"Skipping {repo_name} - doesn't match pattern {repo_pattern}")
                        continue
                    
                    # Get SSH clone URL
                    ssh_url = None
                    for clone_link in repo['links']['clone']:
                        if clone_link['name'] == 'ssh':
                            ssh_url = clone_link['href']
                            break
                    
                    if ssh_url:
                        repos.append(ssh_url)
                        logger.debug(f"Added repository: {ssh_url}")
                    else:
                        logger.warning(f"No SSH clone URL found for {repo_name}")
                
                # Check if there are more pages
                if data['isLastPage']:
                    break
                    
                start = data['nextPageStart']
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching repositories from project {project_key}: {e}")
            
        return repos


class BitbucketCloudClient:
    """Client for Bitbucket Cloud API."""
    
    def __init__(self, username, app_password):
        self.auth = HTTPBasicAuth(username, app_password)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.base_url = "https://api.bitbucket.org/2.0"
        
    def get_workspace_repos(self, workspace_name, repo_pattern=None):
        """Get repositories from a Bitbucket Cloud workspace."""
        logger = logging.getLogger(__name__)
        repos = []
        
        url = f"{self.base_url}/repositories/{workspace_name}"
        
        try:
            logger.info(f"Fetching repositories from workspace: {workspace_name}")
            
            page = 1
            
            while True:
                params = {'page': page, 'pagelen': 100}
                response = self.session.get(url, params=params)
                response.raise_for_status()
                
                data = response.json()
                
                for repo in data['values']:
                    repo_name = repo['name']
                    
                    # Apply regex filter if provided
                    if repo_pattern and not re.match(repo_pattern, repo_name):
                        logger.debug(f"Skipping {repo_name} - doesn't match pattern {repo_pattern}")
                        continue
                    
                    # Get SSH clone URL
                    ssh_url = None
                    if 'links' in repo and 'clone' in repo['links']:
                        for clone_link in repo['links']['clone']:
                            if clone_link['name'] == 'ssh':
                                ssh_url = clone_link['href']
                                break
                    
                    if ssh_url:
                        repos.append(ssh_url)
                        logger.debug(f"Added repository: {ssh_url}")
                    else:
                        logger.warning(f"No SSH clone URL found for {repo_name}")
                
                # Check if there are more pages
                if 'next' not in data:
                    break
                    
                page += 1
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching repositories from workspace {workspace_name}: {e}")
            
        return repos


def discover_repositories(config):
    """Discover repositories from configured Bitbucket instances."""
    logger = logging.getLogger(__name__)
    all_repos = []
    
    bitbucket_config = config.get('bitbucket', {})
    
    # Process Bitbucket Server instances
    server_config = bitbucket_config.get('server')
    if server_config:
        logger.info("Processing Bitbucket Server repositories")
        
        server_url = server_config['url']
        username = server_config['username']
        password = server_config.get('password') or os.getenv('BITBUCKET_SERVER_PASSWORD')
        
        if not password:
            logger.error("Bitbucket Server password not found in config or BITBUCKET_SERVER_PASSWORD env var")
            return []
            
        client = BitbucketServerClient(server_url, username, password)
        
        for project in server_config.get('projects', []):
            project_name = project['name']
            repo_pattern = project.get('repo_pattern')
            
            repos = client.get_project_repos(project_name, repo_pattern)
            all_repos.extend(repos)
            logger.info(f"Found {len(repos)} repositories in project {project_name}")
    
    # Process Bitbucket Cloud instances
    cloud_config = bitbucket_config.get('cloud')
    if cloud_config:
        logger.info("Processing Bitbucket Cloud repositories")
        
        username = cloud_config['username']
        app_password = cloud_config.get('app_password') or os.getenv('BITBUCKET_CLOUD_APP_PASSWORD')
        
        if not app_password:
            logger.error("Bitbucket Cloud app password not found in config or BITBUCKET_CLOUD_APP_PASSWORD env var")
            return []
            
        client = BitbucketCloudClient(username, app_password)
        
        for workspace in cloud_config.get('workspaces', []):
            workspace_name = workspace['name']
            repo_pattern = workspace.get('repo_pattern')
            
            repos = client.get_workspace_repos(workspace_name, repo_pattern)
            all_repos.extend(repos)
            logger.info(f"Found {len(repos)} repositories in workspace {workspace_name}")
    
    return all_repos


def write_repos_yaml(repos, output_path='repos.yaml'):
    """Write discovered repositories to a YAML file."""
    logger = logging.getLogger(__name__)
    
    output_config = {
        'repositories': repos
    }
    
    try:
        with open(output_path, 'w') as f:
            yaml.dump(output_config, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"Successfully wrote {len(repos)} repositories to {output_path}")
        
    except Exception as e:
        logger.error(f"Error writing repos to {output_path}: {e}")
        sys.exit(1)


def main():
    """Main function to discover repositories and generate repos.yaml."""
    logger = setup_logging()
    
    # Get config file path from command line or use default
    config_path = sys.argv[1] if len(sys.argv) > 1 else 'config.yaml'
    
    logger.info("Starting repository discovery")
    
    # Load configuration
    config = load_config(config_path)
    
    if 'bitbucket' not in config:
        logger.error("No 'bitbucket' section found in config")
        sys.exit(1)
    
    # Discover repositories
    repos = discover_repositories(config)
    
    if not repos:
        logger.warning("No repositories found")
        sys.exit(1)
    
    # Remove duplicates while preserving order
    unique_repos = list(dict.fromkeys(repos))
    
    logger.info(f"Discovered {len(unique_repos)} unique repositories")
    
    # Write to repos.yaml
    script_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(script_dir, 'repos.yaml')
    write_repos_yaml(unique_repos, output_path)
    
    logger.info("Repository discovery completed successfully")


if __name__ == '__main__':
    main()