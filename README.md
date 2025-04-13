# HVSR Text2SQL - SQL Validator and Smart Query Assistant

A two-part system for validating SQL queries and providing smart query assistance using validated queries and LLM fallback.

## Overview

This system consists of two main components:
1. SQL Validator App: For data analysts to review and verify LLM-generated queries
2. Smart Query Assistant: An intelligent query interface that prioritizes verified queries

### Components

1. **SQL Validator** (`sqlValidator.py`)
- Allows data analysts to review and verify SQL queries
- Stores verified queries in YAML format
- Captures query metadata (performance, accuracy, etc.)
- Maintains a repository of trusted queries

2. **Smart Query Assistant** (`sample_assistant.py`)
- Primary user interface for query execution
- Two-tier query resolution:
  1. Checks verified queries in YAML first
  2. Falls back to LLM if no match found
- Supports query modification based on user context

3. **Verified Queries Storage** (`verified_queries.yaml`)
- YAML-based storage for validated queries
- Structure:
  ```yaml
  verified_queries:
    - name: "Query Name"
      query_explanation: "Description"
      question: "Sample Question"
      sql: "Verified SQL"
      verified_at: "Date"
      verified_by: "Analyst"
  ```

## Key Features

### SQL Validator
- Query validation interface
- Performance metrics tracking
- Query testing capabilities
- YAML export functionality

### Smart Query Assistant
- Semantic query matching
- Automatic query adaptation
- Context-aware modifications
- LLM fallback capability

## Usage Flow

1. **Query Validation Process**
   - Analysts review LLM-generated queries
   - Test queries against test data
   - Add explanations and metadata
   - Store in verified_queries.yaml

2. **Query Execution Process**
   - User submits natural language question
   - System checks verified queries first
   - Modifies verified query if needed
   - Falls back to LLM if no match found

## Configuration

Required environment setup:
- Python 3.8+
- Streamlit
- OpenAI API key
- Denodo server access

## Architecture

```
Root Folder/
├── sample_assistant.py    # Smart Query Assistant
├── sqlValidator.py       # SQL Validation Tool
├── verified_queries.yaml # Verified Query Storage
└── README.md            # Documentation
```

## Security Note

- API keys should be properly secured
- Access to validation tools should be restricted
- Query execution should follow security protocols

## Future Enhancements

1. Query Performance Tracking
2. Advanced Validation Rules
3. Machine Learning-based Query Matching
4. Enhanced Security Features
1. Use sqlValidator.py to validate new queries
2. Follow YAML structure for new entries

## Contributing

3. Include comprehensive query explanations
4. Test queries before verification
