import frappe
import hmac
import hashlib
import json
from frappe import _

meta_settings = frappe.get_single("Meta Settings")

META_APP_SECRET = meta_settings.get_password("app_secret") 
WEBHOOK_VERIFY_TOKEN = meta_settings.get_password("hub_verify_token")
URL = meta_settings.get("url")
VERSION = meta_settings.get("version")
ACCESS_TOKEN = meta_settings.get_password("access_token")


@frappe.whitelist(allow_guest=True)
def handle_meta_lead():
    params = frappe.local.form_dict

    if "hub.challenge" in params and params.get("hub.verify_token") == WEBHOOK_VERIFY_TOKEN:
        frappe.response["type"] = "text/plain"
        frappe.response["status"] = 200
        return params["hub.challenge"]
    
    # return params["hub.challenge"]

    # return "Webhook received"

@frappe.whitelist(allow_guest=True)
def test_handle_meta_lead():
    params = frappe.local.form_dict

    if "hub.challenge" in params and params.get("hub.verify_token") == WEBHOOK_VERIFY_TOKEN:
        frappe.response["type"] = "text/plain"
        frappe.response["status"] = 200
        return params["hub.challenge"]
    
    # return params["hub.challenge"]

    return "Webhook received"

# @frappe.whitelist(allow_guest=True)
# def handle_meta_lead():
#     """
#     Handle Meta Lead Ads webhook for ERPNext.
#     This function will:
#       - Validate the signature of incoming requests
#       - Handle verification challenge
#       - Process lead data and create CRM Lead entries in ERPNext
#     """
#     # Get request data
#     request_data = frappe.request.data
#     params = frappe.local.form_dict

#     # Step 1: Handle verification challenge
#     if "hub.challenge" in params:
#         if params.get("hub.verify_token") == WEBHOOK_VERIFY_TOKEN:  # Replace with your verification token
#             frappe.response["type"] = "text/plain"
#             return params["hub.challenge"]
#         else:
#             frappe.throw(_("Invalid verification token"), frappe.PermissionError)

#     # Step 2: Validate signature
#     signature = frappe.get_request_header("X-Hub-Signature-256")
#     if not verify_signature(request_data, signature):
#         frappe.throw(_("Invalid signature"), frappe.PermissionError)

#     # Step 3: Process lead data
#     data = json.loads(request_data)
#     if data.get("object") == "page":
#         for entry in data.get("entry", []):
#             for lead_data in entry.get("changes", []):
#                 if lead_data.get("field") == "leadgen":
#                     lead_id = lead_data["value"]["leadgen_id"]
#                     form_id = lead_data["value"]["form_id"]
#                     process_lead(lead_id, form_id)

#     return "Webhook received"


# def verify_signature(payload, signature):
#     """
#     Verify Meta webhook signature.
#     """
#     if not signature:
#         return False
#     try:
#         expected_signature = "sha256=" + hmac.new(
#             key=META_APP_SECRET.encode("utf-8"),
#             msg=payload,
#             digestmod=hashlib.sha256
#         ).hexdigest()
#         return hmac.compare_digest(expected_signature, signature)
#     except Exception as e:
#         frappe.log_error(message=str(e), title="Meta Webhook Signature Error")
#         return False


# def process_lead(lead_id, form_id):
#     """
#     Fetch lead details from Meta Graph API and create a Lead in ERPNext CRM.
#     """ 
#     lead_url = f"{URL}/{VERSION}/{lead_id}?access_token={ACCESS_TOKEN}"

#     try:
#         # Fetch lead data from Facebook
#         response = frappe.session.get(lead_url)
#         lead_data = response.json()

#         # Create or update ERPNext Lead
#         lead_name = lead_data.get("field_data", {}).get("full_name")
#         lead_email = lead_data.get("field_data", {}).get("email")
#         lead_phone = lead_data.get("field_data", {}).get("phone_number")

#         # Insert the lead into ERPNext CRM
#         if lead_name and lead_email:
#             lead_doc = frappe.get_doc({
#                 "doctype": "Lead",
#                 "lead_name": lead_name,
#                 "email_id": lead_email,
#                 "phone": lead_phone,
#                 "source": "Meta Lead Ads",
#             })
#             lead_doc.insert(ignore_permissions=True)
#             frappe.db.commit()

#     except Exception as e:
#         frappe.log_error(message=str(e), title="Meta Lead Processing Error")
