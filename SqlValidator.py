import streamlit as st
import requests
import pandas as pd
import json
import yaml
import time
import os
from datetime import datetime

# Configuration for the app
st.set_page_config(page_title="Denodo SQL Query Validator", layout="wide")

# Constants
YAML_FILE_PATH = "verified_queries.yaml"
API_ENDPOINT = "http://localhost:8008/answerDataQuestion"  # Adjust this to your Denodo AI SDK endpoint

# CSS styling
st.markdown("""
<style>
    .sql-box {
        background-color: #222222; /* dark background for Generated SQL */
        color: white;
        padding: 10px;
        border-radius: 5px;
        font-family: monospace;
    }
    .explanation-box {
        background-color: #333333; /* dark background for Query Explanation */
        color: white;
        padding: 10px;
        border-radius: 5px;
    }
    .results-box {
        background-color: #555555; /* dark background for Query Results */
        color: white;
        padding: 10px;
        border-radius: 5px;
        margin-top: 10px;
    }
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state variables if they don't exist
if 'query_history' not in st.session_state:
    st.session_state.query_history = []
if 'current_query' not in st.session_state:
    st.session_state.current_query = None
if 'current_question' not in st.session_state:
    st.session_state.current_question = ""
if 'current_answer' not in st.session_state:
    st.session_state.current_answer = ""
if 'current_execution_result' not in st.session_state:
    st.session_state.current_execution_result = None
if 'current_query_explanation' not in st.session_state:
    st.session_state.current_query_explanation = ""
if 'tables_used' not in st.session_state:
    st.session_state.tables_used = []
if 'edited_sql' not in st.session_state:
    st.session_state.edited_sql = ""
if 'query_name' not in st.session_state:
    st.session_state.query_name = ""
if 'verified_queries' not in st.session_state:
    # Load any existing verified queries from the YAML file
    if os.path.exists(YAML_FILE_PATH):
        with open(YAML_FILE_PATH, 'r') as file:
            try:
                st.session_state.verified_queries = yaml.safe_load(file) or {'verified_queries': []}
            except yaml.YAMLError:
                st.session_state.verified_queries = {'verified_queries': []}
    else:
        st.session_state.verified_queries = {'verified_queries': []}

# Function to call the Denodo AI SDK API
def query_denodo_ai_sdk(question):
    try:
        # Prepare the request
        payload = {
            "question": question,
            "mode": "data",
            "verbose": True
        }
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json"
        }
        
        # Basic authentication credentials
        auth = ("admin", "admin")
        
        # Make the request to the Denodo AI SDK API with basic auth
        response = requests.post(API_ENDPOINT, json=payload, headers=headers, auth=auth)
        response.raise_for_status()  # Raise an exception for 4XX/5XX responses
        
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to Denodo AI SDK: {str(e)}")
        return None

# Function to save verified queries to YAML file
def save_verified_query(name, question, sql, explanation, username="data_analyst"):
    # Create a new verified query entry
    new_query = {
        'name': name,
        'question': question,
        'verified_at': datetime.now().strftime("%d %B %Y"),
        'verified_by': username,
        'query_explanation': explanation,
        'sql': sql
    }
    
    # Append to our session state
    st.session_state.verified_queries['verified_queries'].append(new_query)
    
    # Save to YAML file
    with open(YAML_FILE_PATH, 'w') as file:
        yaml.dump(st.session_state.verified_queries, file, default_flow_style=False)
    
    return True

# Function to convert the execution result to a DataFrame
def execution_result_to_df(execution_result):
    if not execution_result:
        return pd.DataFrame()
    
    # Extract data from the execution result
    rows = []
    for row_key, row_data in execution_result.items():
        if row_key.startswith("Row"):
            row = {}
            for column in row_data:
                column_name = column.get("columnName", "")
                value = column.get("value", "")
                row[column_name] = value
            rows.append(row)
    
    return pd.DataFrame(rows)

# App header
st.markdown("""
<div class="header-container">
    <h1>Denodo SQL Query Validator</h1>
</div>
""", unsafe_allow_html=True)

# Sidebar for displaying query history and verified queries
with st.sidebar:
    st.header("Query Navigator")
    
    # User information (could be enhanced with authentication)
    username = st.text_input("Your Name", value="data_analyst")
    
    tab1, tab2 = st.tabs(["Recent Queries", "Verified Queries"])
    
    with tab1:
        if st.session_state.query_history:
            for i, (q, _) in enumerate(st.session_state.query_history):
                if st.button(f"{i+1}. {q[:40]}...", key=f"history_{i}"):
                    st.session_state.current_question = q
                    st.experimental_rerun()
        else:
            st.info("No query history yet. Ask a question to get started!")
    
    with tab2:
        verified_queries = st.session_state.verified_queries.get('verified_queries', [])
        if verified_queries:
            for i, query in enumerate(verified_queries):
                if st.button(f"{i+1}. {query['name']}", key=f"verified_{i}"):
                    st.session_state.current_question = query['question']
                    st.session_state.edited_sql = query['sql']
                    st.session_state.query_name = query['name']
                    st.experimental_rerun()
        else:
            st.info("No verified queries yet. Validate a query to add it here!")

# Main content
st.header("Ask a Question")

# Question input
col1, col2 = st.columns([4, 1])
with col1:
    question = st.text_input("Enter your question", value=st.session_state.current_question)
with col2:
    execute_btn = st.button("Execute")

# If question is submitted, call the Denodo AI SDK
if execute_btn and question:
    # Update session state
    st.session_state.current_question = question
    
    with st.spinner("Generating SQL and fetching results..."):
        # Call the Denodo AI SDK
        result = query_denodo_ai_sdk(question)
        
        if result:
            # Update session state with the response
            st.session_state.current_query = result.get("sql_query", "")
            st.session_state.current_execution_result = result.get("execution_result", {})
            st.session_state.current_query_explanation = result.get("query_explanation", "")
            st.session_state.tables_used = result.get("tables_used", [])
            st.session_state.edited_sql = result.get("sql_query", "")
            
            # Add to query history if not already there
            if (question, st.session_state.current_query) not in st.session_state.query_history:
                st.session_state.query_history.insert(0, (question, st.session_state.current_query))
                # Keep only the most recent 10 queries
                st.session_state.query_history = st.session_state.query_history[:10]

# Display results if available
if st.session_state.current_query:
    st.header("Generated Query and Results")
    
    # Display the query results first with new styling
    st.subheader("Query Results")
    if st.session_state.current_execution_result:
        df = execution_result_to_df(st.session_state.current_execution_result)
        st.markdown(f'<div class="results-box">{df.to_html(index=False)}</div>', unsafe_allow_html=True)
    else:
        st.info("No results available.")
    
    # Display the generated SQL query
    st.subheader("Generated SQL")
    st.markdown(f'<div class="sql-box">{st.session_state.current_query}</div>', unsafe_allow_html=True)
    
    # Display the query explanation
    st.subheader("Query Explanation")
    st.markdown(f'<div class="explanation-box">{st.session_state.current_query_explanation}</div>', unsafe_allow_html=True)
    
    # SQL Validation Section
    st.header("Validate or Edit SQL")
    
    # Query name input
    st.session_state.query_name = st.text_input("Query Name", value=st.session_state.query_name)
    
    # Editable SQL
    st.session_state.edited_sql = st.text_area("Edit SQL Query if needed", value=st.session_state.edited_sql, height=200)
    
    # Validation buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Validate & Save"):
            if not st.session_state.query_name:
                st.error("Please provide a name for this query.")
            else:
                # Save the verified query
                success = save_verified_query(
                    st.session_state.query_name,
                    st.session_state.current_question,
                    st.session_state.edited_sql,
                    st.session_state.current_query_explanation,
                    username
                )
                
                if success:
                    st.success(f"Query '{st.session_state.query_name}' verified and saved successfully!")
    
    with col2:
        if st.button("Reset to Original"):
            st.session_state.edited_sql = st.session_state.current_query
            st.experimental_rerun()

# Footer
st.markdown("---")
st.markdown("Denodo SQL Query Validator App | Built with Streamlit")