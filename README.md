# terraform-ui

A comprehensive Terraform data collection and analysis platform.

## Overview

This project provides a complete pipeline for collecting, processing, and presenting Terraform infrastructure data from multiple Git repositories. The system is designed to help teams understand, search, and analyze their Terraform configurations across their entire infrastructure ecosystem.

## Architecture

The platform consists of several stages:

1. **Collection Pipeline** (`backend/collect/`) - Gather `.tf` and `.tfstate` files from Git repositories
2. **Parsing** (future) - Extract and normalize Terraform data
3. **Indexing** (future) - Build searchable indexes of infrastructure data  
4. **Presentation** (future) - Web UI for browsing and searching

## Current Implementation

### Backend Collection Pipeline

The collection pipeline is fully implemented and ready for use. It provides three main stages:

- **Clone Stage** - Shallow clone repositories with sparse checkout for `.tf` files only
- **Override Stage** - Copy override/deployment-specific `.tf` files into repositories
- **Pull Stage** - Execute `terraform state pull` to gather current state data

See [`backend/collect/README.md`](backend/collect/README.md) for detailed setup and usage instructions.

### Quick Start

1. **Install Prerequisites**
   ```bash
   # Install Python dependencies
   pip install pyyaml
   
   # Install Git (if not already installed)
   # See backend/collect/README.md for platform-specific instructions
   
   # Install Terraform (required for state pulling)
   # See backend/collect/README.md for platform-specific instructions
   ```

2. **Configure Repository List**
   ```bash
   # Edit config.yaml to list your Terraform repositories
   cp config.yaml my-config.yaml
   # Edit my-config.yaml with your repository URLs
   ```

3. **Run Collection Pipeline**
   ```bash
   cd backend/collect
   
   # Run all stages
   python clone.py ../../my-config.yaml
   python override.py ../../my-config.yaml  
   python pull.py ../../my-config.yaml
   ```

4. **View Results**
   ```bash
   # Collected data will be in backend/collect/repos/
   ls backend/collect/repos/
   ```

## Example Configuration

```yaml
# config.yaml
repositories:
  - git@github.com:your-org/terraform-infrastructure.git
  - git@github.com:your-org/terraform-modules.git
  
# Optional: Rate limiting between clones
rate_limit: 0.1

# Optional: Override sources  
override_sources:
  - ./aws_deployment_overrides
  - ./k8s/deployment/overrides
```

## Features

### Current Features (Collection Pipeline)

- ✅ Multi-repository Terraform file collection
- ✅ SSH-based Git authentication
- ✅ Sparse checkout (`.tf` files only)
- ✅ Configurable override file injection
- ✅ Terraform state pulling with `terraform state pull`
- ✅ Cross-platform support (Linux, macOS, Windows)
- ✅ Comprehensive error handling and retry logic
- ✅ Configurable logging and rate limiting

### Planned Features

- 🔄 Terraform file parsing and AST analysis
- 🔄 Resource dependency mapping
- 🔄 Configuration validation and linting
- 🔄 Web-based search and browse interface
- 🔄 Resource change tracking and diff analysis
- 🔄 Team collaboration features

## Development

### Testing

```bash
# Run integration tests for collection pipeline
cd backend/collect
python test_pipeline.py
```

### Contributing

1. Follow the existing code style and structure
2. Add appropriate logging and error handling
3. Update documentation for any new features
4. Test on multiple platforms when possible

## License

See LICENSE file for details.