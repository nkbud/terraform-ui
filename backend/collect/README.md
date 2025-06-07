# Terraform File Collection Pipeline

This directory contains the backend pipeline for collecting, overriding, and pulling Terraform `.tf` and `.tfstate` files from a list of Git repositories. This is the first stage of the data pipeline that enables later processes to parse and index Terraform data for search and presentation layers.

## Overview

The collection pipeline consists of four main components:

1. **Repository Discovery** (`repos.py`) - Discover repositories from Bitbucket and generate repos.yaml
2. **Clone Stage** (`clone.py`) - Shallow clone repositories and checkout only `.tf` files
3. **Override Stage** (`override.py`) - Copy override `.tf` files into cloned repositories  
4. **Pull Stage** (`pull.py`) - Run `terraform init` and `terraform state pull` to fetch state files

## Prerequisites

### System Requirements

- Python 3.6+
- Git (available in PATH)
- Terraform (available in PATH) - required for pull stage
- SSH keys configured for Git repository access

### Platform Support

The pipeline supports:
- Linux
- macOS  
- Windows

### Installation

#### Git Installation

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install git
```

**macOS:**
```bash
# Using Homebrew
brew install git

# Or install from https://git-scm.com/download/mac
```

**Windows:**
Download and install from https://git-scm.com/download/win

#### Terraform Installation

**Ubuntu/Debian:**
```bash
# Add HashiCorp GPG key and repository
wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | sudo tee /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform
```

**macOS:**
```bash
# Using Homebrew
brew tap hashicorp/tap
brew install hashicorp/tap/terraform
```

**Windows:**
Download from https://www.terraform.io/downloads or use Chocolatey:
```powershell
choco install terraform
```

#### Python Dependencies

```bash
pip install pyyaml requests
```

## Configuration

Create a `config.yaml` file in the project root with the following structure:

```yaml
# List of Git repositories to collect .tf files from
# Only SSH URLs are supported (git@github.com:org/repo.git format)
repositories:
  - git@github.com:hashicorp/terraform-aws-modules.git
  - git@github.com:terraform-aws-modules/terraform-aws-vpc.git
  - git@github.com:terraform-aws-modules/terraform-aws-security-group.git

# Optional: Configure rate limiting between clones (seconds)
rate_limit: 0.1

# Configuration for automatic repository discovery from Bitbucket
# Run 'python repos.py' to generate repos.yaml from these settings
bitbucket:
  server:
    url: "https://bitbucket.example.com"
    username: "your-username"
    password: "your-app-password"  # or set BITBUCKET_SERVER_PASSWORD env var
    projects:
      - name: "TERRAFORM"
        repo_pattern: "terraform-.*"
      - name: "INFRA" 
        repo_pattern: ".*-terraform"
  cloud:
    username: "your-username"
    app_password: "your-app-password"  # or set BITBUCKET_CLOUD_APP_PASSWORD env var
    workspaces:
      - name: "my-workspace"
        repo_pattern: "terraform-.*"
      - name: "infra-workspace"
        repo_pattern: ".*-infrastructure"
```

### Configuration Options

- **repositories** (required): List of Git SSH URLs to clone
- **rate_limit** (optional): Seconds to wait between repository clones (default: 0.1)
- **bitbucket** (optional): Configuration for automatic repository discovery from Bitbucket Server and Cloud

### Repository Discovery

Instead of manually maintaining a list of repositories, you can use the repository discovery feature to automatically find repositories from Bitbucket:

```bash
# Generate repos.yaml from Bitbucket configuration
python repos.py config.yaml

# Use the discovered repositories
python clone.py repos.yaml
```

The discovery process supports:
- **Bitbucket Server**: Query projects using project keys and regex patterns
- **Bitbucket Cloud**: Query workspaces using workspace names and regex patterns
- **Regex filtering**: Filter repositories by name using regular expressions
- **SSH URL extraction**: Automatically extracts SSH clone URLs for use with clone.py

## Usage

### Running Individual Stages

Each stage can be run independently:

```bash
# Stage 0: Discover repositories (optional)
cd backend/collect
python repos.py [config.yaml]

# Stage 1: Clone repositories
python clone.py [config.yaml]

# Stage 2: Apply overrides
python override.py [config.yaml]

# Stage 3: Pull terraform state
python pull.py [config.yaml]
```

### Running Complete Pipeline

Run all stages in sequence:

```bash
cd backend/collect

# Option 1: Use manual repository list
python clone.py && python override.py && python pull.py

# Option 2: Use repository discovery
python repos.py && python clone.py repos.yaml && python override.py repos.yaml && python pull.py repos.yaml
```

### Using Custom Configuration

```bash
python clone.py /path/to/custom-config.yaml
python override.py /path/to/custom-config.yaml
python pull.py /path/to/custom-config.yaml
```

## Environment Variables

### Logging Configuration

Set the `LOG_LEVEL` environment variable to control verbosity:

```bash
# Debug level logging
export LOG_LEVEL=DEBUG
python clone.py

# Info level logging (default)
export LOG_LEVEL=INFO
python clone.py
```

### Authentication

For repository discovery, you can provide credentials via environment variables:

```bash
# Bitbucket Server
export BITBUCKET_SERVER_PASSWORD="your-app-password"

# Bitbucket Cloud  
export BITBUCKET_CLOUD_APP_PASSWORD="your-app-password"

python repos.py
```

## Directory Structure

After running the pipeline, the directory structure will be:

```
backend/collect/
├── repos.py                # Repository discovery script
├── clone.py                # Clone stage script
├── override.py             # Override stage script  
├── pull.py                 # Pull stage script
├── main.py                 # Pipeline orchestrator
├── README.md               # This file
├── config.yaml             # Configuration file
├── repos.yaml              # Discovered repositories (generated)
└── repos/                  # Cloned repositories
    ├── repo1/
    │   ├── *.tf           # Original .tf files from repo
    │   ├── override*.tf   # Override files (if any)
    │   └── terraform.tfstate  # State file (if available)
    └── repo2/
        └── ...
```

## Stage Details

### Repository Discovery (`repos.py`)

**What it does:**
- Connects to Bitbucket Server and/or Bitbucket Cloud APIs
- Discovers repositories from configured projects/workspaces
- Filters repositories using regex patterns on repository names
- Extracts SSH clone URLs for each matching repository
- Generates a `repos.yaml` file compatible with clone.py

**Requirements:**
- Network access to Bitbucket instances
- Valid credentials (username/password for Server, username/app-password for Cloud)
- Python `requests` library

**Authentication:**
- **Bitbucket Server**: Username and password/app-password
- **Bitbucket Cloud**: Username and app password (not account password)

**Output:**
- `repos.yaml` file containing discovered SSH repository URLs

### Clone Stage (`clone.py`)

**What it does:**
- Performs shallow clones (depth=1) of Git repositories
- Uses sparse checkout to only download `.tf` files
- Clones each repository into `repos/{repo-name}/`
- Supports rate limiting between clones
- Handles SSH authentication using user's SSH keys

**Requirements:**
- Git available in PATH
- SSH keys configured for repository access
- Only SSH URLs are supported (`git@github.com:org/repo.git`)

**Output:**
- Cloned repositories in `repos/` directory
- Each repository contains only `.tf` files

### Override Stage (`override.py`)

**What it does:**
- Copies override `.tf` files from configured source directories
- Places override files in the root of each cloned repository
- Supports multiple override source directories
- Handles file conflicts by overwriting existing files

**Default Override Sources:**
- `./aws_deployment_overrides/*.tf`
- `./k8s/deployment/overrides/*.tf`

**Output:**
- Override `.tf` files copied to each repository root

### Pull Stage (`pull.py`)

**What it does:**
- Runs `terraform init -backend=false` in each repository
- Runs `terraform state pull` to fetch remote state
- Saves state data to `terraform.tfstate` in each repository
- Handles repositories without remote state gracefully

**Requirements:**
- Terraform available in PATH
- Valid Terraform configuration in repositories
- Appropriate cloud provider credentials (AWS, Azure, GCP, etc.)

**Output:**
- `terraform.tfstate` files in each repository directory

## Error Handling

### Retry Logic

All stages implement single-retry logic:
- If an operation fails, it's added to a retry queue
- Each failed operation is retried once
- Final summary shows successful and failed operations

### Common Issues and Solutions

**SSH Key Issues:**
```bash
# Test SSH connectivity
ssh -T git@github.com

# Add SSH key to agent
ssh-add ~/.ssh/id_rsa
```

**Terraform Authentication:**
```bash
# AWS
export AWS_PROFILE=your-profile
# or
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...

# Azure
az login

# GCP
gcloud auth application-default login
```

**Permission Issues:**
```bash
# Make scripts executable
chmod +x backend/collect/*.py
```

## Troubleshooting

### Debug Mode

Enable debug logging for detailed output:

```bash
export LOG_LEVEL=DEBUG
python clone.py
```

### Checking Tool Availability

```bash
# Verify git is available
git --version

# Verify terraform is available  
terraform --version

# Verify SSH connectivity
ssh -T git@github.com
```

### Manual Testing

Test individual operations:

```bash
# Test git clone with sparse checkout
git clone --depth 1 --no-checkout git@github.com:user/repo.git test-repo
cd test-repo
git config core.sparseCheckout true
echo "*.tf" > .git/info/sparse-checkout
echo "**/*.tf" >> .git/info/sparse-checkout
git read-tree -m -u HEAD

# Test terraform commands
cd path/to/repo
terraform init -backend=false
terraform state pull
```

## Integration

This pipeline is designed to be the first stage of a larger data processing system:

1. **Collection** (this pipeline) - Gather `.tf` and `.tfstate` files
2. **Parsing** (future) - Parse Terraform files and extract metadata
3. **Indexing** (future) - Index parsed data for search
4. **Presentation** (future) - Web UI for browsing and searching

## Contributing

When modifying the pipeline:

1. Maintain backward compatibility with existing config format
2. Add appropriate logging at INFO and DEBUG levels
3. Implement retry logic for new operations
4. Test on multiple platforms (Linux, macOS, Windows)
5. Update this README with any new configuration options or requirements

## License

See project root for license information.