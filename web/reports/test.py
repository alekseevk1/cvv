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
import random
import time
from io import BytesIO

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.test import Client
from django.urls import reverse

from jobs.models import Job
from reports.models import ReportSafe, ReportUnsafe, ReportUnknown, ReportComponent, CoverageArchive, \
    CoverageFile, ReportAttr
from users.models import User
from web.populate import populate_users
from web.utils import CVTestCase
from web.vars import JOB_STATUS, FORMAT

LINUX_ATTR = {'name': 'Linux kernel', 'value': [
    {'name': 'Version', 'value': '3.5.0'},
    {'name': 'Architecture', 'value': 'x86_64'},
    {'name': 'Configuration', 'value': 'allmodconfig'}
]}
LKVOG_ATTR = {'name': 'LKVOG strategy', 'value': [{'name': 'Name', 'value': 'separate modules'}]}
COMPUTER = [
    {"node name": "hellwig.intra.ispras.ru"},
    {"CPU model": "Intel(R) Core(TM) i7-3770 CPU @ 3.40GHz"},
    {"number of CPU cores": 8},
    {"memory size": 16808734720},
    {"Linux kernel version": "3.16.7-29-default"},
    {"architecture": "x86_64"}
]

# Only components ['VTGW', 'ASE', 'EMG', 'FVTP', 'RSG', 'SA', 'TR', 'Weaver', 'RP'] can be "failed"
SJC_1 = [
    {
        'requirement': 'linux:mutex',
        'chunks': [
            {
                'module': 'drivers/usb/core/usb1.ko',
                'tool': 'BLAST 2.7.2', 'verifier_input': True, 'log': True,
                'unsafes': ['unsafe1.zip', 'unsafe2.zip'],
                'unknown': 'unknown2.zip'
            },
            {
                'module': 'drivers/usb/core/usb2.ko',
                'tool': 'CPAchecker', 'verifier_input': False, 'log': False,
                'unsafes': ['unsafe3.zip']
            },
            {
                'module': 'drivers/usb/core/usb3.ko',
                'tool': 'CPAchecker', 'verifier_input': True, 'log': False,
                'safe': 'safe.zip'
            },
            {
                'module': 'drivers/usb/core/usb4.ko',
                'tool': 'CPAchecker', 'verifier_input': False, 'log': True,
                'unknown': 'unknown0.zip'
            },
            {
                'module': 'drivers/usb/core/usb5.ko',
                'fail': 'RP'
            }
        ]
    },
    {
        'requirement': 'linux:rule1',
        'chunks': [
            {
                'module': 'drivers/usb/core/usb1.ko',
                'tool': 'BLAST 2.7.2', 'verifier_input': True, 'log': True,
                'safe': 'safe.zip'
            },
            {
                'module': 'drivers/usb/core/usb2.ko',
                'tool': 'CPAchecker', 'verifier_input': False, 'log': False,
                'unsafes': ['unsafe4.zip']
            },
            {
                'module': 'drivers/usb/core/usb3.ko',
                'tool': 'CPAchecker', 'verifier_input': True, 'log': False,
                'unsafes': ['unsafe5.zip']
            },
            {
                'module': 'drivers/usb/core/usb4.ko',
                'tool': 'CPAchecker', 'verifier_input': False, 'log': True,
                'safe': 'safe.zip'
            },
            {
                'module': 'drivers/usb/core/usb5.ko',
                'tool': 'CPAchecker', 'verifier_input': False, 'log': False,
                'unsafes': ['unsafe6.zip']
            }
        ]
    },
    {
        'requirement': 'linux:rule2',
        'chunks': [
            {
                'module': 'drivers/usb/core/usb6.ko',
                'tool': 'CPAchecker', 'verifier_input': False, 'log': False,
                'safe': 'safe.zip'
            },
            {
                'module': 'drivers/usb/core/usb7.ko',
                'tool': 'CPAchecker', 'verifier_input': False, 'log': True,
                'unsafes': ['unsafe7.zip']
            }
        ]
    }
]

SJC_2 = [
    {
        'requirement': 'linux:mutex',
        'chunks': [
            {
                'module': 'drivers/usb/core/usb2.ko',
                'tool': 'CPAchecker', 'verifier_input': True, 'log': True,
                'safe': 'safe.zip'
            }
        ]
    }
]

NSJC_1 = [
    {
        'requirement': 'linux:mutex',
        'module': 'drivers/usb/core/usb1.ko',
        'tool': 'BLAST 2.7.2', 'verifier_input': True, 'log': False,
        'unsafes': ['unsafe1.zip', 'unsafe2.zip'],
        'unknown': 'unknown2.zip'
    },
    {
        'requirement': 'linux:mutex',
        'module': 'drivers/usb/core/usb2.ko',
        'tool': 'CPAchecker', 'verifier_input': False, 'log': True,
        'unsafes': ['unsafe3.zip']
    },
    {
        'requirement': 'linux:mutex',
        'module': 'drivers/usb/core/usb3.ko',
        'tool': 'CPAchecker', 'verifier_input': False, 'log': False,
        'safe': 'safe.zip'
    },
    {
        'requirement': 'linux:mutex',
        'module': 'drivers/usb/core/usb4.ko',
        'tool': 'CPAchecker', 'verifier_input': True, 'log': True,
        'unknown': 'unknown0.zip'
    },
    {
        'requirement': 'linux:mutex',
        'module': 'drivers/usb/core/usb5.ko',
        'fail': 'RP',
        'unknown': 'unknown3.zip'
    }
]

NSJC_2 = [
    {
        'requirement': 'linux:mutex',
        'module': 'drivers/usb/core/usb2.ko',
        'tool': 'CPAchecker', 'verifier_input': True, 'log': True,
        'unsafes': ['unsafe_check.zip']
    }
]

NSJC_3 = [
    {
        'requirement': 'linux:mutex',
        'module': 'drivers/usb/core/usb3.ko',
        'tool': 'CPAchecker', 'verifier_input': True, 'log': False,
        'safe': 'safe.zip'
    },
    {
        'requirement': 'linux:mutex',
        'module': 'drivers/usb/core/usb4.ko',
        'tool': 'CPAchecker', 'verifier_input': False, 'log': True,
        'unknown': 'unknown0.zip'
    },
    {
        'requirement': 'linux:mutex',
        'module': 'drivers/usb/core/usb5.ko',
        'fail': 'ASE',  # No verdicts will be uploaded as component failed before it
        'unknown': 'unknown3.zip'
    }
]

ARCHIVE_PATH = os.path.join(settings.BASE_DIR, 'reports', 'test_files')


def resources():
    return {
        'CPU time': random.randint(100, 10000),
        'memory size': random.randint(10 ** 7, 10 ** 9),
        'wall time': random.randint(100, 10000)
    }


class DecisionError(Exception):
    pass


class TestReports(CVTestCase):
    def setUp(self):
        super().setUp()
        self.service_client = Client()
        User.objects.create_superuser('superuser', '', 'top_secret')
        populate_users(
            manager={'username': 'manager', 'password': 'manager'},
            service={'username': 'service', 'password': 'service'}
        )
        self.client.post(reverse('users:login'), {'username': 'manager', 'password': 'manager'})
        self.client.post(reverse('population'))
        self.job_archive = 'test_job_archive.zip'

    def test_reports(self):
        self.ids_in_use = []
        self.cmp_stack = []
        self.job = Job.objects.order_by('parent').first()
        if self.job is None:
            self.fail('Jobs are not populated')

        # Run decision with default configuration
        self.client.post('/jobs/run_decision/%s/' % self.job.pk, {'mode': 'default', 'conf_name': 'development'})

        # Service sign in and check session parameters
        response = self.service_client.post('/users/service_signin/', {
            'username': 'service', 'password': 'service',
            'job identifier': self.job.identifier
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/html; charset=utf-8')
        self.assertEqual(self.service_client.session.get('job id'), self.job.pk)

        # Decide the job
        self.__decide_job(SJC_1)

        try:
            main_report = ReportComponent.objects.get(parent=None, root__job_id=self.job.pk)
        except ObjectDoesNotExist:
            self.fail("The job decision didn't create core report")

        response = self.client.get(reverse('reports:component', args=[main_report.pk]))
        self.assertEqual(response.status_code, 200)

        response = self.client.get(reverse('reports:unsafes', args=[main_report.pk]))
        if ReportUnsafe.objects.count() == 1:
            self.assertRedirects(response, reverse('reports:unsafe', args=[ReportUnsafe.objects.first().trace_id]))
        else:
            self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('reports:safes', args=[main_report.pk]))
        if ReportSafe.objects.count() == 1:
            self.assertRedirects(response, reverse('reports:safe', args=[ReportSafe.objects.first().id]))
        else:
            self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('reports:unknowns', args=[main_report.pk]))
        if ReportUnknown.objects.count() == 1:
            self.assertRedirects(response, reverse('reports:unknown', args=[ReportUnknown.objects.first().id]))
        else:
            self.assertEqual(response.status_code, 200)

        for report in ReportComponent.objects.filter(~Q(parent=None) & Q(root__job_id=self.job.pk)):
            response = self.client.get(reverse('reports:component', args=[report.pk]))
            self.assertEqual(response.status_code, 200)

        for unsafe in ReportUnsafe.objects.all():
            response = self.client.get(reverse('reports:unsafe', args=[unsafe.trace_id]))
            self.assertEqual(response.status_code, 200)
            response = self.client.get(reverse('reports:unsafe_fullscreen', args=[unsafe.trace_id]))
            self.assertEqual(response.status_code, 200)

        for report in ReportUnknown.objects.all():
            response = self.client.get(reverse('reports:unknown', args=[report.pk]))
            self.assertEqual(response.status_code, 200)

        for report in ReportSafe.objects.all():
            response = self.client.get(reverse('reports:safe', args=[report.pk]))
            self.assertEqual(response.status_code, 200)

        ver_report = ReportComponent.objects.filter(verification=True).first()
        response = self.client.get(reverse('reports:download_files', args=[ver_report.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/zip')

        unsafe = ReportUnsafe.objects.first()
        response = self.client.get(reverse('reports:download_error_trace', args=[unsafe.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        mem = BytesIO()
        for chunk in response.streaming_content:
            mem.write(chunk)
        mem.seek(0)
        first_fname = json.loads(str(mem.read().decode('utf8')))['files'][0]

        response = self.client.post('/reports/get_source/%s/' % unsafe.pk, {'file_name': first_fname})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertNotIn('error', json.loads(str(response.content, encoding='utf8')))

        response = self.client.get('/reports/logcontent/%s/' % main_report.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        res = json.loads(str(response.content, encoding='utf8'))
        self.assertNotIn('error', res)
        self.assertIn('content', res)

        response = self.client.get(reverse('reports:log', args=[main_report.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'text/plain')

        # Get decision results
        response = self.client.get('/jobs/decision_results_json/%s/' % self.job.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        res = json.loads(str(response.content, encoding='utf8'))
        self.assertNotIn('error', res)
        self.assertIn('data', res)

        # Collapse job
        response = self.client.post('/jobs/collapse_reports/%s/' % self.job.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertNotIn('error', json.loads(str(response.content, encoding='utf8')))

        # Test verifier input files
        report = ReportComponent.objects.exclude(root__job_id=self.job.pk, verifier_input='').first()
        self.assertIsNotNone(report)

        response = self.client.post(reverse('jobs:download_file_for_compet', args=[self.job.pk]),
                                    {'filters': json.dumps(['u', 's'])})
        self.assertEqual(response.status_code, 200)
        self.assertIn(response['Content-Type'], {'application/x-zip-compressed', 'application/zip'})

        response = self.client.get(reverse('reports:download_files', args=[report.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertIn(response['Content-Type'], {'application/x-zip-compressed', 'application/zip'})

        # Clear verification files
        response = self.client.post('/reports/clear_verification_files/%s/' % self.job.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertNotIn('error', json.loads(str(response.content, encoding='utf8')))
        self.assertEqual(ReportComponent.objects.filter(root=self.job.reportroot, verification=True)
                         .exclude(verifier_input='').count(), 0)

    def test_coverage(self):
        self.job = Job.objects.order_by('parent').first()
        if self.job is None:
            self.fail('Jobs are not populated')
        self.client.post('/jobs/run_decision/%s/' % self.job.pk, {'mode': 'default', 'conf_name': 'development'})

        DecideJobs('service', 'service', SJC_1, with_full_coverage=True)

        # Test coverage pages for verification report
        report = ReportComponent.objects.filter(verification=True, covnum__gt=0).first()
        self.assertIsNotNone(report)
        response = self.client.get(reverse('reports:coverage', args=[report.id]))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('reports:coverage_light', args=[report.id]))
        self.assertEqual(response.status_code, 200)

        # Test downloading coverage
        carch = CoverageArchive.objects.filter(report=report).first()
        self.assertIsNotNone(carch)
        response = self.client.get(reverse('reports:download_coverage', args=[carch.id]))
        self.assertEqual(response.status_code, 200)
        self.assertIn(response['Content-Type'], {'application/x-zip-compressed', 'application/zip'})

        # Test coverage pages for non-verification report
        report = ReportComponent.objects.filter(verification=False, covnum__gt=0).first()
        self.assertIsNotNone(report)
        response = self.client.get(reverse('reports:coverage', args=[report.id]))
        self.assertEqual(response.status_code, 200)
        response = self.client.get(reverse('reports:coverage_light', args=[report.id]))
        self.assertEqual(response.status_code, 200)

        # Get source code for coverage
        cfile = CoverageFile.objects.filter(archive=carch).first()
        self.assertIsNotNone(cfile)
        # Get with data
        response = self.client.post('/reports/get-coverage-src/%s/' % carch.id,
                                    {'filename': cfile.name, 'with_data': '1'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        res = json.loads(str(response.content, encoding='utf8'))
        self.assertNotIn('error', res)
        self.assertEqual(set(res), {'content', 'data', 'legend'})
        # Get without data
        response = self.client.post('/reports/get-coverage-src/%s/' % carch.id,
                                    {'filename': cfile.name, 'with_data': '0'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        res = json.loads(str(response.content, encoding='utf8'))
        self.assertNotIn('error', res)
        self.assertEqual(set(res), {'content', 'data', 'legend'})

    def test_upload_reports(self):
        self.job = Job.objects.order_by('parent').first()
        if self.job is None:
            self.fail('Jobs are not populated')
        presets_dir = os.path.join(settings.BASE_DIR, 'reports', 'test_files', 'decisions')
        for archname in [os.path.join(presets_dir, x) for x in os.listdir(presets_dir)]:
            with open(archname, mode='rb') as fp:
                response = self.client.post('/jobs/upload_reports/%s/' % self.job.pk, {'archive': fp})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response['Content-Type'], 'application/json')
            self.assertNotIn('error', json.loads(str(response.content, encoding='utf8')))

    def test_upload_decided_job(self):
        job = Job.objects.first()
        self.assertIsNotNone(job)
        self.client.post('/jobs/run_decision/%s/' % job.pk, {'mode': 'default', 'conf_name': 'development'})

        # This class uploads attrs data for verification reports
        DecideJobs('service', 'service', SJC_1)

        # Test attr data
        attrs = ReportAttr.objects.filter(report__root=job.reportroot).exclude(data=None)
        self.assertGreater(attrs.count(), 0, 'There are no attributes with data')
        attr_with_data = attrs.first()

        # Test download attr data file
        response = self.client.get('/reports/attrdata/%s/' % attr_with_data.pk)
        self.assertEqual(response.status_code, 200)

        # Test content of attr data file
        response = self.client.get('/reports/attrdata-content/%s/' % attr_with_data.pk)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        res = json.loads(str(response.content, encoding='utf8'))
        self.assertNotIn('error', res)
        self.assertIn('content', res)

        # Download decided job
        response = self.client.get('/jobs/downloadjob/%s/' % job.pk)
        self.assertEqual(response.status_code, 200)
        with open(os.path.join(settings.MEDIA_ROOT, self.job_archive), mode='wb') as fp:
            for content in response.streaming_content:
                fp.write(content)

        # Remove decided job
        response = self.client.post('/jobs/remove/', {'jobs': json.dumps([job.pk])})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertNotIn('error', json.loads(str(response.content, encoding='utf8')))

        # Get parent for uploading
        if job.parent is None:
            parent = Job.objects.first()
            self.assertIsNotNone(parent)
        else:
            parent = Job.objects.get(id=job.parent_id)

        # Upload downloaded job
        with open(os.path.join(settings.MEDIA_ROOT, self.job_archive), mode='rb') as fp:
            response = self.client.post('/jobs/upload_jobs/%s/' % parent.identifier, {'file': fp})
            fp.close()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertJSONEqual(str(response.content, encoding='utf8'), '{}')
        try:
            Job.objects.get(parent=parent, identifier=job.identifier)
        except ObjectDoesNotExist:
            self.fail('The job was not found after upload')

    def __get_report_id(self, name):
        r_id = '/' + name
        while r_id in self.ids_in_use:
            r_id = '/%s%s' % (name, random.randint(1, 100))
        self.ids_in_use.append(r_id)
        return r_id

    def __upload_start_report(self, name, parent, attrs=None, failed=False):
        r_id = self.__get_report_id(name)
        report = {'id': r_id, 'type': 'start', 'parent id': parent, 'name': name}
        if attrs is not None:
            report['attrs'] = attrs

        response = self.service_client.post('/reports/upload/', {'report': json.dumps(report)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertNotIn('error', json.loads(str(response.content, encoding='utf8')))
        self.assertEqual(len(ReportComponent.objects.filter(
            root__job_id=self.job.pk, identifier=self.job.identifier + r_id,
            parent__identifier=self.job.identifier + parent, component__name=name, finish_date=None
        )), 1)

        self.cmp_stack.append(r_id)
        if failed:
            self.__upload_unknown_report(r_id, 'unknown0.zip')
            while len(self.cmp_stack) > 0:
                self.__upload_finish_report(self.cmp_stack[-1])
            raise DecisionError('Component %s failed!' % name)
        return r_id

    def __upload_finish_report(self, r_id):
        report = {'id': r_id, 'type': 'finish', 'resources': resources(), 'desc': 'Description text', 'log': 'log.zip'}
        with open(os.path.join(ARCHIVE_PATH, 'log.zip'), mode='rb') as fp:
            response = self.service_client.post('/reports/upload/', {'report': json.dumps(report), 'file': [fp]})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertNotIn('error', json.loads(str(response.content, encoding='utf8')))
        self.assertIsNotNone(ReportComponent.objects.get(identifier=self.job.identifier + r_id).finish_date)

        if len(self.cmp_stack) > 0:
            self.cmp_stack.pop()

    def __upload_attrs_report(self, r_id, attrs):
        response = self.service_client.post('/reports/upload/', {
            'report': json.dumps({'id': r_id, 'type': 'attrs', 'attrs': attrs})
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertNotIn('error', json.loads(str(response.content, encoding='utf8')))

    def __upload_data_report(self, r_id, data=None):
        if data is None:
            data = {"newdata": str(random.randint(0, 100))}

        response = self.service_client.post('/reports/upload/', {
            'report': json.dumps({'id': r_id, 'type': 'data', 'data': data})
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertNotIn('error', json.loads(str(response.content, encoding='utf8')))

    def __upload_verification_report(self, name, parent, attrs=None, coverage=None, verifier_input=True, log=True):
        r_id = self.__get_report_id(name)
        if not isinstance(attrs, list):
            attrs = []
        report = {
            'id': r_id, 'type': 'verification', 'parent id': parent, 'name': name, 'attrs': attrs,
            'resources': resources(), 'data': {'description': str(r_id)}
        }

        files = []
        if coverage is not None:
            files.append(open(os.path.join(ARCHIVE_PATH, coverage), mode='rb'))
            report['coverage'] = coverage
        if verifier_input:
            files.append(open(os.path.join(ARCHIVE_PATH, 'verifier_input.zip'), mode='rb'))
            report['input files of static verifiers'] = 'verifier_input.zip'
        if log:
            files.append(open(os.path.join(ARCHIVE_PATH, 'log.zip'), mode='rb'))
            report['log'] = 'log.zip'
        try:
            response = self.service_client.post('/reports/upload/', {'report': json.dumps(report), 'file': files})
        except Exception:
            for f in files:
                f.close()
            raise

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertNotIn('error', json.loads(str(response.content, encoding='utf8')))
        report = ReportComponent.objects.filter(
            root__job_id=self.job.pk, identifier=self.job.identifier + r_id, verification=True,
            parent__identifier=self.job.identifier + parent, component__name=name, finish_date=None
        ).first()
        self.assertIsNotNone(report)
        if log:
            self.assertNotEqual(report.log, '')
        else:
            self.assertEqual(report.log, '')
        if verifier_input:
            self.assertNotEqual(report.verifier_input, '')
        else:
            self.assertEqual(report.verifier_input, '')
        return r_id

    def __upload_progress(self, ts, sj=None, start=False, finish=False):
        data = {
            'total tasks to be generated': ts[0],
            'failed tasks': ts[1],
            'solved tasks': ts[2],
            'expected time for solving tasks': ts[3],
            'start tasks solution': start,
            'finish tasks solution': finish,
        }
        if sj is not None:
            data.update({
                'total subjobs to be solved': sj[0],
                'failed subjobs': sj[1],
                'solved subjobs': sj[2],
                'expected time for solving subjobs': sj[3],
                'start subjobs solution': start,
                'finish subjobs solution': finish
            })
        response = self.service_client.post('/service/update_progress/', {'progress': json.dumps(data)})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertNotIn('error', json.loads(str(response.content, encoding='utf8')))

    def __upload_finish_verification_report(self, r_id):
        response = self.service_client.post('/reports/upload/', {
            'report': json.dumps({'id': r_id, 'type': 'verification finish'})
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertNotIn('error', json.loads(str(response.content, encoding='utf8')))
        self.assertEqual(len(ReportComponent.objects.filter(
            Q(root__job_id=self.job.pk, identifier=self.job.identifier + r_id, verification=True) & ~Q(finish_date=None)
        )), 1)

    def __upload_unknown_report(self, parent, archive):
        r_id = self.__get_report_id('unknown')
        with open(os.path.join(ARCHIVE_PATH, archive), mode='rb') as fp:
            response = self.service_client.post('/reports/upload/', {
                'report': json.dumps({
                    'id': r_id, 'type': 'unknown', 'parent id': parent, 'problem desc': os.path.basename(fp.name)
                }), 'file': fp
            })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertNotIn('error', json.loads(str(response.content, encoding='utf8')))
        self.assertEqual(ReportUnknown.objects.filter(
            root__job_id=self.job.pk, identifier=self.job.identifier + r_id,
            parent__identifier=self.job.identifier + parent
        ).count(), 1)

    def __upload_safe_report(self, parent, attrs, archive, with_proof=True):
        r_id = self.__get_report_id('safe')
        if with_proof:
            with open(os.path.join(ARCHIVE_PATH, archive), mode='rb') as fp:
                response = self.service_client.post('/reports/upload/', {'report': json.dumps({
                    'id': r_id, 'type': 'safe', 'parent id': parent, 'proof': os.path.basename(fp.name), 'attrs': attrs
                }), 'file': fp})
        else:
            response = self.service_client.post('/reports/upload/', {'report': json.dumps({
                'id': r_id, 'type': 'safe', 'parent id': parent, 'proof': None, 'attrs': attrs
            })})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertNotIn('error', json.loads(str(response.content, encoding='utf8')))
        self.assertEqual(len(ReportSafe.objects.filter(
            root__job_id=self.job.pk, identifier=self.job.identifier + r_id,
            parent__identifier=self.job.identifier + parent
        )), 1)

    def __upload_unsafe_report(self, parent, attrs, archive):
        r_id = self.__get_report_id('unsafe')
        with open(os.path.join(ARCHIVE_PATH, archive), mode='rb') as fp:
            response = self.service_client.post('/reports/upload/', {'report': json.dumps({
                'id': r_id, 'type': 'unsafe', 'parent id': parent, 'attrs': attrs,
                'sources': os.path.basename(fp.name), 'error traces': [os.path.basename(fp.name)]
            }), 'file': fp})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertNotIn('error', json.loads(str(response.content, encoding='utf8')))
        self.assertEqual(len(ReportUnsafe.objects.filter(
            root__job_id=self.job.pk, identifier__startswith=self.job.identifier + r_id,
            parent__identifier=self.job.identifier + parent
        )), 1)

    def __upload_job_coverage(self, r_id, coverage):
        report = {'id': r_id, 'type': 'job coverage', 'coverage': coverage}
        files = []
        for carch in coverage.values():
            files.append(open(os.path.join(ARCHIVE_PATH, carch), mode='rb'))
        try:
            response = self.service_client.post('/reports/upload/', {'report': json.dumps(report), 'file': files})
        except Exception:
            for fp in files:
                fp.close()
            raise
        else:
            for fp in files:
                fp.close()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertNotIn('error', json.loads(str(response.content, encoding='utf8')))

    def __decide_job(self, reports_data):
        sch_data = {
            'tasks': {'pending': [], 'processing': [], 'error': [], 'finished': [], 'cancelled': []},
            'task errors': {}, 'task descriptions': {}, 'task solutions': {},
            'jobs': {'pending': [], 'processing': [], 'error': [], 'finished': [], 'cancelled': []},
            'job errors': {}, 'job configurations': {}
        }
        response = self.service_client.post('/service/get_jobs_and_tasks/', {
            'jobs and tasks status': json.dumps(sch_data)
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        res = json.loads(str(response.content, encoding='utf8'))
        self.assertNotIn('error', res)
        self.assertIn('jobs and tasks status', res)
        res_data = json.loads(res['jobs and tasks status'])
        try:
            self.assertIn(self.job.identifier, res_data['jobs']['pending'])
            self.assertIn(self.job.identifier, res_data['job configurations'])
        except KeyError:
            self.fail('Wrong result format')

        response = self.service_client.post('/jobs/decide_job/', {'report': json.dumps({
            'type': 'start', 'id': '/', 'attrs': [{'name': 'CV Core version', 'value': 'latest'}], 'comp': COMPUTER
        }), 'job format': FORMAT})
        self.assertIn(response['Content-Type'], {'application/x-zip-compressed', 'application/zip'})
        self.assertEqual(Job.objects.get(pk=self.job.pk).status, JOB_STATUS[2][0])

        self.__upload_data_report('/', {
            'module1': {'ideal verdict': 'safe', 'verdict': 'unsafe', 'comment': 'This is comment for module1'},
            'module2': {'ideal verdict': 'safe', 'verdict': 'safe'}
        })
        self.__upload_data_report('/', {
            'module3': {'ideal verdict': 'unsafe', 'verdict': 'unsafe', 'comment': 'This is comment for module3'},
            'module4': {'ideal verdict': 'unsafe', 'verdict': 'unknown'}
        })

        core_coverage = {}
        if any('chunks' in chunk for chunk in reports_data):
            progress_sj = [len(reports_data), 0, 0, 100 * len(reports_data) + 10]
            progress_ts = [len(reports_data) * 2, 0, 0, 100 * len(reports_data)]
            self.__upload_progress(progress_ts, progress_sj, True, False)
            for subjob in reports_data:
                if 'chunks' in subjob:
                    try:
                        core_coverage.update(self.__upload_subjob(subjob))
                    except DecisionError:
                        pass
                progress_sj[2] += 1
                progress_sj[3] -= 100
                progress_ts[2] += 2
                progress_ts[3] -= 100
                self.__upload_progress(progress_ts, progress_sj, False, False)
            self.__upload_progress(progress_ts, progress_sj, False, True)
        else:
            try:
                self.__upload_chunks(reports_data)
            except DecisionError:
                pass

        if len(core_coverage) > 0:
            self.__upload_job_coverage('/', core_coverage)

        self.__upload_finish_report('/')

        new_sch_data = sch_data.copy()
        new_sch_data['jobs']['finished'].append(self.job.identifier)
        response = self.service_client.post('/service/get_jobs_and_tasks/', {
            'jobs and tasks status': json.dumps(new_sch_data)
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/json')
        self.assertEqual(Job.objects.get(pk=self.job.pk).status, JOB_STATUS[3][0])

    def __upload_subjob(self, subjob):
        sj = self.__upload_start_report('Sub-job', '/',
                                        [{'name': 'Name',
                                          'value': 'test/dir/and/some/other/text:%s' % subjob['requirement']}])
        lkbce = self.__upload_start_report('LKBCE', sj)
        self.__upload_attrs_report(lkbce, [LINUX_ATTR])
        self.__upload_finish_report(lkbce)

        lkvog = self.__upload_start_report('LKVOG', sj, [LKVOG_ATTR])
        self.__upload_finish_report(lkvog)

        vtg = self.__upload_start_report('VTG', sj, [LINUX_ATTR, LKVOG_ATTR])
        for chunk in subjob['chunks']:
            vtgw = self.__upload_start_report('VTGW', vtg, [
                {'name': 'Requirement', 'value': subjob['requirement']},
                {'name': 'Program fragment', 'value': chunk['module']}
            ], failed=(chunk.get('fail') == 'VTGW'))
            for cmp in ['ASE', 'EMG', 'FVTP', 'RSG', 'SA', 'TR', 'Weaver']:
                cmp_id = self.__upload_start_report(cmp, vtgw, failed=(chunk.get('fail') == cmp))
                self.__upload_finish_report(cmp_id)
            self.__upload_finish_report(vtgw)
        self.__upload_finish_report(vtg)

        vrp = self.__upload_start_report('VRP', sj, [LINUX_ATTR, LKVOG_ATTR])
        for chunk in subjob['chunks']:
            rp = self.__upload_start_report('RP', vrp, [
                {'name': 'Requirement', 'value': subjob['requirement']},
                {'name': 'Program fragment', 'value': chunk['module']}
            ], failed=(chunk.get('fail') == 'RP'))
            self.__upload_verdicts(rp, chunk)
            self.__upload_finish_report(rp)
        self.__upload_finish_report(vrp)

        sj_coverage = {subjob['requirement']: 'Core_coverage.zip'}
        self.__upload_job_coverage(sj, sj_coverage)
        self.__upload_finish_report(sj)
        return sj_coverage

    def __upload_chunks(self, reports_data):
        lkbce = self.__upload_start_report('LKBCE', '/')
        self.__upload_attrs_report(lkbce, [LINUX_ATTR])
        self.__upload_finish_report(lkbce)

        lkvog = self.__upload_start_report('LKVOG', '/', [LKVOG_ATTR])
        self.__upload_finish_report(lkvog)

        vtg = self.__upload_start_report('VTG', '/', [LINUX_ATTR, LKVOG_ATTR])
        for chunk in reports_data:
            vtgw = self.__upload_start_report('VTGW', vtg, [
                {'name': 'Requirement', 'value': chunk['requirement']},
                {'name': 'Program fragment', 'value': chunk['module']}
            ], failed=(chunk.get('fail') == 'VTGW'))
            for cmp in ['ASE', 'EMG', 'FVTP', 'RSG', 'SA', 'TR', 'Weaver']:
                cmp_id = self.__upload_start_report(cmp, vtgw, failed=(chunk.get('fail') == cmp))
                self.__upload_finish_report(cmp_id)
            self.__upload_finish_report(vtgw)
        self.__upload_finish_report(vtg)

        progress_ts = [len(reports_data), 0, 0, 100 * len(reports_data)]
        self.__upload_progress(progress_ts, None, True, False)
        vrp = self.__upload_start_report('VRP', '/', [LINUX_ATTR, LKVOG_ATTR])
        for chunk in reports_data:
            rp = self.__upload_start_report('RP', vrp, [
                {'name': 'Requirement', 'value': chunk['requirement']},
                {'name': 'Program fragment', 'value': chunk['module']}
            ], failed=(chunk.get('fail') == 'RP'))
            self.__upload_verdicts(rp, chunk)
            self.__upload_finish_report(rp)
            progress_ts[2] += 1
            progress_ts[3] -= 100
            self.__upload_progress(progress_ts, None, False, False)
        self.__upload_finish_report(vrp)
        self.__upload_progress(progress_ts, None, False, True)

    def __upload_verdicts(self, parent, chunk):
        if 'unsafes' in chunk:
            coverage = 'partially_coverage.zip'
        else:
            coverage = None
        tool = self.__upload_verification_report(
            chunk['tool'], parent, coverage=coverage,
            verifier_input=chunk.get('verifier_input', False), log=chunk.get('log', False)
        )
        if 'safe' in chunk:
            self.__upload_safe_report(tool, [], chunk['safe'])
        elif 'unsafes' in chunk:
            cnt = 1
            for u in chunk['unsafes']:
                self.__upload_unsafe_report(tool, [{'name': 'entry point', 'value': 'func_%s' % cnt}], u)
                cnt += 1
        if 'unknown' in chunk and 'safe' not in chunk:
            self.__upload_unknown_report(tool, chunk['unknown'])
        self.__upload_finish_verification_report(tool)

    def tearDown(self):
        if os.path.exists(os.path.join(settings.MEDIA_ROOT, self.job_archive)):
            os.remove(os.path.join(settings.MEDIA_ROOT, self.job_archive))
        super().tearDown()


class DecideJobs:
    def __init__(self, username, password, reports_data, with_full_coverage=False, with_progress=False):
        self.service = Client()
        self.username = username
        self.password = password
        self.reports_data = reports_data
        self.full_coverage = with_full_coverage
        self._progress = with_progress
        self.ids_in_use = []
        self._cmp_stack = []
        self.__decide()

    def __decide(self):
        scheduler = Client()
        scheduler.post('/users/service_signin/', {
            'username': self.username, 'password': self.password,
        })
        sch_data = {
            'tasks': {'pending': [], 'processing': [], 'error': [], 'finished': [], 'cancelled': []},
            'task errors': {}, 'task descriptions': {}, 'task solutions': {},
            'jobs': {'pending': [], 'processing': [], 'error': [], 'finished': [], 'cancelled': []},
            'job errors': {}, 'job configurations': {}
        }
        response = scheduler.post('/service/get_jobs_and_tasks/', {'jobs and tasks status': json.dumps(sch_data)})
        res_data = json.loads(json.loads(str(response.content, encoding='utf8'))['jobs and tasks status'])

        for job_identifier in res_data['jobs']['pending']:
            self.service.post('/users/service_signin/', {
                'username': self.username, 'password': self.password, 'job identifier': job_identifier
            })
            self.__decide_job()
            self.service.post('/users/service_signout/')
            sch_data['jobs']['finished'].append(job_identifier)
        scheduler.post('/service/get_jobs_and_tasks/', {'jobs and tasks status': json.dumps(sch_data)})
        scheduler.post('/users/service_signout/')

    def __upload_reports(self, reports, archives):
        archives_fp = []
        try:
            for a_name in archives:
                archives_fp.append(open(os.path.join(ARCHIVE_PATH, a_name), mode='rb'))
            if len(reports) == 1:
                self.service.post('/reports/upload/', {'report': json.dumps(reports[0]), 'file': archives_fp})
            else:
                self.service.post('/reports/upload/', {'reports': json.dumps(reports), 'file': archives_fp})
        except Exception:
            for fp in archives_fp:
                fp.close()
            raise

    def __get_report_id(self, name):
        r_id = '/' + name
        while r_id in self.ids_in_use:
            r_id = '/%s%s' % (name, random.randint(1, 100))
        self.ids_in_use.append(r_id)
        return r_id

    def __upload_start_report(self, name, parent, attrs=None, failed=False, finish=False):
        r_id = self.__get_report_id(name)
        files = set()
        reports = [{'id': r_id, 'type': 'start', 'parent id': parent, 'name': name}]
        if attrs is not None:
            reports[0]['attrs'] = attrs
        self._cmp_stack.append(r_id)

        if failed:
            files.add('unknown0.zip')
            reports.append({
                'id': self.__get_report_id('unknown'), 'type': 'unknown', 'parent id': r_id,
                'problem desc': 'unknown0.zip'
            })
            while len(self._cmp_stack) > 0:
                f_rep, logname = self.__get_finish_report(self._cmp_stack[-1])
                files.add(logname)
                reports.append(f_rep)
            self.__upload_reports(reports, files)
            raise DecisionError('Component %s failed!' % name)

        if finish:
            f_rep, logname = self.__get_finish_report(r_id)
            reports.append(f_rep)
            files.add(logname)

        self.__upload_reports(reports, files)
        return r_id

    def __get_finish_report(self, r_id):
        report = {'id': r_id, 'type': 'finish', 'resources': resources(), 'desc': 'Description text', 'log': 'log.zip'}
        if len(self._cmp_stack) > 0:
            self._cmp_stack.pop()
        return report, 'log.zip'

    def __upload_finish_report(self, r_id):
        f_rep, logname = self.__get_finish_report(r_id)
        self.__upload_reports([f_rep], [logname])

    def __upload_attrs_report(self, r_id, attrs, archive=None):
        if archive is None:
            self.service.post('/reports/upload/', {'report': json.dumps({'id': r_id, 'type': 'attrs', 'attrs': attrs})})
            return
        with open(os.path.join(ARCHIVE_PATH, archive), mode='rb') as fp:
            self.service.post('/reports/upload/', {
                'report': json.dumps({'id': r_id, 'type': 'attrs', 'attrs': attrs}), 'attr data': fp
            })

    def __upload_data_report(self, r_id, data=None):
        if data is None:
            data = {"newdata": str(random.randint(0, 100))}
        self.service.post('/reports/upload/', {'report': json.dumps({'id': r_id, 'type': 'data', 'data': data})})

    def __upload_progress(self, ts, sj=None, start=False, finish=False):
        if not self._progress:
            return
        data = {
            'total tasks to be generated': ts[0],
            'failed tasks': ts[1],
            'solved tasks': ts[2],
            'expected time for solving tasks': ts[3],
            'start tasks solution': start,
            'finish tasks solution': finish,
        }
        if sj is not None:
            data.update({
                'total subjobs to be solved': sj[0],
                'failed subjobs': sj[1],
                'solved subjobs': sj[2],
                'expected time for solving subjobs': sj[3],
                'start subjobs solution': start,
                'finish subjobs solution': finish
            })
        self.service.post('/service/update_progress/', {'progress': json.dumps(data)})
        time.sleep(2)

    def __upload_job_coverage(self, r_id, coverage):
        report = {'id': r_id, 'type': 'job coverage', 'coverage': coverage}
        files = []
        for carch in coverage.values():
            files.append(open(os.path.join(ARCHIVE_PATH, carch), mode='rb'))
        try:
            self.service.post('/reports/upload/', {'report': json.dumps(report), 'file': files})
        except Exception:
            for fp in files:
                fp.close()
            raise
        else:
            for fp in files:
                fp.close()

    def __decide_job(self):
        self.service.post('/jobs/decide_job/', {'report': json.dumps({
            'type': 'start', 'id': '/', 'attrs': [{'name': 'CV Core version', 'value': 'latest'}], 'comp': COMPUTER
        }), 'job format': FORMAT})

        self.__upload_progress([1, 0, 0, 1000], None, True, False)

        core_data = {
            'module1': {'ideal verdict': 'safe', 'verdict': 'unsafe', 'comment': 'This is comment for module1'},
            'module2': {'ideal verdict': 'safe', 'verdict': 'safe'},
            'module3': {'ideal verdict': 'unsafe', 'verdict': 'unsafe', 'comment': 'This is comment for module3'},
            'module4': {'ideal verdict': 'unsafe', 'verdict': 'unknown'}
        }
        # core_data = {
        #     'module1': {
        #         'before fix': {'verdict': 'unsafe', 'comment': 'Comment for module1 before fix'},
        #         'after fix': {'verdict': 'unsafe', 'comment': 'Comment for module1 after fix'},
        #     },
        #     'module2': {
        #         'before fix': {'verdict': 'safe', 'comment': '1'},
        #         'after fix': {'verdict': 'unsafe', 'comment': 'Comment for module2 after fix'},
        #     },
        #     'module3': {
        #         'before fix': {'verdict': 'unsafe', 'comment': 'Comment for module3 before fix'},
        #         'after fix': {'verdict': 'safe', 'comment': '1'},
        #     },
        #     'module4': {
        #         'before fix': {'verdict': 'unsafe', 'comment': '1'},
        #         'after fix': {'verdict': 'unknown', 'comment': '1'},
        #     }
        # }

        self.__upload_data_report('/', core_data)

        core_coverage = {}
        if any('chunks' in chunk for chunk in self.reports_data):
            progress_sj = [len(self.reports_data), 0, 0, 100 * len(self.reports_data) + 10]
            progress_ts = [len(self.reports_data) * 2, 0, 0, 100 * len(self.reports_data)]
            self.__upload_progress(progress_ts, progress_sj, True, False)
            for subjob in self.reports_data:
                if 'chunks' in subjob:
                    try:
                        core_coverage.update(self.__upload_subjob(subjob))
                    except DecisionError:
                        pass
                progress_sj[2] += 1
                progress_sj[3] -= 100
                progress_ts[2] += 2
                progress_ts[3] -= 100
                self.__upload_progress(progress_ts, progress_sj, False, False)
            self.__upload_progress(progress_ts, progress_sj, False, True)
        else:
            try:
                self.__upload_chunks()
            except DecisionError:
                pass

        if self.full_coverage and len(core_coverage) > 0:
            self.__upload_job_coverage('/', core_coverage)
        self.__upload_finish_report('/')

    def __upload_subjob(self, subjob):
        sj = self.__upload_start_report('Sub-job', '/', [{
            'name': 'Name', 'value': 'test/dir/and/some/other/text:{0}'.format(subjob['requirement'])
        }])
        lkbce = self.__upload_start_report('LKBCE', sj)
        self.__upload_attrs_report(lkbce, [LINUX_ATTR])
        self.__upload_finish_report(lkbce)

        self.__upload_start_report('LKVOG', sj, [LKVOG_ATTR], finish=True)

        vtg = self.__upload_start_report('VTG', sj, [LINUX_ATTR, LKVOG_ATTR])
        for chunk in subjob['chunks']:
            vtgw = self.__upload_start_report('VTGW', vtg, [
                {'name': 'Requirement', 'value': subjob['requirement'], 'compare': True, 'associate': True},
                {'name': 'Program fragment', 'value': chunk['module'], 'compare': True, 'associate': True}
            ], failed=(chunk.get('fail') == 'VTGW'))
            for cmp in ['ASE', 'EMG', 'FVTP', 'RSG', 'SA', 'TR', 'Weaver']:
                self.__upload_start_report(cmp, vtgw, failed=(chunk.get('fail') == cmp), finish=True)
            self.__upload_finish_report(vtgw)
        self.__upload_finish_report(vtg)

        vrp = self.__upload_start_report('VRP', sj, [LINUX_ATTR, LKVOG_ATTR])
        for chunk in subjob['chunks']:
            rp = self.__upload_start_report('RP', vrp, [
                {'name': 'Requirement', 'value': subjob['requirement'], 'compare': True, 'associate': True},
                {'name': 'Program fragment', 'value': chunk['module'], 'compare': True, 'associate': True}
            ], failed=(chunk.get('fail') == 'RP'))
            self.__upload_verdicts(rp, chunk)
            self.__upload_finish_report(rp)
        self.__upload_finish_report(vrp)

        if self.full_coverage:
            # sj_coverage = {subjob['requirement']: 'big_full_coverage.zip'}
            sj_coverage = {subjob['requirement']: 'Core_coverage.zip'}
            self.__upload_job_coverage(sj, sj_coverage)
            self.__upload_finish_report(sj)
            return sj_coverage
        else:
            self.__upload_finish_report(sj)
        return {}

    def __upload_chunks(self):
        lkbce = self.__upload_start_report('LKBCE', '/')
        self.__upload_attrs_report(lkbce, [LINUX_ATTR])
        self.__upload_finish_report(lkbce)

        self.__upload_start_report('LKVOG', '/', [LKVOG_ATTR], finish=True)

        vtg = self.__upload_start_report('VTG', '/', [LINUX_ATTR, LKVOG_ATTR])
        for chunk in self.reports_data:
            vtgw = self.__upload_start_report('VTGW', vtg, [
                {'name': 'Requirement', 'value': chunk['requirement'], 'compare': True, 'associate': True},
                {'name': 'Program fragment', 'value': chunk['module'], 'compare': True, 'associate': True}
            ], failed=(chunk.get('fail') == 'VTGW'))
            for cmp in ['ASE', 'EMG', 'FVTP', 'RSG', 'SA', 'TR', 'Weaver']:
                self.__upload_start_report(cmp, vtgw, failed=(chunk.get('fail') == cmp), finish=True)
            self.__upload_finish_report(vtgw)
        self.__upload_finish_report(vtg)

        progress_ts = [len(self.reports_data), 0, 0, 100 * len(self.reports_data)]
        self.__upload_progress(progress_ts, None, True, False)
        vrp = self.__upload_start_report('VRP', '/', [LINUX_ATTR, LKVOG_ATTR])
        for chunk in self.reports_data:
            rp = self.__upload_start_report('RP', vrp, [
                {'name': 'Requirement', 'value': chunk['requirement'], 'compare': True, 'associate': True},
                {'name': 'Program fragment', 'value': chunk['module'], 'compare': True, 'associate': True}
            ], failed=(chunk.get('fail') == 'RP'))
            self.__upload_verdicts(rp, chunk)
            self.__upload_finish_report(rp)
            progress_ts[2] += 1
            progress_ts[3] -= 100
            self.__upload_progress(progress_ts, None, False, False)
        self.__upload_finish_report(vrp)
        self.__upload_progress(progress_ts, None, False, True)

    def __upload_verdicts(self, parent, chunk):
        if 'unsafes' in chunk:
            coverage = 'partially_coverage.zip'
        # elif 'safe' in chunk:
        #     coverage = 'big_full_coverage.zip'
        else:
            # coverage = 'partially_coverage.zip'
            coverage = None

        verification = {
            'id': self.__get_report_id(chunk['tool']), 'type': 'verification',
            'parent id': parent, 'name': chunk['tool'],
            'attrs': [{'name': 'Test', 'value': 'test value', 'data': 'attrdata.txt'}],
            'resources': resources(), 'data': {'description': str(chunk['tool'])},
            'attr data': 'attrdata.zip'
        }

        files = ['attrdata.zip']
        if coverage is not None:
            files.append(coverage)
            verification['coverage'] = coverage
        if chunk.get('verifier_input', False):
            files.append('verifier_input.zip')
            verification['input files of static verifiers'] = 'verifier_input.zip'
        if chunk.get('log', False):
            files.append('log.zip')
            verification['log'] = 'log.zip'

        reports = [verification]
        if 'safe' in chunk:
            files.append(chunk['safe'])
            reports.append({
                'id': self.__get_report_id('safe'), 'type': 'safe', 'parent id': verification['id'], 'attrs': [],
                'proof': os.path.basename(chunk['safe'])
            })
        elif 'unsafes' in chunk:
            cnt = 1
            for u in chunk['unsafes']:
                files.append(u)
                reports.append({
                    'id': self.__get_report_id('unsafe'), 'type': 'unsafe', 'parent id': verification['id'],
                    'attrs': [{'name': 'entry point', 'value': 'func_%s' % cnt}], 'error traces': [os.path.basename(u)],
                    'sources': os.path.basename(u)
                })
                cnt += 1
        if 'unknown' in chunk and 'safe' not in chunk:
            files.append(chunk['unknown'])
            reports.append({
                'id': self.__get_report_id('unknown'), 'type': 'unknown', 'parent id': verification['id'],
                'problem desc': os.path.basename(chunk['unknown'])
            })
        reports.append({'id': verification['id'], 'type': 'verification finish'})
        self.__upload_reports(reports, files)

    def __is_not_used(self):
        pass
