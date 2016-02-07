#!/usr/bin/env python2.7

import argparse
from cStringIO import StringIO
import datetime
import os
import os.path
import sqlite3
import sys
from urlparse import urlparse, urljoin
import xml.dom.minidom
import xml.etree.cElementTree as cET

__version__ = "1.0-0"

class Tag(object):

    tags = {}
    max_id = 0
    hidden_tag_id = -1

    def __init__(self, tag_row):
        self.id = tag_row[0]
        self.name = tag_row[1]
        self.category_id = tag_row[2]
        self.is_category = bool(tag_row[3])
        if self.id > Tag.max_id:
            Tag.max_id = self.id
        Tag.tags[self.id] = self

    def get_parent(self):
        if self.category_id in Tag.tags:
            return Tag.tags[self.category_id]

    def __repr__(self):
        return "[%d, %s, %d, %d]" % (self.id, self.name, self.category_id, int(self.is_category))

    def __str__(self):
        levels = [self.name]
        parent = self.get_parent()
        while parent:
            levels.append(parent.name)
            parent = parent.get_parent()
        levels.reverse()
        return "->".join(levels)

    def is_hidden(self):
        parent = self
        while parent:
            if parent.id == Tag.hidden_tag_id:
                return True
            parent = parent.get_parent()
        return False

    def to_xmp_tags(self):
        t_tags = []
        parent = self
        while parent:
            t_tags.append(parent.name)
            parent = parent.get_parent()
        t_tags.reverse()
        return t_tags, '|'.join(t_tags)

    @classmethod
    def set_hidden_tag_id(cls, tag_id):
        cls.hidden_tag_id = tag_id


class Roll(object):

    rolls = {}

    def __init__(self, roll_row):
        self.id = roll_row[0]
        self.time = roll_row[1]
        Roll.rolls[self.id] = self

    def __repr__(self):
        return "[%d, %d]" % (self.id, self.time)

    def __str__(self):
        return "%d: %s" % (self.id, datetime.datetime.fromtimestamp(self.time).isoformat(' '))

    def to_xmp_tags(self):
        r_tags = ("F-Roll", datetime.datetime.fromtimestamp(self.time).isoformat(' '))
        return r_tags, '|'.join(r_tags)


class Photo(object):

    photos = {}

    def __init__(self, photo_row):
        self.id = photo_row[0]
        self.time = photo_row[1]
        self.base_uri = photo_row[2]
        if not self.base_uri.endswith('/'):
            self.base_uri = self.base_uri + '/'
        self.filename = photo_row[3]
        self.description = photo_row[4]
        self.roll_id = photo_row[5]
        self.default_version_id = photo_row[6]
        self.rating = photo_row[7]
        self.file_path = urlparse(urljoin(self.base_uri, self.filename)).path
        self.versions = {}
        self.tags = []
        Photo.photos[self.id] = self

    def get_roll(self):
        return Roll.rolls[self.roll_id]

    def write_sidecars(self, versions=None, test=False):
        f_tags = set()
        h_tags = set()
        for tag in self.tags:
            f, h = tag.to_xmp_tags()
            f_tags.update(f)
            h_tags.add(h)

        f_tags.update(['f-roll', str(self.get_roll().time)])
        h_tags.add('f-roll|%s' % str(self.get_roll().time))
        versions = self.versions.keys()
        versions.sort()
        k = versions[0]
        f_tags.update(['f-group', str(self.versions[k].import_md5)])
        h_tags.add('f-group|%s' % str(self.versions[k].import_md5))

        if not versions:
            versions = self.versions.keys()
        versions.sort()
        for version in versions:
            vsc = SideCar(self.versions[version], f_tags, h_tags)
            vsc.write(test=test)


class PhotoVersion(object):

    def __init__(self, version_row):
        self.photo_id = version_row[0]
        self.version_id = version_row[1]
        self.name = version_row[2]
        self.base_uri = version_row[3]
        if not self.base_uri.endswith('/'):
            self.base_uri = self.base_uri + '/'
        self.filename = version_row[4]
        self.import_md5 = version_row[5]
        self.file_path = urlparse(urljoin(self.base_uri, self.filename)).path
        self.parent = Photo.photos[self.photo_id]
        Photo.photos[self.photo_id].versions[self.version_id] = self


class SideCar(object):

    XMP_DECL = '<?xml version="1.0" encoding="UTF-8"?>'
    XMP_CONTENT = {
        'x:xmpmeta': {
            'xmlns:x': "adobe:ns:meta/",
            'x:xmptk': "XMP Core 4.4.0-Exiv2",
            'rdf:RDF': {
                'xmlns:rdf': "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
                'rdf:Description': {
                    'rdf:about': "",
                    'xmlns:xmp': "http://ns.adobe.com/xap/1.0/",
                    'xmlns:xmpMM': "http://ns.adobe.com/xap/1.0/mm/",
                    'xmlns:darktable': "http://darktable.sf.net/",
                    'xmlns:dc': "http://purl.org/dc/elements/1.1/",
                    'xmlns:lr': "http://ns.adobe.com/lightroom/1.0/",
                    'darktable:xmp_version': "1",
                    'darktable:raw_params': "0",
                    'darktable:auto_presets_applied': "1",
                    'darktable:mask_id': {'rdf:Seq': {}},
                    'darktable:mask_type': {'rdf:Seq': {}},
                    'darktable:mask_name': {'rdf:Seq': {}},
                    'darktable:mask_version': {'rdf:Seq': {}},
                    'darktable:mask': {'rdf:Seq': {}},
                    'darktable:mask_nb': {'rdf:Seq': {}},
                    'darktable:mask_src': {'rdf:Seq': {}},
                    'darktable:history_modversion': {'rdf:Seq': {}},
                    'darktable:history_enabled': {'rdf:Seq': {}},
                    'darktable:history_operation': {'rdf:Seq': {}},
                    'darktable:history_params': {'rdf:Seq': {}},
                    'darktable:blendop_params': {'rdf:Seq': {}},
                    'darktable:blendop_version': {'rdf:Seq': {}},
                    'darktable:multi_priority': {'rdf:Seq': {}},
                    'darktable:multi_name': {'rdf:Seq': {}},
                }
            }
        }
    }

    def __init__(self, photo_version, flat_tags, heir_tags):
        self.version = photo_version
        self.photo = self.version.parent
        self.f_tags = flat_tags
        self.h_tags = heir_tags

    @classmethod
    def _populate_tag(cls, element, element_dict):
        for key, value in element_dict.items():
            if type(value) == dict:
                se = cET.SubElement(element, key)
                cls._populate_tag(se, value)
            else:
                element.set(key, value)

    @staticmethod
    def _find_tag(root, tag_name):
        for e in root.iter():
            if e.tag == tag_name:
                return e
        return None

    def write(self, test=False):
        root = cET.Element(SideCar.XMP_CONTENT.keys()[0])
        self._populate_tag(root, SideCar.XMP_CONTENT[root.tag])
        desc = self._find_tag(root, 'rdf:Description')
        desc.set('xmp:rating', str(self.photo.rating))
        if self.photo.description:
            dcdesc = cET.SubElement(desc, 'dc:description')
            rdfalt = cET.SubElement(dcdesc, 'rdf:Alt')
            rdfli = cET.SubElement(rdfalt, 'rdf:li')
            rdfli.set('xml:lang', "x-default")
            rdfli.text = self.photo.description
        if len(self.f_tags) > 0:
            dcsub = cET.SubElement(desc, 'dc:subject')
            rdfseq = cET.SubElement(dcsub, 'rdf:Seq')
            for tag in self.f_tags:
                rdfli = cET.SubElement(rdfseq, 'rdf:li')
                rdfli.text = tag
        if len(self.h_tags) > 0:
            lrsub = cET.SubElement(desc, 'lr:hierarchicalSubject')
            rdfseq = cET.SubElement(lrsub, 'rdf:Seq')
            for tag in self.h_tags:
                rdfli = cET.SubElement(rdfseq, 'rdf:li')
                rdfli.text = tag
        scfn = '%s.xmp' % self.version.file_path
        if test:
            sys.stdout.write('SideCar(%s)\n' % scfn)
            sys.stdout.write("%s\n" % SideCar.XMP_DECL)
            xml.dom.minidom.parseString(cET.tostring(root)).writexml(sys.stdout,
                                                                     addindent="  ",
                                                                     newl="\n")
        else:
            with open(scfn, 'wb') as scf:
                scf.write("%s\n" % SideCar.XMP_DECL)
                xml.dom.minidom.parseString(cET.tostring(root)).writexml(scf,
                                                                         addindent="  ",
                                                                         newl="\n")


class FSpotDB(object):

    def __init__(self, db_file, progress_cb=lambda a, b: None):
        self.filename = os.path.abspath(db_file)
        self._db = sqlite3.connect(self.filename)

        cursor = self._db.cursor()

        progress_cb('Loading Tags', 0.0)

        cursor.execute('SELECT data FROM meta WHERE name ="Hidden Tag Id"')
        hidden_tag_row = cursor.fetchone()
        Tag.set_hidden_tag_id(int(hidden_tag_row[0]))

        cursor.execute('SELECT Count(*) FROM tags')
        numrows = cursor.fetchone()[0]

        cursor.execute('SELECT * FROM tags')

        for ct, tag_row in enumerate(cursor.fetchall()):
            Tag(tag_row)
            if ct % 10 == 0:
                progress_cb('Loading Tags', float(ct)/numrows)

        self.tags = Tag.tags

        progress_cb('Loading Tags', 1.0)
        progress_cb('Loading Rolls', 0.0)

        cursor.execute('SELECT Count(*) FROM rolls')
        numrows = cursor.fetchone()[0]

        cursor.execute('SELECT * FROM rolls')

        for ct, roll_row in enumerate(cursor.fetchall()):
            Roll(roll_row)
            if ct % 10 == 0:
                progress_cb('Loading Rolls', float(ct)/numrows)

        self.rolls = Roll.rolls

        progress_cb('Loading Rolls', 1.0)
        progress_cb('Loading Photos', 0.0)

        cursor.execute('SELECT Count(*) FROM photos')
        numrows = cursor.fetchone()[0]

        cursor.execute('SELECT * FROM photos')

        for ct, photo_row in enumerate(cursor.fetchall()):
            Photo(photo_row)
            if ct % 10 == 0:
                progress_cb('Loading Photos', float(ct)/numrows)

        self.photos = Photo.photos

        progress_cb('Loading Photos', 1.0)
        progress_cb('Preparing Photo Versions/Tags', 0.0)

        for ct, photo in enumerate(self.photos.values()):
            cursor.execute('SELECT * FROM photo_versions WHERE photo_id = ?', (photo.id, ))
            for version_row in cursor.fetchall():
                PhotoVersion(version_row)

            cursor.execute('SELECT * FROM photo_tags WHERE photo_id = ?', (photo.id, ))
            for pid, tid in cursor.fetchall():
                photo.tags.append(self.tags[tid])

            if ct % 10 == 0:
                progress_cb('Preparing Photo Versions/Tags', float(ct)/numrows)

        progress_cb('Preparing Photo Versions/Tags', 1.0)
        sys.stdout.write('\n')


    def close(self):
        self._db.close()

    def get_photos_for_path(self, path):
        abspath = 'file://%s' % os.path.abspath(path)
        cursor = self._db.cursor()
        cursor.execute("SELECT id FROM photos WHERE base_uri LIKE ? ORDER BY base_uri", ('%%%s%%' % abspath, ))
        return [self.photos[row[0]] for row in cursor.fetchall()]


class StatusReporter(object):

    def __init__(self):
        self.last_status = None

    def cb(self, text, pcpt):
        if text is not None and text != self.last_status:
            sys.stdout.write('\n')
        self.last_status = text
        sys.stdout.write('\r%s: % 5.1f%%' % (text, 100.0*pcpt))
        sys.stdout.flush()

if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog="fs2dt.py",
                                     description="A program to prepare DarkTable .xmp files from an F-Spot database.",
                                     version=__version__)
    parser.add_argument('-f', '--fspotdb',
                        action='store',
                        default=os.path.join(os.getenv('HOME','./'),'photos.db'),
                        type=str,
                        help='Path to the f-spot database.',
                        metavar='DB_PATH',
                        dest='fspotdb')
    parser.add_argument('-l', '--limit',
                        action='store',
                        default='/',
                        type=str,
                        help='Limit output to files contained within the identified path.',
                        metavar='LIMIT_PATH',
                        dest='limit')
    parser.add_argument('--test',
                        action='store_true',
                        help='Write output to the standard output rather than to files.',
                        dest='test')
    args = parser.parse_args()

    sr = StatusReporter()

    db = FSpotDB(args.fspotdb, progress_cb=sr.cb)
    photos = db.get_photos_for_path(args.limit)
    for photo in photos:
        photo.write_sidecars(test=args.test)