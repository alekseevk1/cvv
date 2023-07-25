#!/usr/bin/env python3
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

import os

from utils.utils import get_args_parser, Session

parser = get_args_parser('Upload ZIP archive of verification job to parent verification job.')
parser.add_argument('parent', help='Parent verification job identifier or its name.')
parser.add_argument('--archive', help='ZIP archive name.', required=True)
args = parser.parse_args()

if not os.path.exists(args.archive):
    raise FileNotFoundError('ZIP archive of verification job "{0}" does not exist'.format(args.archive))

with Session(args) as session:
    session.upload_job(args.parent, args.archive)

print('ZIP archive of verification job "{0}" was successfully uploaded for parent verification job "{1}"'
      .format(args.archive, args.parent))
