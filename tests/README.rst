=====
Tests
=====

From the root of the project, run

.. code-block::

  $ python -m pytest

The tests that require Amazon S3 access will be skipped if you have no credentials. You can test using a
key like so:

.. code-block::

  $ AWS_ACCESS_KEY_ID=ID AWS_SECRET_ACCESS_KEY=KEY python -m pytest

The key used for Travis is generated using the Amazon CloudFormation template at
https://github.com/rasterio/rasterio/blob/master/cloudformation/travis.template. If you had to fork
Rasterio and run your own tests, you could `use this template <http://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/cfn-console-create-stack.html>`__ to create your own IAM user and get a new key from your stack's "Outputs" field.
