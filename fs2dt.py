#!/usr/bin/env python2.7

import collections
import datetime
import os.path
import sqlite3
from urlparse import urlparse, urljoin
import xml.etree.cElementTree as ET


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


class PhotoVersion(object):

    def __init__(self, version_row):
        self.photo_id = version_row[0]
        self.version_id = version_row[1]
        self.name = version_row[2]
        self.base_uri = version_row[3]
        self.filename = version_row[4]
        self.import_md5 = version_row[5]
        self.file_path = urlparse(urljoin(self.base_uri, self.filename)).path
        Photo.photos[self.photo_id].versions[self.version_id] = self


class SideCar(object):

    DECL = '<?xml version="1.0" encoding="UTF-8"?>'
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

    def __init__(self, photo):
        self.photo = photo

    def _populate_tag(self, element, element_dict):
        for key, value in element_dict.items():
            if type(value) == dict:
                se = ET.SubElement(element, key)
                self._populate_tag(se, value)
            else:
                element.set(key, value)

    def write(self):

        root = ET.Element(SideCar.XMP_CONTENT.keys()[0])
        self._populate_tag(root, SideCar.XMP_CONTENT[root.tag])
        pass


COMMENT = """
   xmp:Rating="4"
   xmpMM:DerivedFrom="DSC_0139.jpg"
   <dc:description>
    <rdf:Alt>
     <rdf:li xml:lang="x-default">this is the description</rdf:li>
    </rdf:Alt>
   </dc:description>
   <dc:subject>
    <rdf:Seq>
     <rdf:li>DC-Washington: George's_teeth/dentures</rdf:li>
     <rdf:li>My_Tag</rdf:li>
     <rdf:li>TEST</rdf:li>
    </rdf:Seq>
   </dc:subject>
   <lr:hierarchicalSubject>
    <rdf:Seq>
     <rdf:li>TEST|DC-Washington: George's_teeth/dentures</rdf:li>
     <rdf:li>TEST|My_Tag</rdf:li>
    </rdf:Seq>
   </lr:hierarchicalSubject>
"""


class FSpotDB(object):

    def __init__(self, db_file):
        self.filename = os.path.abspath(db_file)
        self.db = sqlite3.connect(self.filename)

        cursor = self.db.cursor()

        cursor.execute('SELECT data FROM meta WHERE name ="Hidden Tag Id"')
        hidden_tag_row = cursor.fetchone()
        Tag.set_hidden_tag_id(int(hidden_tag_row[0]))

        cursor.execute('SELECT * FROM tags')

        for tag_row in cursor.fetchall():
            Tag(tag_row)

        self.tags = Tag.tags

        cursor.execute('SELECT * FROM rolls')

        for roll_row in cursor.fetchall():
            Roll(roll_row)

        self.rolls = Roll.rolls

        cursor.execute('SELECT * FROM photos')

        for photo_row in cursor.fetchall():
            Photo(photo_row)

        self.photos = Photo.photos

        for photo in self.photos.values():
            cursor.execute('SELECT * FROM photo_versions WHERE photo_id = ?', (photo.id, ))
            for version_row in cursor.fetchall():
                PhotoVersion(version_row)

            cursor.execute('SELECT * FROM photo_tags WHERE photo_id = ?', (photo.id, ))
            for pid, tid in cursor.fetchall():
                photo.tags.append(self.tags[tid])

        self.db.close()


if __name__ == "__main__":
    db = FSpotDB('f-spot.db')

    for photo in db.photos.values():
        for photo_version in photo.versions.values():
            print "PhotoID:", photo.id
            print "PhotoPath:", photo_version.file_path
            subs = set()
            hsubs = set()
            for tag in photo.tags:
                tags, htag = tag.to_xmp_tags()
                subs.update(tags)
                hsubs.add(htag)
            try:
                tags, htag = photo.get_roll().to_xmp_tags()
                subs.update(tags)
                hsubs.add(htag)
            except KeyError:
                pass
            print "Subject:", subs
            print "HeiraricalSubject:", hsubs
