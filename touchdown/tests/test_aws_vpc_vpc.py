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

from . import aws


class TestVpc(aws.TestBasicUsage):

    def setUpResource(self):
        self.expected_resource_id = 'vpc-1a2b3c4d'
        self.resource = self.aws.add_vpc(
            name='test-vpc',
            cidr_block='192.168.0.1/25',
        )
