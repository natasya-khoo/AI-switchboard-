"""
Review and Match Detected Components
"""
import streamlit as st
from database import Database
from component_matcher import ComponentMatcher
import pandas as pd

st.set_page_config(page_title="Review Detections", page_icon="🔍", layout="wide")

st.title("🔍 Review Detected Components")

# Initialize
if 'db' not in st.session_state:
    st.session_state.db = Database()
    st.session_state.db.connect()

db = st.session_state.db
matcher = ComponentMatcher(db)

# Check project
if not st.session_state.get('current_project'):
    st.warning("⚠️ Please select a project first")
    st.stop()

project = st.session_state.current_project

st.info(f"📁 Project: **{project['project_name']}** ({project['project_code']})")

# Get detections
detections = db.get_detections_for_project(project['project_id'])

if not detections:
    st.warning("No detections found for this project. Please upload and analyze a drawing first.")
    
    if st.button("📤 Go to Upload Page"):
        st.switch_page("pages/upload_drawing.py")
    
    st.stop()

# Statistics
st.subheader("Detection Summary")

status_counts = {}
for d in detections:
    status = d['match_status']
    status_counts[status] = status_counts.get(status, 0) + 1

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Detected", len(detections))

with col2:
    st.metric("✅ Matched", status_counts.get('matched', 0))

with col3:
    st.metric("⚠️ Review", status_counts.get('review', 0))

with col4:
    st.metric("🆕 New", status_counts.get('new', 0) + status_counts.get('pending', 0))

# Filters
st.markdown("---")

col1, col2, col3 = st.columns(3)

with col1:
    filter_status = st.selectbox(
        "Filter by Status",
        ["All", "matched", "review", "new", "pending"]
    )

with col2:
    filter_class = st.selectbox(
        "Filter by Class",
        ["All"] + list(set(d['itclass'] for d in detections))
    )

with col3:
    filter_confidence = st.selectbox(
        "Filter by Confidence",
        ["All", "high", "medium", "low"]
    )

# Apply filters
filtered_detections = detections

if filter_status != "All":
    filtered_detections = [d for d in filtered_detections if d['match_status'] == filter_status]

if filter_class != "All":
    filtered_detections = [d for d in filtered_detections if d['itclass'] == filter_class]

if filter_confidence != "All":
    filtered_detections = [d for d in filtered_detections if d['confidence_level'] == filter_confidence]

st.caption(f"Showing {len(filtered_detections)} of {len(detections)} detections")

# Review interface
st.markdown("---")
st.subheader("Component Review")

for idx, detection in enumerate(filtered_detections):
    status_emoji = {
        'matched': '✅',
        'review': '⚠️',
        'new': '🆕',
        'pending': '⏳',
        'rejected': '❌'
    }
    
    emoji = status_emoji.get(detection['match_status'], '❓')
    
    with st.expander(
        f"{emoji} {idx+1}. {detection['itemname']} - Qty: {detection['qty']} - {detection['itclass']}",
        expanded=(detection['match_status'] in ['review', 'new', 'pending'])
    ):
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown("**🤖 AI Detected Information**")
            
            st.text(f"Item Name: {detection['itemname']}")
            st.text(f"Class: {detection['itclass']}")
            st.text(f"Quantity: {detection['qty']}")
            st.text(f"Manufacturer: {detection['manufacturer']}")
            st.text(f"Model: {detection['model_number']}")
            st.text(f"Rating: {detection['rating']}")
            st.text(f"Confidence: {detection['confidence_level']}")
            
            if detection['itemdesc']:
                st.text_area("Description", value=detection['itemdesc'], height=80, disabled=True, key=f"desc_{detection['detection_id']}")
        
        with col2:
            st.markdown("**💾 Database Match**")
            
            if detection['matched_component_id']:
                # Get matched component details
                db.cursor.execute("""
                    SELECT * FROM estimator.component_library
                    WHERE component_id = %s
                """, (detection['matched_component_id'],))
                
                matched = db.cursor.fetchone()
                
                if matched:
                    st.success(f"Match Score: {detection['match_score']:.1f}%")
                    st.text(f"Item Name: {matched['itemname']}")
                    st.text(f"Manufacturer: {matched['manufacturer']}")
                    st.text(f"Model: {matched['model_number']}")
                    st.text(f"Unit Price: ${matched['unit_price']:.2f}")
                    st.text(f"Markup: {matched['markup_pct']:.1f}%")
                    
                    # Action buttons
                    col_a, col_b = st.columns(2)
                    
                    with col_a:
                        if detection['match_status'] == 'review':
                            if st.button("✅ Approve Match", key=f"approve_{detection['detection_id']}"):
                                db.cursor.execute("""
                                    UPDATE estimator.detected_components
                                    SET match_status = 'matched'
                                    WHERE detection_id = %s
                                """, (detection['detection_id'],))
                                db.commit()
                                st.success("Match approved!")
                                st.rerun()
                    
                    with col_b:
                        if st.button("🔄 Find Different Match", key=f"rematch_{detection['detection_id']}"):
                            st.session_state[f"show_suggestions_{detection['detection_id']}"] = True
            
            else:
                st.warning("No match found in database")
                
                # Show suggestions
                suggestions = matcher.get_match_suggestions(detection, limit=5)
                
                if suggestions:
                    st.markdown("**Suggestions:**")
                    
                    for sug_idx, sug in enumerate(suggestions):
                        if st.button(
                            f"[{sug['match_score']:.0f}%] {sug['itemname']} - ${sug['unit_price']:.2f}",
                            key=f"sug_{detection['detection_id']}_{sug_idx}"
                        ):
                            # Apply match
                            db.update_detection_match(
                                detection['detection_id'],
                                sug['component_id'],
                                sug['match_score'],
                                'manual'
                            )
                            db.commit()
                            st.success("Match applied!")
                            st.rerun()
                
                # Add new component option
                st.markdown("---")
                
                if st.button("➕ Add as New Component", key=f"new_{detection['detection_id']}"):
                    st.session_state[f"show_new_form_{detection['detection_id']}"] = True
                
                # New component form
                if st.session_state.get(f"show_new_form_{detection['detection_id']}"):
                    with st.form(f"new_component_{detection['detection_id']}"):
                        st.markdown("**Create New Component**")
                        
                        unit_price = st.number_input("Unit Price ($)", min_value=0.0, step=0.01, value=0.0)
                        markup_pct = st.number_input("Markup (%)", min_value=0.0, max_value=100.0, value=15.0)
                        supplier_code = st.text_input("Supplier Code", value="")
                        
                        col_a, col_b = st.columns(2)
                        
                        with col_a:
                            if st.form_submit_button("Create & Match", type="primary"):
                                # Create component
                                component_data = {
                                    'itemname': detection['itemname'],
                                    'itemdesc': detection['itemdesc'],
                                    'itdesc2': detection['itdesc2'],
                                    'itdesc3': detection['itdesc3'],
                                    'itdesc4': detection['itdesc4'],
                                    'itclass': detection['itclass'],
                                    'manufacturer': detection['manufacturer'],
                                    'model_number': detection['model_number'],
                                    'rating': detection['rating'],
                                    'unit_price': unit_price,
                                    'markup_pct': markup_pct,
                                    'supplier_code': supplier_code,
                                    'lead_time_days': None,
                                    'source': 'ai_created',
                                    'created_by': 'system'
                                }
                                
                                component_id = db.add_component(component_data)
                                
                                # Match detection
                                db.update_detection_match(
                                    detection['detection_id'],
                                    component_id,
                                    100.0,
                                    'manual'
                                )
                                
                                db.commit()
                                st.success(f"Component created and matched! ID: {component_id}")
                                st.rerun()
                        
                        with col_b:
                            if st.form_submit_button("Cancel"):
                                st.session_state[f"show_new_form_{detection['detection_id']}"] = False
                                st.rerun()

# Bulk actions
st.markdown("---")
st.subheader("Bulk Actions")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("✅ Approve All Auto-Matched", type="primary"):
        db.cursor.execute("""
            UPDATE estimator.detected_components
            SET match_status = 'matched'
            WHERE project_id = %s
            AND match_status = 'review'
            AND match_score >= 85
        """, (project['project_id'],))
        db.commit()
        st.success("Auto-matched components approved!")
        st.rerun()

with col2:
    matched_count = status_counts.get('matched', 0)
    if matched_count > 0:
        if st.button(f"💰 Generate BOM ({matched_count} items)", type="secondary"):
            st.switch_page("pages/4_💰_Generate_BOM.py")

with col3:
    if st.button("🔄 Refresh", type="secondary"):
        st.rerun()