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

from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.template.loader import TemplateDoesNotExist
from django.urls import reverse
from django.utils.translation import gettext as _, activate

from marks.models import MarkSafe, MarkUnsafe, MarkUnknown
from reports.models import AttrName
from tools.profiling import unparallel_group
from users.models import Extended
from web.populate import Population
from web.utils import logger, BridgeErrorResponse, BridgeException
from web.vars import USER_ROLES, UNKNOWN_ERROR


def index_page(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect(reverse('jobs:tree'))
    return HttpResponseRedirect(reverse('users:login'))


@unparallel_group(['Job', 'MarkUnsafeCompare', 'MarkUnsafeConvert',
                   MarkSafe, MarkUnsafe, MarkUnknown, AttrName])
@login_required
def population(request):
    try:
        activate(request.user.extended.language)
    except ObjectDoesNotExist:
        activate(request.LANGUAGE_CODE)
    if not request.user.extended or request.user.extended.role != USER_ROLES[2][0]:
        return BridgeErrorResponse(_("You don't have an access to this page"))
    need_service = (len(Extended.objects.filter(role=USER_ROLES[4][0])) == 0)
    if request.method == 'POST':
        service_username = request.POST.get('service_username', '')
        if len(service_username) == 0:
            service_username = None
        if need_service and service_username is None:
            return BridgeErrorResponse(_("Can't populate without Manager and service user"))
        try:
            changes = Population(
                user=request.user, service=(service_username, request.POST.get('service_password'))
            ).changes
        except BridgeException as e:
            return render(request, 'Population.html', {'error': str(e)})
        except Exception as e:
            logger.exception(e)
            return render(request, 'Population.html', {'error': str(UNKNOWN_ERROR)})
        return render(request, 'Population.html', {'changes': changes})
    return render(request, 'Population.html', {'need_service': need_service})


@login_required
def help_pages(request, page=''):
    return render(request, 'help/main.html', {'page': page})


@login_required
def get_help_pages(request, page=''):
    try:
        return render(request, 'help/{}.html'.format(page))
    except TemplateDoesNotExist:
        return HttpResponse('<div class="ui header center aligned red">{}</div>'.
                            format(_('Required object does not exist')))
