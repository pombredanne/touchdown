# Copyright 2014 Isotoma Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from touchdown.core.resource import Resource
from touchdown.core.plan import Plan
from touchdown.core import argument

from ..account import Account
from ..common import SimpleDescribe, SimpleApply, SimpleDestroy


class VPC(Resource):

    resource_name = "vpc"

    name = argument.String()
    cidr_block = argument.IPNetwork(field='CidrBlock')
    tenancy = argument.String(default="default", choices=["default", "dedicated"], field="InstanceTenancy")

    tags = argument.Dict()

    account = argument.Resource(Account)


class Describe(SimpleDescribe, Plan):

    resource = VPC
    service_name = 'ec2'
    describe_action = "describe_vpcs"
    describe_list_key = "Vpcs"
    key = 'VpcId'

    def get_describe_filters(self):
        if self.key in self.object:
            return {
                "Filters": [
                    {'Name': 'vpc-id', 'Values': [self.object[self.key]]}
                ]
            }

        return {
            "Filters": [
                {'Name': 'tag:Name', 'Values': [self.resource.name]},
            ],
        }


class Apply(SimpleApply, Describe):

    create_action = "create_vpc"
    waiter = 'vpc_available'


class Destroy(SimpleDestroy, Describe):

    destroy_action = "delete_vpc"
    #waiter = 'vpc_terminated'
