from hashlib import sha256
from io import BytesIO
import json
import stat
import unittest
from unittest.mock import patch
import uuid
from zipfile import ZipFile,ZipInfo,ZIP_DEFLATED
from local_workbench import collaboration_package as codec


def rewrite(data,transform):
    output=BytesIO()
    with ZipFile(BytesIO(data)) as source,ZipFile(output,'w',ZIP_DEFLATED) as target:
        entries=[(item,source.read(item.filename)) for item in source.infolist()]
        for item,raw in transform(entries): target.writestr(item,raw)
    return output.getvalue()


class CollaborationPackageTests(unittest.TestCase):
    def setUp(self):
        self.metadata={'id':str(uuid.uuid4()),'source_id':'engineering-only','base_revision':3}
        self.files={'base.json':b'{"blocks":[]}','originals/snapshot.pdf':b'%PDF-isolated-fake-bytes'}
        self.package=codec.build_package('work',self.metadata,self.files)

    def test_roundtrip_digest_identity_and_determinism(self):
        result=codec.read_package(self.package)
        self.assertEqual(result['files'],self.files);self.assertEqual(result['metadata'],self.metadata)
        self.assertEqual(result['package_id'],self.metadata['id']);self.assertEqual(result['digest'],sha256(self.package).hexdigest())
        self.assertEqual(codec.build_package('work',self.metadata,self.files),self.package)
        self.assertEqual(codec.read_package(codec.build_package('submission',self.metadata,{'result.json':b'{}'}))['kind'],'submission')

    def test_unsafe_names_and_casefold_collisions(self):
        for name in ('../escape','/absolute','C:/absolute','a\\b','a/../b','a//b','NUL.txt','name.','bad\x00name'):
            with self.subTest(name=name),self.assertRaises(ValueError):codec.build_package('work',self.metadata,{name:b'x'})
        for files in ({'A.json':b'a','a.json':b'b'},{'é.json':b'a','e\u0301.json':b'b'},{'a':b'file','a/b':b'child'}):
            with self.assertRaises(ValueError):codec.build_package('work',self.metadata,files)

    def test_database_extension_or_signature_rejected(self):
        for files in ({'workflow.sqlite':b'x'},{'innocent.json':b'SQLite format 3\0other'}):
            with self.assertRaises(ValueError):codec.build_package('work',self.metadata,files)

    def test_corrupted_inventory_and_extra_files_rejected(self):
        changed=rewrite(self.package,lambda entries:[(info,b'changed' if info.filename=='files/base.json' else raw) for info,raw in entries])
        with self.assertRaises(ValueError):codec.read_package(changed)
        extra=rewrite(self.package,lambda entries:entries+[(ZipInfo('files/extra.json'),b'{}')])
        with self.assertRaises(ValueError):codec.read_package(extra)
        with self.assertRaises(ValueError):codec.read_package(self.package[:-25])

    def test_unsupported_manifest_version_duplicate_keys_and_identity(self):
        def altered(transform):
            def update(entries):
                result=[]
                for info,raw in entries:
                    if info.filename=='manifest.json':raw=transform(raw)
                    result.append((info,raw))
                return result
            return rewrite(self.package,update)
        def version(raw):
            data=json.loads(raw);data['version']=2;return json.dumps(data).encode()
        def identity(raw):
            data=json.loads(raw);data['package_id']=str(uuid.uuid4());return json.dumps(data).encode()
        for package in (altered(version),altered(identity),altered(lambda raw:raw.replace(b'"version":1',b'"version":1,"version":1'))):
            with self.assertRaises(ValueError):codec.read_package(package)

    def test_duplicate_case_collision_and_symlink_entries_rejected(self):
        for change in ('duplicate','case','symlink','traversal'):
            def update(entries):
                entry=ZipInfo('files/base.json' if change=='duplicate' else 'FILES/BASE.JSON' if change=='case' else '../escape' if change=='traversal' else 'files/link')
                if change=='symlink':entry.create_system=3;entry.external_attr=(stat.S_IFLNK|0o777)<<16
                return entries+[(entry,b'link-or-file')]
            with self.subTest(change=change),self.assertRaises(ValueError):codec.read_package(rewrite(self.package,update))

    def test_size_caps_before_reading_or_allocating_large_payload(self):
        with patch.object(codec,'MAX_ARCHIVE_BYTES',len(self.package)-1),self.assertRaises(ValueError):codec.read_package(self.package)
        with patch.object(codec,'MAX_FILE_BYTES',2),self.assertRaises(ValueError):codec.read_package(self.package)
        with patch.object(codec,'MAX_TOTAL_BYTES',10),self.assertRaises(ValueError):codec.read_package(self.package)
        with patch.object(codec,'MAX_FILES',1),self.assertRaises(ValueError):codec.read_package(self.package)
        with patch.object(codec,'MAX_FILE_BYTES',2),self.assertRaises(ValueError):codec.build_package('work',self.metadata,self.files)
        with self.assertRaises(ValueError):codec.build_package('unknown',self.metadata,self.files)
        with self.assertRaises(ValueError):codec.build_package('work',{'id':'not-a-uuid'},self.files)
