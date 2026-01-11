import streamlit as st
import requests
import pandas as pd
import json
from typing import Dict, Any, Optional

# Configuration
API_BASE_URL = "http://localhost:8080"

# Page config
st.set_page_config(
    page_title="NLQ → Athena Query Interface",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    .main {
        padding: 0rem 1rem;
    }
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        margin: 1rem 0;
    }
    </style>
    """, unsafe_allow_html=True)

# Initialize session state
if 'query_history' not in st.session_state:
    st.session_state.query_history = []
if 'current_result' not in st.session_state:
    st.session_state.current_result = None

def make_api_request(endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make API request to FastAPI backend"""
    url = f"{API_BASE_URL}{endpoint}"
    try:
        if method == "POST":
            response = requests.post(url, json=data, timeout=300)  # Increased to 5 minutes
        else:
            response = requests.get(url, timeout=60)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.Timeout:
        st.error("⏱️ Request timed out. The model may be loading for the first time (this can take several minutes).")
        st.info("💡 Tip: Try again in a moment. First-time model loading can take 2-5 minutes.")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"API Error: {str(e)}")
        if hasattr(e.response, 'text'):
            st.error(f"Details: {e.response.text}")
        return None

def load_suggestions(target: str) -> Dict[str, Any]:
    """Load query suggestions from API"""
    return make_api_request(f"/nlq/suggestions?target={target}")

def load_schema(target: str) -> Dict[str, Any]:
    """Load database schema from API"""
    return make_api_request(f"/nlq/schema?target={target}")

# Header
st.title("🔍 NLQ → Athena Query Interface")
st.markdown("Convert natural language questions to SQL and query AWS Athena")

# Sidebar configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    
    # UUID configuration
    st.subheader("Authentication")
    account_uuid = st.text_input(
        "Account UUID",
        value="00000000-0000-0000-0000-000000000000",
        help="Account UUID for authentication - determines database access"
    )
    property_uuid = st.text_input(
        "Property UUID",
        value="00000000-0000-0000-0000-000000000000",
        help="Property UUID for authentication - determines database access"
    )
    
    # Quick UUID presets
    st.caption("Quick presets:")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("All 0s (Super)"):
            st.session_state.preset_account = "00000000-0000-0000-0000-000000000000"
            st.session_state.preset_property = "00000000-0000-0000-0000-000000000000"
            st.rerun()
    with col2:
        if st.button("All 1s (Peninsula)"):
            st.session_state.preset_account = "11111111-1111-1111-1111-111111111111"
            st.session_state.preset_property = "11111111-1111-1111-1111-111111111111"
            st.rerun()
    
    # Update inputs if preset was clicked
    if 'preset_account' in st.session_state:
        account_uuid = st.session_state.preset_account
        property_uuid = st.session_state.preset_property
        del st.session_state.preset_account
        del st.session_state.preset_property
    
    # Database selection for schema/suggestions viewing only
    st.subheader("Schema Browser Target")
    target = st.selectbox(
        "View schema for",
        options=["peninsula_incident", "londoner_granded"],
        help="Select which database schema to browse (for suggestions/schema tabs only)"
    )
    
    # Query options
    st.subheader("Query Options")
    dry_run = st.checkbox("Dry Run", value=False, help="Generate SQL without executing")
    max_rows = st.slider("Max Rows", min_value=10, max_value=1000, value=100, step=10)
    dialect = st.selectbox("SQL Dialect", options=["athena", "postgres"], index=0)
    
    # Info section
    st.divider()
    st.caption(f"API: {API_BASE_URL}")
    st.caption("Database access determined by UUID")
    
    # Performance tips
    with st.expander("⚡ Performance Tips", expanded=False):
        st.caption("• **First query**: 2-5 minutes (model loading)")
        st.caption("• **Subsequent queries**: 5-15 seconds")
        st.caption("• **Dry run mode**: Faster, skips Athena execution")
        st.caption("• **Limit rows**: Use smaller max_rows for faster results")
    
    # Show UUID permissions mapping
    with st.expander("📋 UUID Mappings", expanded=False):
        st.caption("**All 0s**: Both databases (super user)")
        st.caption("**All 1s**: Peninsula only")
        st.caption("See permissions_config.py for more")

# Main tabs
tab1, tab2, tab3, tab4 = st.tabs(["💬 Query", "💡 Suggestions", "📊 Schema", "📜 History"])

# Tab 1: Query Interface
with tab1:
    st.header("Ask a Question")
    
    # Important note
    st.info("ℹ️ **First Query After Restart**: Model loads on first use (~60-120 seconds). Subsequent queries are much faster (~5-15 seconds).")
    
    # Question input
    question = st.text_area(
        "Natural Language Question",
        placeholder="e.g., Show me all incidents from last month at The Peninsula Manila",
        height=100,
        key="question_input"
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        submit_button = st.button("🚀 Generate & Execute Query", type="primary", use_container_width=True)
    with col2:
        clear_button = st.button("🗑️ Clear", use_container_width=True)
    
    if clear_button:
        st.session_state.current_result = None
        st.rerun()
    
    if submit_button and question:
        # Create progress bar and status text
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        try:
            # Step 1: Preparing request
            status_text.text("🔧 Preparing request...")
            progress_bar.progress(10)
            
            # Prepare request
            request_data = {
                "text": question,
                "context": {
                    "account_uuid": account_uuid,
                    "property_uuid": property_uuid,
                    "language": "en"
                },
                "sql": {
                    "dialect": dialect
                },
                "execution": {
                    "dry_run": dry_run,
                    "max_rows": max_rows
                },
                "model": {
                    "name": "Qwen/Qwen2.5-Coder-7B-Instruct",
                    "temperature": 0.0,
                    "max_tokens": 256
                },
                "trace": {
                    "source": "streamlit-ui"
                }
            }
            
            # Step 2: Generating SQL
            status_text.text("🤖 Generating SQL query (this may take 5-15 seconds)...")
            progress_bar.progress(30)
            
            # Make API request
            result = make_api_request("/nlq/execute", method="POST", data=request_data)
            
            # Step 3: Processing results
            if result:
                status_text.text("📊 Processing results...")
                progress_bar.progress(80)
                
                if not dry_run and result.get("success"):
                    status_text.text("⚡ Executing Athena query...")
                    progress_bar.progress(90)
                
                # Complete
                status_text.text("✅ Complete!")
                progress_bar.progress(100)
                
                st.session_state.current_result = result
                st.session_state.query_history.append({
                    "question": question,
                    "result": result
                })
                
                # Clean up after a short delay
                import time
                time.sleep(0.5)
            
            # Remove progress indicators
            progress_bar.empty()
            status_text.empty()
            
        except Exception as e:
            progress_bar.empty()
            status_text.empty()
            st.error(f"Error: {str(e)}")
    
    # Display results
    if st.session_state.current_result:
        result = st.session_state.current_result
        
        if result.get("success"):
            st.markdown('<div class="success-box">✅ Query executed successfully!</div>', unsafe_allow_html=True)
            
            # SQL Query
            st.subheader("🔧 Generated SQL")
            sql_query = result.get("sql", {}).get("query", "")
            st.code(sql_query, language="sql")
            
            # Confidence and explanation
            col1, col2 = st.columns(2)
            with col1:
                confidence = result.get("sql", {}).get("confidence", 0)
                st.metric("Confidence", f"{confidence:.1%}")
            with col2:
                latency = result.get("trace", {}).get("latency_ms", 0)
                st.metric("Latency", f"{latency:.0f} ms")
            
            # Explanation
            if result.get("explanation"):
                with st.expander("📝 Query Explanation", expanded=False):
                    st.info(result["explanation"])
            
            # Results
            execution = result.get("execution", {})
            if execution.get("executed") and execution.get("data"):
                st.subheader("📊 Results")
                data = execution["data"]
                
                # Show row count
                row_count = data.get("row_count", 0)
                st.caption(f"Showing {row_count} row(s)")
                
                # Display data
                if data.get("rows"):
                    df = pd.DataFrame(data["rows"])
                    
                    # Determine display type
                    display_type = result.get("display", {}).get("type", "table")
                    
                    if display_type == "chart" and len(df.columns) >= 2:
                        # Try to create a chart
                        st.line_chart(df.set_index(df.columns[0]))
                    else:
                        st.dataframe(df, use_container_width=True)
                    
                    # Download button
                    csv = df.to_csv(index=False)
                    st.download_button(
                        label="📥 Download as CSV",
                        data=csv,
                        file_name="query_results.csv",
                        mime="text/csv"
                    )
                else:
                    st.info("Query returned no results")
            elif execution.get("executed"):
                st.info("Query executed successfully but returned no data")
            else:
                st.info("Dry run mode - query not executed")
            
            # Trace information
            with st.expander("🔍 Trace Details", expanded=False):
                trace = result.get("trace", {})
                st.json(trace)
        else:
            error_msg = result.get("error", "Unknown error occurred")
            st.markdown(f'<div class="error-box">❌ {error_msg}</div>', unsafe_allow_html=True)

# Tab 2: Suggestions
with tab2:
    st.header("💡 Query Suggestions")
    st.markdown(f"Suggested queries for **{target}** database")
    
    if st.button("🔄 Refresh Suggestions", key="refresh_suggestions"):
        with st.spinner("Loading suggestions..."):
            suggestions_data = load_suggestions(target)
            if suggestions_data:
                st.session_state.suggestions = suggestions_data
    
    # Auto-load on first visit
    if 'suggestions' not in st.session_state:
        with st.spinner("Loading suggestions..."):
            st.session_state.suggestions = load_suggestions(target)
    
    if st.session_state.get('suggestions'):
        suggestions = st.session_state.suggestions.get('suggestions', [])
        
        if suggestions:
            # Group by category
            categories = {}
            for sugg in suggestions:
                cat = sugg.get('category', 'Other')
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(sugg)
            
            # Display by category
            for category, items in categories.items():
                st.subheader(f"📂 {category}")
                for item in items:
                    query_text = item.get('query', item.get('question', 'Unknown'))
                    with st.expander(f"💬 {query_text}", expanded=False):
                        st.caption(item.get('description', ''))
                        if st.button("Use this question", key=f"use_{query_text[:30]}"):
                            st.session_state.question_input = query_text
                            st.rerun()
        else:
            st.info("No suggestions available")

# Tab 3: Schema
with tab3:
    st.header("📊 Database Schema")
    st.markdown(f"Schema information for **{target}** database")
    
    if st.button("🔄 Refresh Schema", key="refresh_schema"):
        with st.spinner("Loading schema..."):
            schema_data = load_schema(target)
            if schema_data:
                st.session_state.schema = schema_data
    
    # Auto-load on first visit
    if 'schema' not in st.session_state:
        with st.spinner("Loading schema..."):
            st.session_state.schema = load_schema(target)
    
    if st.session_state.get('schema'):
        schema = st.session_state.schema
        
        # Database info
        st.subheader("Database Information")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Database", schema.get('database', 'N/A'))
        with col2:
            st.metric("Tables", len(schema.get('tables', [])))
        
        # Tables
        for table in schema.get('tables', []):
            with st.expander(f"📋 Table: {table['name']}", expanded=False):
                st.caption(table.get('description', 'No description'))
                
                # Columns
                if table.get('columns'):
                    df_cols = pd.DataFrame([
                        {
                            'Column': col['name'],
                            'Type': col['type'],
                            'Description': col.get('description', '')
                        }
                        for col in table['columns']
                    ])
                    st.dataframe(df_cols, use_container_width=True)
                
                # Sample values
                if table.get('sample_values'):
                    st.caption("**Sample Values:**")
                    for col_name, values in table['sample_values'].items():
                        if values:
                            st.text(f"{col_name}: {', '.join(map(str, values[:5]))}")

# Tab 4: History
with tab4:
    st.header("📜 Query History")
    
    if st.session_state.query_history:
        st.caption(f"Total queries: {len(st.session_state.query_history)}")
        
        for i, item in enumerate(reversed(st.session_state.query_history)):
            with st.expander(f"Query {len(st.session_state.query_history) - i}: {item['question'][:50]}...", expanded=False):
                st.markdown(f"**Question:** {item['question']}")
                
                result = item['result']
                if result.get('success'):
                    sql = result.get('sql', {}).get('query', '')
                    st.code(sql, language='sql')
                    
                    execution = result.get('execution', {})
                    if execution.get('data', {}).get('rows'):
                        df = pd.DataFrame(execution['data']['rows'])
                        st.dataframe(df, use_container_width=True)
                else:
                    st.error(result.get('error', 'Unknown error'))
        
        if st.button("🗑️ Clear History"):
            st.session_state.query_history = []
            st.rerun()
    else:
        st.info("No queries in history yet")

# Footer
st.divider()
st.caption("NLQ → Athena Query Interface | Powered by FastAPI + Streamlit")
