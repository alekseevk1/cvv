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

import mimetypes
import os

from django.http import JsonResponse, StreamingHttpResponse, HttpResponseNotAllowed
from django.utils.translation import gettext_lazy as _
from django.views.generic.base import View, ContextMixin
from django.views.generic.detail import SingleObjectMixin, SingleObjectTemplateResponseMixin

from users.utils import ViewData
from web.utils import logger, BridgeException
from web.vars import UNKNOWN_ERROR, VIEW_TYPES


# TODO: check if it used anywhere
class AuthenticatedMixin:
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(super(), 'dispatch'):
            # This mixin should be used together with main View based class
            raise BridgeException()

        if not request.user.is_authenticated:
            raise BridgeException(_('You are not signing in'))
        try:
            return getattr(super(), 'dispatch')(request, *args, **kwargs)
        except Exception as e:
            if isinstance(e, BridgeException):
                message = str(e.message)
            else:
                logger.exception(e)
                message = str(UNKNOWN_ERROR)
            raise BridgeException(message=message)


class JSONResponseMixin:
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(super(), 'dispatch'):
            # This mixin should be used together with main View based class
            raise BridgeException(response_type='json')

        if not request.user.is_authenticated:
            raise BridgeException(_('You are not signing in'), response_type='json')
        try:
            return getattr(super(), 'dispatch')(request, *args, **kwargs)
        except Exception as e:
            if isinstance(e, BridgeException):
                message = str(e.message)
            else:
                logger.exception(e)
                message = str(UNKNOWN_ERROR)
            raise BridgeException(message=message, response_type='json')


class JsonDetailView(JSONResponseMixin, SingleObjectMixin, View):
    def get(self, *args, **kwargs):
        self.__is_not_used(*args, **kwargs)
        self.object = self.get_object()
        return JsonResponse(self.get_context_data(object=self.object))

    def __is_not_used(self, *args, **kwargs):
        pass


class JsonDetailPostView(JSONResponseMixin, SingleObjectMixin, View):
    def post(self, *args, **kwargs):
        self.__is_not_used(*args, **kwargs)
        self.object = self.get_object()
        return JsonResponse(self.get_context_data(object=self.object))

    def __is_not_used(self, *args, **kwargs):
        pass


class JsonView(JSONResponseMixin, ContextMixin, View):
    def post(self, *args, **kwargs):
        self.__is_not_used(*args, **kwargs)
        return JsonResponse(self.get_context_data())

    def __is_not_used(self, *args, **kwargs):
        pass


class DetailPostView(JSONResponseMixin, SingleObjectTemplateResponseMixin, SingleObjectMixin, View):
    def post(self, *args, **kwargs):
        self.__is_not_used(*args, **kwargs)
        self.object = self.get_object()
        return self.render_to_response(self.get_context_data(object=self.object))

    def __is_not_used(self, *args, **kwargs):
        pass


class StreamingResponseView(View):
    file_name = None
    generator = None
    file_size = None

    def get_generator(self):
        return self.generator

    def get_filename(self):
        return self.file_name

    def get(self, *args, **kwargs):
        self.__is_not_used(*args, **kwargs)

        try:
            self.generator = self.get_generator()
        except Exception as e:
            if not isinstance(e, BridgeException):
                logger.exception(e)
                raise BridgeException()
            raise

        if self.generator is None:
            raise BridgeException()

        self.file_name = self.get_filename()
        if not isinstance(self.file_name, str) or len(self.file_name) == 0:
            raise BridgeException()

        mimetype = mimetypes.guess_type(os.path.basename(self.file_name))[0]
        response = StreamingHttpResponse(self.generator, content_type=mimetype)
        if self.file_size is not None:
            response['Content-Length'] = self.file_size
        response['Content-Disposition'] = 'attachment; filename="%s"' % self.file_name
        return response

    def __is_not_used(self, *args, **kwargs):
        pass


class StreamingResponsePostView(StreamingResponseView):
    def get(self, *args, **kwargs):
        return HttpResponseNotAllowed(['post'])

    def post(self, *args, **kwargs):
        return super().get(*args, **kwargs)


class DataViewMixin:
    def get_view(self, view_type):
        if not hasattr(self, 'request'):
            raise BridgeException()
        request = getattr(self, 'request')
        if view_type not in VIEW_TYPES:
            raise BridgeException()
        return ViewData(request.user, view_type, request.POST if request.method == 'POST' else request.GET)
