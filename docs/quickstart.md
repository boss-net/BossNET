# Quick Start Guide

This guide will help you get started with the Bangladesh Student Data Analytics project quickly.

## Prerequisites

- Python 3.8 or higher
- Git
- PostgreSQL (for data storage)
- Redis (for caching)

## Setup Steps

1. Clone the repository:
   \`\`\`bash
   git clone https://github.com/boss-net/bossnet.git
   cd bossnet
   \`\`\`

2. Create and activate a virtual environment:
   \`\`\`bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   \`\`\`

3. Install dependencies:
   \`\`\`bash
   # For development
   pip install -e ".[dev]"

   # For production
   pip install .
   \`\`\`

4. Set up pre-commit hooks:
   \`\`\`bash
   pre-commit install
   \`\`\`

5. Configure environment variables:
   \`\`\`bash
   cp .env.example .env
   # Edit .env with your configuration
   \`\`\`

## Development Workflow

### Code Quality

Our project uses several tools to maintain code quality:

- **black**: Code formatting
  \`\`\`bash
  black .
  \`\`\`

- **isort**: Import sorting
  \`\`\`bash
  isort .
  \`\`\`

- **flake8**: Code linting
  \`\`\`bash
  flake8 .
  \`\`\`

- **bandit**: Security checks
  \`\`\`bash
  bandit -r src/
  \`\`\`

### Running Tests

\`\`\`bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_specific.py
\`\`\`

### Database Setup

1. Create the database:
   \`\`\`bash
   createdb student_analytics_db
   \`\`\`

2. Run migrations:
   \`\`\`bash
   python src/data_processing/run_migrations.py
   \`\`\`

### Running the Application

1. Start the API server:
   \`\`\`bash
   uvicorn src.api.main:app --reload
   \`\`\`

2. Access the API documentation:
   - OpenAPI UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Project Structure

\`\`\`
bossnet/
├── src/                  # Source code
│   ├── data_processing/  # Data processing modules
│   ├── models/          # Analytics models
│   ├── api/            # API endpoints
│   └── utils/          # Utility functions
├── tests/               # Test suite
├── docs/               # Documentation
├── notebooks/          # Jupyter notebooks
└── deploy/            # Deployment configurations
\`\`\`

## Common Tasks

### Adding New Features

1. Create a new branch:
   \`\`\`bash
   git checkout -b feature/your-feature-name
   \`\`\`

2. Make your changes
3. Run tests and quality checks:
   \`\`\`bash
   pytest
   pre-commit run --all-files
   \`\`\`

4. Commit your changes:
   \`\`\`bash
   git add .
   git commit -m "Add: your feature description"
   \`\`\`

### Processing Data

1. Place raw data in appropriate directory:
   \`\`\`bash
   raw_data/[category]/your_data_file.csv
   \`\`\`

2. Run processing script:
   \`\`\`bash
   python src/data_processing/process_data.py --source [category]
   \`\`\`

### Generating Reports

\`\`\`bash
python src/reports/generate_reports.py --type [report_type] --output [path]
\`\`\`

## Troubleshooting

### Common Issues

1. **Database Connection Issues**
   - Check PostgreSQL service is running
   - Verify database credentials in .env
   - Ensure database exists

2. **Import Errors**
   - Verify virtual environment is activated
   - Check all dependencies are installed
   - Confirm Python path is correct

3. **Pre-commit Hook Failures**
   - Run `pre-commit run --all-files` to check all files
   - Address individual tool errors
   - Update tool configurations if needed

### Getting Help

- Check the documentation in `docs/`
- Review existing issues on GitHub
- Contact the development team
- Join our community discussions

## Next Steps

- Review the [Contributing Guidelines](CONTRIBUTING.md)
- Explore the [API Documentation](docs/api.md)
- Check out [Example Notebooks](notebooks/)
- Read about [Deployment](docs/deployment.md)

## Additional Resources

- [Project README](../README.md)
- [Security Guidelines](security.md)
- [Data Dictionary](data_dictionary/README.md)
- [API Reference](api-reference/README.md)
