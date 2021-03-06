# Copyright 2015 Isotoma Limited
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
from touchdown.core import argument, serializers

from .vpc import VPC
from .customer_gateway import CustomerGateway
from .vpn_gateway import VpnGateway
from ..common import SimpleDescribe, SimpleApply, SimpleDestroy


class VpnConnection(Resource):

    resource_name = "vpn_connection"

    name = argument.String()
    customer_gateway = argument.Resource(CustomerGateway, field="CustomerGatewayId")
    vpn_gateway = argument.Resource(VpnGateway, field="VpnGatewayId")
    type = argument.String(default="ipsec.1", choices=["ipsec.1"], field="Type")

    static_routes_only = argument.Boolean(
        default=True,
        field="Options",
        serializer=serializers.Dict(StaticRoutesOnly=serializers.Boolean()),
    )

    static_routes = argument.List()
    # FIXME: This should somehow be a list of argument.IPNetwork

    tags = argument.Dict()
    vpc = argument.Resource(VPC)


class Describe(SimpleDescribe, Plan):

    resource = CustomerGateway
    service_name = 'ec2'
    describe_action = "describe_vpn_connections"
    describe_list_key = "VpnConnections"
    key = "VpnConnectionId"

    def get_describe_filters(self):
        vpc = self.runner.get_plan(self.resource.vpc)
        if not vpc.resource_id:
            return None

        if self.key in self.object:
            return {
                "Filters": [
                    {'Name': 'vpn-connection-id', 'Values': [self.object[self.key]]}
                ]
            }

        return {
            "Filters": [
                {'Name': 'tag:Name', 'Values': [self.resource.name]},
            ],
        }


class Apply(SimpleApply, Describe):

    create_action = "create_vpn_connection"
    waiter = "vpn_connection_available"

    def update_object(self):
        remote_routes = set(r['DestinationCidrBlock'] for r in self.object.get('Routes', []) if r['State'] != 'deleted')
        local_routes = set(self.resource.static_routes)

        for route in local_routes.difference(remote_routes):
            yield self.generic_action(
                "Add missing route {}".format(route),
                self.client.create_vpn_connection_route,
                VpnConnectionId=serializers.Identifier(),
                DestinationCidrBlock=route,
            )

        for route in remote_routes.difference(local_routes):
            yield self.generic_action(
                "Remove stale route {}".format(route),
                self.client.create_vpn_connection_route,
                VpnConnectionId=serializers.Identifier(),
                DestinationCidrBlock=route,
            )


class Destroy(SimpleDestroy, Describe):

    destroy_action = "delete_vpn_connection"
    waiter = "vpn_connection_deleted"
