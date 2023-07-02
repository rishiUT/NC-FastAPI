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
import time

# Before connecting to MTurk, set up your AWS account and IAM settings as
# described here:
# https://blog.mturk.com/how-to-use-iam-to-control-api-access-to-your-mturk-account-76fe2c2e66e2
#
# Follow AWS best practices for setting up credentials here:
# http://boto3.readthedocs.io/en/latest/guide/configuration.html

# Use the Amazon Mechanical Turk Sandbox to publish test Human Intelligence
# Tasks (HITs) without paying any money.  Sign up for a Sandbox account at
# https://requestersandbox.mturk.com/ with the same credentials as your main
# MTurk account.

# By default, HITs are created in the free-to-use Sandbox
create_hits_in_live = False

environments = {
        "live": {
            "endpoint": "https://mturk-requester.us-east-1.amazonaws.com",
            "preview": "https://www.mturk.com/mturk/preview",
            "manage": "https://requester.mturk.com/mturk/manageHITs",
            "reward": "2.00"
        },
        "sandbox": {
            "endpoint": "https://mturk-requester-sandbox.us-east-1.amazonaws.com",
            "preview": "https://workersandbox.mturk.com/mturk/preview",
            "manage": "https://requestersandbox.mturk.com/mturk/manageHITs",
            "reward": "0.00"
        },
}
mturk_environment = environments["live"] if create_hits_in_live else environments["sandbox"]
file_to_save_hit_ids = "active_hits_live.txt" if create_hits_in_live else "active_hits_sandbox.txt"

# use profile if one was passed as an arg, otherwise
profile_name = sys.argv[1] if len(sys.argv) >= 2 else None
session = boto3.Session(profile_name=profile_name)
client = session.client(
    service_name='mturk',
    region_name='us-east-1',
    endpoint_url=mturk_environment['endpoint'],
)

# Test that you can connect to the API by checking your account balance
user_balance = client.get_account_balance()

# In Sandbox this always returns $10,000. In live, it will be your acutal balance.
print("Your account balance is {}".format(user_balance['AvailableBalance']))

# The question we ask the workers is contained in this file.
question_sample = open("my_external_question.xml", "r").read()

# Example of using qualification to restrict responses to Workers who have had
# at least 0% of their assignments approved. See:
# http://docs.aws.amazon.com/AWSMechTurk/latest/AWSMturkAPI/ApiReference_QualificationRequirementDataStructureArticle.html#ApiReference_QualificationType-IDs
worker_requirements = [{
    'QualificationTypeId': '000000000000000000L0',
    'Comparator': 'GreaterThanOrEqualTo',
    'IntegerValues': [0],
    'RequiredToPreview': True,
}]

# Since each hit can only be completed once, we will make as many hits as we want respondents
max_respondents = 50
max_per_task = 1 # This is the number of people that can do each task. This should be 1, since we want people to be able to do the task multiple times.
with open(file_to_save_hit_ids, "a") as myfile:
    for i in range(max_respondents):

        # Create the HIT
        response = client.create_hit(
            Title='Negotiate for a Craigslist Item',
            Description='Bargain with another user to buy or sell an item on craigslist for approximately a goal price',
            Question=question_sample,
            Reward=mturk_environment['reward'],
            AssignmentDurationInSeconds=900,
            LifetimeInSeconds=1209600, # Time until expiration, currently two weeks
            Keywords='negotiation, research, bargain, discussion, interaction, recording, audio',
            MaxAssignments=max_per_task,
            AutoApprovalDelayInSeconds=6000,
            QualificationRequirements=worker_requirements
        )

        # The response included several fields that will be helpful later
        hit_type_id = response['HIT']['HITTypeId']
        hit_id = response['HIT']['HITId']
        print("\nCreated HIT: {}".format(hit_id))

        myfile.write(str(hit_id) + "\n")

        print("\nYou can work the HIT here:")
        print(mturk_environment['preview'] + "?groupId={}".format(hit_type_id))

        print("\nAnd see results here:")
        print(mturk_environment['manage'])
        

