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

import click

from .runner import Runner
from .workspace import Workspace
from . import errors


class ConsoleInterface(object):

    def render_plan(self, plan):
        for resource, actions in plan:
            if actions:
                click.echo("%s:" % resource)
                for action in actions:
                    description = list(action.description)
                    click.echo("  * %s" % description[0])
                    for line in description[1:]:
                        click.echo("    %s" % line)
                click.echo("")

    def confirm_plan(self, plan):
        click.echo("Generated a plan to update infrastructure configuration:")
        click.echo()

        self.render_plan(plan)

        return click.confirm("Do you want to continue?")


@click.group()
@click.option('--debug/--no-debug', default=False, envvar='DEBUG')
@click.pass_context
def main(ctx, debug):
    g = {"workspace": Workspace()}
    execfile("Touchdownfile", g)
    ctx.obj = g['workspace']


@main.command()
@click.pass_context
def apply(ctx):
    r = Runner(ctx.obj, ConsoleInterface())
    try:
        r.apply()
    except errors.Error as e:
        raise click.ClickException(str(e))


@main.command()
@click.pass_context
def plan(ctx):
    r = Runner(ctx.obj, ConsoleInterface())
    r.ui.render_plan(r.plan())


if __name__ == "__main__":
    main()
