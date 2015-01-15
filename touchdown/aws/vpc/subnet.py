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
from touchdown.core.plan import Plan, Present
from touchdown.core import argument, serializers

from .vpc import VPC
from .route_table import RouteTable
from .network_acl import NetworkACL
from ..common import SimpleDescribe, SimpleApply, SimpleDestroy


class Subnet(Resource):

    resource_name = "subnet"

    name = argument.String()
    cidr_block = argument.IPNetwork(field='CidrBlock')
    availability_zone = argument.String(field='AvailabilityZone')
    route_table = argument.Resource(RouteTable)
    network_acl = argument.Resource(NetworkACL)
    tags = argument.Dict()
    vpc = argument.Resource(VPC, field='VpcId')


class Describe(SimpleDescribe, Plan):

    resource = Subnet
    service_name = 'ec2'
    describe_action = "describe_subnets"
    describe_list_key = "Subnets"
    key = 'SubnetId'

    def get_describe_filters(self):
        return {
            "Filters": [
                {'Name': 'cidrBlock', 'Values': [str(self.resource.cidr_block)]},
            ],
        }

    def describe_object(self):
        object = super(Describe, self).describe_object()
        if not object or not object.get(self.key, None):
            return object

        subnet_id = object[self.key]

        network_acl = self.client.describe_network_acls(
            Filters=[
                {'Name': 'association.subnet-id', 'Values': [subnet_id]},
            ],
        )['NetworkAcls']

        if network_acl:
            for assoc in network_acl[0].get('Associations', []):
                if assoc['SubnetId'] == subnet_id:
                    object['NetworkAclId'] = assoc['NetworkAclId']
                    object['NetworkAclAssociationId'] = assoc['NetworkAclAssociationId']
                    break

        route_tables = self.client.describe_route_tables(
            Filters=[
                {'Name': 'association.subnet-id', 'Values': [subnet_id]},
            ],
        )['RouteTables']

        if route_tables:
            for assoc in route_tables[0].get('Associations', []):
                if assoc['SubnetId'] == subnet_id:
                    object['RouteTableId'] = assoc['RouteTableId']
                    object['RouteTableAssociationId'] = assoc['RouteTableAssociationId']
                    break

        return object


class Apply(SimpleApply, Describe):

    create_action = "create_subnet"

    signature = (
        Present('name'),
        Present('vpc'),
        Present('cidr_block'),
    )

    def update_object(self):
        if self.resource.route_table:
            if not self.object.get("RouteTableAssociationId", None):
                yield self.generic_action(
                    "Associate route table",
                    self.client.associate_route_table,
                    SubnetId=serializers.Identifier(),
                    RouteTableId=serializers.Context(serializers.Argument("route_table"), serializers.Identifier()),
                )
            elif self.object['RouteTableId'] != self.runner.get_plan(self.resource.route_table).resource_id:
                yield self.generic_action(
                    "Replace route table association",
                    self.client.associate_route_table,
                    AssociationId=self.object["RouteTableAssociationId"],
                    RouteTableId=serializers.Context(serializers.Argument("route_table"), serializers.Identifier()),
                )
        elif self.object.get("RouteTableAssociationId", None):
            yield self.generic_action(
                "Disassociate route table",
                self.client.disassociate_route_table,
                AssociationId=self.object["RouteTableAssociationId"],
            )

        #if self.resource.network_acl and (not self.object or self.object.get("NetworkAclAssociationId", None)):
        #    if self.runner.get_plan(self.resource.network_acl).resource_id != self.object.get('NetworkAclId', None):
        #        yield self.generic_action(
        #            "Replace Network ACL association",
        #            self.client.replace_network_acl_association,
        #            AssociationId=self.object['NetworkAclAssociationId'],
        #            NetworkAclId=serializers.Context(serializers.Argument("network_acl"), serializers.Identifier()),
        #        )


class Destroy(SimpleDestroy, Describe):

    destroy_action = "delete_subnet"
