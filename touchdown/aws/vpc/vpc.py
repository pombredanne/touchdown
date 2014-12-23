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

from botocore import session

from touchdown.core.resource import Resource
from touchdown.core.policy import Policy
from touchdown.core.action import Action
from touchdown.core.argument import String
from touchdown.core import errors

from .subnet import Subnet
from .common import VPCMixin
from ..common import SetTags


class VPC(Resource):

    """ A DNS zone hosted at Amazon Route53 """

    resource_name = "vpc"

    subresources = [
        Subnet,
    ]

    name = String()
    cidr_block = String()


class AddVPC(Action):

    @property
    def description(self):
        yield "Add virtual private cloud '{}'".format(self.resource.name)

    def run(self):
        operation = self.policy.service.get_operation("CreateVpc")
        response, data = operation.call(
            self.policy.endpoint,
            CidrBlock=self.resource.cidr_block,
        )

        if response.status_code != 200:
            raise errors.Error("Unable to create VPC")

        # FIXME: Create and invoke CreateTags to set the name here.


class Apply(Policy, VPCMixin):

    name = "apply"
    resource = VPC
    default = True

    def get_vpc(self):
        operation = self.service.get_operation("DescribeVpcs")
        response, data = operation.call(self.endpoint)
        for vpc in data['Vpcs']:
            if vpc['CidrBlock'] == self.resource.cidr_block:
                return vpc

    def get_actions(self, runner):
        zone = self.get_vpc()

        if not zone:
            yield AddVPC(self)
            return

        tags = dict((v["Key"], v["Value"]) for v in zone.get('Tags', []))

        if tags.get('name', '') != self.resource.name:
            yield SetTags(
                self,
                resources=[zone['VpcId']],
                tags={"name": self.resource.name}
            )