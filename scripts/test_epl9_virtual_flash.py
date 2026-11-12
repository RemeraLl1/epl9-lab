"""Synthetic logical-model checks only; no camera or vendor firmware required."""
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from epl9_virtual_flash import (DEFAULT_LAYOUT, FaultPlan, FlashError,
                               IntegrityError, VirtualFlashStore)


class VirtualFlashTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "store"
        self.layout = {"main": {"base": 0x1000, "aliases": [0x2000], "size": 256},
                       "osd": {"base": 0x3000, "aliases": [], "size": 128}}
        self.original = {"main": bytes([0x55]) * 256, "osd": bytes([0x33]) * 128}
        self.new = bytes(range(256))
        self.store = VirtualFlashStore.create(self.path, self.original, layout=self.layout,
                                             page_size=32, erase_block_size=128)

    def reopen(self):
        self.store.close()
        self.store = VirtualFlashStore.open(self.path)
        return self.store

    def test_defaults(self):
        self.assertEqual(DEFAULT_LAYOUT['main']['base'], 0x406e0000)
        self.assertEqual(DEFAULT_LAYOUT['main']['aliases'], [0x806e0000])
        self.assertEqual(DEFAULT_LAYOUT['osd']['base'], 0x421e0000)
        self.assertEqual(DEFAULT_LAYOUT['main']['size'], 26214400)

    def test_success_persistence_and_identity(self):
        result = self.store.program_component('main', self.new)
        self.assertEqual(result['return_code'], 0)
        self.assertEqual(result['erased_blocks'], 2)
        self.assertEqual(result['programmed_pages'], 8)
        self.assertEqual(result['programmed_bytes'], 256)
        report = self.store.identity_report()
        self.assertFalse(report['hardware_qualified'])
        self.assertEqual(self.reopen().identity_report(), report)
        self.assertEqual(self.store.read_component('main'), self.new)
        self.assertEqual(self.store.read_component('osd'), self.original['osd'])
        self.assertEqual(report['components']['main']['original_sha256'], hashlib.sha256(self.original['main']).hexdigest())
        self.assertEqual((self.path.stat().st_mode & 0o777), 0o700)
        for file in self.path.iterdir():
            self.assertEqual(file.stat().st_mode & 0o777, 0o600)

    def test_bounds_and_geometry(self):
        for args in [('main', -1, 1), ('main', 255, 2), ('other', 0, 1)]:
            with self.assertRaises(FlashError):
                self.store.read(*args)
        for offset, length in [(1, 128), (0, 32), (0, 0), (128, 256)]:
            with self.assertRaises(FlashError):
                self.store.erase('main', offset, length)
        for offset, data in [(31, b'xx'), (0, b'x'*33), (0,b'')]:
            with self.assertRaises(FlashError):
                self.store.program('main', offset, data)
        with self.assertRaises(FlashError):
            self.store.program_component('main', b'bad')
        self.assertEqual(self.store.read_component('main'), self.original['main'])

    def test_no_zero_to_one_and_close(self):
        with self.assertRaises(FlashError):
            self.store.program('main', 0, b'\xff')
        self.store.erase('main', 0, 128)
        self.store.program('main', 0, b'\x00'*32)
        with self.assertRaises(FlashError):
            self.store.program('main', 0, b'\xff')
        self.reopen()
        self.assertEqual(self.store.read('main', 0, 32), bytes(32))
        self.store.close()
        self.store.close()
        with self.assertRaises(FlashError):
            self.store.read_component('main')

    def test_erase_error_preserves_later_blocks(self):
        r = self.store.program_component('main', self.new, FaultPlan('erase_error', block_index=1))
        self.assertEqual((r['status'],r['stage'],r['offset'],r['return_code']), ('error','erase',128,0x3101))
        self.assertTrue(r['returned'])
        self.assertEqual(self.reopen().read_component('main'), self.new[:128]+self.original['main'][128:])
        self.assertEqual(self.store.last_result,r)

    def test_program_error_erased_tail(self):
        r = self.store.program_component('main', self.new, FaultPlan('program_error', page_index=2))
        self.assertEqual(r['offset'],64)
        self.assertEqual(r['programmed_pages'],2)
        self.assertEqual(self.reopen().read_component('main'),self.new[:64]+b'\xff'*64+self.original['main'][128:])

    def test_partial_power_loss_checkpoint_without_close(self):
        r = self.store.program_component('main', self.new, FaultPlan('power_loss',page_index=2,partial_bytes=7))
        self.assertFalse(r['returned'])
        self.assertIsNone(r['return_code'])
        self.assertEqual(r['status'],'interrupted')
        self.assertEqual(r['programmed_bytes'],71)
        reopened=VirtualFlashStore.open(self.path)
        self.assertEqual(reopened.last_result,r)
        self.assertEqual(reopened.read_component('main'),self.new[:71]+b'\xff'*57+self.original['main'][128:])

    def test_erase_power_loss_boundary(self):
        r=self.store.program_component('main',self.new,FaultPlan('power_loss',stage='erase',block_index=1))
        self.assertEqual(r['erased_blocks'],1)
        self.assertEqual(self.reopen().read_component('main'),self.new[:128]+self.original['main'][128:])

    def test_readback_corruption_is_persistent_success(self):
        r=self.store.program_component('main',self.new,FaultPlan('readback_mismatch',page_index=3))
        self.assertEqual(r['return_code'],0)
        self.assertTrue(r['corruption_injected'])
        expected=bytearray(self.new)
        expected[96]^=1
        self.assertEqual(self.reopen().read_component('main'),expected)
        self.assertNotEqual(r['actual_sha256'],r['expected_sha256'])

    def test_fault_validation_precedes_mutation(self):
        for f in [FaultPlan('bad'),FaultPlan('program_error',page_index=8),
                  FaultPlan('erase_error',block_index=-1),FaultPlan('power_loss',partial_bytes=33),
                  FaultPlan('erase_error',partial_bytes=1)]:
            with self.assertRaises(FlashError):
                self.store.program_component('main',self.new,f)
        self.assertEqual(self.store.read_component('main'),self.original['main'])

    def test_component_tampering_rejected(self):
        file=self.path/'main.flash.bin'
        file.write_bytes(b'x'*256)
        with self.assertRaises(IntegrityError):
            VirtualFlashStore.open(self.path)

    def test_truncated_component_rejected(self):
        (self.path/'main.flash.bin').write_bytes(b'bad')
        with self.assertRaises(IntegrityError):
            VirtualFlashStore.open(self.path)

    def test_manifest_tampering_rejected(self):
        file=self.path/'manifest.json'
        m=json.loads(file.read_text())
        m['last_result']={'status':'invented'}
        file.write_text(json.dumps(m))
        with self.assertRaises(IntegrityError):
            VirtualFlashStore.open(self.path)

    def test_rehashed_inconsistent_manifest_rejected(self):
        file=self.path/'manifest.json'
        m=json.loads(file.read_text())
        m['components']['main']['size']=128
        del m['manifest_sha256']
        m['manifest_sha256']=hashlib.sha256(json.dumps(m,sort_keys=True,separators=(',',':')).encode()).hexdigest()
        file.write_text(json.dumps(m))
        with self.assertRaises(IntegrityError):
            VirtualFlashStore.open(self.path)

    def test_manifest_symlink_rejected(self):
        file=self.path/'manifest.json'
        target=self.path/'saved.json'
        file.rename(target)
        file.symlink_to(target)
        with self.assertRaises(IntegrityError):
            VirtualFlashStore.open(self.path)

    def test_component_symlink_rejected(self):
        file=self.path/'main.flash.bin'
        target=self.path/'saved.bin'
        file.rename(target)
        file.symlink_to(target)
        with self.assertRaises(IntegrityError):
            VirtualFlashStore.open(self.path)

    def test_recovery_write_after_interruption(self):
        self.store.program_component('main',self.new,FaultPlan('power_loss',page_index=5,partial_bytes=9))
        self.reopen()
        r=self.store.program_component('main',self.original['main'])
        self.assertEqual(r['status'],'success')
        self.assertEqual(self.reopen().read_component('main'),self.original['main'])

    def test_report_is_defensive_copy(self):
        r=self.store.program_component('main',self.new)
        r['events'].clear()
        report=self.store.identity_report()
        report['layout']['main']['size']=0
        self.assertTrue(self.store.last_result['events'])
        self.assertEqual(self.store.identity_report()['layout']['main']['size'],256)

    def test_close_without_checkpoint_discards_ram_changes(self):
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in self.path.iterdir()}
        self.store.erase('main', 0, 128)
        self.store.program('main', 0, bytes(32))
        self.store.close(checkpoint=False)
        after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                 for p in self.path.iterdir()}
        self.assertEqual(before, after)
        self.assertEqual(VirtualFlashStore.open(self.path).read_component('main'),
                         self.original['main'])
        with self.assertRaises(FlashError):
            self.store.read_component('main')

    def test_close_without_checkpoint_preserves_disk_corruption(self):
        self.store.program_component('main', self.new)
        file = self.path / 'main.flash.bin'
        corrupted = b'x' * 256
        file.write_bytes(corrupted)
        before = {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                  for p in self.path.iterdir()}
        self.store.close(checkpoint=False)
        after = {p.name: (p.read_bytes(), p.stat().st_mtime_ns)
                 for p in self.path.iterdir()}
        self.assertEqual(before, after)
        self.assertEqual(file.read_bytes(), corrupted)
        with self.assertRaises(IntegrityError):
            VirtualFlashStore.open(self.path)

    def test_create_never_overwrites_store(self):
        with self.assertRaises(FileExistsError):
            VirtualFlashStore.create(self.path,self.original,layout=self.layout,page_size=32,erase_block_size=128)
        self.assertEqual(VirtualFlashStore.open(self.path).read_component('main'),self.original['main'])

    def test_layout_rejected_before_creation(self):
        self.layout['main']['aliases']=[0x3000]
        other=Path(self.temp.name)/'invalid'
        with self.assertRaises(FlashError):
            VirtualFlashStore.create(other,self.original,layout=self.layout,page_size=32,erase_block_size=128)
        self.assertFalse(other.exists())


if __name__ == '__main__':
    unittest.main()
