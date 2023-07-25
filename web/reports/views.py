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
import os
import re
from io import BytesIO
from wsgiref.util import FileWrapper

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponseRedirect
from django.template.defaulttags import register
from django.utils.decorators import method_decorator
from django.utils.translation import gettext as _, override
from django.views.generic.base import TemplateView
from django.views.generic.detail import SingleObjectMixin, DetailView

import reports.utils
import web.CustomViews as Bview
from jobs.JobTableProperties import TableTree
from jobs.ViewJobData import ViewJobData
from jobs.models import Job
from jobs.utils import JobAccess
from marks.tables import ReportMarkTable
from reports.UploadReport import UploadReport
from reports.comparison import JobsComparison
from reports.coverage import GetCoverage, GetCoverageSrcHTML
from reports.etv import GetSource, GetETV
from reports.models import ReportRoot, Report, ReportComponent, ReportSafe, ReportUnknown, ReportUnsafe, \
    AttrName, ReportAttr, CoverageArchive
from reports.utils import get_edited_error_trace, get_error_trace_content, modify_error_trace, get_html_error_trace
from service.models import Task
from tools.profiling import LoggedCallMixin
from web.utils import logger, ArchiveFileContent, BridgeException, BridgeErrorResponse
from web.vars import JOB_STATUS, VIEW_TYPES, LOG_FILE, PROBLEM_DESC_FILE


# These filters are used for visualization component specific data. They should not be used for any other purposes.
@register.filter
def get(dictionary, key):
    if dictionary:
        return dictionary.get(key)
    else:
        return None


@register.filter
def index(List, i):
    return List[int(i)]


@register.filter
def get_dict_val(d, key):
    return d.get(key)


@register.filter
def sort_list(l):
    return sorted(l)


@register.filter
def sort_tests_list(l):
    return sorted(l, key=lambda test: test.lstrip('1234567890'))


@register.filter
def sort_bugs_list(l):
    return sorted(l, key=lambda bug: bug[12:].lstrip('~'))


@register.filter
def calculate_test_stats(test_results):
    test_stats = {
        "passed tests": 0,
        "failed tests": 0,
        "missed comments": 0,
        "excessive comments": 0,
        "tests": 0
    }

    for result in test_results.values():
        test_stats["tests"] += 1
        if result["ideal verdict"] == result["verdict"]:
            test_stats["passed tests"] += 1
            if result.get('comment'):
                test_stats["excessive comments"] += 1
        else:
            test_stats["failed tests"] += 1
            if not result.get('comment'):
                test_stats["missed comments"] += 1

    return test_stats


@register.filter
def calculate_validation_stats(validation_results):
    validation_stats = {
        "found bug before fix and safe after fix": 0,
        "found bug before fix and non-safe after fix": 0,
        "found non-bug before fix and safe after fix": 0,
        "found non-bug before fix and non-safe after fix": 0,
        "missed comments": 0,
        "excessive comments": 0,
        "bugs": 0
    }

    for result in validation_results.values():
        validation_stats["bugs"] += 1

        is_found_bug_before_fix = False

        if "before fix" in result:
            if result["before fix"]["verdict"] == "unsafe":
                is_found_bug_before_fix = True
                if result["before fix"]["comment"]:
                    validation_stats["excessive comments"] += 1
            elif 'comment' not in result["before fix"] or not result["before fix"]["comment"]:
                validation_stats["missed comments"] += 1

        is_found_safe_after_fix = False

        if "after fix" in result:
            if result["after fix"]["verdict"] == "safe":
                is_found_safe_after_fix = True
                if result["after fix"]["comment"]:
                    validation_stats["excessive comments"] += 1
            elif 'comment' not in result["after fix"] or not result["after fix"]["comment"]:
                validation_stats["missed comments"] += 1

        if is_found_bug_before_fix:
            if is_found_safe_after_fix:
                validation_stats["found bug before fix and safe after fix"] += 1
            else:
                validation_stats["found bug before fix and non-safe after fix"] += 1
        else:
            if is_found_safe_after_fix:
                validation_stats["found non-bug before fix and safe after fix"] += 1
            else:
                validation_stats["found non-bug before fix and non-safe after fix"] += 1

    return validation_stats


@method_decorator(login_required, name='dispatch')
class ReportComponentView(LoggedCallMixin, Bview.DataViewMixin, DetailView):
    model = ReportComponent
    template_name = 'reports/ReportMain.html'

    def get_context_data(self, **kwargs):
        job = self.object.root.job
        if not JobAccess(self.request.user, job).can_view():
            raise BridgeException(code=400)
        coverage = {}
        for identifier, functions, lines in self.object.coverages. \
                values_list('identifier', 'lines_percent', 'functions_percent'):
            if identifier:
                coverage[identifier] = functions, lines
        return {
            'report': self.object,
            'status': reports.utils.ReportStatus(self.object),
            'data': reports.utils.ReportData(self.object),
            'resources': reports.utils.report_resources(self.object, self.request.user),
            'computer': reports.utils.computer_description(self.object.computer.description),
            'SelfAttrsData': reports.utils.ReportAttrsTable(self.object).table_data,
            'parents': reports.utils.get_parents(self.object), 'coverage': coverage,
            'reportdata': ViewJobData(self.request.user, self.get_view(VIEW_TYPES[2]), self.object),
            'TableData': reports.utils.ReportChildrenTable(self.request.user, self.object, self.get_view(VIEW_TYPES[3]))
        }


@method_decorator(login_required, name='dispatch')
class ComponentLogView(LoggedCallMixin, SingleObjectMixin, Bview.StreamingResponseView):
    model = ReportComponent
    pk_url_kwarg = 'report_id'

    def get_generator(self):
        self.object = self.get_object()
        if not JobAccess(self.request.user, self.object.root.job).can_view():
            return BridgeErrorResponse(400)
        if not self.object.log:
            raise BridgeException(_("The component doesn't have log"))

        content = ArchiveFileContent(self.object, 'log', LOG_FILE).content
        self.file_size = len(content)
        return FileWrapper(BytesIO(content), 8192)

    def get_filename(self):
        return '%s-log.txt' % self.object.component.name


class ComponentLogContent(LoggedCallMixin, Bview.JsonDetailView):
    model = ReportComponent
    pk_url_kwarg = 'report_id'

    def get_context_data(self, **kwargs):
        if not JobAccess(self.request.user, self.object.root.job).can_view():
            raise BridgeException(code=400)
        if not self.object.log:
            raise BridgeException(_("The component doesn't have log"))

        content = ArchiveFileContent(self.object, 'log', LOG_FILE).content
        if len(content) > 10 ** 5:
            content = str(_('The component log is huge and can not be shown but you can download it'))
        else:
            content = content.decode('utf8')
        return {'content': content}


@method_decorator(login_required, name='dispatch')
class AttrDataFileView(LoggedCallMixin, SingleObjectMixin, Bview.StreamingResponseView):
    model = ReportAttr

    def get_generator(self):
        self.object = self.get_object()
        if not JobAccess(self.request.user, self.object.report.root.job).can_view():
            raise BridgeException(code=400)
        if not self.object.data:
            raise BridgeException(_("The attribute doesn't have data"))

        content = self.object.data.file.read()
        self.file_size = len(content)
        return FileWrapper(BytesIO(content), 8192)

    def get_filename(self):
        return 'Attr-Data' + os.path.splitext(self.object.data.file.name)[-1]


class AttrDataContentView(LoggedCallMixin, Bview.JsonDetailView):
    model = ReportAttr

    def get_context_data(self, **kwargs):
        if not JobAccess(self.request.user, self.object.report.root.job).can_view():
            raise BridgeException(code=400)
        if not self.object.data:
            raise BridgeException(_("The attribute doesn't have data"))

        content = self.object.data.file.read()
        if len(content) > 10 ** 5:
            content = str(_('The attribute data is huge and can not be shown but you can download it'))
        else:
            content = content.decode('utf8')
        return {'content': content}


@method_decorator(login_required, name='dispatch')
class DownloadVerifierFiles(LoggedCallMixin, SingleObjectMixin, Bview.StreamingResponseView):
    model = ReportComponent

    def get_generator(self):
        self.object = self.get_object()
        if not self.object.verifier_input:
            raise BridgeException(_("The report doesn't have input files of static verifiers"))
        return FileWrapper(self.object.verifier_input.file, 8192)

    def get_filename(self):
        return '%s files.zip' % self.object.component.name


@method_decorator(login_required, name='dispatch')
class SafesListView(LoggedCallMixin, Bview.DataViewMixin, DetailView):
    model = ReportComponent
    pk_url_kwarg = 'report_id'
    template_name = 'reports/report_list.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        values = context['TableData'].table_data['values']
        number_of_objects = len(values)

        # If there is only one element in table, and first column of table is link, redirect to this link
        if request.GET.get('view_type') != VIEW_TYPES[5][0] \
                and number_of_objects == 1 and isinstance(values[0], list) \
                and len(values[0]) > 0 and 'href' in values[0][0] and values[0][0]['href']:
            return HttpResponseRedirect(values[0][0]['href'])
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not JobAccess(self.request.user, self.object.root.job).can_view():
            raise BridgeException(code=400)
        tbl = reports.utils.SafesTable(self.request.user, self.object, self.get_view(VIEW_TYPES[5]), self.request.GET)
        context.update({'report': self.object, 'TableData': tbl})
        return context


@method_decorator(login_required, name='dispatch')
class UnsafesListView(LoggedCallMixin, Bview.DataViewMixin, DetailView):
    model = ReportComponent
    pk_url_kwarg = 'report_id'
    template_name = 'reports/report_list.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        values = context['TableData'].table_data['values']
        number_of_objects = len(values)

        # If there is only one element in table, and first column of table is link, redirect to this link
        if request.GET.get('view_type') != VIEW_TYPES[4][0] \
                and number_of_objects == 1 and isinstance(values[0], list) \
                and len(values[0]) > 0 and 'href' in values[0][0] and values[0][0]['href']:
            return HttpResponseRedirect(values[0][0]['href'])
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not JobAccess(self.request.user, self.object.root.job).can_view():
            raise BridgeException(code=400)
        tbl = reports.utils.UnsafesTable(self.request.user, self.object, self.get_view(VIEW_TYPES[4]), self.request.GET)
        context.update({'report': self.object, 'TableData': tbl})
        return context


@method_decorator(login_required, name='dispatch')
class UnknownsListView(LoggedCallMixin, Bview.DataViewMixin, DetailView):
    model = ReportComponent
    pk_url_kwarg = 'report_id'
    template_name = 'reports/report_list.html'

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        context = self.get_context_data(object=self.object)
        values = context['TableData'].table_data['values']
        number_of_objects = len(values)

        # If there is only one element in table, and first column of table is link, redirect to this link
        if request.GET.get('view_type') != VIEW_TYPES[6][0] \
                and number_of_objects == 1 and isinstance(values[0], list) \
                and len(values[0]) > 0 and 'href' in values[0][0] and values[0][0]['href']:
            return HttpResponseRedirect(values[0][0]['href'])
        return self.render_to_response(context)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if not JobAccess(self.request.user, self.object.root.job).can_view():
            raise BridgeException(code=400)
        tbl = reports.utils.UnknownsTable(self.request.user, self.object,
                                          self.get_view(VIEW_TYPES[6]), self.request.GET)
        context.update({'report': self.object, 'TableData': tbl})
        return context


@method_decorator(login_required, name='dispatch')
class ReportSafeView(LoggedCallMixin, Bview.DataViewMixin, DetailView):
    template_name = 'reports/reportLeaf.html'
    model = ReportSafe

    def get_context_data(self, **kwargs):
        if not JobAccess(self.request.user, self.object.root.job).can_view():
            raise BridgeException(code=400)

        proof = None
        is_modifiable = False
        if self.object.proof:
            try:
                proof = GetETV(get_error_trace_content(self.object), self.request.user)
                if not proof.data.get('edges'):
                    proof = None
                if proof:
                    is_manager = self.request.user.extended.role == '2'
                    is_modifiable = bool(is_manager or bool(proof.data.get('is_modifiable', True)))
            except Exception as e:
                logger.exception(e, stack_info=True)

        return {
            'report': self.object, 'report_type': 'safe',
            'parents': reports.utils.get_parents(self.object),
            'resources': reports.utils.get_leaf_resources(self.request.user, self.object),
            'SelfAttrsData': reports.utils.report_attibutes(self.object),
            'etv': proof, 'is_modifiable': is_modifiable,
            'MarkTable': ReportMarkTable(self.request.user, self.object, self.get_view(VIEW_TYPES[11]))
        }


@method_decorator(login_required, name='dispatch')
class ReportUnknownView(LoggedCallMixin, Bview.DataViewMixin, DetailView):
    template_name = 'reports/reportLeaf.html'
    model = ReportUnknown

    def get_context_data(self, **kwargs):
        if not JobAccess(self.request.user, self.object.root.job).can_view():
            raise BridgeException(code=400)

        return {
            'report': self.object, 'report_type': 'unknown',
            'parents': reports.utils.get_parents(self.object),
            'resources': reports.utils.get_leaf_resources(self.request.user, self.object),
            'SelfAttrsData': reports.utils.report_attibutes(self.object),
            'main_content': ArchiveFileContent(
                self.object, 'problem_description', PROBLEM_DESC_FILE).content.decode('utf8'),
            'MarkTable': ReportMarkTable(self.request.user, self.object, self.get_view(VIEW_TYPES[12]))
        }


@method_decorator(login_required, name='dispatch')
class ReportUnsafeViewById(LoggedCallMixin, Bview.DataViewMixin, DetailView):
    template_name = 'reports/reportLeaf.html'
    model = ReportUnsafe

    def get_context_data(self, **kwargs):
        if not JobAccess(self.request.user, self.object.root.job).can_view():
            raise BridgeException(code=400)
        try:
            etv = GetETV(get_error_trace_content(self.object), self.request.user)
            is_manager = self.request.user.extended.role == '2'
            is_modifiable = bool(is_manager or bool(etv.data.get('is_modifiable', True)))
        except Exception as e:
            logger.exception(e, stack_info=True)
            etv = None
            is_modifiable = False
        return {
            'report': self.object, 'report_type': 'unsafe', 'parents': reports.utils.get_parents(self.object),
            'SelfAttrsData': reports.utils.report_attibutes(self.object),
            'MarkTable': ReportMarkTable(self.request.user, self.object, self.get_view(VIEW_TYPES[10])),
            'etv': etv, 'include_assumptions': self.request.user.extended.assumptions,
            'resources': reports.utils.get_leaf_resources(self.request.user, self.object),
            'is_modifiable': is_modifiable
        }


@method_decorator(login_required, name='dispatch')
class ReportUnsafeView(LoggedCallMixin, Bview.DataViewMixin, DetailView):
    template_name = 'reports/reportLeaf.html'
    model = ReportUnsafe
    slug_url_kwarg = 'trace_id'
    slug_field = 'trace_id'

    def get_context_data(self, **kwargs):
        if not JobAccess(self.request.user, self.object.root.job).can_view():
            raise BridgeException(code=400)
        try:
            etv = GetETV(get_error_trace_content(self.object), self.request.user)
            is_manager = self.request.user.extended.role == '2'
            is_modifiable = bool(is_manager or bool(etv.data.get('is_modifiable', True)))
        except Exception as e:
            logger.exception(e, stack_info=True)
            etv = None
            is_modifiable = False
        return {
            'report': self.object, 'report_type': 'unsafe', 'parents': reports.utils.get_parents(self.object),
            'SelfAttrsData': reports.utils.report_attibutes(self.object),
            'MarkTable': ReportMarkTable(self.request.user, self.object, self.get_view(VIEW_TYPES[10])),
            'etv': etv, 'include_assumptions': self.request.user.extended.assumptions,
            'resources': reports.utils.get_leaf_resources(self.request.user, self.object),
            'is_modifiable': is_modifiable
        }


@method_decorator(login_required, name='dispatch')
class FullscreenReportUnsafe(LoggedCallMixin, DetailView):
    template_name = 'reports/etv_fullscreen.html'
    model = ReportUnsafe
    slug_url_kwarg = 'trace_id'
    slug_field = 'trace_id'

    def get_context_data(self, **kwargs):
        if not JobAccess(self.request.user, self.object.root.job).can_view():
            raise BridgeException(code=400)
        etv = GetETV(get_error_trace_content(self.object), self.request.user)
        is_manager = self.request.user.extended.role == '2'
        is_modifiable = bool(is_manager or bool(etv.data.get('is_modifiable', True)))
        return {
            'report': self.object,
            'include_assumptions': self.request.user.extended.assumptions,
            'etv': etv,
            'is_modifiable': is_modifiable
        }


@method_decorator(login_required, name='dispatch')
class EditReportUnsafe(LoggedCallMixin, DetailView):
    template_name = 'reports/etv_edit.html'
    model = ReportUnsafe
    slug_url_kwarg = 'trace_id'
    slug_field = 'trace_id'

    def get_context_data(self, **kwargs):
        if not JobAccess(self.request.user, self.object.root.job).can_view():
            raise BridgeException(code=400)
        return {
            'report': self.object,
            'include_assumptions': self.request.user.extended.assumptions,
            'etv': GetETV(get_error_trace_content(self.object), self.request.user),
            'is_edited_exist': os.path.exists(get_edited_error_trace(self.object))
        }


class UnsafeApplyView(LoggedCallMixin, Bview.JsonDetailPostView):
    model = ReportUnsafe

    def get_context_data(self, **kwargs):
        notes = json.loads(self.request.POST.get('notes', "{}"))
        warns = json.loads(self.request.POST.get('warns', "{}"))
        is_manager = self.request.user.extended.role == '2'
        is_modifiable = bool(self.request.POST.get('is_modifiable', False))
        is_modifiable = not is_manager or is_modifiable
        for common_key in set(notes.keys()).intersection(set(warns.keys())):
            if notes[common_key] and not warns[common_key]:
                del warns[common_key]
            if not notes[common_key] and warns[common_key]:
                del notes[common_key]
        if notes or warns:
            modify_error_trace(self.object, notes, warns, is_modifiable)
        return {}


class UnsafeCancelView(LoggedCallMixin, Bview.JsonDetailPostView):
    model = ReportUnsafe

    def get_context_data(self, **kwargs):
        edited_error_trace = get_edited_error_trace(self.object)
        if os.path.exists(edited_error_trace):
            os.remove(edited_error_trace)
        return {}


class SourceCodeView(LoggedCallMixin, Bview.JsonView):

    def get_context_data(self, **kwargs):
        witness_type = self.request.POST.get('witness_type', 'violation')
        report_id = self.kwargs['id']
        try:
            if witness_type == 'correctness':
                report = ReportSafe.objects.get(id=report_id)
                proof = GetETV(get_error_trace_content(report), self.request.user)
                lines = proof.lines
            else:
                # Violation
                report = ReportUnsafe.objects.get(id=report_id)
                lines = {}
        except ObjectDoesNotExist:
            raise BridgeException(code=406)
        return {
            'name': self.request.POST['file_name'],
            'content': GetSource(report, self.request.POST['file_name'], lines).data
        }


@method_decorator(login_required, name='dispatch')
class DownloadErrorTrace(LoggedCallMixin, SingleObjectMixin, Bview.StreamingResponseView):
    model = ReportUnsafe
    pk_url_kwarg = 'unsafe_id'
    file_name = 'error trace.json'

    def get_generator(self):
        self.object = self.get_object()
        content = get_error_trace_content(self.object).encode('utf8')
        self.file_size = len(content)
        return FileWrapper(BytesIO(content), 8192)


@method_decorator(login_required, name='dispatch')
class DownloadErrorTraceHtml(LoggedCallMixin, SingleObjectMixin, Bview.StreamingResponseView):
    model = ReportUnsafe
    pk_url_kwarg = 'unsafe_id'
    file_name = 'error-trace.zip'

    def get_generator(self):
        self.object = self.get_object()
        src = dict()
        etv = GetETV(get_error_trace_content(self.object), self.request.user)
        for file in etv.data['files']:
            file_prep = re.sub(r'[^A-Za-z0-9_]+', '', str(file))
            cnt = GetSource(self.object, file).data
            src[file_prep] = cnt
        return get_html_error_trace(etv, src, self.request.user.extended.assumptions)


@method_decorator(login_required, name='dispatch')
class DownloadProof(LoggedCallMixin, SingleObjectMixin, Bview.StreamingResponseView):
    model = ReportSafe
    pk_url_kwarg = 'safe_id'
    file_name = 'proof.json'

    def get_generator(self):
        self.object = self.get_object()
        content = get_error_trace_content(self.object).encode('utf8')
        self.file_size = len(content)
        return FileWrapper(BytesIO(content), 8192)


@method_decorator(login_required, name='dispatch')
class DownloadProofHtml(LoggedCallMixin, SingleObjectMixin, Bview.StreamingResponseView):
    model = ReportSafe
    pk_url_kwarg = 'safe_id'
    file_name = 'proof.zip'

    def get_generator(self):
        self.object = self.get_object()
        src = dict()
        etv = GetETV(get_error_trace_content(self.object), self.request.user)
        for file in etv.data['files']:
            file_prep = re.sub(r'[^A-Za-z0-9_]+', '', str(file))
            cnt = GetSource(self.object, file, etv.lines).data
            src[file_prep] = cnt
        return get_html_error_trace(etv, src, self.request.user.extended.assumptions)


class UnsafeUploadView(LoggedCallMixin, Bview.JsonDetailPostView):
    model = ReportUnsafe

    def get_context_data(self, **kwargs):
        file = self.request.FILES['file']
        try:
            edited_error_trace = json.loads(file.read().decode('utf8'))
        except Exception as e:
            logger.exception("Error while parsing error trace: %s" % e, stack_info=True)
            raise BridgeException(_("Cannot parse edited error trace"))
        edited_error_trace_file_name = get_edited_error_trace(self.object)
        with open(edited_error_trace_file_name, "w") as fd:
            json.dump(edited_error_trace, fd, ensure_ascii=False, sort_keys=True, indent=4)

        return {}


@method_decorator(login_required, name='dispatch')
class ReportsComparisonView(LoggedCallMixin, TemplateView, Bview.DataViewMixin):
    template_name = 'reports/comparison/two_reports.html'

    def get_context_data(self, **kwargs):
        try:
            root1 = ReportRoot.objects.get(job_id=self.kwargs['job1_id'])
            root2 = ReportRoot.objects.get(job_id=self.kwargs['job2_id'])
        except ObjectDoesNotExist:
            raise BridgeException(code=406)
        if self.request.GET:
            args = json.loads(self.request.GET.get('data', '{}'))
            other_jobs = json.loads(self.request.GET.get('jobs', '[]'))
        else:
            args = {}
            other_jobs = []
        tree = TableTree(self.request.user, self.get_view(VIEW_TYPES[1]))
        jobs_tree = list()
        for job in tree.values:
            jobs_tree.append(
                {
                    'id': job['id'],
                    'level': 10 * job['level'],
                    'name': job['values'][0]['value'],
                    'parent': job['parent'],
                    'children': job['children'],
                    'double_children': job['double_children']
                }
            )
        return {'data': JobsComparison([root1, root2], args, other_jobs, jobs_tree)}


@method_decorator(login_required, name='dispatch')
class CoverageView(LoggedCallMixin, DetailView):
    template_name = 'reports/coverage/coverage.html'
    model = ReportComponent
    pk_url_kwarg = 'report_id'

    def get_context_data(self, **kwargs):
        return {
            'coverage': GetCoverage(self.object, self.request.GET, False),
            'SelfAttrsData': reports.utils.report_attributes_with_parents(self.object)
        }


@method_decorator(login_required, name='dispatch')
class CoverageLightView(LoggedCallMixin, DetailView):
    template_name = 'reports/coverage/coverage_light.html'
    model = ReportComponent
    pk_url_kwarg = 'report_id'

    def get_context_data(self, **kwargs):
        return {
            'coverage': GetCoverage(self.object, self.request.GET, True),
            'SelfAttrsData': reports.utils.report_attributes_with_parents(self.object)
        }


class CoverageSrcView(LoggedCallMixin, Bview.JsonDetailPostView):
    model = CoverageArchive
    pk_url_kwarg = 'archive_id'

    def get_context_data(self, **kwargs):
        if self.request.POST.get('show_function_bodies', "true") == "true":
            hide_function_bodies = False
        else:
            hide_function_bodies = True
        res = GetCoverageSrcHTML(self.object, self.request.POST['filename'], bool(int(self.request.POST['with_data'])),
                                 hide_function_bodies)
        return {'content': res.src_html, 'data': res.data_html, 'legend': res.legend}


@method_decorator(login_required, name='dispatch')
class DownloadCoverageView(LoggedCallMixin, SingleObjectMixin, Bview.StreamingResponseView):
    model = CoverageArchive

    def get_generator(self):
        self.object = self.get_object()
        return FileWrapper(self.object.archive.file, 8192)

    def get_filename(self):
        return '%s coverage.zip' % self.object.report.component.name


class UploadReportView(LoggedCallMixin, Bview.JsonDetailPostView):
    model = Job
    unparallel = [ReportRoot, AttrName, Task]

    def dispatch(self, request, *args, **kwargs):
        with override(settings.DEFAULT_LANGUAGE):
            return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()
        try:
            return queryset.get(id=int(self.request.session['job id']))
        except ObjectDoesNotExist:
            raise BridgeException(code=404)

    def get_context_data(self, **kwargs):
        if not JobAccess(self.request.user, self.object).core_access():
            raise BridgeException("User '%s' don't have access to upload report for job '%s'" %
                                  (self.request.user.username, self.object.identifier))
        if self.object.status != JOB_STATUS[2][0]:
            raise BridgeException('Reports can be uploaded only for processing jobs')

        archives = {}
        for f in self.request.FILES.getlist('file'):
            archives[f.name] = f

        if 'report' in self.request.POST:
            data = json.loads(self.request.POST['report'])
            err = UploadReport(self.object, data, archives).error
            if err is not None:
                raise BridgeException(err)
        elif 'reports' in self.request.POST:
            data = json.loads(self.request.POST['reports'])
            if not isinstance(data, list):
                raise BridgeException('Wrong format of reports data')
            for d in data:
                err = UploadReport(self.object, d, archives).error
                if err is not None:
                    raise BridgeException(err)
        else:
            raise BridgeException('Report json data is required')
        return {}


class ClearVerificationFiles(LoggedCallMixin, Bview.JsonDetailPostView):
    model = Job
    pk_url_kwarg = 'job_id'
    unparallel = [Report]

    def get_context_data(self, **kwargs):
        if not JobAccess(self.request.user, self.object).can_clear_verifications():
            raise BridgeException(_("You can't remove verification files of this job"))
        reports.utils.remove_verification_files(self.object)
        return {}
