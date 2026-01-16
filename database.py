"""
Database operations for AI Estimator
"""
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import List, Dict, Optional
from config import db_config

class Database:
    """Handle database connections and operations"""
    
    def __init__(self, use_erp=False):
        """Initialize database connection"""
        if use_erp:
            self.config = {
                'dbname': db_config.ERP_DB_NAME,
                'user': db_config.ERP_DB_USER,
                'password': db_config.ERP_DB_PASSWORD,
                'host': db_config.ERP_DB_HOST,
                'port': db_config.ERP_DB_PORT
            }
        else:
            self.config = {
                'dbname': db_config.AI_DB_NAME,
                'user': db_config.AI_DB_USER,
                'password': db_config.AI_DB_PASSWORD,
                'host': db_config.AI_DB_HOST,
                'port': db_config.AI_DB_PORT
            }
        
        self.conn = None
        self.cursor = None
    
    def connect(self):
        """Establish database connection"""
        try:
            self.conn = psycopg2.connect(**self.config)
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            return True
        except Exception as e:
            print(f"Database connection error: {e}")
            return False
    
    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()
    
    def commit(self):
        """Commit transaction"""
        if self.conn:
            self.conn.commit()
    
    def rollback(self):
        """Rollback transaction"""
        if self.conn:
            self.conn.rollback()
    
    # ============================================
    # Component Library Operations
    # ============================================
    
    def search_components(self, search_term: str, itclass: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """Search component library"""
        if itclass:
            query = """
                SELECT * FROM estimation.component_library
                WHERE itclass = %s
                AND (
                    search_vector @@ plainto_tsquery('english', %s)
                    OR itemname ILIKE %s
                    OR manufacturer ILIKE %s
                    OR model_number ILIKE %s
                )
                AND is_active = TRUE
                ORDER BY created_date DESC
                LIMIT %s
            """
            self.cursor.execute(query, (
                itclass, search_term, 
                f"%{search_term}%", f"%{search_term}%", f"%{search_term}%",
                limit
            ))
        else:
            query = """
                SELECT * FROM estimation.component_library
                WHERE (
                    search_vector @@ plainto_tsquery('english', %s)
                    OR itemname ILIKE %s
                    OR manufacturer ILIKE %s
                    OR model_number ILIKE %s
                )
                AND is_active = TRUE
                ORDER BY created_date DESC
                LIMIT %s
            """
            self.cursor.execute(query, (
                search_term, 
                f"%{search_term}%", f"%{search_term}%", f"%{search_term}%",
                limit
            ))
        
        return self.cursor.fetchall()
    
    def get_all_components(self, itclass: Optional[str] = None) -> List[Dict]:
        """Get all components, optionally filtered by class"""
        if itclass:
            query = """
                SELECT * FROM estimation.component_library
                WHERE itclass = %s AND is_active = TRUE
                ORDER BY itemname
            """
            self.cursor.execute(query, (itclass,))
        else:
            query = """
                SELECT * FROM estimation.component_library
                WHERE is_active = TRUE
                ORDER BY itemname
            """
            self.cursor.execute(query)
        
        return self.cursor.fetchall()
    
    def add_component(self, component_data: Dict) -> int:
        """Add new component to library"""
        query = """
            INSERT INTO estimation.component_library (
                itemname, itemdesc, itdesc2, itdesc3, itdesc4,
                itclass, manufacturer, model_number, rating,
                unit_price, markup_pct, supplier_code, lead_time_days,
                source, created_by
            ) VALUES (
                %(itemname)s, %(itemdesc)s, %(itdesc2)s, %(itdesc3)s, %(itdesc4)s,
                %(itclass)s, %(manufacturer)s, %(model_number)s, %(rating)s,
                %(unit_price)s, %(markup_pct)s, %(supplier_code)s, %(lead_time_days)s,
                %(source)s, %(created_by)s
            )
            RETURNING component_id
        """
        
        self.cursor.execute(query, component_data)
        return self.cursor.fetchone()['component_id']
    
    # ============================================
    # Project Operations
    # ============================================
    
    def create_project(self, project_code: str, project_name: str = None, 
                      client_name: str = None, created_by: str = 'system') -> int:
        """Create new project"""
        query = """
            INSERT INTO estimation.projects (
                project_code, project_name, client_name, created_by
            ) VALUES (%s, %s, %s, %s)
            ON CONFLICT (project_code) 
            DO UPDATE SET updated_date = NOW()
            RETURNING project_id
        """
        
        self.cursor.execute(query, (
            project_code,
            project_name or f"Project {project_code}",
            client_name,
            created_by
        ))
        
        return self.cursor.fetchone()['project_id']
    
    def get_project(self, project_code: str) -> Optional[Dict]:
        """Get project by code"""
        query = """
            SELECT * FROM estimation.projects
            WHERE project_code = %s
        """
        self.cursor.execute(query, (project_code,))
        return self.cursor.fetchone()
    
    def list_projects(self, status: Optional[str] = None) -> List[Dict]:
        """List all projects"""
        if status:
            query = """
                SELECT * FROM estimation.v_project_summary
                WHERE status = %s
                ORDER BY created_date DESC
            """
            self.cursor.execute(query, (status,))
        else:
            query = """
                SELECT * FROM estimation.v_project_summary
                ORDER BY created_date DESC
            """
            self.cursor.execute(query)
        
        return self.cursor.fetchall()
    
    # ============================================
    # Detection Operations
    # ============================================
    
    def save_drawing_analysis(self, project_id: int, drawing_filename: str,
                             drawing_type: str, ai_response: Dict) -> int:
        """Save drawing analysis results"""
        query = """
            INSERT INTO estimation.drawing_analysis (
                project_id, drawing_filename, drawing_type,
                ai_raw_response, total_components_detected, status
            ) VALUES (%s, %s, %s, %s, %s, 'processed')
            RETURNING analysis_id
        """
        
        import json
        self.cursor.execute(query, (
            project_id,
            drawing_filename,
            drawing_type,
            json.dumps(ai_response),
            len(ai_response.get('components', []))
        ))
        
        return self.cursor.fetchone()['analysis_id']
    
    def save_detected_component(self, analysis_id: int, project_id: int,
                               component_data: Dict) -> int:
        """Save detected component"""
        query = """
            INSERT INTO estimation.detected_components (
                analysis_id, project_id,
                itemname, itemdesc, itdesc2, itdesc3, itdesc4,
                itclass, qty, manufacturer, model_number, rating,
                notes, confidence_level, location_on_drawing
            ) VALUES (
                %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s
            )
            RETURNING detection_id
        """
        
        self.cursor.execute(query, (
            analysis_id, project_id,
            component_data.get('itemname', ''),
            component_data.get('itemdesc', ''),
            component_data.get('itdesc2', ''),
            component_data.get('itdesc3', ''),
            component_data.get('itdesc4', ''),
            component_data.get('itclass', 'OTHER'),
            component_data.get('qty', 1),
            component_data.get('manufacturer', 'Unknown'),
            component_data.get('model_number', 'Unknown'),
            component_data.get('rating', ''),
            component_data.get('notes', ''),
            component_data.get('confidence', 'medium'),
            component_data.get('location_on_drawing', '')
        ))
        
        return self.cursor.fetchone()['detection_id']
    
    def update_detection_match(self, detection_id: int, component_id: int,
                              match_score: float, match_method: str = 'auto'):
        """Update detection with matched component"""
        query = """
            UPDATE estimation.detected_components
            SET matched_component_id = %s,
                match_score = %s,
                match_method = %s,
                match_status = CASE 
                    WHEN %s >= 85 THEN 'matched'
                    WHEN %s >= 70 THEN 'review'
                    ELSE 'pending'
                END,
                matched_date = NOW()
            WHERE detection_id = %s
        """
        
        self.cursor.execute(query, (
            component_id, match_score, match_method,
            match_score, match_score, detection_id
        ))
    
    def get_detections_for_project(self, project_id: int, 
                                   status: Optional[str] = None) -> List[Dict]:
        """Get all detections for a project"""
        if status:
            query = """
                SELECT * FROM estimation.detected_components
                WHERE project_id = %s AND match_status = %s
                ORDER BY detection_id
            """
            self.cursor.execute(query, (project_id, status))
        else:
            query = """
                SELECT * FROM estimation.detected_components
                WHERE project_id = %s
                ORDER BY detection_id
            """
            self.cursor.execute(query, (project_id,))
        
        return self.cursor.fetchall()
    
    # ============================================
    # BOM Operations
    # ============================================
    
    def add_bom_item(self, project_id: int, component_id: int, qty: int,
                    unit_price: float, markup_pct: float, 
                    labor_hours: float = 0, notes: str = '',
                    source_detection_id: Optional[int] = None) -> int:
        """Add item to BOM"""
        query = """
            INSERT INTO estimation.bom_items (
                project_id, component_id, qty,
                unit_price, markup_pct,
                line_total, estimated_labor_hours,
                notes, source_detection_id
            ) VALUES (
                %s, %s, %s,
                %s, %s,
                %s * %s, %s,
                %s, %s
            )
            RETURNING bom_id
        """
        
        self.cursor.execute(query, (
            project_id, component_id, qty,
            unit_price, markup_pct,
            qty, unit_price, labor_hours,
            notes, source_detection_id
        ))
        
        return self.cursor.fetchone()['bom_id']
    
    def get_bom_items(self, project_id: int) -> List[Dict]:
        """Get all BOM items for project"""
        query = """
            SELECT * FROM estimation.v_complete_bom
            WHERE project_id = %s
            ORDER BY line_sequence
        """
        self.cursor.execute(query, (project_id,))
        return self.cursor.fetchall()
    
    # ============================================
    # ERP Read Operations (for displaying data)
    # ============================================
    
    def get_erp_projects(self, limit: int = 100, search: Optional[str] = None) -> List[Dict]:
        """Get projects from ERP database (READ ONLY)"""
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
        
        params = []
        
        if search:
            query += """
                AND (
                    pjodno ILIKE %s
                    OR custname ILIKE %s
                    OR pjdesc ILIKE %s
                )
            """
            search_param = f'%{search}%'
            params.extend([search_param, search_param, search_param])
        
        query += " ORDER BY pjoddate DESC LIMIT %s"
        params.append(limit)
        
        self.cursor.execute(query, params)
        return self.cursor.fetchall()
    
    def get_erp_project_items(self, pjodno: str) -> List[Dict]:
        """Get items for a specific ERP project (READ ONLY)"""
        query = """
            SELECT 
                seqno,
                itemname,
                itemdesc,
                itdesc2,
                itdesc3,
                itdesc4,
                itclass,
                qty,
                unitprc,
                markup,
                notes,
                sindex
            FROM smbe.sosopoit
            WHERE parentky = %s
            AND itemname IS NOT NULL
            ORDER BY seqno
        """
        
        self.cursor.execute(query, (pjodno,))
        return self.cursor.fetchall()
    
    def get_erp_item_components(self, sosopoit_sindex: str) -> List[Dict]:
        """Get components for a specific ERP item (READ ONLY)"""
        query = """
            SELECT 
                stkcode,
                qty,
                unitprc,
                sec
            FROM smbe.sosopiac
            WHERE parentky = %s
            ORDER BY sec
        """
        
        self.cursor.execute(query, (sosopoit_sindex,))
        return self.cursor.fetchall()
    
    # ============================================
    # ERP Import Operations
    # ============================================
    
    def import_from_erp(self, limit: Optional[int] = None) -> int:
        """Import components from ERP database (sosopoit items)"""
        erp_db = Database(use_erp=True)
        
        if not erp_db.connect():
            print("Failed to connect to ERP database")
            return 0
        
        # Get unique items from sosopoit
        query = """
            SELECT DISTINCT ON (itemname, COALESCE(itclass, 'OTHER'))
                itemname, itemdesc, itdesc2, itdesc3, itdesc4,
                itclass, unitprc, markup, sindex
            FROM smbe.sosopoit
            WHERE itemname IS NOT NULL AND itemname != ''
            ORDER BY itemname, COALESCE(itclass, 'OTHER'), NDATE DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        erp_db.cursor.execute(query)
        rows = erp_db.cursor.fetchall()
        
        imported = 0
        
        for row in rows:
            # Parse manufacturer and model from itemname
            parts = row['itemname'].split()
            manufacturer = "Unknown"
            model_number = "Unknown"
            
            known_manufacturers = ['Schneider', 'ABB', 'Siemens', 'Legrand', 'Hager', 'GE']
            for mfg in known_manufacturers:
                if mfg in row['itemname']:
                    manufacturer = mfg
                    # Try to extract model
                    if len(parts) > 1:
                        model_number = parts[-1]
                    break
            
            component_data = {
                'itemname': row['itemname'],
                'itemdesc': row['itemdesc'] or '',
                'itdesc2': row['itdesc2'] or '',
                'itdesc3': row['itdesc3'] or '',
                'itdesc4': row['itdesc4'] or '',
                'itclass': row['itclass'] or 'OTHER',
                'manufacturer': manufacturer,
                'model_number': model_number,
                'rating': '',
                'unit_price': float(row['unitprc']) if row['unitprc'] else 0.0,
                'markup_pct': float(row['markup']) if row['markup'] else 15.0,
                'supplier_code': '',
                'lead_time_days': None,
                'source': 'imported',
                'created_by': 'erp_import'
            }
            
            try:
                # Check if already exists
                existing = self.search_components(row['itemname'], row['itclass'], limit=1)
                
                if not existing:
                    self.add_component(component_data)
                    imported += 1
            except Exception as e:
                print(f"Error importing {row['itemname']}: {e}")
                continue
        
        self.commit()
        erp_db.close()
        
        return imported
    
    def import_stock_items_from_erp(self, limit: Optional[int] = None) -> int:
        """
        Import stock items (component library) from sosopiac table
        """
        erp_db = Database(use_erp=True)
        
        if not erp_db.connect():
            print("Failed to connect to ERP database")
            return 0
        
        # Get unique stock items with pricing info
        query = """
            SELECT 
                stkcode,
                AVG(unitprc) as avg_price,
                MAX(unitprc) as max_price,
                MIN(unitprc) as min_price,
                COUNT(*) as usage_count,
                MAX(NDATE) as last_used
            FROM smbe.sosopiac
            WHERE stkcode IS NOT NULL 
            AND stkcode != ''
            AND unitprc IS NOT NULL
            AND unitprc > 0
            GROUP BY stkcode
            ORDER BY usage_count DESC, last_used DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        try:
            erp_db.cursor.execute(query)
            rows = erp_db.cursor.fetchall()
        except Exception as e:
            print(f"Error querying sosopiac: {e}")
            erp_db.close()
            return 0
        
        imported = 0
        skipped = 0
        
        print(f"Found {len(rows)} unique stock items in sosopiac...")
        
        for row in rows:
            stkcode = row['stkcode']
            
            # Parse stkcode to extract component details
            # Example formats: "MCB-3P-63A-SCH", "CONTACTOR-40A-ABB", etc.
            parts = stkcode.split('-')
            
            itemname = stkcode  # Use stkcode as itemname
            itclass = parts[0] if len(parts) > 0 else 'OTHER'
            manufacturer = "Unknown"
            model_number = stkcode
            rating = ""
            
            # Try to extract manufacturer from stkcode
            known_manufacturers = [
                'SCH', 'SCHNEIDER', 'ABB', 'SIE', 'SIEMENS', 
                'LEG', 'LEGRAND', 'HAG', 'HAGER', 'GE', 
                'EATON', 'LS', 'MIT', 'MITSUBISHI'
            ]
            
            for part in parts:
                for mfg in known_manufacturers:
                    if mfg in part.upper():
                        if mfg == 'SCH':
                            manufacturer = 'Schneider'
                        elif mfg == 'SIE':
                            manufacturer = 'Siemens'
                        elif mfg == 'LEG':
                            manufacturer = 'Legrand'
                        elif mfg == 'HAG':
                            manufacturer = 'Hager'
                        elif mfg == 'MIT':
                            manufacturer = 'Mitsubishi'
                        else:
                            manufacturer = part
                        break
            
            # Extract rating (look for patterns like 63A, 415V, 3P)
            import re
            ratings = []
            for part in parts:
                if re.match(r'\d+[AV]', part):
                    ratings.append(part)
                elif re.match(r'\d+P', part):
                    ratings.append(part)
            
            rating = ' '.join(ratings) if ratings else ''
            
            # Use average price
            unit_price = float(row['avg_price']) if row['avg_price'] else 0.0
            
            component_data = {
                'itemname': itemname,
                'itemdesc': f"Stock Code: {stkcode}",
                'itdesc2': f"Usage Count: {row['usage_count']}",
                'itdesc3': f"Price Range: ${row['min_price']:.2f} - ${row['max_price']:.2f}",
                'itdesc4': f"Last Used: {row['last_used']}" if row['last_used'] else '',
                'itclass': itclass,
                'manufacturer': manufacturer,
                'model_number': model_number,
                'rating': rating,
                'unit_price': unit_price,
                'markup_pct': 0.0,  # Will be calculated from sosopoit
                'supplier_code': stkcode,
                'lead_time_days': None,
                'source': 'imported',
                'created_by': 'erp_import_sosopiac'
            }
            
            try:
                # Check if exists by stkcode (supplier_code)
                self.cursor.execute("""
                    SELECT component_id 
                    FROM estimation.component_library
                    WHERE supplier_code = %s
                    AND is_active = TRUE
                    LIMIT 1
                """, (stkcode,))
                
                existing = self.cursor.fetchone()
                
                if not existing:
                    self.add_component(component_data)
                    imported += 1
                    
                    if imported % 50 == 0:
                        print(f"Imported {imported} stock items...")
                else:
                    skipped += 1
                    
            except Exception as e:
                print(f"Error importing '{stkcode}': {e}")
                continue
        
        self.commit()
        erp_db.close()
        
        print(f"\n✅ Import complete!")
        print(f"   Imported: {imported}")
        print(f"   Skipped: {skipped}")
        
        return imported
    
    def import_projects_from_erp(self, limit: Optional[int] = None) -> int:
        """
        Import projects from sosopjod table
        """
        erp_db = Database(use_erp=True)
        
        if not erp_db.connect():
            print("Failed to connect to ERP database")
            return 0
        
        # Get projects from sosopjod
        query = """
            SELECT 
                pjodno as project_code,
                pjdesc as project_name,
                custname as client_name,
                quotno as estimate_number,
                pjoddate as created_date,
                pjodstatus,
                amount as total_amount,
                salepers,
                custpono,
                deldate
            FROM smbe.sosopjod
            WHERE pjodno IS NOT NULL
            AND pjodno != ''
            ORDER BY NDATE DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        try:
            erp_db.cursor.execute(query)
            rows = erp_db.cursor.fetchall()
        except Exception as e:
            print(f"Error querying sosopjod: {e}")
            erp_db.close()
            return 0
        
        imported = 0
        skipped = 0
        
        print(f"Found {len(rows)} projects in sosopjod...")
        
        for row in rows:
            project_code = row['project_code']
            project_name = row['project_name'] or f"Project {project_code}"
            client_name = row['client_name'] or ''
            
            try:
                # Check if exists
                existing = self.get_project(project_code)
                
                if not existing:
                    # Create project
                    project_id = self.create_project(
                        project_code,
                        project_name,
                        client_name,
                        created_by='erp_import_sosopjod'
                    )
                    
                    # Update additional fields
                    if row.get('estimate_number'):
                        self.cursor.execute("""
                            UPDATE estimation.projects
                            SET estimate_number = %s,
                                notes = %s,
                                status = 'imported'
                            WHERE project_id = %s
                        """, (
                            row['estimate_number'],
                            f"Imported from ERP. PO: {row.get('custpono', '')}",
                            project_id
                        ))
                    
                    imported += 1
                    
                    if imported % 10 == 0:
                        print(f"Imported {imported} projects...")
                else:
                    skipped += 1
                    
            except Exception as e:
                print(f"Error importing project '{project_code}': {e}")
                continue
        
        self.commit()
        erp_db.close()
        
        print(f"\n✅ Import complete!")
        print(f"   Imported: {imported}")
        print(f"   Skipped: {skipped}")
        
        return imported
    
    def import_project_details_from_erp(self, project_code: str) -> int:
        """
        Import panel details for a specific project from sosopoit
        Linked by parentky (project code)
        """
        erp_db = Database(use_erp=True)
        
        if not erp_db.connect():
            print("Failed to connect to ERP database")
            return 0
        
        # Get project
        project = self.get_project(project_code)
        if not project:
            print(f"Project {project_code} not found. Import projects first.")
            erp_db.close()
            return 0
        
        # Get items for this project from sosopoit
        query = """
            SELECT 
                itemname,
                itemdesc,
                itdesc2,
                itdesc3,
                itdesc4,
                itclass,
                qty,
                unitprc,
                markup,
                notes
            FROM smbe.sosopoit
            WHERE parentky = %s
            AND itemname IS NOT NULL
            ORDER BY seqno
        """
        
        try:
            erp_db.cursor.execute(query, (project_code,))
            rows = erp_db.cursor.fetchall()
        except Exception as e:
            print(f"Error querying sosopoit: {e}")
            erp_db.close()
            return 0
        
        imported = 0
        
        print(f"Found {len(rows)} items for project {project_code}...")
        
        for row in rows:
            itemname = row['itemname']
            
            # Try to find matching component in library
            self.cursor.execute("""
                SELECT component_id 
                FROM estimation.component_library
                WHERE itemname = %s
                AND is_active = TRUE
                LIMIT 1
            """, (itemname,))
            
            component = self.cursor.fetchone()
            
            if component:
                # Add to BOM
                try:
                    self.add_bom_item(
                        project_id=project['project_id'],
                        component_id=component['component_id'],
                        qty=int(row['qty']) if row['qty'] else 1,
                        unit_price=float(row['unitprc']) if row['unitprc'] else 0.0,
                        markup_pct=float(row['markup']) if row['markup'] else 0.0,
                        labor_hours=0,
                        notes=row['notes'] or ''
                    )
                    imported += 1
                except Exception as e:
                    print(f"Error adding BOM item '{itemname}': {e}")
            else:
                print(f"Component '{itemname}' not found in library - skipping")
        
        self.commit()
        erp_db.close()
        
        print(f"\n✅ Imported {imported} items to project {project_code}")
        
        return imported