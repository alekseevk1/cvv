#
# CVV is a continuous verification visualizer.
# Copyright (c) 2019-2023 ISP RAS (http://www.ispras.ru)
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

import datetime
import logging
import multiprocessing
import os
import time

from django.utils.timezone import now

from marks.Download import AllMarksGen
from marks.models import MarkUnsafe, MarkSafe, MarkUnknown
from marks.utils import DownloadTags

AUTOSAVE_DIR = "autosave"
AUTOSAVE_INTERVAL = 86400  # in seconds


def auto_save():
    logger = logging.getLogger('web')
    project_dir = os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, os.pardir))
    autosave_dir = os.path.join(project_dir, AUTOSAVE_DIR)
    if not os.path.exists(autosave_dir):
        os.makedirs(autosave_dir, exist_ok=True)
    tags = {}
    while True:
        curr_time = now()
        created_time = now() - datetime.timedelta(seconds=AUTOSAVE_INTERVAL)

        # Marks.
        if MarkUnsafe.objects.filter(change_date__gte=created_time).count() or \
                MarkSafe.objects.filter(change_date__gte=created_time).count() or \
                MarkUnknown.objects.filter(change_date__gte=created_time).count():
            generator = AllMarksGen()
            file_name = os.path.join(autosave_dir, generator.name)
            with open(file_name, "wb") as f:
                for line in generator:
                    f.write(line)
            logger.info("Save marks into file '{}'".format(file_name))

        # Tags.
        for tags_type in ['safe', 'unsafe']:
            generator = DownloadTags(tags_type)
            tags_str = generator._data
            is_create_backup = True
            if tags.get(tags_type, "") == tags_str:
                is_create_backup = False
            if is_create_backup:
                tags[tags_type] = tags_str
                file_name = os.path.join(autosave_dir,
                                         'Tags-%s-%s-%s-%s.json' % (tags_type, curr_time.day, curr_time.month,
                                                                    curr_time.year))
                with open(file_name, "wb") as f:
                    f.write(generator._data)
                logger.info("Save {} tags into file '{}'".format(tags_type, file_name))

        time.sleep(AUTOSAVE_INTERVAL)


def start_auto_save():
    multiprocessing.Process(target=auto_save, name="service_auto_save").start()
