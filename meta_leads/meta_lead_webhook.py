import frappe
import hmac
import hashlib
import json
from werkzeug.wrappers import Response

# Fetch configurations from "Meta Settings" doctype
meta_settings = frappe.get_single("Meta Settings")
META_APP_SECRET = meta_settings.get_password("app_secret")
WEBHOOK_VERIFY_TOKEN = meta_settings.get_password("hub_verify_token")
URL = meta_settings.get("url")
VERSION = meta_settings.get("version")
ACCESS_TOKEN = meta_settings.get_password("access_token")

@frappe.whitelist(allow_guest=True)
def test_handle_meta_lead():
    """
    Main webhook handler for Meta Lead Ads. Handles verification requests,
    validates signature, processes lead data, and creates ERPNext Lead entries.
    """
    # Parse request data and parameters
    params = frappe.local.form_dict
    request_data = frappe.request.data


    # Handle verification challenge
    if "hub.challenge" in params:
        if params.get("hub.verify_token") == WEBHOOK_VERIFY_TOKEN:
            return Response(params["hub.challenge"], mimetype="text/plain", status=200)
    
    log_request = frappe.get_doc({
        "doctype": "Note",
        "title": "Meta Webhook Request",
        "content": request_data,
    })
    log_request.insert(ignore_permissions=True)
    frappe.db.commit()

    # Validate the signature
    signature = frappe.get_request_header("X-Hub-Signature-256")
    if not verify_signature(request_data, signature):
        frappe.throw(_("Invalid signature"), frappe.PermissionError)

    # Process lead data
    data = json.loads(request_data)
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            for change in entry.get("changes", []):
                if change.get("field") == "leadgen":
                    lead_id = change["value"]["leadgen_id"]
                    form_id = change["value"]["form_id"]
                    process_lead(lead_id, form_id)

    return "Webhook received"

def verify_signature(payload, signature):
    """
    Verifies the Meta webhook request signature using the app secret.
    """
    if not signature:
        return False
    try:
        expected_signature = "sha256=" + hmac.new(
            key=META_APP_SECRET.encode("utf-8"),
            msg=payload,
            digestmod=hashlib.sha256
        ).hexdigest()
        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        frappe.log_error(message=str(e), title="Meta Webhook Signature Error")
        return False

def process_lead(lead_id, form_id):
    """
    Fetches lead details from Meta Graph API and creates a Lead in ERPNext CRM.
    """
    lead_url = f"{URL}/{VERSION}/{lead_id}?access_token={ACCESS_TOKEN}"

    try:
        # Fetch lead data from Meta
        response = frappe.session.get(lead_url)
        lead_data = response.json()

        # Parse lead information
        field_data = {field["name"]: field["values"][0] for field in lead_data.get("field_data", [])}
        lead_name = field_data.get("full_name")
        lead_company = field_data.get("company_name")
        lead_phone = field_data.get("phone_number")

        # Insert the lead into ERPNext CRM if necessary data is available
        if lead_name and lead_company:
            lead_doc = frappe.get_doc({
                "doctype": "CRM Lead",
                "first_name": lead_name,
                "middle_name": lead_company,
                "phone": lead_phone,
                "source": "Campaign",
            })
            lead_doc.insert(ignore_permissions=True)
            frappe.db.commit()
            frappe.logger().info(f"Lead created successfully: {lead_doc.name}")
        else:
            frappe.logger().warning("Lead data incomplete. Missing name or email.")

    except Exception as e:
        frappe.log_error(message=str(e), title="Meta Lead Processing Error")
