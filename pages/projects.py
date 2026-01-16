"""
Project Management
"""
import streamlit as st
from database import Database
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Projects", page_icon="📊", layout="wide")

st.title("📊 Project Management")

# Initialize BOTH databases
if 'db' not in st.session_state:
    st.session_state.db = Database(use_erp=False)  # Estimator DB
    st.session_state.db.connect()

if 'db_erp' not in st.session_state:
    st.session_state.db_erp = Database(use_erp=True)  # ERP DB (read-only)
    st.session_state.db_erp.connect()

db = st.session_state.db
db_erp = st.session_state.db_erp

# Tabs
tab1, tab2, tab3, tab4 = st.tabs([
    "📋 Estimation Projects", 
    "📥 ERP Projects (SMBE)", 
    "➕ Create New", 
    "📈 Analytics"
])

# ============================================
# TAB 1: ESTIMATION PROJECTS
# ============================================
with tab1:
    st.subheader("Estimation Projects (AI-Generated)")
    st.caption("Projects created in this system with AI component detection")
    
    # Filters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status_filter = st.selectbox(
            "Filter by Status",
            ["All", "draft", "reviewed", "approved", "exported"],
            key="est_status"
        )
    
    with col2:
        sort_by = st.selectbox(
            "Sort by",
            ["Created Date (Newest)", "Created Date (Oldest)", 
             "Total Cost (Highest)", "Total Cost (Lowest)"],
            key="est_sort"
        )
    
    with col3:
        search_query = st.text_input(
            "Search Projects", 
            placeholder="Project code or name...",
            key="est_search"
        )
    
    # Get projects from ESTIMATOR database
    if status_filter == "All":
        projects = db.list_projects()
    else:
        projects = db.list_projects(status=status_filter)
    
    # Apply search
    if search_query:
        projects = [
            p for p in projects
            if search_query.lower() in p['project_code'].lower()
            or search_query.lower() in (p['project_name'] or '').lower()
        ]
    
    # Apply sorting
    if "Newest" in sort_by:
        projects = sorted(projects, key=lambda x: x['created_date'], reverse=True)
    elif "Oldest" in sort_by:
        projects = sorted(projects, key=lambda x: x['created_date'])
    elif "Highest" in sort_by:
        projects = sorted(projects, key=lambda x: x['grand_total'], reverse=True)
    else:  # Lowest
        projects = sorted(projects, key=lambda x: x['grand_total'])
    
    if projects:
        st.caption(f"Showing {len(projects)} estimation projects")
        
        # Display as cards
        for project in projects:
            with st.container():
                col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
                
                with col1:
                    st.markdown(f"### {project['project_name']}")
                    st.caption(f"Code: {project['project_code']}")
                    if project.get('client_name'):
                        st.caption(f"Client: {project['client_name']}")
                
                with col2:
                    status_colors = {
                        'draft': '🟡',
                        'reviewed': '🟢',
                        'approved': '🔵',
                        'exported': '✅'
                    }
                    status_emoji = status_colors.get(project['status'], '⚪')
                    st.metric("Status", f"{status_emoji} {project['status'].title()}")
                
                with col3:
                    st.metric("Total Value", f"${project['grand_total']:,.2f}")
                    st.caption(f"Items: {project.get('total_line_items', 0)}")
                
                with col4:
                    if st.button("📂 Open", key=f"open_{project['project_id']}", use_container_width=True):
                        st.session_state.current_project = project
                        st.success(f"Opened {project['project_code']}")
                        st.rerun()
                
                st.markdown("---")
    
    else:
        st.info("No estimation projects found. Create a new project or import from ERP.")

# ============================================
# TAB 2: ERP PROJECTS (READ-ONLY VIEW)
# ============================================
with tab2:
    st.subheader("ERP Projects (SMBE Database)")
    st.caption("🔒 Read-only view of production projects from smbe.sosopjod")
    
    # Filters
    col1, col2 = st.columns(2)
    
    with col1:
        erp_search = st.text_input(
            "Search ERP Projects",
            placeholder="Project code, customer name...",
            key="erp_search"
        )
    
    with col2:
        erp_limit = st.number_input(
            "Show records",
            min_value=10,
            max_value=500,
            value=50,
            step=10,
            key="erp_limit"
        )
    
    # Query ERP database
    try:
        query = """
            SELECT 
                pjodno,
                pjoddate,
                custname,
                pjdesc,
                amount,
                gstamt,
                pjodstatus,
                quotno,
                salepers,
                deldate
            FROM smbe.sosopjod
            WHERE pjodno IS NOT NULL
        """
        
        if erp_search:
            query += f"""
                AND (
                    pjodno ILIKE '%{erp_search}%'
                    OR custname ILIKE '%{erp_search}%'
                    OR pjdesc ILIKE '%{erp_search}%'
                )
            """
        
        query += f" ORDER BY pjoddate DESC LIMIT {erp_limit}"
        
        db_erp.cursor.execute(query)
        erp_projects = db_erp.cursor.fetchall()
        
        if erp_projects:
            st.success(f"Found {len(erp_projects)} ERP projects")
            
            # Convert to DataFrame for display
            df = pd.DataFrame(erp_projects)
            
            # Format dates
            if 'pjoddate' in df.columns:
                df['pjoddate'] = pd.to_datetime(df['pjoddate']).dt.strftime('%Y-%m-%d')
            if 'deldate' in df.columns:
                df['deldate'] = pd.to_datetime(df['deldate']).dt.strftime('%Y-%m-%d')
            
            # Format amounts
            if 'amount' in df.columns:
                df['amount'] = df['amount'].apply(lambda x: f"${float(x):,.2f}" if x else "$0.00")
            
            # Display table
            st.dataframe(
                df[[
                    'pjodno', 'pjoddate', 'custname', 'pjdesc', 
                    'amount', 'quotno', 'salepers'
                ]],
                use_container_width=True,
                hide_index=True,
                column_config={
                    "pjodno": "Project No",
                    "pjoddate": "Date",
                    "custname": "Customer",
                    "pjdesc": "Description",
                    "amount": "Amount",
                    "quotno": "Quote No",
                    "salepers": "Sales Person"
                }
            )
            
            # Import functionality
            st.markdown("---")
            st.subheader("📥 Import Selected Project")
            
            col1, col2 = st.columns([3, 1])
            
            with col1:
                selected_pjodno = st.selectbox(
                    "Select project to import as estimation template",
                    options=df['pjodno'].tolist(),
                    format_func=lambda x: f"{x} - {df[df['pjodno']==x]['custname'].values[0] or 'No customer'}"
                )
            
            with col2:
                if st.button("📥 Import", type="primary", use_container_width=True):
                    # Get selected project details
                    selected = df[df['pjodno'] == selected_pjodno].iloc[0]
                    
                    # Check if already exists in estimation
                    existing = db.get_project(selected_pjodno)
                    
                    if existing:
                        st.warning(f"⚠️ Project {selected_pjodno} already exists in estimation database")
                    else:
                        try:
                            # Create in estimation database
                            project_id = db.create_project(
                                project_code=selected_pjodno,
                                project_name=selected['pjdesc'] or selected_pjodno,
                                client_name=selected['custname'] or '',
                                created_by='erp_import'
                            )
                            
                            # Update with ERP details
                            db.cursor.execute("""
                                UPDATE estimation.projects
                                SET 
                                    estimate_number = %s,
                                    notes = %s,
                                    status = 'imported'
                                WHERE project_id = %s
                            """, (
                                selected.get('quotno', ''),
                                f"Imported from SMBE on {datetime.now().strftime('%Y-%m-%d')}. Original amount: {selected['amount']}",
                                project_id
                            ))
                            
                            db.commit()
                            
                            st.success(f"✅ Imported {selected_pjodno} as estimation project!")
                            st.balloons()
                            
                            # Option to import items too
                            if st.checkbox("Also import project items from sosopoit?"):
                                items_imported = db.import_project_details_from_erp(selected_pjodno)
                                if items_imported > 0:
                                    st.success(f"✅ Imported {items_imported} items")
                                else:
                                    st.info("No items found or components not in library")
                        
                        except Exception as e:
                            st.error(f"❌ Error importing: {e}")
                            db.rollback()
        
        else:
            st.info("No ERP projects found matching your criteria")
    
    except Exception as e:
        st.error(f"❌ Error accessing ERP database: {e}")
        st.caption("Make sure db_erp connection is active")

# ============================================
# TAB 3: CREATE NEW (Your existing code)
# ============================================
with tab3:
    st.subheader("Create New Estimation Project")
    
    with st.form("create_project_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            project_code = st.text_input(
                "Project Code *",
                placeholder="EST-2025-001",
                help="Unique project identifier"
            )
            
            project_name = st.text_input(
                "Project Name *",
                placeholder="Main Switchboard Upgrade"
            )
            
            estimate_number = st.text_input(
                "Estimate Number",
                placeholder=f"EST-{datetime.now().strftime('%Y%m%d')}"
            )
        
        with col2:
            client_name = st.text_input(
                "Client Name",
                placeholder="ABC Corporation"
            )
            
            labor_rate = st.number_input(
                "Labor Rate ($/hour)",
                min_value=0.0,
                value=80.0,
                step=1.0
            )
            
            markup_pct = st.number_input(
                "Default Markup (%)",
                min_value=0.0,
                max_value=100.0,
                value=15.0,
                step=1.0
            )
        
        notes = st.text_area("Notes", placeholder="Project notes...")
        
        col1, col2 = st.columns(2)
        
        with col1:
            submitted = st.form_submit_button("Create Project", type="primary", use_container_width=True)
        
        with col2:
            reset = st.form_submit_button("Reset", use_container_width=True)
        
        if submitted:
            if not project_code or not project_name:
                st.error("⚠️ Project Code and Project Name are required")
            else:
                try:
                    # Create project
                    project_id = db.create_project(
                        project_code,
                        project_name,
                        client_name,
                        created_by='user'
                    )
                    
                    # Update additional fields
                    db.cursor.execute("""
                        UPDATE estimation.projects
                        SET 
                            labor_rate_per_hour = %s,
                            default_markup_pct = %s,
                            notes = %s,
                            estimate_number = %s
                        WHERE project_id = %s
                    """, (labor_rate, markup_pct, notes, estimate_number, project_id))
                    
                    db.commit()
                    
                    st.success(f"✅ Project {project_code} created successfully!")
                    
                    # Load and set as current project
                    new_project = db.get_project(project_code)
                    st.session_state.current_project = new_project
                    
                    st.balloons()
                
                except Exception as e:
                    st.error(f"❌ Error creating project: {e}")
                    db.rollback()

# ============================================
# TAB 4: ANALYTICS (Your existing code)
# ============================================
with tab4:
    st.subheader("Project Analytics")
    
    # Get all projects from ESTIMATOR only
    all_projects = db.list_projects()
    
    if not all_projects:
        st.info("No estimation projects to analyze yet")
        st.stop()
    
    # Statistics
    total_projects = len(all_projects)
    total_value = sum(p['grand_total'] for p in all_projects)
    avg_project_value = total_value / total_projects if total_projects > 0 else 0
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Estimation Projects", total_projects)
    
    with col2:
        st.metric("Total Estimated Value", f"${total_value:,.2f}")
    
    with col3:
        st.metric("Avg Project Value", f"${avg_project_value:,.2f}")
    
    # Charts
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Projects by Status")
        
        df = pd.DataFrame(all_projects)
        status_counts = df['status'].value_counts()
        st.bar_chart(status_counts)
    
    with col2:
        st.subheader("Project Values Over Time")
        
        df['month'] = pd.to_datetime(df['created_date']).dt.strftime('%Y-%m')
        monthly_values = df.groupby('month')['grand_total'].sum()
        st.line_chart(monthly_values)
    
    # Recent projects table
    st.markdown("---")
    st.subheader("Recent Estimation Projects (Last 10)")
    
    recent_projects = sorted(all_projects, key=lambda x: x['created_date'], reverse=True)[:10]
    
    if recent_projects:
        df = pd.DataFrame(recent_projects)
        df = df[['project_code', 'project_name', 'status', 'created_date', 'grand_total']]
        df['created_date'] = pd.to_datetime(df['created_date']).dt.strftime('%Y-%m-%d')
        df['grand_total'] = df['grand_total'].apply(lambda x: f"${x:,.2f}")
        
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "project_code": "Code",
                "project_name": "Name",
                "status": "Status",
                "created_date": "Created",
                "grand_total": "Total Value"
            }
        )