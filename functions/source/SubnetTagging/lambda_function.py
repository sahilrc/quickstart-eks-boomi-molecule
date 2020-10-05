import json
import logging
import boto3
import subprocess
import shlex
import re
import requests
from ruamel import yaml
from datetime import date, datetime
from crhelper import CfnResource
from time import sleep

logger = logging.getLogger(__name__)
helper = CfnResource(json_logging=True, log_level='DEBUG')

try:
    client = boto3.client('ec2')
except Exception as init_exception:
    helper.init_failure(init_exception)

def json_serial(o):
    if isinstance(o, (datetime, date)):
        return o.strftime('%Y-%m-%dT%H:%M:%SZ')
    raise TypeError("Object of type '%s' is not JSON serializable" % type(o))

def add_subnet_tags(subnet_ids, key, value):
    try:
        client.create_tags(
            Resources=subnet_ids,
            Tags=[{'Key': key, 'Value': value},],
        )
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to add tags in the subnet. {e}")

def remove_subnet_tags(subnet_ids, key, value):
    try:
        client.delete_tags(
            Resources=subnet_ids,
            Tags=[{'Key': key, 'Value': value},],
        )
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to delete tags from the subnet. {e}")

def enable_dns_hostname(vpc_id):
    try:
        client.modify_vpc_attribute(
            EnableDnsHostnames ={
                'Value': True,
            },
            VpcId=vpc_id,
        )
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to updated VPC DNS HostName. {e}")

def disable_dns_hostname(vpc_id):
    try:
        client.modify_vpc_attribute(
            EnableDnsHostnames ={
                'Value': False,
            },
            VpcId=vpc_id,
        )
        return True
    except Exception as e:
        raise RuntimeError(f"Failed to updated VPC DNS HostName. {e}")

def handler_init(event):
    logger.debug('Received event: %s' % json.dumps(event, default=json_serial))

    cluster_name = None
    vpc_id = None
    private_subnet_ids = None
    public_subnet_ids = None
    cluster_name = event['ResourceProperties']['ClusterName']
    vpc_id = event['ResourceProperties']['VPCID']
    private_subnet_ids = event['ResourceProperties']['PrivateSubnetIds']
    public_subnet_ids = event['ResourceProperties']['PublicSubnetIds']

    return cluster_name, vpc_id, private_subnet_ids, public_subnet_ids

@helper.create
def create_handler(event, _):
    cluster_name, vpc_id, private_subnet_ids, public_subnet_ids = handler_init(event)
    enable_dns_hostname(vpc_id)
    add_subnet_tags(private_subnet_ids, 'kubernetes.io/role/internal-elb', "1")
    add_subnet_tags(public_subnet_ids, 'kubernetes.io/role/elb', "1")
    add_subnet_tags(private_subnet_ids, 'kubernetes.io/cluster/{}'.format(cluster_name), "shared")
    add_subnet_tags(public_subnet_ids, 'kubernetes.io/cluster/{}'.format(cluster_name), "shared")
    return True

@helper.delete
def delete_handler(event, _):
    cluster_name, vpc_id, private_subnet_ids, public_subnet_ids = handler_init(event)
    remove_subnet_tags(private_subnet_ids, 'kubernetes.io/role/internal-elb', "1")
    remove_subnet_tags(public_subnet_ids, 'kubernetes.io/role/elb', "1")
    remove_subnet_tags(private_subnet_ids, 'kubernetes.io/cluster/{}'.format(cluster_name), "shared")
    remove_subnet_tags(public_subnet_ids, 'kubernetes.io/cluster/{}'.format(cluster_name), "shared")
    return True

def lambda_handler(event, context):
    helper(event, context)
