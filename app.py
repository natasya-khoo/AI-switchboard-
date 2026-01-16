"""
Cantal Electric - AI Estimation System
Main Streamlit Application
"""
import streamlit as st
from database import Database
from config import db_config, estimator_config
import pandas as pd
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Cantal Electric - AI Estimator",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        padding: 20px 0;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 20px;
        border-radius: 10px;
        margin: 10px 0;
    }
    .success-box {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
        padding: 15px;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #fff3cd;
        border-left: 5px solid #ffc107;
        padding: 15px;
        margin: 10px 0;
    }
    .info-box {
        background-color: #d1ecf1;
        border-left: 5px solid #17a2b8;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'db' not in st.session_state:
    st.session_state.db = Database()
    st.session_state.db.connect()

if 'current_project' not in st.session_state:
    st.session_state.current_project = None

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/200x80?text=Cantal+Electric", use_container_width=True)
    st.title("⚡ AI Estimator")
    st.markdown("---")
    
    # Project selector
    st.subheader("Current Project")
    
    db = st.session_state.db
    projects = db.list_projects()
    
    if projects:
        project_options = {p['project_code']: p['project_name'] for p in projects}
        
        selected_code = st.selectbox(
            "Select Project",
            options=[''] + list(project_options.keys()),
            format_func=lambda x: project_options.get(x, '-- New Project --')
        )
        
        if selected_code:
            st.session_state.current_project = db.get_project(selected_code)
            
            if st.session_state.current_project:
                st.success(f"✓ {st.session_state.current_project['project_name']}")
                st.caption(f"Status: {st.session_state.current_project['status']}")
    
    st.markdown("---")
    
    # Quick actions
    st.subheader("Quick Actions")
    
    if st.button("➕ New Project", use_container_width=True):
        st.session_state.show_new_project = True
    
    if st.button("📥 Import from ERP", use_container_width=True):
        with st.spinner("Importing from ERP..."):
            count = db.import_from_erp(limit=100)
            db.commit()
            st.success(f"Imported {count} components")
    
    st.markdown("---")
    
    # Database status
    st.subheader("Database Status")
    
    try:
        components = db.get_all_components()
        st.metric("Components in Library", len(components))
        
        if projects:
            st.metric("Total Projects", len(projects))
    except Exception as e:
        st.error(f"DB Error: {e}")

# Main content
st.markdown('<div class="main-header">⚡ Cantal Electric AI Estimation System</div>', unsafe_allow_html=True)

# New project dialog
if st.session_state.get('show_new_project', False):
    with st.form("new_project_form"):
        st.subheader("Create New Project")
        
        col1, col2 = st.columns(2)
        
        with col1:
            project_code = st.text_input("Project Code *", placeholder="P2025001")
            project_name = st.text_input("Project Name", placeholder="Main Switchboard Project")
        
        with col2:
            client_name = st.text_input("Client Name", placeholder="ABC Corporation")
            estimate_number = st.text_input("Estimate Number", placeholder=f"EST-{datetime.now().strftime('%Y%m%d')}")
        
        col1, col2 = st.columns(2)
        
        with col1:
            submitted = st.form_submit_button("Create Project", type="primary", use_container_width=True)
        
        with col2:
            cancelled = st.form_submit_button("Cancel", use_container_width=True)
        
        if submitted and project_code:
            try:
                project_id = db.create_project(project_code, project_name, client_name)
                db.commit()
                st.success(f"✓ Project {project_code} created!")
                st.session_state.show_new_project = False
                st.session_state.current_project = db.get_project(project_code)
                st.rerun()
            except Exception as e:
                st.error(f"Error creating project: {e}")
        
        if cancelled:
            st.session_state.show_new_project = False
            st.rerun()

# Dashboard
if st.session_state.current_project:
    project = st.session_state.current_project
    
    st.subheader(f"📊 Dashboard: {project['project_name']}")
    
    # Metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Materials Cost",
            f"${project['total_materials_cost']:,.2f}"
        )
    
    with col2:
        st.metric(
            "Labor Hours",
            f"{project['total_labor_hours']:.1f}h"
        )
    
    with col3:
        st.metric(
            "Labor Cost",
            f"${project['total_labor_cost']:,.2f}"
        )
    
    with col4:
        st.metric(
            "Grand Total",
            f"${project['grand_total']:,.2f}",
            delta=f"{project['default_markup_pct']}% markup"
        )
    
    st.markdown("---")
    
    # Recent activity
    tab1, tab2, tab3 = st.tabs(["📋 BOM Items", "🔍 Detections", "📄 Drawings"])
    
    with tab1:
        bom_items = db.get_bom_items(project['project_id'])
        
        if bom_items:
            df = pd.DataFrame(bom_items)
            
            # Format currency columns
            if 'unit_price' in df.columns:
                df['unit_price'] = df['unit_price'].apply(lambda x: f"${x:.2f}")
            if 'line_total' in df.columns:
                df['line_total'] = df['line_total'].apply(lambda x: f"${x:.2f}")
            
            st.dataframe(
                df[['itemname', 'itclass', 'qty', 'unit_price', 'line_total']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No BOM items yet. Upload a drawing to get started.")
    
    with tab2:
        detections = db.get_detections_for_project(project['project_id'])
        
        if detections:
            # Status breakdown
            status_counts = {}
            for d in detections:
                status = d['match_status']
                status_counts[status] = status_counts.get(status, 0) + 1
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Total Detected", len(detections))
            with col2:
                st.metric("Auto-Matched", status_counts.get('matched', 0))
            with col3:
                st.metric("Needs Review", status_counts.get('review', 0))
            with col4:
                st.metric("New Items", status_counts.get('new', 0))
            
            # Detections table
            df = pd.DataFrame(detections)
            st.dataframe(
                df[['itemname', 'itclass', 'qty', 'confidence_level', 'match_status']],
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No detections yet. Upload a drawing to analyze.")
    
    with tab3:
        st.info("Drawing analysis feature - coming soon")

else:
    # Welcome screen
    st.markdown("""
    <div class="info-box">
        <h3>👋 Welcome to Cantal Electric AI Estimator</h3>
        <p>Get started by creating a new project or selecting an existing one from the sidebar.</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.subheader("🚀 Features")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        ### 🤖 AI-Powered Detection
        - DeepSeek AI analyzes electrical drawings
        - Automatic component recognition
        - High accuracy detection
        """)
    
    with col2:
        st.markdown("""
        ### 📚 Component Library
        - Import from existing ERP
        - Fuzzy matching algorithm
        - Price and markup tracking
        """)
    
    with col3:
        st.markdown("""
        ### 💰 Auto BOM Generation
        - Instant bill of materials
        - Labor estimation
        - Excel export for ERP entry
        """)
    
    st.markdown("---")
    
    # Recent projects
    if projects:
        st.subheader("📊 Recent Projects")
        
        df = pd.DataFrame(projects)
        df = df[['project_code', 'project_name', 'status', 'created_date', 'grand_total']]
        df['grand_total'] = df['grand_total'].apply(lambda x: f"${x:,.2f}")
        df['created_date'] = pd.to_datetime(df['created_date']).dt.strftime('%Y-%m-%d')
        
        st.dataframe(df, use_container_width=True, hide_index=True)

# Footer
st.markdown("---")
st.caption("Cantal Electric AI Estimator v1.0 | Powered by DeepSeek AI")