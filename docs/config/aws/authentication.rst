.. currentmodule: touchdown.aws

Authentication
==============

Access keys
-----------

The simplest way to start performing actions against AWS is to add a :class:`~touchdown.aws.account.Account` object to your workspace::

    aws = workspace.add_aws(
        access_key_id='AKIDFKJDKFJF',
        secret_acess_key='skdfkoeJIJE4e2SFF',
        region='eu-west-1',
    )


Assuming a role
---------------

You can combine this with :class:`touchdown.aws.external_account.ExternalRole` to assume a role::

    other_account = aws.add_external_role(
        name='my-role',
        arn='',
    )
