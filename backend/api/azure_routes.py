"""
Azure Authentication API Routes - Handle Azure CLI authentication status and subscription management
"""
from flask import Blueprint, request, jsonify
from typing import Tuple
import subprocess
import json
import sys
import os
import platform

azure_bp = Blueprint('azure', __name__)

def get_base_dir():
    if getattr(sys, 'frozen', False):
        # Running as compiled exe
        return os.path.dirname(sys.executable)
    else:
        # Running as script
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def get_az_command_path() -> str:
    base_dir = get_base_dir()

    if platform.system() == 'Windows':
        az_path = os.path.join(base_dir, 'azure-cli', 'bin', 'az.cmd')
        if os.path.exists(az_path):
            return az_path

    return 'az'



def run_az_command(command: list) -> Tuple[dict, int]:
    """
    Run an Azure CLI command and return the result.
    
    Args:
        command: List of command parts (e.g., ['az', 'account', 'show'])
                 The first element will be replaced with the actual az path
        
    Returns:
        Tuple of (result_dict, status_code)
    """
    # Get the az command path
    az_path = get_az_command_path()
    
    # Replace 'az' with the actual path (create a new list to avoid modifying the original)
    if command and len(command) > 0 and command[0] == 'az':
        command = [az_path] + command[1:]
    
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        if result.returncode == 0:
            try:
                output = json.loads(result.stdout) if result.stdout.strip() else {}
                return {"success": True, "data": output}, 200
            except json.JSONDecodeError:
                # Some commands return non-JSON output
                return {"success": True, "data": result.stdout.strip()}, 200
        else:
            error_msg = result.stderr.strip() or result.stdout.strip()
            return {
                "success": False,
                "error": error_msg or "Azure CLI command failed",
                "returncode": result.returncode
            }, 400
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": "Azure CLI command timed out"
        }, 408
    except FileNotFoundError:
        return {
            "success": False,
            "error": f"Azure CLI not found at {az_path}. Please ensure Azure CLI is installed."
        }, 503
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }, 500


@azure_bp.route('/status', methods=['GET'])
def check_azure_status():
    """
    Check if user is logged in to Azure CLI and get current account info
    GET /api/azure/status
    
    Response:
        {
            "success": true,
            "logged_in": true,
            "account": {
                "id": "...",
                "name": "...",
                "tenantId": "...",
                "isDefault": true
            },
            "subscription": {
                "id": "...",
                "name": "...",
                "state": "Enabled"
            }
        }
    """
    # Check if logged in by trying to get current account
    result, status_code = run_az_command(['az', 'account', 'show'])
    print("result", result)
    print("status_code", status_code)
    if not result.get('success'):
        return jsonify({
            "success": False,
            "logged_in": False,
            "error": result.get('error', 'Not logged in to Azure')
        }), status_code
    
    account_data = result.get('data', {})
    
    # Get subscription info
    subscription = {}
    if account_data:
        subscription = {
            "id": account_data.get('id', ''),
            "name": account_data.get('name', ''),
            "state": account_data.get('state', ''),
            "tenantId": account_data.get('tenantId', '')
        }
    
    return jsonify({
        "success": True,
        "logged_in": True,
        "account": {
            "id": account_data.get('user', {}).get('name', '') if isinstance(account_data.get('user'), dict) else account_data.get('user', {}),
            "name": account_data.get('name', ''),
            "tenantId": account_data.get('tenantId', ''),
            "isDefault": account_data.get('isDefault', False)
        },
        "subscription": subscription
    }), 200


@azure_bp.route('/accounts', methods=['GET'])
def list_azure_accounts():
    """
    List all available Azure accounts
    GET /api/azure/accounts
    
    Response:
        {
            "success": true,
            "accounts": [
                {
                    "id": "...",
                    "name": "...",
                    "tenantId": "...",
                    "isDefault": true
                },
                ...
            ]
        }
    """
    result, status_code = run_az_command(['az', 'account', 'list', '--output', 'json'])
    
    if not result.get('success'):
        return jsonify(result), status_code
    
    accounts = result.get('data', [])
    if not isinstance(accounts, list):
        accounts = []
    
    return jsonify({
        "success": True,
        "accounts": accounts
    }), 200


@azure_bp.route('/subscriptions', methods=['GET'])
def list_subscriptions():
    """
    List all available subscriptions
    GET /api/azure/subscriptions
    
    Response:
        {
            "success": true,
            "subscriptions": [
                {
                    "id": "...",
                    "name": "...",
                    "state": "Enabled",
                    "isDefault": true
                },
                ...
            ]
        }
    """
    result, status_code = run_az_command(['az', 'account', 'list', '--output', 'json'])
    
    if not result.get('success'):
        return jsonify(result), status_code
    
    subscriptions = result.get('data', [])
    if not isinstance(subscriptions, list):
        subscriptions = []
    
    # Format subscriptions
    formatted_subs = []
    for sub in subscriptions:
        formatted_subs.append({
            "id": sub.get('id', ''),
            "name": sub.get('name', ''),
            "state": sub.get('state', ''),
            "tenantId": sub.get('tenantId', ''),
            "isDefault": sub.get('isDefault', False)
        })
    
    return jsonify({
        "success": True,
        "subscriptions": formatted_subs
    }), 200


@azure_bp.route('/subscription/set', methods=['POST'])
def set_subscription():
    """
    Set the active Azure subscription
    POST /api/azure/subscription/set
    
    Request:
        {
            "subscription_id": "..." or "subscription_name": "..."
        }
    
    Response:
        {
            "success": true,
            "message": "Subscription set successfully",
            "subscription": {
                "id": "...",
                "name": "..."
            }
        }
    """
    try:
        data = request.json or {}
        subscription_id = data.get('subscription_id')
        subscription_name = data.get('subscription_name')
        
        if not subscription_id and not subscription_name:
            return jsonify({
                "success": False,
                "error": "Either subscription_id or subscription_name must be provided"
            }), 400
        
        # Use subscription ID if provided, otherwise use name
        subscription_identifier = subscription_id or subscription_name
        
        # Set the subscription
        result, status_code = run_az_command(['az', 'account', 'set', '--subscription', subscription_identifier])
        
        if not result.get('success'):
            return jsonify(result), status_code
        
        # Get the updated subscription info
        account_result, account_status = run_az_command(['az', 'account', 'show'])
        
        if account_result.get('success'):
            account_data = account_result.get('data', {})
            return jsonify({
                "success": True,
                "message": "Subscription set successfully",
                "subscription": {
                    "id": account_data.get('id', ''),
                    "name": account_data.get('name', '')
                }
            }), 200
        else:
            return jsonify({
                "success": True,
                "message": "Subscription set successfully, but could not verify"
            }), 200
            
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
