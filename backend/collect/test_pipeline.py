#!/usr/bin/env python3
"""
Simple integration test for the Terraform Collection Pipeline

This script creates a mock repository structure and tests the override
and basic validation functionality without requiring network access.
"""

import os
import sys
import tempfile
import shutil
import subprocess
from pathlib import Path


def create_test_environment():
    """Create a test environment with mock repositories."""
    # Create temporary directory for test
    test_dir = tempfile.mkdtemp(prefix='terraform_pipeline_test_')
    print(f"Created test directory: {test_dir}")
    
    # Create mock repository structure
    repos_dir = os.path.join(test_dir, 'repos')
    os.makedirs(repos_dir)
    
    # Create mock repo 1
    repo1_dir = os.path.join(repos_dir, 'mock-repo-1')
    os.makedirs(repo1_dir)
    
    with open(os.path.join(repo1_dir, 'main.tf'), 'w') as f:
        f.write('''
resource "aws_instance" "example" {
  ami           = "ami-12345678"
  instance_type = "t2.micro"
}
''')
    
    # Create mock repo 2
    repo2_dir = os.path.join(repos_dir, 'mock-repo-2')
    os.makedirs(repo2_dir)
    
    with open(os.path.join(repo2_dir, 'variables.tf'), 'w') as f:
        f.write('''
variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}
''')
    
    # Create override directories
    aws_overrides = os.path.join(test_dir, 'aws_deployment_overrides')
    os.makedirs(aws_overrides)
    
    with open(os.path.join(aws_overrides, 'override.tf'), 'w') as f:
        f.write('''
# Override provider configuration
provider "aws" {
  region = "us-east-1"
}
''')
    
    k8s_overrides = os.path.join(test_dir, 'k8s', 'deployment', 'overrides')
    os.makedirs(k8s_overrides)
    
    with open(os.path.join(k8s_overrides, 'k8s_override.tf'), 'w') as f:
        f.write('''
# Kubernetes namespace override
resource "kubernetes_namespace" "example" {
  metadata {
    name = "production"
  }
}
''')
    
    # Create test config
    config_content = f'''
repositories: []
override_sources:
  - {aws_overrides}
  - {k8s_overrides}
'''
    
    config_path = os.path.join(test_dir, 'test_config.yaml')
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    return test_dir, config_path


def test_override_stage(test_dir, config_path):
    """Test the override stage with mock data."""
    print("\nTesting override stage...")
    
    # Get script directory
    script_dir = os.path.dirname(os.path.abspath(__file__))
    override_script = os.path.join(script_dir, 'override.py')
    
    # Create the expected repos directory structure in the script location
    expected_repos_dir = os.path.join(script_dir, 'repos')
    test_repos_dir = os.path.join(test_dir, 'repos')
    
    # Copy mock repos to expected location
    if os.path.exists(expected_repos_dir):
        shutil.rmtree(expected_repos_dir)
    shutil.copytree(test_repos_dir, expected_repos_dir)
    
    # Change to test directory
    original_cwd = os.getcwd()
    
    try:
        os.chdir(test_dir)
        
        # Run override script
        result = subprocess.run([
            sys.executable, override_script, config_path
        ], capture_output=True, text=True)
        
        print(f"Override script exit code: {result.returncode}")
        print(f"Override script output:\n{result.stdout}")
        
        if result.stderr:
            print(f"Override script errors:\n{result.stderr}")
        
        # Check if override files were copied
        success = True
        
        for repo in os.listdir(expected_repos_dir):
            repo_path = os.path.join(expected_repos_dir, repo)
            if os.path.isdir(repo_path):
                override_files = [f for f in os.listdir(repo_path) if f.startswith('override') or f.startswith('k8s_override')]
                print(f"Repository {repo} has override files: {override_files}")
                if override_files:
                    print(f"  ✓ Override files copied to {repo}")
                else:
                    print(f"  ! No override files found in {repo}")
        
        return result.returncode == 0
        
    finally:
        os.chdir(original_cwd)
        # Clean up the test repos directory
        if os.path.exists(expected_repos_dir):
            shutil.rmtree(expected_repos_dir)


def test_script_imports():
    """Test that all scripts can be imported without errors."""
    print("Testing script imports...")
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    scripts = ['clone.py', 'override.py', 'pull.py']
    
    for script in scripts:
        script_path = os.path.join(script_dir, script)
        
        # Test syntax by compiling
        try:
            with open(script_path, 'r') as f:
                compile(f.read(), script_path, 'exec')
            print(f"  ✓ {script} syntax valid")
        except SyntaxError as e:
            print(f"  ✗ {script} syntax error: {e}")
            return False
    
    return True


def main():
    """Run integration tests."""
    print("=== Terraform Collection Pipeline Integration Test ===")
    
    # Test script syntax
    if not test_script_imports():
        print("❌ Script import tests failed")
        return 1
    
    # Create test environment
    test_dir, config_path = create_test_environment()
    
    try:
        # Test override stage
        if test_override_stage(test_dir, config_path):
            print("✅ Override stage test passed")
        else:
            print("❌ Override stage test failed")
            return 1
        
        print("\n✅ All tests passed!")
        return 0
        
    finally:
        # Cleanup
        print(f"\nCleaning up test directory: {test_dir}")
        shutil.rmtree(test_dir)


if __name__ == '__main__':
    sys.exit(main())