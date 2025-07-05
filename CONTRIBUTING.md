# Contributing to Bangladesh Student Data Analytics

Thank you for your interest in contributing to the Bangladesh Student Data Analytics project! This document provides guidelines and instructions for contributing.

## Table of Contents
- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Submitting Changes](#submitting-changes)
- [Coding Standards](#coding-standards)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to [project maintainers].

## Getting Started

1. Fork the repository
2. Clone your fork:
   \`\`\`bash
   git clone https://github.com/your-username/bossnet.git
   cd bossnet
   \`\`\`

3. Set up your development environment:
   \`\`\`bash
   ./setup_dev_environment.sh
   \`\`\`

4. Create a new branch for your feature/fix:
   \`\`\`bash
   git checkout -b feature/your-feature-name
   \`\`\`

## Development Workflow

1. Activate the virtual environment:
   \`\`\`bash
   source venv/bin/activate
   \`\`\`

2. Make your changes following our coding standards

3. Run tests locally:
   \`\`\`bash
   pytest
   \`\`\`

4. Format your code:
   \`\`\`bash
   black .
   isort .
   \`\`\`

5. Check code quality:
   \`\`\`bash
   flake8
   \`\`\`

## Submitting Changes

1. Commit your changes:
   \`\`\`bash
   git add .
   git commit -m "Description of your changes"
   \`\`\`

2. Push to your fork:
   \`\`\`bash
   git push origin feature/your-feature-name
   \`\`\`

3. Create a Pull Request through GitHub

### Pull Request Guidelines

- Fill in the provided PR template
- Include tests for new functionality
- Update documentation as needed
- Ensure CI checks pass
- Link relevant issues

## Coding Standards

We follow these coding standards:

- PEP 8 style guide
- Type hints for function arguments and return values
- Docstrings for all public functions, classes, and modules
- Maximum line length of 127 characters
- Clear, descriptive variable and function names
- Comments for complex logic

Example:
\`\`\`python
def calculate_student_performance(
    student_data: pd.DataFrame,
    metrics: List[str]
) -> Dict[str, float]:
    """
    Calculate student performance metrics.

    Args:
        student_data: DataFrame containing student information
        metrics: List of metrics to calculate

    Returns:
        Dictionary of calculated metrics
    """
    # Implementation
\`\`\`

## Testing Guidelines

- Write tests for all new functionality
- Maintain test coverage above 80%
- Use meaningful test names and descriptions
- Include both positive and negative test cases
- Mock external dependencies

Example:
\`\`\`python
def test_calculate_student_performance_valid_data():
    """Test performance calculation with valid student data."""
    # Test implementation
\`\`\`

## Documentation

- Update README.md for significant changes
- Document new features in docs/
- Include docstrings for all public APIs
- Provide examples for new functionality
- Update data dictionary for data structure changes

### Documentation Style

Use Markdown for documentation:
\`\`\`markdown
# Component Name

## Overview
Brief description

## Usage
Example usage code or instructions

## Parameters
- `param1`: Description
- `param2`: Description
\`\`\`

## Data Handling

When working with educational data:

1. Never commit real student data
2. Use anonymized sample data for testing
3. Follow data privacy guidelines
4. Document data structures and relationships

## Reporting Issues

- Use the issue tracker
- Include reproducible examples
- Provide system information
- Tag issues appropriately

## Review Process

1. Code review by maintainers
2. CI/CD checks
3. Documentation review
4. Security review for sensitive components

## Getting Help

- Check existing documentation
- Search closed issues
- Ask in discussions
- Contact maintainers

Thank you for contributing to improving education data analysis in Bangladesh!
