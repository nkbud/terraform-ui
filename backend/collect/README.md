# Terraform File Collection Pipeline

This directory contains the backend pipeline for collecting, overriding, and pulling Terraform `.tf` and `.tfstate` files from a list of Git repositories. This is the first stage of the data pipeline that enables later processes to parse and index Terraform data for search and presentation layers.

## Overview

The collection pipeline consists of three main stages:

1. **Clone Stage** (`clone.py`) - Shallow clone repositories and checkout only `.tf` files
2. **Override Stage** (`override.py`) - Copy override `.tf` files into cloned repositories  
3. **Pull Stage** (`pull.py`) - Run `terraform init` and `terraform state pull` to fetch state files

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
pip install pyyaml
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

# Optional: Configure override source directories
override_sources:
  - ./aws_deployment_overrides
  - ./k8s/deployment/overrides
```

### Configuration Options

- **repositories** (required): List of Git SSH URLs to clone
- **rate_limit** (optional): Seconds to wait between repository clones (default: 0.1)
- **override_sources** (optional): Directories containing override `.tf` files (default: `./aws_deployment_overrides` and `./k8s/deployment/overrides`)

## Usage

### Running Individual Stages

Each stage can be run independently:

```bash
# Stage 1: Clone repositories
cd backend/collect
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
python clone.py && python override.py && python pull.py
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

## Directory Structure

After running the pipeline, the directory structure will be:

```
backend/collect/
├── clone.py                 # Clone stage script
├── override.py             # Override stage script  
├── pull.py                 # Pull stage script
├── README.md               # This file
└── repos/                  # Cloned repositories
    ├── repo1/
    │   ├── *.tf           # Original .tf files from repo
    │   ├── override*.tf   # Override files (if any)
    │   └── terraform.tfstate  # State file (if available)
    └── repo2/
        └── ...
```

## Stage Details

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