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

from ..vpc import SecurityGroup
from .subnet_group import SubnetGroup


class BaseCacheCluster(object):

    instance_class = argument.String(field="CacheNodeType")
    engine = argument.String(field='Engine', aws_update=False)
    engine_version = argument.String(field='EngineVersion')
    port = argument.Integer(min=1, max=32768, field='Port', aws_update=False)
    security_groups = argument.ResourceList(SecurityGroup, field='SecurityGroupIds')
    availability_zone = argument.String(field='PreferredAvailabilityZone')
    multi_az = argument.Boolean(field='AZMode')
    auto_minor_version_upgrade = argument.Boolean(field='AutoMinorVersionUpgrade')
    num_cache_nodes = argument.Integer(field='NumCacheNodes')
    subnet_group = argument.Resource(SubnetGroup, field='CacheSubnetGroupName')
    # parameter_group = argument.Resource(ParamaterGroup, field='CacheParameterGroupName')
    apply_immediately = argument.Boolean(field="ApplyImmediately", aws_create=False)

    # tags = argument.Dict()
    account = argument.Resource(Account)


class CacheCluster(BaseCacheCluster, Resource):

    resource_name = "cache_cluster"

    name = argument.String(regex=r"[a-z1-9\-]{1,20}", field="CacheClusterId")
    # replication_group = argument.Resource("touchdown.aws.elasticache.replication_group.ReplicationGroup", field='ReplicationGroupId')


class Describe(SimpleDescribe, Plan):

    resource = CacheCluster
    service_name = 'elasticache'
    describe_action = "describe_cache_clusters"
    describe_notfound_exception = "CacheClusterNotFound"
    describe_list_key = "CacheClusters"
    key = 'CacheClusterId'


class Apply(SimpleApply, Describe):

    create_action = "create_cache_cluster"
    # update_action = "modify_cache_cluster"
    waiter = "cache_cluster_available"


class Destroy(SimpleDestroy, Describe):

    destroy_action = "delete_cache_cluster"
    waiter = "cache_cluster_deleted"
