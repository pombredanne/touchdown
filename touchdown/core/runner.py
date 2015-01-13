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

import logging

from . import errors, target


logger = logging.getLogger(__name__)


class Plan(object):

    tips_first = False
    """ If ``tips_first`` is set then the least dependended up nodes will be
    visited first. This is useful if you are deleting all nodes - for example,
    you need to delete subnets before you can delete the VPC they are in.

    If ``tips_first`` is False then the most dependended upon nodes will be
    visited first. This is the default, and is used when creating and apply
    changes - a VPC needs to exist before you can create a subnet in it.
    """

    def __init__(self, node):
        self.node = node
        self.map = {}
        self._prepare()

    def _add_dependency(self, node, dep):
        if self.tips_first:
            self.map.setdefault(dep, set()).add(node)
        else:
            self.map.setdefault(node, set()).add(dep)

    def _prepare(self):
        queue = [self.node]
        visiting = set()
        visited = set()

        while queue:
            node = queue.pop(0)
            visiting.add(node)

            self.map.setdefault(node, set())

            for dep in node.dependencies:
                if dep in visiting:
                    raise errors.CycleError(
                        'Circular reference between %s and %s' % (node, dep)
                    )
                self._add_dependency(node, dep)
                if dep not in visited and dep not in queue:
                    queue.append(dep)

            visiting.remove(node)
            visited.add(node)

    def get_ready(self):
        """ Yields resources that are ready to be applied """
        for node, deps in self.map.iteritems():
            if not deps:
                yield node

    def complete(self, node):
        """ Marks a node as complete - it's dependents may proceed """
        del self.map[node]
        for deps in self.map.itervalues():
            deps.difference_update((node,))

    def all(self):
        """ Visits all remaining nodes in order immediately """
        while self.map:
            ready = list(self.get_ready())
            if not ready:
                return

            for node in ready:
                print node
                yield node
                self.complete(node)


class Describe(Plan):
    pass


class Apply(Plan):
    pass


class Destroy(Plan):
    tips_first = True


class Runner(object):

    def __init__(self, target, node, ui):
        self.target = target
        self._plan = Plan(node)
        self.node = node
        self.ui = ui
        self.resources = {}

    def get_target(self, resource):
        if resource not in self.resources:
            klass = resource.target
            if not klass:
                #FIXME: This needs to be less rubbish
                klass = resource.targets.get(
                    self.target,
                    resource.targets.get("describe", target.NullTarget),
                )
            self.resources[resource] = klass(self, resource)
        return self.resources[resource]

    def dot(self):
        graph = ["digraph ast {"]

        for node, deps in self._plan.map.items():
            if not node.dot_ignore:
                graph.append('{} [label="{}"];'.format(id(node), node))
                for dep in deps:
                    if not dep.dot_ignore:
                        graph.append("{} -> {};".format(id(node), id(dep)))

        graph.append("}")
        return "\n".join(graph)

    def plan(self):
        plan = []
        with self.ui.progress(list(self._plan.all()), label="Creating change plan") as resolved:
            for resource in resolved:
                actions = tuple(self.get_target(resource).get_actions())
                if not actions:
                    logger.debug("No actions for {} - skipping".format(resource))
                    continue
                plan.append((resource, actions))

        return plan

    def apply(self):
        plan = self.plan()

        if not plan:
            raise errors.NothingChanged()

        if not self.ui.confirm_plan(plan):
            return

        with self.ui.progress(plan, label="Apply changes") as plan:
            for resource, actions in plan:
                for action in actions:
                    # if not ui.confirm_action(action):
                    #     continue
                    action.run()
