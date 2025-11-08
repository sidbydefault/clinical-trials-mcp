# Clinical Trials MCP

A Model Context Protocol (MCP) server for matching patients with clinical trials using synthetic healthcare data.

## Overview

This project provides an MCP server that intelligently matches patients to relevant clinical trials based on their demographics, medical conditions, and trial eligibility criteria.

## Features

- Patient demographic and condition data management
- Clinical trial database with eligibility criteria
- Vector-based semantic search for trial matching
- MCP server implementation for integration with LLM applications

## Project Structure

```
clinical-trial-mcp/
├── src/              # Core application code
├── docs/             # Documentation
├── examples/         # Sample data and setup examples
├── notebooks/        # Jupyter notebooks for experimentation
└── data/             # Data storage (gitignored)
```

## Prerequisites

- Python 3.11+
- Docker and Docker Compose (optional)
- Poetry or pip for dependency management

## Quick Start

1. Clone the repository
2. Copy `.env.example` to `.env` and configure
3. Install dependencies: `make install`
4. Set up the database: `python examples/setup_example.py`
5. Run the server: `make run`

## Documentation

- [Database Schema](docs/DATABASE_SCHEMA.md)
- [Vector Store Schema](docs/VECTOR_STORE_SCHEMA.md)

## Development

- `make install` - Install dependencies
- `make test` - Run tests
- `make lint` - Run linting
- `make format` - Format code

## License

MIT
