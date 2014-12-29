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

from touchdown.core import errors
from touchdown.core.action import Action
from touchdown.core.resource import Resource


class GenericAction(Action):

    def __init__(self, runner, target, description, api, **kwargs):
        super(GenericAction, self).__init__(runner, target)
        self.api = api
        self._description = description
        self.kwargs = kwargs

    @property
    def description(self):
        yield self._description

    def run(self):
        params = {}
        params.update(self.kwargs)

        for name, argument in self.resource.arguments:
            if not argument.present(self.resource):
                continue

            if not hasattr(argument, "aws_field"):
                continue

            value = getattr(self.resource, name)
            if isinstance(value, Resource):
                value = self.runner.get_target(value).resource_id

            params[argument.aws_field] = value

        self.api(**params)


class SetTags(Action):

    def __init__(self, runner, target, tags):
        super(SetTags, self).__init__(runner, target)
        self.tags = tags

    @property
    def description(self):
        yield "Set tags on resource {}".format(self.resource.name)
        for k, v in self.tags.items():
            yield "{} = {}".format(k, v)

    def run(self):
        self.target.client.create_tags(
            Resources=[self.target.resource_id],
            Tags=[{"Key": k, "Value": v} for k, v in self.tags.items()],
        )


class SimpleApply(object):

    """
    A simple data-driven resource for AWS api's that a moderately well behaved.

    For example::

        cache CacheClusterApply(SimplyApply, Target):
            resource = CacheCluster
            create_action = "create_cache_cluster"
            describe_action = "describe_cache_cluster"
            describe_list_key = "CacheClusters"
            key = 'CacheClusterId'
    """

    name = "apply"
    default = True

    def get_describe_filters(self):
        return {
            self.describe_list_key: self.resource.name
        }

    def describe_object(self, runner):
        results = getattr(self.client, self.describe_action)(
            **self.get_describe_filters(runner)
        )

        objects = results[self.describe_list_key]

        if len(objects) > 1:
            raise errors.Error("Expecting to find one {}, but found {}".format(self.resource, len(objects)))

        if len(objects) == 1:
            return objects[0]

    def get_create_extra_args(self):
        return {}

    def create_object(self, runner):
        return GenericAction(
            runner,
            self,
            "Creating {}".format(self.resource),
            getattr(self.client, self.add_action),
            **self.get_create_extra_args()
        )

    def get_actions(self, runner):
        self.object = self.describe_object(runner)

        if not self.object:
            self.object = {}
            yield self.create_object(runner)

        if hasattr(self.resource, "tags"):
            local_tags = dict(self.resource.tags)
            local_tags['name'] = self.resource.name

            remote_tags = dict((v["Key"], v["Value"]) for v in self.object.get('Tags', []))

            tags = {}
            for k, v in local_tags.items():
                if k not in remote_tags or remote_tags[k] != v:
                    tags[k] = v

            if tags:
                yield SetTags(
                    runner,
                    self,
                    tags={"name": self.resource.name}
                )

    @property
    def resource_id(self):
        return self.object[self.key]
