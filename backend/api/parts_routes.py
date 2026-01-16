"""
Parts API Routes - Handle fetching parts from database
"""
from flask import Blueprint, request, jsonify
import sys
import os
from typing import List, Dict, Any, Optional

# Add backend directory to path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

try:
    from database.db_config import get_db_session
    from database.models import Part, Machine, MachinePart
    DB_AVAILABLE = True
except ImportError:
    DB_AVAILABLE = False
    print("Warning: Database models not available. Parts functionality will be disabled.")

parts_bp = Blueprint('parts', __name__)


@parts_bp.route('/parts', methods=['GET'])
def get_all_parts():
    """
    Get all parts from database with associated machine information
    GET /api/parts
    
    Query Parameters:
        - ai_status: Filter by AI status (optional)
        - machine_id: Filter by machine ID (optional)
        - search: Search term for part number, manufacturer, description (optional)
        - limit: Limit number of results (optional, default: 1000)
        - offset: Offset for pagination (optional, default: 0)
    
    Response:
        {
            "success": true,
            "parts": [
                {
                    "id": 1,
                    "part_manufacturer": "...",
                    "manufacturer_part_number": "...",
                    "part_description": "...",
                    "ai_status": "...",
                    "machines": [
                        {
                            "id": 1,
                            "equipment_id": "...",
                            "equipment_alias": "...",
                            "machine_description": "...",
                            "plant": "...",
                            "quantity": 1.0
                        }
                    ],
                    ...
                }
            ],
            "total": 100,
            "filters_applied": {
                "ai_status": "...",
                "machine_id": "...",
                "search": "..."
            }
        }
    """
    if not DB_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Database not available. Please check database configuration."
        }), 503
    
    try:
        # Get query parameters
        ai_status = request.args.get('ai_status', '').strip()
        machine_id = request.args.get('machine_id', '').strip()
        search = request.args.get('search', '').strip()
        limit = int(request.args.get('limit', 1000))
        offset = int(request.args.get('offset', 0))
        
        # Get database session (will try to initialize if needed)
        try:
            session = get_db_session()
        except RuntimeError as e:
            return jsonify({
                "success": False,
                "error": str(e),
                "parts": [],
                "total": 0,
                "limit": limit,
                "offset": offset,
                "filters_applied": {
                    "ai_status": None,
                    "machine_id": None,
                    "search": None
                }
            }), 503
        
        try:
            # Start with base query
            query = session.query(Part)
            
            # Apply filters
            if ai_status:
                query = query.filter(Part.ai_status == ai_status)
            
            if machine_id:
                # Filter parts that are associated with this machine
                # Use distinct() to avoid duplicates when a part has multiple machine associations
                query = query.join(MachinePart).filter(
                    MachinePart.machine_id == int(machine_id)
                ).distinct()
            
            if search:
                # Search across multiple fields
                search_term = f"%{search}%"
                query = query.filter(
                    (Part.part_manufacturer.like(search_term)) |
                    (Part.manufacturer_part_number.like(search_term)) |
                    (Part.part_description.like(search_term)) |
                    (Part.notes.like(search_term)) |
                    (Part.notes_by_ai.like(search_term))
                )
            
            # Get total count before pagination
            total = query.count()
            
            # Apply pagination
            parts = query.offset(offset).limit(limit).all()
            
            # Convert to dictionaries with machine information
            parts_data = []
            for part in parts:
                part_dict = _part_to_dict(part)
                
                # Get associated machines
                machine_parts = session.query(MachinePart).filter(
                    MachinePart.part_id == part.id
                ).all()
                
                machines_data = []
                for mp in machine_parts:
                    machine = session.query(Machine).filter(
                        Machine.id == mp.machine_id
                    ).first()
                    
                    if machine:
                        machines_data.append({
                            "id": machine.id,
                            "equipment_id": machine.equipment_id,
                            "equipment_alias": machine.equipment_alias,
                            "machine_description": machine.machine_description,
                            "plant": machine.plant,
                            "group_responsibility": machine.group_responsibility,
                            "quantity": float(mp.quantity) if mp.quantity else 1.0,
                            "cspl_line_number": mp.cspl_line_number,
                            "original_order": mp.original_order,
                            "parent_folder": mp.parent_folder
                        })
                
                part_dict["machines"] = machines_data
                parts_data.append(part_dict)
            
            return jsonify({
                "success": True,
                "parts": parts_data,
                "total": total,
                "limit": limit,
                "offset": offset,
                "filters_applied": {
                    "ai_status": ai_status if ai_status else None,
                    "machine_id": int(machine_id) if machine_id else None,
                    "search": search if search else None
                }
            })
            
        finally:
            session.close()
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@parts_bp.route('/parts/machines', methods=['GET'])
def get_all_machines():
    """
    Get all machines from database
    GET /api/parts/machines
    
    Response:
        {
            "success": true,
            "machines": [
                {
                    "id": 1,
                    "equipment_id": "...",
                    "equipment_alias": "...",
                    "machine_description": "...",
                    "plant": "...",
                    "parts_count": 10
                }
            ],
            "total": 5
        }
    """
    if not DB_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Database not available. Please check database configuration."
        }), 503
    
    try:
        # Get database session (will try to initialize if needed)
        try:
            session = get_db_session()
        except RuntimeError as e:
            return jsonify({
                "success": False,
                "error": str(e),
                "machines": [],
                "total": 0
            }), 503
        
        try:
            machines = session.query(Machine).all()
            
            machines_data = []
            for machine in machines:
                # Count parts for this machine
                parts_count = session.query(MachinePart).filter(
                    MachinePart.machine_id == machine.id
                ).count()
                
                machines_data.append({
                    "id": machine.id,
                    "equipment_id": machine.equipment_id,
                    "equipment_alias": machine.equipment_alias,
                    "machine_description": machine.machine_description,
                    "plant": machine.plant,
                    "group_responsibility": machine.group_responsibility,
                    "eam_equipment_id": machine.eam_equipment_id,
                    "parts_count": parts_count,
                    "created_at": machine.created_at.isoformat() if machine.created_at else None,
                    "updated_at": machine.updated_at.isoformat() if machine.updated_at else None
                })
            
            return jsonify({
                "success": True,
                "machines": machines_data,
                "total": len(machines_data)
            })
            
        finally:
            session.close()
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


def _part_to_dict(part: Part) -> Dict[str, Any]:
    """
    Convert a Part SQLAlchemy object to a dictionary.
    """
    return {
        "id": part.id,
        "part_manufacturer": part.part_manufacturer,
        "manufacturer_part_number": part.manufacturer_part_number,
        "part_description": part.part_description,
        "part_number_ai_modified": part.part_number_ai_modified,
        "suggested_supplier": part.suggested_supplier,
        "supplier_part_number": part.supplier_part_number,
        "gore_stock_number": part.gore_stock_number,
        "is_part_likely_to_fail": part.is_part_likely_to_fail,
        "will_failures_stop_machine": part.will_failures_stop_machine,
        "stocking_decision": part.stocking_decision,
        "min_qty_to_stock": float(part.min_qty_to_stock) if part.min_qty_to_stock else None,
        "part_preplacement_line_number": part.part_preplacement_line_number,
        "notes": part.notes,
        "ai_status": part.ai_status,
        "notes_by_ai": part.notes_by_ai,
        "ai_confidence": part.ai_confidence,
        "ai_confidence_confirmed": part.ai_confidence_confirmed,
        "recommended_replacement": part.recommended_replacement,
        "replacement_manufacturer": part.replacement_manufacturer,
        "replacement_price": float(part.replacement_price) if part.replacement_price else None,
        "replacement_currency": part.replacement_currency,
        "replacement_source_type": part.replacement_source_type,
        "replacement_source_url": part.replacement_source_url,
        "replacement_notes": part.replacement_notes,
        "replacement_confidence": part.replacement_confidence,
        "will_notes": part.will_notes,
        "nejat_notes": part.nejat_notes,
        "kc_notes": part.kc_notes,
        "ricky_notes": part.ricky_notes,
        "stephanie_notes": part.stephanie_notes,
        "pit_notes": part.pit_notes,
        "initial_email_communication": part.initial_email_communication,
        "follow_up_email_communication_date": part.follow_up_email_communication_date.isoformat() if part.follow_up_email_communication_date else None,
        "created_at": part.created_at.isoformat() if part.created_at else None,
        "updated_at": part.updated_at.isoformat() if part.updated_at else None
    }


@parts_bp.route('/parts/update', methods=['POST'])
def update_parts():
    """
    Update parts with replacement information
    POST /api/parts/update
    
    Request:
        {
            "parts": [
                {
                    "id": 1,
                    "recommended_replacement": "...",
                    "replacement_manufacturer": "...",
                    "replacement_price": 100.0,
                    "replacement_currency": "USD",
                    "replacement_source_type": "...",
                    "replacement_source_url": "...",
                    "replacement_notes": "...",
                    "replacement_confidence": "..."
                },
                ...
            ]
        }
    
    Response:
        {
            "success": true,
            "updated": 5,
            "errors": []
        }
    """
    if not DB_AVAILABLE:
        return jsonify({
            "success": False,
            "error": "Database not available. Please check database configuration."
        }), 503
    
    try:
        data = request.json or {}
        parts_data = data.get('parts', [])
        
        if not parts_data:
            return jsonify({
                "success": False,
                "error": "No parts provided"
            }), 400
        
        if not isinstance(parts_data, list):
            return jsonify({
                "success": False,
                "error": "Parts must be a list"
            }), 400
        
        session = get_db_session()
        updated_count = 0
        errors = []
        
        try:
            for part_data in parts_data:
                part_id = part_data.get('id')
                if not part_id:
                    errors.append(f"Part missing 'id' field: {part_data}")
                    continue
                
                # Find the part
                part = session.query(Part).filter(Part.id == part_id).first()
                if not part:
                    errors.append(f"Part with id {part_id} not found")
                    continue
                
                # Update replacement fields
                if 'recommended_replacement' in part_data:
                    part.recommended_replacement = part_data.get('recommended_replacement')
                if 'replacement_manufacturer' in part_data:
                    part.replacement_manufacturer = part_data.get('replacement_manufacturer')
                if 'replacement_price' in part_data:
                    part.replacement_price = part_data.get('replacement_price')
                if 'replacement_currency' in part_data:
                    part.replacement_currency = part_data.get('replacement_currency')
                if 'replacement_source_type' in part_data:
                    part.replacement_source_type = part_data.get('replacement_source_type')
                if 'replacement_source_url' in part_data:
                    part.replacement_source_url = part_data.get('replacement_source_url')
                if 'replacement_notes' in part_data:
                    part.replacement_notes = part_data.get('replacement_notes')
                if 'replacement_confidence' in part_data:
                    part.replacement_confidence = part_data.get('replacement_confidence')
                
                updated_count += 1
            
            session.commit()
            
            return jsonify({
                "success": True,
                "updated": updated_count,
                "errors": errors
            })
            
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

