"""
Save API Routes - Handle saving products and machines to database
"""
from flask import Blueprint, request, jsonify
import sys
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
import traceback

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

try:
    from database.db_config import get_db_session
    from database.models import Machine, Part, MachinePart, AnalysisLog
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("Warning: Database models not available. Save functionality will be disabled.")

save_bp = Blueprint('save', __name__)


@save_bp.route('/save', methods=['POST'])
def save_data():
    """
    Save products and machine information to database
    POST /api/save
    
    Request:
        {
            "general_info": {
                "eam_equipment_id": "...",
                "equipment_description": "...",
                "alias": "...",
                "plant": "...",
                "group_responsible": "...",
                "participating_associates": {
                    "initiator": {"name": "..."}
                }
            },
            "products": [
                {
                    "part_manufacturer": "...",
                    "manufacturer_part_number": "...",
                    "part_description": "...",
                    ...
                },
                ...
            ],
            "create_log": true  // optional, default true
        }
        
    Response:
        {
            "success": true,
            "machine_id": 1,
            "parts_saved": 10,
            "parts_updated": 2,
            "machine_parts_linked": 10,
            "log_id": 5  // if create_log is true
        }
    """
    if not DB_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Database not available. Please check database configuration."
        }), 503
    
    try:
        data = request.json or {}
        general_info = data.get('general_info', {})
        products = data.get('products', [])
        create_log = data.get('create_log', True)
        
        if not products:
            return jsonify({"success": False, "error": "No products provided"}), 400
        
        if not isinstance(products, list):
            return jsonify({"success": False, "error": "Products must be a list"}), 400
        
        # Get database session (will try to initialize if needed)
        try:
            session = get_db_session()
        except RuntimeError as e:
            return jsonify({
                "success": False,
                "error": str(e),
                "parts_saved": 0,
                "parts_updated": 0,
                "machine_parts_linked": 0
            }), 503
        
        try:
            # Step 1: Create or update Machine
            machine = None
            equipment_id = general_info.get('eam_equipment_id') or general_info.get('equipment_id')
            
            if equipment_id:
                # Try to find existing machine
                machine = session.query(Machine).filter(
                    Machine.equipment_id == equipment_id
                ).first()
                
                if machine:
                    # Update existing machine
                    machine.equipment_alias = general_info.get('alias') or machine.equipment_alias
                    machine.machine_description = general_info.get('equipment_description') or machine.machine_description
                    machine.plant = general_info.get('plant') or machine.plant
                    machine.group_responsibility = general_info.get('group_responsible') or machine.group_responsibility
                else:
                    # Create new machine
                    machine = Machine(
                        equipment_id=equipment_id,
                        equipment_alias=general_info.get('alias'),
                        machine_description=general_info.get('equipment_description'),
                        plant=general_info.get('plant'),
                        group_responsibility=general_info.get('group_responsible'),
                        eam_equipment_id=equipment_id
                    )
                    session.add(machine)
                    session.flush()  # Get machine.id
            
            # Step 2: Create or update Parts and link to Machine
            parts_saved = 0
            parts_updated = 0
            machine_parts_linked = 0
            machine_parts_updated = 0
            
            # Track machine-part links we've processed in this transaction to avoid duplicates
            processed_links = set()
            
            for product_data in products:
                part_manufacturer = product_data.get('part_manufacturer') or product_data.get('manufacturer', '')
                manufacturer_part_number = product_data.get('manufacturer_part_number') or product_data.get('part_number', '')
                
                if not part_manufacturer or not manufacturer_part_number:
                    continue  # Skip products without required fields
                
                # Try to find existing part
                part = session.query(Part).filter(
                    Part.part_manufacturer == part_manufacturer,
                    Part.manufacturer_part_number == manufacturer_part_number
                ).first()
                
                if part:
                    # Update existing part with new data
                    parts_updated += 1
                    _update_part_from_product(part, product_data)
                else:
                    # Create new part
                    part = Part(
                        part_manufacturer=part_manufacturer,
                        manufacturer_part_number=manufacturer_part_number
                    )
                    _update_part_from_product(part, product_data)
                    session.add(part)
                    parts_saved += 1
                    session.flush()  # Get part.id
                
                # Step 3: Link part to machine if machine exists
                if machine and part.id:
                    # Create a unique key for this machine-part combination
                    link_key = (machine.id, part.id)
                    
                    # Skip if we've already processed this link in this transaction
                    if link_key in processed_links:
                        continue
                    
                    # Check if link already exists in database
                    existing_link = session.query(MachinePart).filter(
                        MachinePart.machine_id == machine.id,
                        MachinePart.part_id == part.id
                    ).first()
                    
                    if existing_link:
                        # Update existing link with new data
                        qty_str = product_data.get('qty_on_machine', '1')
                        try:
                            qty = float(qty_str) if qty_str else 1.0
                        except (ValueError, TypeError):
                            qty = 1.0
                        
                        existing_link.quantity = qty
                        existing_link.cspl_line_number = product_data.get('cspl_line_number') or existing_link.cspl_line_number
                        existing_link.original_order = product_data.get('original_order') or existing_link.original_order
                        existing_link.parent_folder = product_data.get('parent_folder') or existing_link.parent_folder
                        machine_parts_updated += 1
                    else:
                        # Create new link
                        qty_str = product_data.get('qty_on_machine', '1')
                        try:
                            qty = float(qty_str) if qty_str else 1.0
                        except (ValueError, TypeError):
                            qty = 1.0
                        
                        machine_part = MachinePart(
                            machine_id=machine.id,
                            part_id=part.id,
                            quantity=qty,
                            cspl_line_number=product_data.get('cspl_line_number'),
                            original_order=product_data.get('original_order'),
                            parent_folder=product_data.get('parent_folder')
                        )
                        session.add(machine_part)
                        machine_parts_linked += 1
                    
                    # Mark this link as processed
                    processed_links.add(link_key)
            
            # Step 4: Create analysis log if requested
            log_id = None
            if create_log:
                try:
                    # Get request metadata
                    user_agent = request.headers.get('User-Agent', '')
                    ip_address = request.remote_addr or ''
                    
                    analysis_log = AnalysisLog(
                        analysis_type='product_analysis',
                        status='completed',
                        input_data={'products': products[:10]},  # Store first 10 for reference
                        output_data={'total_products': len(products)},
                        products_count=len(products),
                        user_agent=user_agent[:500],  # Limit length
                        ip_address=ip_address
                    )
                    session.add(analysis_log)
                    session.flush()
                    log_id = analysis_log.id
                except Exception as e:
                    print(f"Warning: Could not create analysis log: {e}")
            
            # Commit all changes
            session.commit()
            
            return jsonify({
                "success": True,
                "machine_id": machine.id if machine else None,
                "parts_saved": parts_saved,
                "parts_updated": parts_updated,
                "machine_parts_linked": machine_parts_linked,
                "machine_parts_updated": machine_parts_updated,
                "log_id": log_id
            })
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
            
    except Exception as e:
        error_msg = str(e)
        traceback.print_exc()
        return jsonify({
            "success": False,
            "error": error_msg
        }), 500


def _update_part_from_product(part: Part, product_data: Dict[str, Any]):
    """
    Update a Part object with data from a product dictionary.
    Handles all fields including AI analysis and replacement data.
    """
    # Basic part information
    if 'part_description' in product_data:
        part.part_description = product_data.get('part_description')
    if 'part_number_ai_modified' in product_data:
        part.part_number_ai_modified = product_data.get('part_number_ai_modified')
    if 'suggested_supplier' in product_data:
        part.suggested_supplier = product_data.get('suggested_supplier')
    if 'supplier_part_number' in product_data:
        part.supplier_part_number = product_data.get('supplier_part_number')
    if 'gore_stock_number' in product_data:
        part.gore_stock_number = product_data.get('gore_stock_number')
    if 'is_part_likely_to_fail' in product_data:
        part.is_part_likely_to_fail = product_data.get('is_part_likely_to_fail')
    if 'will_failures_stop_machine' in product_data:
        part.will_failures_stop_machine = product_data.get('will_failures_stop_machine')
    if 'stocking_decision' in product_data:
        part.stocking_decision = product_data.get('stocking_decision')
    if 'min_qty_to_stock' in product_data:
        min_qty = product_data.get('min_qty_to_stock')
        if min_qty:
            try:
                part.min_qty_to_stock = float(min_qty)
            except (ValueError, TypeError):
                pass
    if 'part_preplacement_line_number' in product_data:
        part.part_preplacement_line_number = product_data.get('part_preplacement_line_number')
    if 'notes' in product_data:
        part.notes = product_data.get('notes')
    
    # AI Analysis Fields
    if 'ai_status' in product_data:
        part.ai_status = product_data.get('ai_status')
    if 'notes_by_ai' in product_data:
        part.notes_by_ai = product_data.get('notes_by_ai')
    if 'ai_confidence' in product_data:
        part.ai_confidence = product_data.get('ai_confidence')
    if 'ai_confidence_confirmed' in product_data:
        part.ai_confidence_confirmed = product_data.get('ai_confidence_confirmed')
    
    # Replacement Information
    if 'recommended_replacement' in product_data:
        part.recommended_replacement = product_data.get('recommended_replacement')
    if 'replacement_manufacturer' in product_data:
        part.replacement_manufacturer = product_data.get('replacement_manufacturer')
    if 'replacement_price' in product_data:
        price = product_data.get('replacement_price')
        if price is not None:
            try:
                part.replacement_price = float(price)
            except (ValueError, TypeError):
                pass
    if 'replacement_currency' in product_data:
        part.replacement_currency = product_data.get('replacement_currency')
    if 'replacement_source_type' in product_data:
        part.replacement_source_type = product_data.get('replacement_source_type')
    if 'replacement_source_url' in product_data:
        part.replacement_source_url = product_data.get('replacement_source_url')
    if 'replacement_notes' in product_data:
        part.replacement_notes = product_data.get('replacement_notes')
    if 'replacement_confidence' in product_data:
        part.replacement_confidence = product_data.get('replacement_confidence')
    
    # Team Notes
    if 'will_notes' in product_data:
        part.will_notes = product_data.get('will_notes')
    if 'nejat_notes' in product_data:
        part.nejat_notes = product_data.get('nejat_notes')
    if 'kc_notes' in product_data:
        part.kc_notes = product_data.get('kc_notes')
    if 'ricky_notes' in product_data:
        part.ricky_notes = product_data.get('ricky_notes')
    if 'stephanie_notes' in product_data:
        part.stephanie_notes = product_data.get('stephanie_notes')
    if 'pit_notes' in product_data:
        part.pit_notes = product_data.get('pit_notes')
    
    # Communication
    if 'initial_email_communication' in product_data:
        part.initial_email_communication = product_data.get('initial_email_communication')
    if 'follow_up_email_communication_date' in product_data:
        date_str = product_data.get('follow_up_email_communication_date')
        if date_str:
            try:
                # Try to parse date string
                part.follow_up_email_communication_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                # If parsing fails, store as string in notes or skip
                pass

