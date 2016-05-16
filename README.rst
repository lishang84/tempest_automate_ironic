tempest_automate_ironic

automate test with real API request (not fake) for ironic cases based on https://github.com/rameshg87/tempest

Openstack tempest uses fake request for unit test,and https://github.com/rameshg87/tempest overwrite whe request method, instead of real http request.

Now I use the real http request to do some ironic test cases.

More information see tempest_automate_ironic/tempest/scenario/automate/README.rst
