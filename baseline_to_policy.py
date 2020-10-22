import argparse
from http import HTTPStatus
import json
import requests
import time

get_baseline_url = "https://%s/api/system-baseline/v1/baselines/%s"
get_baseline_list_url = "https://%s/api/system-baseline/v1/baselines"
post_policy_url = "https://%s/api/policies/v1/policies?alsoStore=true"

class SetEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, set):
            return sorted(list(obj))
        if isinstance(obj, list):
            return sorted(obj)
        return json.JSONEncoder.default(self, obj)

def _make_request(url, username, password, ssl_verify):
    response = requests.get(
        url, auth=(username, password), verify=ssl_verify
    )
    if response.status_code != HTTPStatus.OK:
        raise RuntimeError("bad response from server: %s" % response.status_code)
    result = response.json()
    if "data" in result and len(result["data"]) == 0:
        raise RuntimeError("no results found for request")
    elif "results" in result and len(result["results"]) == 0:
        raise RuntimeError("no results found for request")
    return result

def _post_request(url, username, password, ssl_verify, json_data):
    headers = {'content-type': 'application/json'}
    response = requests.post(
        url, data=json_data, headers=headers, auth=(username, password), verify=ssl_verify
    )
    if response.status_code != HTTPStatus.CREATED:
        raise RuntimeError("bad response from server: %s" % response.status_code)
    result = response.json()
    if "data" in result and len(result["data"]) == 0:
        raise RuntimeError("no results found for request")
    elif "results" in result and len(result["results"]) == 0:
        raise RuntimeError("no results found for request")
    return result

parser = argparse.ArgumentParser(description="create policy from baseline")
parser.add_argument("baseline_id", help="baseline ID or display name")
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

baseline_uuid = args.baseline_id
verify=args.ssl_verify

# Get baseline by UUID
baseline = _make_request(
    get_baseline_url % (args.api_hostname, baseline_uuid),
    args.api_username,
    args.api_password,
    args.ssl_verify,
)

# Generate policy condition from baseline facts
conditions = []
for fact in baseline['data'][0]['baseline_facts']:
    if 'value' in fact:
        if fact['name'].startswith('tags'):
            conditions.append(str(f"'{fact['name']}'='{fact['value']}'"))
        else:
            conditions.append(str(f"'facts.{fact['name']}'='{fact['value']}'"))
    if 'values' in fact:
        for subfact in fact['values']:
            if fact['name'].startswith('tags'):
                # remove insights_client. source from tag name (policy does not handle it)
                tag_name = subfact['name'].split('.')[1]
                conditions.append(str(f"'{fact['name']}.{tag_name}'='{subfact['value']}'"))
            else:
                conditions.append(str(f"'facts.{fact['name']}.{subfact['name']}'='{subfact['value']}'"))

actions="email;webhook"
description=str(f"Generated from {baseline['data'][0]['display_name']}")
isEnabled="False"
current_time = time.strftime("%m/%d/%Y %H:%M", time.localtime())
name=str(f"Baseline policy for {baseline['data'][0]['display_name']} ({current_time})")

json=str(f"{{\"name\":\"{name}\", \"description\":\"{description}\", \"conditions\":\"NOT ({' AND '.join(conditions)})\", \"actions\":\"{actions}\", \"isEnabled\":\"{isEnabled}\"}}")

# Create policy via POST request
baseline = _post_request(
    post_policy_url % (args.api_hostname),
    args.api_username,
    args.api_password,
    args.ssl_verify,
    json,
)
