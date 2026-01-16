-- Connect to your database
\c estimator

-- Create the missing views
CREATE OR REPLACE VIEW estimator.v_project_summary AS
SELECT 
    p.project_id,
    p.project_code,
    p.project_name,
    p.client_name,
    p.status,
    p.created_date,
    p.updated_date,
    COUNT(DISTINCT b.bom_id) as total_line_items,
    SUM(b.qty) as total_components,
    p.total_materials_cost,
    p.total_labor_hours,
    p.total_labor_cost,
    p.total_markup,
    p.grand_total,
    p.created_by
FROM estimator.projects p
LEFT JOIN estimator.bom_items b ON p.project_id = b.project_id
GROUP BY p.project_id;

-- Create complete BOM view
CREATE OR REPLACE VIEW estimator.v_complete_bom AS
SELECT 
    b.project_id,
    p.project_code,
    p.project_name,
    b.bom_id,
    b.line_sequence,
    c.itemname,
    c.itemdesc,
    c.itdesc2,
    c.itdesc3,
    c.itdesc4,
    c.itclass,
    c.manufacturer,
    c.model_number,
    c.rating,
    b.qty,
    b.unit_price,
    b.markup_pct,
    b.line_total,
    b.estimated_labor_hours,
    b.price_override,
    b.notes
FROM estimator.bom_items b
JOIN estimator.projects p ON b.project_id = p.project_id
JOIN estimator.component_library c ON b.component_id = c.component_id
ORDER BY b.project_id, b.line_sequence;

-- Create detection status view
CREATE OR REPLACE VIEW estimator.v_detection_status AS
SELECT 
    d.project_id,
    p.project_code,
    COUNT(*) as total_detected,
    SUM(CASE WHEN d.match_status = 'matched' THEN 1 ELSE 0 END) as auto_matched,
    SUM(CASE WHEN d.match_status = 'review' THEN 1 ELSE 0 END) as needs_review,
    SUM(CASE WHEN d.match_status = 'new' THEN 1 ELSE 0 END) as new_items,
    SUM(CASE WHEN d.match_status = 'rejected' THEN 1 ELSE 0 END) as rejected
FROM estimator.detected_components d
JOIN estimator.projects p ON d.project_id = p.project_id
GROUP BY d.project_id, p.project_code;