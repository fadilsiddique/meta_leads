import frappe
import hmac
import hashlib
import json
from werkzeug.wrappers import Response
import requests

# Fetch configurations from "Meta Settings" doctype
meta_settings = frappe.get_single("Meta Settings")
META_APP_SECRET = meta_settings.get_password("app_secret")
WEBHOOK_VERIFY_TOKEN = meta_settings.get_password("hub_verify_token")
URL = meta_settings.get("url")
VERSION = meta_settings.get("version")
ACCESS_TOKEN = meta_settings.get_password("access_token")

# frappe.log_error(frappe.get_traceback(), f"007 {ACCESS_TOKEN}")

@frappe.whitelist(allow_guest=True)
def test_handle_meta_lead():
    params = frappe.local.form_dict
    request_data = frappe.request.data
    decoded_data = request_data.decode("utf-8")
    data = json.loads(decoded_data)

    try:
        # Log the user executing the function
        # frappe.log_error(frappe.get_traceback(), f"1 {params}")

        # Handle verification challenge
        if "hub.challenge" in params:
            if params.get("hub.verify_token") == WEBHOOK_VERIFY_TOKEN:
                # frappe.log_error(frappe.get_traceback(), f"2 {data}")

                # Attempt to create a Note and log it
                return Response(params["hub.challenge"], mimetype="text/plain", status=200)


        # frappe.log_error(frappe.get_traceback(), f"3 {data}")
            

        # frappe.log_error(frappe.get_traceback(), f"4 {params}")
    except Exception as e:
        # Log any error that occurs in Error Log doctype
        frappe.log_error(frappe.get_traceback(), f"5 {e}") 

    # Validate the signature
    signature = frappe.get_request_header("X-Hub-Signature-256")
    # frappe.log_error(frappe.get_traceback(), f"6 {signature}")

        
    if verify_signature(request_data, signature):
        # frappe.log_error(frappe.get_traceback(), f"60 {signature} {data}")
    # Process lead data
        if data.get("object") == "page":
            # frappe.log_error(frappe.get_traceback(), f"8 {data.get('object')}")
            for entry in data.get("entry", []):
                for change in entry.get("changes", []):
                    if change.get("field") == "leadgen":
                        lead_id = change["value"]["leadgen_id"]
                        form_id = change["value"]["form_id"]
                        process_lead(lead_id, form_id)
                        # frappe.log_error(frappe.get_traceback(), f"100 {lead_id} {form_id}")
    else:
        frappe.log_error(frappe.get_traceback(), f"7")

    return "Webhook received"

def verify_signature(payload, signature):

    # payload = json.loads(payload)
    """
    Verifies the Meta webhook request signature using the app secret.
    """

    # frappe.log_error(frappe.get_traceback(), f"101 {payload}")
    if not signature:
        frappe.log_error(frappe.get_traceback(), f"9")
        return False
    try:
        key = META_APP_SECRET.encode("utf-8") if isinstance(META_APP_SECRET, str) else META_APP_SECRET

        msg = payload


        expected_signature = "sha256=" + hmac.new(
            key=key,
            msg=msg,
            digestmod=hashlib.sha256
        ).hexdigest()
        # frappe.log_error(frappe.get_traceback(), f"10 {expected_signature} {signature}")
        return hmac.compare_digest(expected_signature, signature)
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), f"11 {e}")
        return False

def process_lead(lead_id, form_id):
    """
    Fetches lead details from Meta Graph API and creates a Lead in ERPNext CRM.
    """
    lead_url = f"https://{URL}/{VERSION}/{lead_id}?access_token={ACCESS_TOKEN}"
    # frappe.log_error(frappe.get_traceback(), f"12 Lead URL: {lead_url}")
    payload ={}
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    # frappe.log_error(frappe.get_traceback(), f"13 Making API request to Meta")
    response = requests.request("GET", lead_url, headers=headers, data=payload, timeout=10)

    # frappe.log_error( f"99 Response Status:")
    # log_request = frappe.get_doc({
    #     "doctype": "Note",
    #     "title": "Meta Webhook Bros",
    #     "content": response.text,
    #     "public":1
    # })
    # log_request.insert(ignore_permissions=True)
    # frappe.db.commit()
    # frappe.log_error(f"98 Response Content: {response}")
    # frappe.log_error(f"098", {json.dumps(response.json())})

    # check_type=type(response.json())

    # frappe.log_error(f"098090", {check_type})

    # log_request = frappe.get_doc({
    #     "doctype": "Note",
    #     "title": "JSON WEBHOOK RES",
    #     "content": str(response.json()),
    #     "public":1
    # })
    # log_request.insert(ignore_permissions=True)
    # frappe.db.commit()
    
    
    try:

        if response.status_code == 200:
            try:
                lead_data = response.json()
                # frappe.log_error(f"Parsed Lead Data:  {response.status_code}")
            except ValueError as e:
                frappe.log_error(f"Failed to parse JSON response: {e}")
                return

            # Extract and log field data
            field_data = {field["name"]: field["values"][0] for field in lead_data.get("field_data", [])}
            # frappe.log_error(f"1001 Parsed Lead Data: {response.status_code} - Data: {json.dumps(lead_data)}", "Meta Lead JSON Parsing")
            # log_request = frappe.get_doc({
            #     "doctype": "Note",
            #     "title": "Field Data",
            #     "content": str(field_data),
            #     "public":1
            # })
            # log_request.insert(ignore_permissions=True)
            # frappe.db.commit()
            # frappe.log_error(f"Note created on field")


            lead_name = field_data.get("full_name").replace(">","")
            lead_company = field_data.get("company_name").replace(">","")
            lead_phone = field_data.get("phone_number")
            # frappe.log_error(f"Lead Name: {lead_name}, Lead Company: {lead_company}, Lead Phone: {lead_phone} Meta Lead Data")

            # Insert the lead into ERPNext CRM if data is complete
            if lead_name and lead_company:
                lead_doc = frappe.get_doc({
                    "doctype": "CRM Lead",
                    "first_name": lead_name,
                    "last_name": lead_company,
                    "mobile_no": lead_phone,
                    "custom_meta_id": lead_id,
                    "source": "Meta ads",
                })
                # frappe.log_error(frappe.get_traceback(), f"Prepared Lead Doc: {lead_doc.as_dict()}")

                try:
                    lead_doc.insert(ignore_permissions=True)
                    frappe.db.commit()
                    # frappe.log_error(f"Lead Document Inserted Successfully")
                except Exception as e:
                    frappe.log_error(frappe.get_traceback(), f"Failed to insert Lead Document: {e}")
            else:
                frappe.log_error(frappe.get_traceback(), f"Insufficient lead data: {field_data}")
        else:
            # Log any unexpected status code
            frappe.log_error(f"Unexpected status code: {response.status_code}, Response: {response.text}")

    except requests.exceptions.RequestException as e:
        # Log network or connection errors specifically
        frappe.log_error(f"Request failed: {e}")