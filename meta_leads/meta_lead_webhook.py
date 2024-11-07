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
    params = frappe.local.form_dict
    request_data = frappe.request.data
    decoded_data = request_data.decode("utf-8")
    data = json.loads(decoded_data)

    try:
        # Log the user executing the function
        frappe.log_error(frappe.get_traceback(), f"1 {params}")

        # Handle verification challenge
        if "hub.challenge" in params:
            if params.get("hub.verify_token") == WEBHOOK_VERIFY_TOKEN:
                frappe.log_error(frappe.get_traceback(), f"2 {data}")

                # Attempt to create a Note and log it
                return Response(params["hub.challenge"], mimetype="text/plain", status=200)
        log_request = frappe.get_doc({
            "doctype": "Note",
            "title": "Meta Webhook Request",
            "content": "Webhook test note",
            "public":1
        })
        log_request.insert(ignore_permissions=True)
        frappe.db.commit()

        frappe.log_error(frappe.get_traceback(), f"3 {data}")
            

        frappe.log_error(frappe.get_traceback(), f"4 {params}")
    except Exception as e:
        # Log any error that occurs in Error Log doctype
        frappe.log_error(frappe.get_traceback(), f"5 {data}") 

    # Validate the signature
    signature = frappe.get_request_header("X-Hub-Signature-256")
    frappe.log_error(frappe.get_traceback(), f"6 {signature}")

        
    if verify_signature(data, signature):
        frappe.log_error(frappe.get_traceback(), f"60 {signature} {data}")
    # Process lead data
        if data.get("object") == "page":
            frappe.log_error(frappe.get_traceback(), f"8 {data.get('object')}")
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    if change.get("field") == "leadgen":
                        lead_id = change["value"]["leadgen_id"]
                        form_id = change["value"]["form_id"]
                        process_lead(lead_id, form_id)
                        frappe.log_error(frappe.get_traceback(), f"100 {lead_id} {form_id}")
    else:
        frappe.log_error(frappe.get_traceback(), f"7 {signature}")

    return "Webhook received"

def verify_signature(payload, signature):

    # payload = json.loads(payload)
    """
    Verifies the Meta webhook request signature using the app secret.
    """

    frappe.log_error(frappe.get_traceback(), f"101 {payload}")
    if not signature:
        frappe.log_error(frappe.get_traceback(), f"9")
        return False
    try:
        expected_signature = "sha256=" + hmac.new(
            key=META_APP_SECRET.encode("utf-8"),
            msg=payload,
            digestmod=hashlib.sha256
        ).hexdigest()
        frappe.log_error(frappe.get_traceback(), f"10 {payload}")
        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"11 {e}")
        return False

def process_lead(lead_id, form_id):
    """
    Fetches lead details from Meta Graph API and creates a Lead in ERPNext CRM.
    """
    lead_url = f"{URL}/{VERSION}/{lead_id}?access_token={ACCESS_TOKEN}"
    frappe.log_error(frappe.get_traceback(), f"12 {lead_url}")

    try:
        # Fetch lead data from Meta
        response = frappe.session.get(lead_url)
        lead_data = response.json()

        # Parse lead information
        field_data = {field["name"]: field["values"][0] for field in lead_data.get("field_data", [])}
        lead_name = field_data.get("full_name")
        lead_company = field_data.get("company_name")
        lead_phone = field_data.get("phone_number")
        frappe.log_error(frappe.get_traceback(), f"18 {field_data}")

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
            frappe.log_error(frappe.get_traceback(), f"13 {lead_doc}")
        else:
            frappe.log_error(frappe.get_traceback(), f"14 {field_data}")

    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"15")
