# Copyright 2017 Amazon.com, Inc. or its affiliates

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

# http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sys
import boto3
from xml.dom.minidom import parseString

# Before connecting to MTurk, set up your AWS account and IAM settings as described here:
# https://blog.mturk.com/how-to-use-iam-to-control-api-access-to-your-mturk-account-76fe2c2e66e2
#
# Follow AWS best practices for setting up credentials here:
# http://boto3.readthedocs.io/en/latest/guide/configuration.html

# Use the Amazon Mechanical Turk Sandbox to publish test Human Intelligence Tasks (HITs) without paying any money.
# Sign up for a Sandbox account at https://requestersandbox.mturk.com/ with the same credentials as your main MTurk account.

# By default, HITs are created in the free-to-use Sandbox
create_hits_in_live = True
file_to_save_hit_ids = "active_hits_live.txt" if create_hits_in_live else "active_hits_sandbox.txt"
hit_ids = []
file1 = open(file_to_save_hit_ids, 'r')
for line in file1:
    hit_ids.append(line) 


environments = {
        "live": {
            "endpoint": "https://mturk-requester.us-east-1.amazonaws.com",
            "preview": "https://www.mturk.com/mturk/preview",
            "manage": "https://requester.mturk.com/mturk/manageHITs",
            "reward": "0.00"
        },
        "sandbox": {
            "endpoint": "https://mturk-requester-sandbox.us-east-1.amazonaws.com",
            "preview": "https://workersandbox.mturk.com/mturk/preview",
            "manage": "https://requestersandbox.mturk.com/mturk/manageHITs",
            "reward": "0.11"
        },
}
mturk_environment = environments["live"] if create_hits_in_live else environments["sandbox"]

# use profile if one was passed as an arg, otherwise
profile_name = sys.argv[2] if len(sys.argv) >= 3 else None
session = boto3.Session(profile_name=profile_name)
client = session.client(
    service_name='mturk',
    region_name='us-east-1',
    endpoint_url=mturk_environment['endpoint'],
)

for hit_id in hit_ids:
    hit_id = hit_id[:-1]
    hit = client.get_hit(HITId=hit_id)
    print('Hit {} status: {}'.format(hit_id, hit['HIT']['HITStatus']))
    
    response2 = client.update_expiration_for_hit(
        HITId=hit_id,
        ExpireAt=0,
    )
