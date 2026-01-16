"""
Generate Bill of Materials
"""
import streamlit as st
from database import Database
from config import estimator_config
import pandas as pd
from datetime import datetime
import io

st.set_page_config(page_title="Generate BOM", page_icon="💰", layout="wide")

st.title("💰 Generate Bill of Materials")

# Initialize
if 'db' not in st.session_state:
    st.session_state.db = Database()
    st.session_state.db.connect()

db = st.session_state.db

# Check project
if not st.session_state.get('current_project'):
    st.warning("⚠️ Please select a project first")
    st.stop()

project = st.session_state.current_project

st.info(f"📁 Project: **{project['project_name']}** ({project['project_code']})")

# Tabs
tab1, tab2, tab3 = st.tabs(["🔨 Generate BOM", "📋 View BOM", "📤 Export"])

with tab1:
    st.subheader("Generate BOM from Matched Components")
    
    # Get matched detections
    matched_detections = db.get_detections_for_project(project['project_id'], status='matched')
    
    if not matched_detections:
        st.warning("No matched components found. Please review and approve detections first.")
        
        if st.button("🔍 Go to Review Page"):
            st.switch_page("pages/3_🔍_Review_Detections.py")
        
        st.stop()
    
    st.success(f"Found {len(matched_detections)} matched components ready for BOM")
    
    # Settings
    st.markdown("---")
    st.subheader("BOM Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        labor_rate = st.number_input(
            "Labor Rate ($/hour)",
            min_value=0.0,
            value=float(project.get('labor_rate_per_hour', 80.0)),
            step=1.0
        )
        
        default_markup = st.number_input(
            "Default Markup (%)",
            min_value=0.0,
            max_value=100.0,
            value=float(project.get('default_markup_pct', 15.0)),
            step=1.0
        )
    
    with col2:
        consolidate_duplicates = st.checkbox("Consolidate Duplicate Items", value=True)
        include_labor = st.checkbox("Include Labor Estimation", value=True)
    
    # Preview
    st.markdown("---")
    st.subheader("BOM Preview")
    
    # Build BOM preview
    bom_preview = []
    
    for detection in matched_detections:
        # Get component details
        db.cursor.execute("""
            SELECT * FROM estimator.component_library
            WHERE component_id = %s
        """, (detection['matched_component_id'],))
        
        component = db.cursor.fetchone()
        
        if component:
            # Calculate labor
            labor_hours = 0
            if include_labor:
                comp_class = detection['itclass']
                labor_hours = estimator_config.LABOR_ESTIMATES.get(comp_class, 0.5) * detection['qty']
            
            # Calculate line total
            unit_price = float(component['unit_price'])
            qty = detection['qty']
            markup_pct = float(component['markup_pct'])
            line_total = unit_price * qty
            
            bom_preview.append({
                'detection_id': detection['detection_id'],
                'component_id': component['component_id'],
                'itemname': component['itemname'],
                'itclass': component['itclass'],
                'manufacturer': component['manufacturer'],
                'model_number': component['model_number'],
                'qty': qty,
                'unit_price': unit_price,
                'markup_pct': markup_pct,
                'line_total': line_total,
                'labor_hours': labor_hours,
                'notes': detection.get('notes', '')
            })
    
    if consolidate_duplicates:
        # Consolidate by component_id
        consolidated = {}
        for item in bom_preview:
            comp_id = item['component_id']
            if comp_id in consolidated:
                consolidated[comp_id]['qty'] += item['qty']
                consolidated[comp_id]['line_total'] += item['line_total']
                consolidated[comp_id]['labor_hours'] += item['labor_hours']
            else:
                consolidated[comp_id] = item.copy()
        
        bom_preview = list(consolidated.values())
    
    # Display preview
    if bom_preview:
        df = pd.DataFrame(bom_preview)
        
        # Format for display
        display_df = df.copy()
        display_df['unit_price'] = display_df['unit_price'].apply(lambda x: f"${x:.2f}")
        display_df['line_total'] = display_df['line_total'].apply(lambda x: f"${x:.2f}")
        display_df['labor_hours'] = display_df['labor_hours'].apply(lambda x: f"{x:.2f}h")
        
        st.dataframe(
            display_df[['itemname', 'itclass', 'qty', 'unit_price', 'line_total', 'labor_hours']],
            use_container_width=True,
            hide_index=True
        )
        
        # Calculate totals
        total_materials = sum(item['line_total'] for item in bom_preview)
        total_labor_hours = sum(item['labor_hours'] for item in bom_preview)
        total_labor_cost = total_labor_hours * labor_rate
        subtotal = total_materials + total_labor_cost
        markup_amount = subtotal * (default_markup / 100)
        grand_total = subtotal + markup_amount
        
        # Display totals
        st.markdown("---")
        st.subheader("Cost Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Materials", f"${total_materials:,.2f}")
        
        with col2:
            st.metric("Labor", f"${total_labor_cost:,.2f}", delta=f"{total_labor_hours:.1f}h")
        
        with col3:
            st.metric("Markup", f"${markup_amount:,.2f}", delta=f"{default_markup:.1f}%")
        
        with col4:
            st.metric("Grand Total", f"${grand_total:,.2f}")
        
        # Generate BOM button
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("✅ Generate BOM", type="primary", use_container_width=True):
                with st.spinner("Generating BOM..."):
                    # Delete existing BOM items
                    db.cursor.execute("""
                        DELETE FROM estimator.bom_items
                        WHERE project_id = %s
                    """, (project['project_id'],))
                    
                    # Insert BOM items
                    for idx, item in enumerate(bom_preview, start=1):
                        db.cursor.execute("""
                            INSERT INTO estimator.bom_items (
                                project_id, component_id, qty,
                                unit_price, markup_pct, line_total,
                                estimated_labor_hours, notes,
                                source_detection_id, line_sequence
                            ) VALUES (
                                %s, %s, %s,
                                %s, %s, %s,
                                %s, %s,
                                %s, %s
                            )
                        """, (
                            project['project_id'],
                            item['component_id'],
                            item['qty'],
                            item['unit_price'],
                            item['markup_pct'],
                            item['line_total'],
                            item['labor_hours'],
                            item['notes'],
                            item.get('detection_id'),
                            idx
                        ))
                    
                    # Update project totals
                    db.cursor.execute("""
                        UPDATE estimator.projects
                        SET 
                            total_materials_cost = %s,
                            total_labor_hours = %s,
                            total_labor_cost = %s,
                            total_markup = %s,
                            grand_total = %s,
                            labor_rate_per_hour = %s,
                            default_markup_pct = %s,
                            status = 'reviewed',
                            updated_date = NOW()
                        WHERE project_id = %s
                    """, (
                        total_materials,
                        total_labor_hours,
                        total_labor_cost,
                        markup_amount,
                        grand_total,
                        labor_rate,
                        default_markup,
                        project['project_id']
                    ))
                    
                    db.commit()
                    
                    st.success("✅ BOM Generated Successfully!")
                    st.balloons()
                    
                    # Update session state
                    st.session_state.current_project = db.get_project(project['project_code'])
                    
                    # Switch to View BOM tab
                    st.rerun()
        
        with col2:
            if st.button("🔄 Recalculate", use_container_width=True):
                st.rerun()

with tab2:
    st.subheader("Current BOM")
    
    # Get BOM items
    bom_items = db.get_bom_items(project['project_id'])
    
    if not bom_items:
        st.info("No BOM generated yet. Go to the 'Generate BOM' tab to create one.")
    else:
        # Display BOM
        df = pd.DataFrame(bom_items)
        
        # Format for display
        display_df = df.copy()
        
        # Select and format columns
        columns_to_show = [
            'line_sequence', 'itemname', 'itclass', 'manufacturer', 
            'model_number', 'qty', 'unit_price', 'markup_pct', 'line_total'
        ]
        
        display_df = display_df[columns_to_show]
        display_df['unit_price'] = display_df['unit_price'].apply(lambda x: f"${float(x):.2f}")
        display_df['markup_pct'] = display_df['markup_pct'].apply(lambda x: f"{float(x):.1f}%")
        display_df['line_total'] = display_df['line_total'].apply(lambda x: f"${float(x):.2f}")
        
        st.dataframe(
            display_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "line_sequence": "Line",
                "itemname": "Item Name",
                "itclass": "Class",
                "manufacturer": "Manufacturer",
                "model_number": "Model",
                "qty": "Qty",
                "unit_price": "Unit Price",
                "markup_pct": "Markup",
                "line_total": "Line Total"
            }
        )
        
        # Totals
        st.markdown("---")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Materials", f"${project['total_materials_cost']:,.2f}")
        
        with col2:
            st.metric("Labor", f"${project['total_labor_cost']:,.2f}")
        
        with col3:
            st.metric("Markup", f"${project['total_markup']:,.2f}")
        
        with col4:
            st.metric("Grand Total", f"${project['grand_total']:,.2f}")
        
        # Actions
        st.markdown("---")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("✏️ Edit BOM", use_container_width=True):
                st.info("Edit functionality - coming soon")
        
        with col2:
            if st.button("🗑️ Clear BOM", use_container_width=True):
                if st.session_state.get('confirm_delete'):
                    db.cursor.execute("""
                        DELETE FROM estimator.bom_items
                        WHERE project_id = %s
                    """, (project['project_id'],))
                    db.commit()
                    st.success("BOM cleared")
                    st.session_state.confirm_delete = False
                    st.rerun()
                else:
                    st.session_state.confirm_delete = True
                    st.warning("⚠️ Click again to confirm deletion")
        
        with col3:
            if st.button("🔄 Regenerate", use_container_width=True):
                st.info("Switch to 'Generate BOM' tab to regenerate")

with tab3:
    st.subheader("Export BOM")
    
    # Check if BOM exists
    bom_items = db.get_bom_items(project['project_id'])
    
    if not bom_items:
        st.warning("No BOM to export. Please generate BOM first.")
        st.stop()
    
    st.success(f"Ready to export {len(bom_items)} items")
    
    # Export options
    st.markdown("---")
    
    export_format = st.radio(
        "Export Format",
        ["Excel (For ERP Entry)", "Excel (Full Details)", "CSV"],
        horizontal=True
    )
    
    # Export settings
    with st.expander("Export Settings"):
        include_descriptions = st.checkbox("Include all descriptions", value=True)
        include_labor = st.checkbox("Include labor details", value=True)
        include_costs = st.checkbox("Include cost breakdown", value=True)
        
        # Company header
        company_name = st.text_input("Company Name", value="Cantal Electric Pte Ltd")
        company_address = st.text_area("Company Address", value="")
    
    # Generate export
    st.markdown("---")
    
    if st.button("📥 Generate Export File", type="primary", use_container_width=True):
        with st.spinner("Generating export file..."):
            from utils.excel_export import ExcelExporter
            
            exporter = ExcelExporter()
            
            if export_format == "Excel (For ERP Entry)":
                output = exporter.export_for_erp(
                    project,
                    bom_items,
                    company_name
                )
                filename = f"BOM_ERP_{project['project_code']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            
            elif export_format == "Excel (Full Details)":
                output = exporter.export_detailed(
                    project,
                    bom_items,
                    company_name,
                    company_address
                )
                filename = f"BOM_Detailed_{project['project_code']}_{datetime.now().strftime('%Y%m%d')}.xlsx"
                mime_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            
            else:  # CSV
                output = exporter.export_csv(bom_items)
                filename = f"BOM_{project['project_code']}_{datetime.now().strftime('%Y%m%d')}.csv"
                mime_type = "text/csv"
            
            # Log export
            db.cursor.execute("""
                INSERT INTO estimator.export_log (
                    project_id, export_type, export_format,
                    items_count, exported_by
                ) VALUES (%s, %s, %s, %s, 'user')
            """, (
                project['project_id'],
                export_format.lower(),
                filename.split('.')[-1],
                len(bom_items)
            ))
            db.commit()
            
            # Download button
            st.download_button(
                label="⬇️ Download File",
                data=output,
                file_name=filename,
                mime=mime_type,
                type="primary",
                use_container_width=True
            )
            
            st.success("✅ Export file generated successfully!")
    
    # Export history
    st.markdown("---")
    st.subheader("Export History")
    
    db.cursor.execute("""
        SELECT export_id, export_date, export_type, export_format,
               items_count, erp_entered
        FROM estimator.export_log
        WHERE project_id = %s
        ORDER BY export_date DESC
        LIMIT 10
    """, (project['project_id'],))
    
    exports = db.cursor.fetchall()
    
    if exports:
        df = pd.DataFrame(exports)
        df['export_date'] = pd.to_datetime(df['export_date']).dt.strftime('%Y-%m-%d %H:%M')
        df['erp_entered'] = df['erp_entered'].apply(lambda x: '✅' if x else '⏳')
        
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "export_id": "ID",
                "export_date": "Date",
                "export_type": "Type",
                "export_format": "Format",
                "items_count": "Items",
                "erp_entered": "ERP Status"
            }
        )
    else:
        st.info("No export history yet")