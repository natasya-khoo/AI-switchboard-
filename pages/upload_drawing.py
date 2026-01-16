"""
Upload and Analyze Drawings
"""
import streamlit as st
from database import Database
from deepseek_client import DeepSeekClient
from component_matcher import ComponentMatcher
import os
from datetime import datetime

st.set_page_config(page_title="Upload Drawing", page_icon="📤", layout="wide")

st.title("📤 Upload & Analyze Drawing")

# Initialize
if 'db' not in st.session_state:
    st.session_state.db = Database()
    st.session_state.db.connect()

db = st.session_state.db

# Check if project is selected
if not st.session_state.get('current_project'):
    st.warning("⚠️ Please select or create a project first from the Home page")
    st.stop()

project = st.session_state.current_project

st.info(f"📁 Current Project: **{project['project_name']}** ({project['project_code']})")

# Upload section
st.subheader("1️⃣ Upload Drawing")

uploaded_file = st.file_uploader(
    "Select electrical drawing file",
    type=['pdf', 'png', 'jpg', 'jpeg'],
    help="Supported formats: PDF, PNG, JPG"
)

if uploaded_file:
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.subheader("Drawing Preview")
        
        # Save temporarily
        temp_dir = "/tmp/ai_estimator"
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, uploaded_file.name)
        
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.read())
        
        # Display preview
        if uploaded_file.type == "application/pdf":
            from pdf2image import convert_from_path
            images = convert_from_path(temp_path, dpi=150, first_page=1, last_page=1)
            st.image(images[0], use_container_width=True)
        else:
            st.image(temp_path, use_container_width=True)
    
    with col2:
        st.subheader("File Information")
        st.text(f"Filename: {uploaded_file.name}")
        st.text(f"Size: {uploaded_file.size / 1024:.1f} KB")
        st.text(f"Type: {uploaded_file.type}")
        
        st.markdown("---")
        
        # Analysis button
        if st.button("🚀 Analyze with DeepSeek AI", type="primary", use_container_width=True):
            st.session_state.analyze_drawing = True
            st.session_state.temp_drawing_path = temp_path
            st.session_state.drawing_filename = uploaded_file.name

# Analysis section
if st.session_state.get('analyze_drawing'):
    st.markdown("---")
    st.subheader("2️⃣ AI Analysis")
    
    with st.spinner("🤖 DeepSeek AI is analyzing the drawing..."):
        # Initialize DeepSeek client
        client = DeepSeekClient()
        
        # Analyze drawing
        result = client.detect_components(
            st.session_state.temp_drawing_path,
            project['project_code']
        )
        
        if result:
            st.success("✅ Analysis complete!")
            
            # Save to database
            analysis_id = db.save_drawing_analysis(
                project['project_id'],
                st.session_state.drawing_filename,
                result['drawing_info'].get('drawing_type', 'unknown'),
                result
            )
            
            # Save detected components
            matcher = ComponentMatcher(db)
            
            detection_stats = {
                'auto_matched': 0,
                'needs_review': 0,
                'new_items': 0
            }
            
            for component in result['components']:
                # Save detection
                detection_id = db.save_detected_component(
                    analysis_id,
                    project['project_id'],
                    component
                )
                
                # Try to match
                component_id, match_score, match_type = matcher.match_component(component)
                
                if component_id:
                    db.update_detection_match(detection_id, component_id, match_score)
                
                # Update stats
                if match_type == 'auto':
                    detection_stats['auto_matched'] += 1
                elif match_type == 'review':
                    detection_stats['needs_review'] += 1
                else:
                    detection_stats['new_items'] += 1
            
            db.commit()
            
            # Display results
            st.subheader("Analysis Results")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric(
                    "Total Components",
                    len(result['components']),
                    help="Total components detected in drawing"
                )
            
            with col2:
                st.metric(
                    "✅ Auto-Matched",
                    detection_stats['auto_matched'],
                    help="Components automatically matched to library"
                )
            
            with col3:
                st.metric(
                    "⚠️ Needs Review",
                    detection_stats['needs_review'],
                    help="Components with medium confidence match"
                )
            
            with col4:
                st.metric(
                    "🆕 New Items",
                    detection_stats['new_items'],
                    help="Components not found in library"
                )
            
            # Drawing info
            st.markdown("---")
            st.subheader("Drawing Information")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.text(f"Drawing Type: {result['drawing_info'].get('drawing_type', 'N/A')}")
                st.text(f"Voltage System: {result['drawing_info'].get('voltage_system', 'N/A')}")
            
            with col2:
                st.text(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                st.text(f"AI Model: DeepSeek")
            
            # Component preview
            st.markdown("---")
            st.subheader("Detected Components Preview")
            
            import pandas as pd
            df = pd.DataFrame(result['components'])
            
            if not df.empty:
                display_df = df[['itemname', 'itclass', 'qty', 'manufacturer', 'confidence']]
                st.dataframe(display_df, use_container_width=True, hide_index=True)
            
            # Next steps
            st.markdown("---")
            st.success("✨ Ready for review! Go to the **Review Detections** page to verify and approve components.")
            
            if st.button("➡️ Go to Review Page", type="primary"):
                st.switch_page("pages/review_detections.py")
            
            # Reset state
            st.session_state.analyze_drawing = False
        
        else:
            st.error("❌ Analysis failed. Please check your API key and try again.")
            st.session_state.analyze_drawing = False

# Recent analyses
st.markdown("---")
st.subheader("📜 Recent Analyses")

try:
    # Query recent analyses for this project
    if db.cursor is None:
        st.error("Database connection error. Please refresh the page.")
    else:
        db.cursor.execute("""
            SELECT analysis_id, drawing_filename, drawing_type, 
                   total_components_detected, ai_analysis_date
            FROM estimation.drawing_analysis
            WHERE project_id = %s
            ORDER BY ai_analysis_date DESC
            LIMIT 10
        """, (project['project_id'],))
        
        analyses = db.cursor.fetchall()
    
    if analyses:
        import pandas as pd
        df = pd.DataFrame(analyses)
        df['ai_analysis_date'] = pd.to_datetime(df['ai_analysis_date']).dt.strftime('%Y-%m-%d %H:%M')
        
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "analysis_id": "ID",
                "drawing_filename": "Filename",
                "drawing_type": "Type",
                "total_components_detected": "Components",
                "ai_analysis_date": "Analyzed At"
            }
        )
    else:
        st.info("No previous analyses for this project.")

except Exception as e:
    st.error(f"Error loading analyses: {e}")