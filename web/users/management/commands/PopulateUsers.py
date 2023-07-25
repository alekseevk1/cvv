#
# CVV is a continuous verification visualizer.
# Copyright (c) 2023 ISP RAS (http://www.ispras.ru)
# Ivannikov Institute for System Programming of the Russian Academy of Sciences
#
# Copyright (c) 2018 ISP RAS (http://www.ispras.ru)
# Ivannikov Institute for System Programming of the Russian Academy of Sciences
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

import json

from django.core.management.base import BaseCommand, CommandError

from web.populate import populate_users


class Command(BaseCommand):
    help = """
Populates administrator, manager and service users.
Accept four optional arguments: 'admin', 'manager', 'service' in json format and 'exist-ok' without any value.
Example argument: '{"username": "uname", "password": "pass", "last_name": "Name1", "first_name": "Name2"}'.
'last_name' and 'first_name' are not required; 'username' and 'password' are required. 'email' can be set for admin.
    """

    def add_arguments(self, parser):
        parser.add_argument('--admin', dest='admin', help='Administrator data in json format')
        parser.add_argument('--manager', dest='manager', help='Manager data in json format')
        parser.add_argument('--service', dest='service', help='Service data in json format')
        parser.add_argument('--exist-ok', dest='exist-ok', default=False, action='store_true',
                            help='Do not fail if users already exist')

    def handle(self, *args, **options):
        users = {'admin': None, 'manager': None, 'service': None, 'exist_ok': options['exist-ok']}
        if 'admin' in options and options['admin'] is not None:
            users['admin'] = json.loads(options['admin'])
        if 'manager' in options and options['manager'] is not None:
            users['manager'] = json.loads(options['manager'])
        if 'service' in options and options['service'] is not None:
            users['service'] = json.loads(options['service'])
        try:
            res = populate_users(**users)
        except Exception as e:
            raise CommandError(str(e))
        if res is not None:
            raise CommandError(res)
        self.stdout.write(self.style.SUCCESS('Users were successfully created'))
