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

from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve

from web import views

urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('users/', include(('users.urls', 'users'), namespace='users')),
    path('jobs/', include(('jobs.urls', 'jobs'), namespace='jobs')),
    path('reports/', include(('reports.urls', 'reports'), namespace='reports')),
    path('marks/', include(('marks.urls', 'marks'), namespace='marks')),
    path('service/', include(('service.urls', 'service'), namespace='service')),
    path('tools/', include(('tools.urls', 'tools'), namespace='tools')),
    path('', views.index_page),
    path('population/', views.population, name='population'),
    path('help/<slug:page>/', views.help_pages, name='help'),
    path('get_help_pages/<slug:page>/', views.get_help_pages, name="get_help_pages"),
    path('help/', views.help_pages, name='help'),
    path('media/<path>', serve, {'document_root': settings.MEDIA_ROOT, 'show_indexes': True})
]
