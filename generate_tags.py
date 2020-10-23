import argparse
from http import HTTPStatus
import json
import uuid
import requests
import sys
from difflib import unified_diff

from dictdiffer import diff
from tqdm.auto import tqdm

import product_ids

get_host_by_name_url = "https://%s/api/inventory/v1/hosts?display_name=%s"
get_host_url = "https://%s/api/inventory/v1/hosts/%s"
get_system_profile_url = get_host_url + "/system_profile"
filename = "tags.yaml"

def _create_file(filename):
    fo = open(filename, "wb")
    #print ("Name of the file: ", fo.name)
    #print ("Closed or not : ", fo.closed)
    #print ("Opening mode : ", fo.mode)
    fo.close()

def _append_file(filename, string):
    fo = open(filename, "a")
    fo.write(string)
    fo.close()

def _make_request(url, username, password, ssl_verify):
    response = requests.get(
        url, auth=(args.api_username, args.api_password), verify=ssl_verify
    )
    if response.status_code != HTTPStatus.OK:
        raise RuntimeError("bad response from server: %s" % response.status_code)
    result = response.json()
    if "data" in result and len(result["data"]) == 0:
        raise RuntimeError("no results found for request")
    elif "results" in result and len(result["results"]) == 0:
        raise RuntimeError("no results found for request")
    return result

def _is_uuid(input_string):
    try:
        uuid.UUID(input_string)
        return True
    except:
        return False

parser = argparse.ArgumentParser(description="view changes for an insights host")
parser.add_argument("inventory_id", help="inventory ID or display name")
parser.add_argument("api_username", help="cloud.redhat.com username")
parser.add_argument("api_password", help="cloud.redhat.com password")
parser.add_argument(
    "-a",
    "--api_hostname",
    default="cloud.redhat.com",
    help="API hostname to connect to",
)
parser.add_argument(
    "--disable-ssl-verify",
    dest="ssl_verify",
    action="store_false",
    help="disable SSL hostname verification (only useful for testing)",
)
parser.set_defaults(tls_validation=True)

args = parser.parse_args()

inv_uuid = args.inventory_id
verify = args.tls_validation


if not _is_uuid(args.inventory_id):
    # assume we got a display name if we didn't get a uuid
    inv_record = _make_request(
        get_host_by_name_url % (args.api_hostname, args.inventory_id),
        args.api_username,
        args.api_password,
        args.ssl_verify,
    )
    inv_uuid = inv_record["results"][0]["id"]

# Get system_profile
host_data = _make_request(
    get_host_url % (args.api_hostname, inv_uuid),
    args.api_username,
    args.api_password,
    args.ssl_verify,
)

display_name = host_data["results"][0]["display_name"]

tqdm.write(f"fetching system profiles for {display_name}...")
system_profile_data = _make_request(
    get_system_profile_url % (args.api_hostname, inv_uuid),
    args.api_username,
    args.api_password,
    args.ssl_verify,
)
system_profile = system_profile_data["results"][0]["system_profile"]

_create_file(filename)

# Append static tags
_append_file(filename, "Owner: First Last\n")
_append_file(filename, "Slack: slackid\n")

# Simple check for fact value
#for name, value in system_profile.items():
#    print (name, value)
#    print(f"name: {name} - value: {value}")
#    if name is "os_release" and value is "8.2":
#        print(f"name: {name} - value: {value}")
#        _append_file(filename, "OS: RHEL8.2\n")

# Simple check for fact value
if system_profile['os_release'] and system_profile['os_release'] == "8.2":
    #print(f"Adding tag: OS: RHEL8.2")
    _append_file(filename, "OS: RHEL8.2\n")

# Simple check for fact value in list
if system_profile['installed_services']:
    subs = 'httpd'
    res = [i for i in system_profile['installed_services'] if subs in i] 
    if res:
        #print(f"Found: {res}")
        _append_file(filename, "Workload: Webserver\n")

# Lookup installed_products and map to name
if system_profile['installed_products']:
    _append_file(filename, "Products:\n")    
    for product in system_profile['installed_products']:
        #print(f"Red Hat product found: {product['id']}")
        #print(f"Red Hat product name lookup for {product['id']}: {product_ids.products_lookup[product['id']]}")
        _append_file(filename, f"- {product_ids.products_lookup[product['id']]}\n")

# Validate file content
#print(f"\nContent of {filename}")
#for tag in open(filename, "r"):
#    print(tag)

exit()
