"""Offline OCI descriptor/lock tests; do not contact Docker or PostgreSQL."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools'))
from verify_image_lock import verify  # noqa: E402


class ImageLock(unittest.TestCase):
    def setUp(self):
        self.lock = json.loads((ROOT/'IMAGE_LOCK.json').read_text())
        self.indices={n:{'manifests':[{'digest':item['platform_manifest_digest'],
                'platform':{'os':'linux','architecture':'amd64'}}]}
                for n,item in self.lock['images'].items()}

    def test_valid_descriptor_only(self):
        result=verify(self.lock,self.indices)
        self.assertEqual(result['status'],'REGISTRY_MANIFEST_MATCH_ONLY_NOT_E2E')
        self.assertEqual(set(result['images']),{'postgres','python'})

    def test_wrong_child_rejected(self):
        self.indices['postgres']['manifests'][0]['digest']='sha256:'+'0'*64
        with self.assertRaisesRegex(ValueError,'child mismatch'):
            verify(self.lock,self.indices)

    def test_wrong_platform_rejected(self):
        self.indices['python']['manifests'][0]['platform']['architecture']='arm64'
        with self.assertRaisesRegex(ValueError,'child mismatch'):
            verify(self.lock,self.indices)

    def test_tag_only_reference_rejected(self):
        self.lock['images']['python']['reference']='python:3.12.15-bookworm'
        with self.assertRaisesRegex(ValueError,'not tag plus digest'):
            verify(self.lock,self.indices)


if __name__=='__main__':
    unittest.main(verbosity=2)
