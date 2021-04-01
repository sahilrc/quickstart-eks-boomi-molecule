import requests
import logging
import json
import copy
import urllib3

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
message = ''
code = ''
retries = 10

SUCCESS = "SUCCESS"
FAILED = "FAILED"

headers = {'Content-Type': 'application/json', 'Accept': 'application/json'}


def send(event, context, responseStatus, responseData, physicalResourceId=None, noEcho=False, reason=''):
    responseUrl = event['ResponseURL']

    print(responseUrl)

    responseBody = {}
    responseBody['Status'] = responseStatus
    responseBody['Reason'] = reason if reason else 'See the details in CloudWatch Log Stream: ' + \
                                                   context.log_stream_name
    responseBody['PhysicalResourceId'] = physicalResourceId or context.log_stream_name
    responseBody['StackId'] = event['StackId']
    responseBody['RequestId'] = event['RequestId']
    responseBody['LogicalResourceId'] = event['LogicalResourceId']
    responseBody['NoEcho'] = noEcho
    responseBody['Data'] = responseData

    json_responseBody = json.dumps(responseBody)

    print("Response body:\n" + json_responseBody)

    headers = {
        'content-type': '',
        'content-length': str(len(json_responseBody))
    }

    try:
        response = requests.put(responseUrl,
                                data=json_responseBody,
                                headers=headers)
        print("Status code: " + response.reason)
    except Exception as e:
        print("send(..) failed executing requests.put(..): " + str(e))


def lambda_handler(event, context):
    logger.debug(event)
    status = SUCCESS
    pid = 'None'
    response = {}
    reason = ''

    sanitized_event = copy.deepcopy(event)
    sanitized_event['ResourceProperties']['BoomiPassword'] = "<Redacted>"
    try:
        username = event['ResourceProperties']['BoomiUsername']
        password = event['ResourceProperties']['BoomiPassword']
        account_id = event['ResourceProperties']['BoomiAccountID']

        headers.update(urllib3.util.make_headers(
            basic_auth=f"{username}:{password}"))
        API_URL = f"https://api.boomi.com/api/rest/v1/{account_id}/Account/{account_id}"

        if event['RequestType'] == 'Create':
            resp = requests.get(API_URL, headers=headers)
            resp.raise_for_status()
            jsonresp = resp.json()
            boomistatus = (jsonresp["status"])
            boomient = (jsonresp["licensing"]["enterprise"]["purchased"])
            boomientused = (jsonresp["licensing"]["enterprise"]["used"])

            if boomistatus == "active":
                print("Account active")
            else:
                print('Exception: Boomi account is inactive')

            if boomient > boomientused:
                print("License available")
            else:
                print('Exception: No enterprise license available')

    except requests.exceptions.RequestException as err:
        logging.error(
            'Please contact your account administrator for assistance')
        logging.error(err.response.text)
        reason = (str('Please contact your account administrator for assistance'))
        status = FAILED

    except Exception as e:
        logging.error('Unhandled exception', exc_info=True)
        reason = (str(e))
        status = FAILED
    finally:
        send(event, context, status, response, pid, reason=reason)
