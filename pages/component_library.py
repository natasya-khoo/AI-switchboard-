"""
Component Library Management with ERP Import
"""
import streamlit as st
import sys
sys.path.append('..')
from database import Database
import pandas as pd

st.set_page_config(page_title="Component Library", page_icon="📚", layout="wide")

st.title("📚 Component Library")

# Initialize database
if 'db' not in st.session_state:
    st.session_state.db = Database(use_erp=False)
    st.session_state.db.connect()

db = st.session_state.db

# Tabs
tab1, tab2, tab3 = st.tabs(["📋 Browse", "➕ Add New", "📊 Statistics"])

# ============================================
# TAB 1: BROWSE COMPONENTS
# ============================================
with tab1:
    st.subheader("Component Library")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        itclass_filter = st.selectbox(
            "Component Class",
            ["All", "MCB", "MCCB", "CONTACTOR", "RELAY", "BUSBAR", "TERMINAL", "CABLE", "TRANSFORMER", "OTHER"]
        )
    
    with col2:
        search_query = st.text_input("Search", placeholder="Search components...")
    
    with col3:
        show_inactive = st.checkbox("Show Inactive", value=False)
    
    # Get components
    if itclass_filter == "All":
        components = db.get_all_components()
    else:
        components = db.get_all_components(itclass=itclass_filter)
    
    # Apply search
    if search_query:
        components = [
            c for c in components
            if search_query.lower() in c['itemname'].lower()
            or search_query.lower() in (c['manufacturer'] or '').lower()
            or search_query.lower() in (c['model_number'] or '').lower()
        ]
    
    # Filter inactive
    if not show_inactive:
        components = [c for c in components if c.get('is_active', True)]
    
    if components:
        st.success(f"Found {len(components)} components")
        
        # Display as table
        df = pd.DataFrame(components)
        display_df = df[[
            'itemname', 'manufacturer', 'model_number', 'itclass', 
            'rating', 'unit_price', 'markup_pct', 'supplier_code'
        ]]
        
        st.dataframe(
            display_df,
            width='stretch',
            hide_index=True,
            column_config={
                "itemname": "Item Name",
                "manufacturer": "Manufacturer",
                "model_number": "Model",
                "itclass": "Class",
                "rating": "Rating",
                "unit_price": st.column_config.NumberColumn("Unit Price", format="$%.2f"),
                "markup_pct": st.column_config.NumberColumn("Markup %", format="%.1f%%"),
                "supplier_code": "Supplier Code"
            }
        )
    
    else:
        st.info("No components found. Try adjusting your filters or import from ERP.")

# ============================================
# TAB 2: ADD NEW / IMPORT
# ============================================
with tab2:
    st.subheader("Add Components")
    
    # Import section at the top
    st.markdown("### 📥 Import from ERP Database")
    
    st.info("💡 Import components from **CS database → smbe.sosopiac** table")
    
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        import_limit = st.number_input(
            "Number of components to import",
            min_value=10,
            max_value=10000,
            value=100,
            step=50,
            help="Start with 100 for testing, then increase"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)
        import_all = st.checkbox("Import All", help="Import all unique stock codes (no limit)")
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        
        if st.button("📥 Import Now", type="primary", width='stretch'):
            limit = None if import_all else import_limit
            
            with st.spinner(f"Importing from sosopiac..."):
                try:
                    # Create progress placeholder
                    progress_text = st.empty()
                    progress_bar = st.progress(0)
                    
                    progress_text.text("Connecting to ERP database...")
                    progress_bar.progress(10)
                    
                    # Run import
                    imported_count = db.import_stock_items_from_erp(limit=limit)
                    
                    progress_bar.progress(100)
                    
                    if imported_count > 0:
                        st.success(f"✅ Successfully imported {imported_count} components!")
                        st.balloons()
                        
                        # Show sample of imported data
                        st.markdown("#### Sample of Imported Components")
                        recent = db.get_all_components()[-10:]  # Last 10
                        if recent:
                            sample_df = pd.DataFrame(recent)[['itemname', 'manufacturer', 'itclass', 'unit_price']]
                            st.dataframe(sample_df, width='stretch', hide_index=True)
                        
                        st.info("🔄 Refresh the page to see all imported components in the Browse tab")
                    else:
                        st.warning("⚠️ No new components imported. All components may already exist in the library.")
                
                except Exception as e:
                    st.error(f"❌ Error importing from ERP: {str(e)}")
                    st.exception(e)
    
    st.markdown("---")
    
    # Manual add section
    st.markdown("### ➕ Add Component Manually")
    
    with st.form("add_component_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            itemname = st.text_input(
                "Item Name *",
                placeholder="MCB-3P-63A-SCH",
                help="Unique component identifier"
            )
            
            manufacturer = st.text_input(
                "Manufacturer *",
                placeholder="Schneider"
            )
            
            model_number = st.text_input(
                "Model Number",
                placeholder="NSX250F"
            )
            
            itclass = st.selectbox(
                "Component Class *",
                ["MCB", "MCCB", "CONTACTOR", "RELAY", "BUSBAR", 
                 "TERMINAL", "CABLE", "TRANSFORMER", "PANEL", "OTHER"]
            )
            
            rating = st.text_input(
                "Rating",
                placeholder="63A 3P 415V"
            )
        
        with col2:
            unit_price = st.number_input(
                "Unit Price ($) *",
                min_value=0.0,
                value=0.0,
                step=0.01,
                format="%.2f"
            )
            
            markup_pct = st.number_input(
                "Default Markup (%)",
                min_value=0.0,
                max_value=200.0,
                value=15.0,
                step=1.0
            )
            
            supplier_code = st.text_input(
                "Supplier/Stock Code",
                placeholder="Internal stock code"
            )
            
            lead_time_days = st.number_input(
                "Lead Time (days)",
                min_value=0,
                max_value=365,
                value=7,
                step=1
            )
        
        itemdesc = st.text_area(
            "Description",
            placeholder="Detailed component description...",
            height=100
        )
        
        col1, col2, col3 = st.columns([2, 1, 1])
        
        with col1:
            st.caption("* Required fields")
        
        with col2:
            submitted = st.form_submit_button("➕ Add Component", type="primary", width='stretch')
        
        with col3:
            reset = st.form_submit_button("🔄 Reset", width='stretch')
        
        if submitted:
            if not itemname or not manufacturer or not itclass:
                st.error("⚠️ Item Name, Manufacturer, and Component Class are required")
            else:
                try:
                    component_data = {
                        'itemname': itemname,
                        'itemdesc': itemdesc,
                        'itdesc2': '',
                        'itdesc3': '',
                        'itdesc4': '',
                        'itclass': itclass,
                        'manufacturer': manufacturer,
                        'model_number': model_number or 'Unknown',
                        'rating': rating,
                        'unit_price': unit_price,
                        'markup_pct': markup_pct,
                        'supplier_code': supplier_code,
                        'lead_time_days': lead_time_days if lead_time_days > 0 else None,
                        'source': 'manual',
                        'created_by': 'user'
                    }
                    
                    component_id = db.add_component(component_data)
                    db.commit()
                    
                    st.success(f"✅ Component '{itemname}' added successfully! (ID: {component_id})")
                    st.balloons()
                    
                    st.info("Switch to the Browse tab to see your new component")
                
                except Exception as e:
                    st.error(f"❌ Error adding component: {str(e)}")
                    db.rollback()

# ============================================
# TAB 3: STATISTICS
# ============================================
with tab3:
    st.subheader("Component Library Statistics")
    
    # Get all components
    all_components = db.get_all_components()
    
    if not all_components:
        st.info("📭 No components in library yet. Import from ERP or add manually.")
        st.stop()
    
    df = pd.DataFrame(all_components)
    
    # Convert decimal types to float for charting
    if 'unit_price' in df.columns:
        df['unit_price'] = df['unit_price'].astype(float)
    if 'markup_pct' in df.columns:
        df['markup_pct'] = df['markup_pct'].astype(float)
    
    # Statistics
    total_components = len(df)
    avg_price = df['unit_price'].mean()
    total_value = df['unit_price'].sum()
    unique_manufacturers = df['manufacturer'].nunique()
    unique_classes = df['itclass'].nunique()
    
    # Metrics row
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Total Components", f"{total_components:,}")
    
    with col2:
        st.metric("Avg Unit Price", f"${avg_price:.2f}")
    
    with col3:
        st.metric("Total Value", f"${total_value:,.2f}")
    
    with col4:
        st.metric("Manufacturers", unique_manufacturers)
    
    with col5:
        st.metric("Component Classes", unique_classes)
    
    # Charts
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Components by Class")
        class_counts = df['itclass'].value_counts().head(10)
        st.bar_chart(class_counts)
    
    with col2:
        st.subheader("🏭 Components by Manufacturer")
        mfg_counts = df['manufacturer'].value_counts().head(10)
        st.bar_chart(mfg_counts)
    
    # Top expensive components
    st.markdown("---")
    st.subheader("💰 Top 10 Most Expensive Components")
    
    top_expensive = df.nlargest(10, 'unit_price')[
        ['itemname', 'manufacturer', 'itclass', 'unit_price']
    ].copy()
    top_expensive['unit_price'] = top_expensive['unit_price'].apply(lambda x: f"${x:.2f}")
    
    st.dataframe(
        top_expensive,
        width='stretch',
        hide_index=True,
        column_config={
            "itemname": "Component",
            "manufacturer": "Manufacturer",
            "itclass": "Class",
            "unit_price": "Unit Price"
        }
    )
    
    # Source breakdown
    st.markdown("---")
    st.subheader("📦 Components by Source")
    
    if 'source' in df.columns:
        source_counts = df['source'].value_counts()
        
        col1, col2 = st.columns([1, 2])
        
        with col1:
            for source, count in source_counts.items():
                pct = (count / total_components) * 100
                st.metric(
                    str(source).replace('_', ' ').title(),
                    f"{count}",
                    f"{pct:.1f}%"
                )
        
        with col2:
            st.bar_chart(source_counts)
    
    # Price distribution
    st.markdown("---")
    st.subheader("💵 Price Distribution")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Min Price", f"${df['unit_price'].min():.2f}")
    
    with col2:
        st.metric("Median Price", f"${df['unit_price'].median():.2f}")
    
    with col3:
        st.metric("Max Price", f"${df['unit_price'].max():.2f}")
    
    # Price histogram
    st.line_chart(df['unit_price'].value_counts().sort_index())