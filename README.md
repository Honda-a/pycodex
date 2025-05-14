# PyCodex

Python code indexing and search for Claude Desktop integration.

## Overview

PyCodex is a tool that scans Python files in a directory, parses them, and creates a searchable database of code elements such as modules, classes, functions, methods, and variables. It provides an MCP (Model Context Protocol) server that can be used by Claude Desktop to search and retrieve code snippets based on natural language queries.

## Features

- Scans Python files while respecting `.gitignore` patterns
- Parses Python code to extract information about modules, classes, functions, methods, and variables
- Indexes the code in a SQLite database
- Provides MCP tools and resources for Claude Desktop integration
- Includes a CLI for easy interaction

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/pycodex.git
cd pycodex

# Install with Poetry
poetry install

# Or install with pip
pip install .
```

## Usage

### CLI Commands

PyCodex provides several CLI commands for working with your code:

#### Indexing a Directory

```bash
# Index the current directory
pycodex index

# Index a specific directory
pycodex index /path/to/your/code

# Specify a project name
pycodex index /path/to/your/code --name YourProjectName
```

#### Searching Indexed Code

```bash
# Basic search
pycodex search "database connection"

# Search with project ID
pycodex search "database connection" --project 1

# Structured search (search only within classes)
pycodex search "class:Database"
```

#### Viewing Projects

```bash
# List all indexed projects
pycodex projects
```

#### Viewing a File

```bash
# View a file with syntax highlighting
pycodex view /path/to/your/file.py
```

#### Running the MCP Server

```bash
# Run the MCP server for Claude Desktop integration
pycodex serve
```

### Using with Claude Desktop

To use PyCodex with Claude Desktop:

1. Run the MCP server:
   ```bash
   pycodex serve
   ```

2. Configure Claude Desktop to use the PyCodex MCP server (the specific steps depend on Claude Desktop's configuration).

3. Restart Claude Desktop or refresh the server list.

4. Ask Claude to search your codebase with natural language queries, such as:
   - "Find all Python classes related to database connections"
   - "Show me functions that handle authentication"
   - "Where is the code that processes user input?"

## MCP Features

PyCodex provides the following MCP tools and resources:

### Tools

- `index_directory`: Index Python files in a directory
- `search_code`: Search for code in indexed projects
- `get_file_content`: Get the content of a specific file

### Resources

- `pycodex://projects`: Get all indexed projects
- `pycodex://project/{project_id}`: Get information about a specific project

## Development

### Project Structure

```
pycodex/
├── __init__.py
├── cli.py
├── core/
│   ├── __init__.py
│   ├── scanner.py
│   ├── parser.py
│   ├── indexer.py
│   └── search.py
├── models/
│   ├── __init__.py
│   └── database.py
└── server.py
```

### Database Schema

PyCodex uses SQLite to store indexed code information with the following schema:

- **Projects**: Represents a code repository
- **Modules**: Represents Python files
- **Classes**: Represents Python classes
- **Functions**: Represents Python functions and methods
- **Variables**: Represents Python variables
- **Imports**: Represents Python imports

## License

MIT
