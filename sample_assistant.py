import streamlit as st
import requests
import pandas as pd
import yaml
import json
import os
import base64
from typing import Dict, Any, Tuple, List, Optional
from datetime import datetime

# Import LangChain components
from langchain.llms import OpenAI
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain

# Configuration
YAML_FILE_PATH = "verified_queries.yaml"
DENODO_AI_SDK_ENDPOINT = "http://localhost:8008/answerDataQuestion"
DENODO_CATALOG_ENDPOINT = "http://localhost:39090/denodo-data-catalog/public/api/askaquestion/execute"
SERVER_ID = 1
VERIFY_SSL = False

# Set up page configuration
st.set_page_config(page_title="Smart Query Assistant", layout="wide")

# Add CSS styling
st.markdown("""
<style>
    .header-container {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 1rem 0;
    }
    .query-box {
        background-color: #1E1E1E;  /* Dark background for SQL */
        color: #FFFFFF;  /* White text */
        padding: 15px;
        border-radius: 5px;
        font-family: monospace;
        margin-bottom: 10px;
        border: 1px solid #333;
    }
    .result-box {
        background-color: #e6ffe6;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .explanation-box {
        background-color: #2D2D2D;  /* Dark background for explanations */
        color: #FFFFFF;  /* White text */
        padding: 15px;
        border-radius: 5px;
        margin: 10px 0;
        border: 1px solid #333;
        line-height: 1.5;
    }
    .source-tag {
        background-color: #ff9999;
        color: white;
        padding: 3px 6px;
        border-radius: 3px;
        font-size: 0.8em;
        margin-right: 10px;
    }
    .match-tag {
        background-color: #99cc99;
        color: white;
        padding: 3px 6px;
        border-radius: 3px;
        font-size: 0.8em;
        margin-right: 10px;
    }
    /* SQL syntax highlighting */
    .query-box code {
        color: #569CD6;  /* Light blue for SQL keywords */
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'history' not in st.session_state:
    st.session_state.history = []
if 'openai_api_key' not in st.session_state:
    # Declare the API key in the program itself (replace with your actual key)
    DEFAULT_OPENAI_API_KEY = ""
    st.session_state.openai_api_key = DEFAULT_OPENAI_API_KEY
if 'denodo_username' not in st.session_state:
    st.session_state.denodo_username = "admin"
if 'denodo_password' not in st.session_state:
    st.session_state.denodo_password = "admin"

# Load verified queries from YAML
def load_verified_queries():
    if os.path.exists(YAML_FILE_PATH):
        with open(YAML_FILE_PATH, 'r') as file:
            try:
                data = yaml.safe_load(file)
                return data.get('verified_queries', []) if data else []
            except yaml.YAMLError:
                st.error(f"Error parsing YAML file: {YAML_FILE_PATH}")
                return []
    return []

# Execute VQL function
def execute_vql(vql: str, limit: int = 1000) -> Tuple[int, Dict[str, Any]]:
    """
    Execute VQL against Data Catalog with support for various authentication methods.
    """
    execution_url = DENODO_CATALOG_ENDPOINT
    server_id = SERVER_ID
    verify_ssl = VERIFY_SSL
    auth = (st.session_state.denodo_username, st.session_state.denodo_password)
    
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }
    
    # Calculate basic auth header
    if isinstance(auth, tuple):
        username, password = auth
        auth_string = f"{username}:{password}"
        encoded_auth = base64.b64encode(auth_string.encode('utf-8')).decode('utf-8')
        headers['Authorization'] = f'Basic {encoded_auth}'
    
    data = {
        "vql": vql,
        "limit": limit
    }
    
    st.write("Debug - Executing VQL:", vql)  # Debug log
    
    try:
        response = requests.post(
            f"{execution_url}?serverId={server_id}",
            json=data,
            headers=headers,
            verify=verify_ssl
        )
        response.raise_for_status()
        
        json_response = response.json()
        st.write("Debug - API Response:", json_response)  # Debug log
        
        # Return the full response even if no rows
        return 200, {
            "rows": json_response.get('rows', []),
            "columnNames": json_response.get('columnNames', [])
        }
        
    except requests.HTTPError as e:
        error_msg = f"Data Catalog API error: {str(e)}"
        st.error(error_msg)
        try:
            st.write("Debug - Error Response:", e.response.json())  # Debug log
        except:
            st.write("Debug - Raw Error:", str(e))
        return e.response.status_code, {"error": error_msg}
    except Exception as e:
        error_msg = f"Failed to execute query: {str(e)}"
        st.error(error_msg)
        return 500, {"error": error_msg}

def display_query_results(status_code: int, result: Dict[str, Any], sql: str):
    """Helper function to display query results in Streamlit"""
    if (status_code == 200):
        if "error" in result:
            st.error(result["error"])
            return
        
        # Display SQL query first
        st.subheader("Executed SQL Query")
        st.code(sql, language="sql")
        
        # Handle the specific response format
        if "rows" in result:
            try:
                # Extract data from the new response format
                rows_data = []
                columns = []
                
                for row in result["rows"]:
                    if "values" in row:
                        row_dict = {}
                        for value in row["values"]:
                            # Get column name (or use the 'column' field if columnName is NULL)
                            col_name = value.get("columnName") or value.get("column")
                            if col_name and col_name not in columns:
                                columns.append(col_name)
                            # Get the value
                            row_dict[col_name] = value.get("value")
                        rows_data.append(row_dict)
                
                if columns and rows_data:
                    # Create DataFrame
                    df = pd.DataFrame(rows_data)
                    
                    # Display results
                    st.subheader("Query Results")
                    st.dataframe(df, use_container_width=True)
                    st.success(f"Found {len(df)} rows")
                    
                    # Display raw values for debugging
                    st.write("Debug - Data:", rows_data)
                else:
                    st.info("Query executed but no data was returned")
                    st.write("Debug - Raw Response:", result)
            except Exception as e:
                st.error(f"Error processing results: {str(e)}")
                st.write("Debug - Raw Response:", result)
        else:
            st.warning("Query response missing 'rows' field")
            st.write("Debug - Raw Response:", result)
    else:
        st.error(f"Query execution failed with status code {status_code}")
        st.write("Debug - Error Details:", result.get('error', 'Unknown error'))

# Parse execution JSON
def parse_execution_json(json_response: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse the execution JSON response from Data Catalog into a format
    similar to the AI SDK's output format.
    """
    execution_result = {}
    columns = json_response.get('columnNames', [])
    rows = json_response.get('rows', [])
    
    for i, row in enumerate(rows):
        row_data = []
        for j, value in enumerate(row):
            if j < len(columns):
                row_data.append({
                    "columnName": columns[j],
                    "value": str(value)
                })
        execution_result[f"Row {i+1}"] = row_data
    
    return execution_result

# Convert execution result to DataFrame
def execution_result_to_df(execution_result: Dict[str, Any]) -> pd.DataFrame:
    """
    Convert the execution result dictionary to a pandas DataFrame.
    """
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

# Function to check if a question matches any verified query using LangChain
def find_matching_query(question: str, verified_queries: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """Use LangChain with OpenAI to determine if the question matches a previously answered query."""
    if not verified_queries or not st.session_state.openai_api_key:
        return None

    # Create a string representation of all verified queries
    queries_str = ""
    for i, query in enumerate(verified_queries):
        queries_str += f"Query {i+1}:\n"
        queries_str += f"Name: {query.get('name', '')}\n"
        queries_str += f"Question: {query.get('question', '')}\n"
        queries_str += f"SQL: {query.get('sql', '')}\n"
        queries_str += f"Explanation: {query.get('query_explanation', '')}\n\n"
    
    # Updated template for strict JSON formatting
    template_str = """You are an expert at matching user questions with verified SQL queries.
Your task is to analyze the user's question and find the most similar verified query.

Follow these comparison rules carefully:
1. Core Query Components:
   - What is being counted/summed/averaged?
   - Which time period is being queried?
   - What status or category filters are needed?

2. Pattern Matching:
   - Match main action (count, sum, etc.)
   - Match time period (specific year)
   - Match status (delivered, canceled, shipped, etc.)
   - Look for status values in SQL comments

3. Modification Requirements:
   - List ALL required changes in modifications
   - Include both year AND status changes when needed
   - Be explicit about which status value to use
   - Use values from SQL comments when available

Output a SINGLE LINE JSON:
{{"match":boolean,"query_number":number,"similarity":number,"modification_needed":boolean,"modifications":string}}

Example modifications:
- Multiple changes: {{"match":true,"query_number":1,"similarity":95,"modification_needed":true,"modifications":"Change year from 2018 to 2017 in WHERE clause AND update order_status from 'canceled' to 'shipped' (value from comment)"}}
- Status only: {{"match":true,"query_number":1,"similarity":90,"modification_needed":true,"modifications":"Update order_status from 'delivered' to 'shipped' using value from comment"}}
- Year only: {{"match":true,"query_number":1,"similarity":85,"modification_needed":true,"modifications":"Change year from 2018 to 2017 in WHERE clause"}}

User Question: {question}

Previously verified queries:
{verified_queries}

Output JSON:"""

    # Create prompt template
    prompt = PromptTemplate(
        input_variables=["question", "verified_queries"],
        template=template_str
    )

    # Create LLMChain with lower temperature for consistent output
    llm = OpenAI(temperature=0, api_key=st.session_state.openai_api_key)
    chain = LLMChain(llm=llm, prompt=prompt)
    
    try:
        with st.spinner("Checking for similar queries..."):
            # Get raw response and clean it
            response = chain.run(question=question, verified_queries=queries_str)
            response = response.strip().strip('"\'')
            
            # Debug logging
            st.write("Debug - Raw LLM response:", response)
            
            try:
                # Parse the cleaned response
                response_json = json.loads(response)
                
                # Validate response format
                required_keys = {"match", "query_number", "similarity", "modification_needed", "modifications"}
                if not all(key in response_json for key in required_keys):
                    st.error(f"Missing required keys in response. Found keys: {list(response_json.keys())}")
                    return None
                
                if not response_json["match"]:
                    return None
                
                query_number = int(response_json["query_number"])
                if not (0 < query_number <= len(verified_queries)):
                    st.error(f"Invalid query number: {query_number}")
                    return None
                
                return {
                    "verified_query": verified_queries[query_number - 1],
                    "similarity": response_json["similarity"],
                    "modification_needed": response_json["modification_needed"],
                    "modifications": response_json["modifications"]
                }
                
            except json.JSONDecodeError as e:
                st.error(f"Failed to parse JSON response: {str(e)}")
                st.text(f"Raw response: {response}")
                return None
                
    except Exception as e:
        st.error(f"Error while checking for query matches: {str(e)}")
        return None

# Function to query Denodo AI SDK
def query_denodo_ai_sdk(question: str) -> Dict[str, Any]:
    """
    Query the Denodo AI SDK with the given question.
    """
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
        auth = (st.session_state.denodo_username, st.session_state.denodo_password)
        
        # Make the request to the Denodo AI SDK API
        with st.spinner("Generating answer with AI SDK..."):
            response = requests.post(DENODO_AI_SDK_ENDPOINT, json=payload, headers=headers, auth=auth)
            response.raise_for_status()
            
            return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Error connecting to Denodo AI SDK: {str(e)}")
        return {}

# Function to adjust SQL based on modifications from the LLM
def adjust_sql(original_sql: str, modifications: str) -> str:
    """Use LangChain to adjust SQL based on the modifications."""
    if not modifications or not st.session_state.openai_api_key:
        return original_sql
    
    template = """
    You are an expert SQL developer. Your task is to analyze and modify SQL based on user requirements.

    Original SQL:
    {original_sql}
    
    Modification instructions:
    {modifications}
    
    Rules:
    1. Analyze ALL Components:
       - Column aliases: Update to match the context (e.g., "Products Delivered" → "Products Shipped")
       - SQL Comments: Extract valid status values
       - WHERE conditions: Year and status filters
    
    2. ONLY modify these parts:
       - Column aliases in SELECT clause to match the question context
       - Year in BETWEEN clause as requested
       - Status values using options from comments
    
    3. Column Alias Guidelines:
       - Match the verb from user's question (delivered → shipped)
       - Keep "Number of" prefix if present
       - Maintain quote style and capitalization
       - Example: "Number of Products Delivered" → "Number of Products Shipped"
    
    4. Keep Intact:
       - Query structure
       - Table names
       - Aggregation functions
       - Comment content
    
    Example:
    User asks "how many orders shipped in 2017":
    Original: SELECT COUNT(*) AS "Number of Products Delivered"
    Modified: SELECT COUNT(*) AS "Number of Products Shipped"

    Return complete SQL with both alias and condition changes.
    """
    
    prompt = PromptTemplate(
        input_variables=["original_sql", "modifications"],
        template=template
    )
    
    # Create LLMChain
    llm = OpenAI(temperature=0, api_key=st.session_state.openai_api_key)
    chain = LLMChain(llm=llm, prompt=prompt)
    
    try:
        with st.spinner("Adjusting SQL query..."):
            modified_sql = chain.run(original_sql=original_sql, modifications=modifications)
            return modified_sql.strip()
    except Exception as e:
        st.error(f"Error adjusting SQL: {str(e)}")
        return original_sql

# App header
st.markdown("""
<div class="header-container">
    <h1>Smart Query Assistant</h1>
</div>
""", unsafe_allow_html=True)

# Sidebar for configuration
with st.sidebar:
    st.header("Configuration")
    # Now the API key input will have a default value declared in the code.
    st.session_state.openai_api_key = st.text_input("OpenAI API Key", value=st.session_state.openai_api_key, type="password")
    
    # Denodo credentials
    st.session_state.denodo_username = st.text_input("Denodo Username", value=st.session_state.denodo_username)
    st.session_state.denodo_password = st.text_input("Denodo Password", value=st.session_state.denodo_password, type="password")
    
    # History
    st.header("Query History")
    if st.session_state.history:
        for i, (q, _) in enumerate(reversed(st.session_state.history[-5:])):
            if st.button(f"{q[:40]}{'...' if len(q) > 40 else ''}", key=f"history_{i}"):
                st.session_state.current_question = q
                st.experimental_rerun()
    else:
        st.info("No query history yet")

# Main content
st.header("Ask a Question")

# Input for question
question = st.text_input("Enter your question about the data")

if st.button("Submit") and question:
    # Add to history
    if question not in [q for q, _ in st.session_state.history]:
        st.session_state.history.append((question, datetime.now()))
        
    # Section to display results
    st.header("Results")
    
    # Load verified queries
    verified_queries = load_verified_queries()
    
    # Check if the question matches any verified query
    match_info = None
    if verified_queries and st.session_state.openai_api_key:
        match_info = find_matching_query(question, verified_queries)
    
    if match_info:
        verified_query = match_info["verified_query"]
        st.markdown(f"<span class='match-tag'>MATCHED QUERY</span> Found a similar verified query: '{verified_query.get('name')}'", unsafe_allow_html=True)
        
        # Display similarity information
        st.markdown(f"**Similarity:** {match_info.get('similarity')}")
        
        # Get the SQL from the verified query
        sql = verified_query.get("sql", "")
        
        # Check if modifications are needed
        if match_info.get("modification_needed", False):
            st.info(f"Modifications needed: {match_info.get('modifications', '')}")
            
            # Adjust the SQL based on the modifications
            adjusted_sql = adjust_sql(sql, match_info.get("modifications", ""))
            
            st.subheader("Original SQL")
            st.markdown(f"<div class='query-box'>{sql}</div>", unsafe_allow_html=True)
            
            st.subheader("Adjusted SQL")
            st.markdown(f"<div class='query-box'>{adjusted_sql}</div>", unsafe_allow_html=True)
            
            # Use the adjusted SQL
            sql = adjusted_sql
        else:
            # Display the original SQL
            st.subheader("SQL Query")
            st.markdown(f"<div class='query-box'>{sql}</div>", unsafe_allow_html=True)
        
        # Execute the query and display results
        status_code, result = execute_vql(sql)
        display_query_results(status_code, result, sql)
        
        # Display explanation
        if verified_query.get("query_explanation"):
            st.subheader("Query Explanation")
            st.markdown(f'<div class="explanation-box">{verified_query["query_explanation"]}</div>', unsafe_allow_html=True)
    else:
        # If no match is found, use the Denodo AI SDK
        st.markdown("<span class='source-tag'>AI SDK</span> No matching verified query found. Using AI to generate an answer.", unsafe_allow_html=True)
        
        # Query the Denodo AI SDK
        ai_result = query_denodo_ai_sdk(question)
        
        if ai_result:
            # Display the AI's answer   
            st.subheader("Answer")
            st.markdown(f"<div class='result-box'>{ai_result.get('answer', '')}</div>", unsafe_allow_html=True)
                
            # Display the SQL query
            st.subheader("Generated SQL")
            st.markdown(f"<div class='query-box'>{ai_result.get('sql_query', '')}</div>", unsafe_allow_html=True)
            
            # Display the explanation
            st.subheader("Explanation")
            st.markdown(f"<div class='explanation-box'>{ai_result.get('query_explanation', '')}</div>", unsafe_allow_html=True)
            
            # Display the execution result
            st.subheader("Query Results")
            
            # Convert execution result to DataFrame
            execution_result = ai_result.get('execution_result', {})
            df = execution_result_to_df(execution_result)
            st.dataframe(df, use_container_width=True)
            
            # Display any related questions suggested by the AI
            related_questions = ai_result.get('related_questions', [])
            if related_questions:
                st.subheader("Related Questions")
                for rq in related_questions:
                    if st.button(rq):
                        # Set this as the new question and rerun
                        question = rq
                        st.experimental_rerun()
        else:
            st.error("Failed to get a response from the Denodo AI SDK. Please check the connection and try again.")

# Footer
st.markdown("---")
st.markdown("Smart Query Assistant | Built for Denodo")