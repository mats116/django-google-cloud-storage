# -*- coding: utf-8 -*-
"""
Google Cloud Storage file backend for Django
"""

import os
import mimetypes
from django.conf import settings
from django.core.files.storage import Storage
import cloudstorage as gcs

__author__ = "kazuki.matsuda@intimatemerger.com"
__license__ = "GNU GENERAL PUBLIC LICENSE"


class GoogleCloudStorage(Storage):

    def __init__(self, location=None, base_url=None):
        if location is None:
            location = '/' + settings.GOOGLE_CLOUD_STORAGE_BUCKET + '/'
        self.location = location
        if base_url is None:
            base_url = settings.GOOGLE_CLOUD_STORAGE_URL
        self.base_url = base_url

    def _open(self, name, mode='r'):
        filename = self.gen_filename(name)

        # rb is not supported
        if mode == 'rb':
            mode = 'r'

        if mode == 'w':
            type, encoding = mimetypes.guess_type(name)
            options = {'cache-control': settings.GOOGLE_CLOUD_STORAGE_CACHE_CONTROL}
            if self.enable_public(filename):
                options['x-goog-acl'] = 'public-read'
            gcs_file = gcs.open(filename, mode=mode, content_type=type, options=options)
        else:
            gcs_file = gcs.open(filename, mode=mode)

        return gcs_file

    def _save(self, name, content):
        filename = self.gen_filename(name)
        filename = os.path.normpath(filename)
        type, encoding = mimetypes.guess_type(name)
        options = {'cache-control': settings.GOOGLE_CLOUD_STORAGE_CACHE_CONTROL}
        if self.enable_public(filename):
            options['x-goog-acl'] = 'public-read'

        # Files are stored with public-read permissions.
        # Check out the google acl options if you need to alter this.
        gss_file = gcs.open(filename, mode='w', content_type=type, options=options)
        try:
            content.open()
        except:
            pass
        gss_file.write(content.read())
        try:
            content.close()
        except:
            pass
        gss_file.close()
        return name

    def delete(self, name):
        filename = self.gen_filename(name)
        try:
            gcs.delete(filename)
        except gcs.NotFoundError:
            pass

    def exists(self, name):
        try:
            self.stat_file(name)
            return True
        except gcs.NotFoundError:
            return False

    def listdir(self, path=None):
        directories, files = [], []
        bucketContents = gcs.listbucket(self.location, prefix=path)
        for entry in bucketContents:
            filePath = entry.filename
            head, tail = os.path.split(filePath)
            subPath = os.path.join(self.location, path)
            head = head.replace(subPath, '', 1)
            if head == "":
                head = None
            if not head and tail:
                files.append(tail)
            if head:
                if not head.startswith("/"):
                    head = "/" + head
                dir = head.split("/")[1]
                if dir not in directories:
                    directories.append(dir)
        return directories, files

    def size(self, name):
        stats = self.stat_file(name)
        return stats.st_size

    def accessed_time(self, name):
        raise NotImplementedError

    def created_time(self, name):
        stats = self.stat_file(name)
        return stats.st_ctime

    def modified_time(self, name):
        return self.created_time(name)

    def url(self, name):
        server_software = os.getenv("SERVER_SOFTWARE", "")
        if not server_software.startswith("Google App Engine"):
            pass
        return self.base_url + name.encode('utf-8')

    def stat_file(self, name):
        filename = self.gen_filename(name)
        return gcs.stat(filename)

    def gen_filename(self, name):
        return self.location + name.encode('utf-8')

    def enable_public(self, filename):
        if filename.startswith(self.location + 'documents/'):  # for Wagtail
            return False
        else:
            return True
