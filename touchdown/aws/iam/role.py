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

import json

from touchdown.core.resource import Resource
from touchdown.core.plan import Plan
from touchdown.core import argument, errors, serializers

from ..account import Account
from ..common import SimpleDescribe, SimpleApply, SimpleDestroy


class Role(Resource):

    resource_name = "role"

    name = argument.String(field="RoleName")
    path = argument.String(field='Path')
    assume_role_policy = argument.Dict(field="AssumeRolePolicyDocument", serializer=serializers.Json())

    policies = argument.Dict()
    account = argument.Resource(Account)

    def clean_assume_role_policy(self, policy):
        if frozenset(policy.keys()).difference(frozenset(("Version", "Statement"))):
            raise errors.InvalidParameter("Unexpected policy key")

        result = {}
        result['Version'] = policy.get('Version', '2012-10-17')
        result['Statement'] = []
        for statement in policy.get("Statement", []):
            s = {
                "Action": statement["Action"],
                "Effect": statement["Effect"],
                "Principal": statement["Principal"],
                "Sid": statement.get("Sid", ""),
            }
            result['Statement'].append(s)
        return result


class Describe(SimpleDescribe, Plan):

    resource = Role
    service_name = 'iam'
    describe_action = "list_roles"
    describe_list_key = "Roles"
    key = 'RoleName'

    def describe_object(self):
        paginator = self.client.get_paginator("list_roles")
        for page in paginator.paginate():
            for role in page['Roles']:
                if role['RoleName'] == self.resource.name:
                    return role


class Apply(SimpleApply, Describe):

    create_action = "create_role"

    def update_object(self):
        policy_names = []

        for change in super(Apply, self).update_object():
            yield change

        remote_policy = self.object.get('AssumeRolePolicyDocument', None)
        if remote_policy and remote_policy != self.resource.assume_role_policy:
            yield self.generic_action(
                "Update 'Assume Role Policy' document",
                self.client.update_assume_role_policy,
                RoleName=serializers.Identifier(),
                PolicyDocument=serializers.Json(serializers.Argument("assume_role_policy")),
            )

        # If the object exists then we can look at the roles it has
        # Otherwise we assume its a new role and it will have no policies
        if self.object:
            policy_names = self.client.list_role_policies(
                RoleName=self.resource.name,
            )['PolicyNames']

        for name, document in self.resource.policies.items():
            document = json.loads(document)

            changed = False
            if name not in policy_names:
                changed = True

            # We can't do a single API to get all names and documents for all
            # policies, so for each policy that *might* have changed we have to
            # call teh API and check.
            # Save an API call by only doing it for policies that definitely
            # exist
            if not changed:
                policy = self.client.get_role_policy(
                    RoleName=self.resource.name,
                    PolicyName=name,
                )

                if policy['PolicyDocument'] != document:
                    changed = True

            if changed:
                yield self.generic_action(
                    "Put policy {}".format(name),
                    self.client.put_role_policy,
                    RoleName=self.resource.name,
                    PolicyName=name,
                    PolicyDocument=json.dumps(document),
                )

        for name in policy_names:
            if name not in self.resource.policies:
                yield self.generic_action(
                    "Delete policy {}".format(name),
                    self.client.delete_role_policy,
                    RoleName=self.resource.name,
                    PolicyName=name,
                )


class Destroy(SimpleDestroy, Describe):

    destroy_action = "delete_role"

    def destroy_object(self):
        result = self.client.list_role_policies(RoleName=self.resource.name)
        for name in result.get('PolicyNames', []):
            yield self.generic_action(
                "Delete policy {}".format(name),
                self.client.delete_role_policy,
                RoleName=self.resource.name,
                PolicyName=name,
            )

        for change in super(Destroy, self).destroy_object():
            yield change
