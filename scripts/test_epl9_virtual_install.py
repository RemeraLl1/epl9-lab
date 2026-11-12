"""Synthetic local controls for native-updater/storage adapters; no camera files."""
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

import epl9_virtual_install as vi
from epl9_virtual_flash import VirtualFlashStore, FaultPlan, IntegrityError
from epl9_recovery_audit import fixture, decoded_payload
from mn103_subset import Memory, Region, parse_listing, Fault


class CPU:
    def __init__(self, data):
        self.package_size = len(data)
        self.memory = Memory([Region(vi.BUFFER, bytearray(data), True, 'fixture')])
        self.r = dict(a0=0x806e0000, a1=vi.BUFFER, d0=len(data), d1=0)


def plain(kind=0x100, address=0x406e0000):
    raw = fixture(kind=kind, address=address, size=64)
    return raw[:32]+decoded_payload(raw[32:-32])+raw[-32:]


class VirtualInstall(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.sizepatch = patch.dict(vi.SIZES, main=128, osd=128)
        self.sizepatch.start()
        self.addCleanup(self.sizepatch.stop)
        initial = {'main': b'\xff'*128, 'osd': b'\xff'*128}
        layout = {'main':dict(base=0x406e0000, aliases=[0x806e0000], size=128),
                  'osd':dict(base=0x421e0000, aliases=[], size=128)}
        store = VirtualFlashStore.create(Path(self.tmp.name)/'flash', initial,
            layout=layout, page_size=16, erase_block_size=64)
        self.handle = vi.StoreHandle(store)
        self.addCleanup(lambda: None if self.handle.store.closed else self.handle.store.close())

    def test_alias_bounds(self):
        self.assertEqual(vi.component_name(0x806e0000, 128), 'main')
        self.assertEqual(vi.component_name(0x421e0000, 128), 'osd')
        for address, length in ((0x406e0001,128),(0x406e0000,127),(0x40000000,128)):
            with self.assertRaises(Fault): vi.component_name(address,length)

    def test_native_storage_adapter_writes_then_reopens_and_reads_actual_data(self):
        data, events = plain(), []
        cpu = CPU(data)
        leaf = vi.ProgramLeaf(self.handle,events)
        leaf.validate(cpu,0xf0,24)
        result = leaf.apply(cpu)
        self.assertEqual(result['return_code'],0)
        self.assertEqual(self.handle.reopens,1)
        self.assertEqual(self.handle.store.read_component('main'),data)
        cpu.memory.regions[0].data[:] = b'\xcd'*128
        cpu.r.update(a0=0x806e0000,a1=vi.BUFFER,d1=128)
        vi.ReadLeaf(self.handle,events).apply(cpu)
        self.assertEqual(bytes(cpu.memory.regions[0].data),data)
        self.assertEqual(self.handle.reopens,2)
        self.assertEqual([e['native_entry'] for e in events],['0x60439f38','0x604014c6'])


    def test_verification_reopen_does_not_repair_disk_corruption_from_RAM(self):
        data=plain();events=[];cpu=CPU(data)
        vi.ProgramLeaf(self.handle,events).apply(cpu)
        path=self.handle.store.path/'main.flash.bin'
        damaged=bytearray(path.read_bytes());damaged[33]^=1
        path.write_bytes(damaged)
        with self.assertRaises(IntegrityError):
            self.handle.reopen()
        self.assertEqual(path.read_bytes(),bytes(damaged))

    def test_native_leaf_ABIs_are_explicit(self):
        for leaf in (vi.ProgramLeaf(self.handle,[]),vi.ReadLeaf(self.handle,[])):
            with self.assertRaises(Fault):leaf.validate(CPU(plain()),0,0)

    def test_destination_kind_mismatch_rejected(self):
        with self.assertRaisesRegex(Fault,'destination'):
            vi.ProgramLeaf(self.handle,[]).apply(CPU(plain(0x101,0x421e0000)))

    def test_program_failure_is_return_code_not_native_success(self):
        events=[];cpu=CPU(plain())
        vi.ProgramLeaf(self.handle,events,'main',FaultPlan('program_error',page_index=2)).apply(cpu)
        self.assertEqual(cpu.r['d0'],0x3101)
        self.assertEqual(events[0]['programmed_pages'],2)
        self.assertNotEqual(self.handle.store.read_component('main'),plain())

    def test_power_loss_is_interruption_not_native_return(self):
        cpu=CPU(plain());events=[]
        with self.assertRaises(vi.PowerLoss):
            vi.ProgramLeaf(self.handle,events,'main',FaultPlan('power_loss',page_index=2,partial_bytes=3)).apply(cpu)
        self.assertFalse(events[0]['returned'])
        self.assertIsNone(events[0]['return_code'])
        self.assertEqual(events[0]['programmed_bytes'],35)

    def test_persisted_mismatch_is_read_instead_of_expected_bytes(self):
        data=plain();cpu=CPU(data);events=[]
        vi.ProgramLeaf(self.handle,events,'main',FaultPlan('readback_mismatch',page_index=2)).apply(cpu)
        self.assertEqual(cpu.r['d0'],0)
        cpu.r.update(a0=0x806e0000,a1=vi.BUFFER,d1=128)
        vi.ReadLeaf(self.handle,events).apply(cpu)
        actual=bytes(cpu.memory.regions[0].data)
        self.assertNotEqual(actual,data)
        self.assertNotEqual(vi.sum32(actual),0)
        self.assertEqual(events[-1]['envelope_sha256'],vi.sha(actual))

    def test_read_error_does_not_copy_data(self):
        cpu=CPU(plain());events=[]
        cpu.r.update(d1=128)
        before=bytes(cpu.memory.regions[0].data)
        vi.ReadLeaf(self.handle,events,'main').apply(cpu)
        self.assertEqual(cpu.r['d0'],0x3102)
        self.assertEqual(bytes(cpu.memory.regions[0].data),before)
        self.assertFalse(events[-1]['copied'])

    def test_fourth_checksum_loop_has_full_state_crosschecks(self):
        # Exact reviewed short instruction window; the full runner separately
        # checks these bytes against its pinned E-PL9 main before using it.
        lines='''6043a109\t0c\tclr\td3
6043a10a\tf8c602\tlsr\t2,d2
6043a10d\t8001\tmov\t1,d0
6043a10f\tdb\tsetlb\t
6043a110\t76\tmov\t(a2),d1
6043a111\t52\tinc4\ta2
6043a112\te7\tadd\td1,d3
6043a113\tf102\tsub\td0,d2
6043a115\td9\tlne\t'''
        image=bytes.fromhex('0cf8c6028001db7652e7f102d9')
        code=parse_listing(lines,image,0x6043a109)
        rows=vi.crosscheck_lower_checksum(code)
        self.assertEqual(len(rows),10)
        self.assertTrue(all(r['full_register_flags_memory_equal'] for r in rows))


if __name__=='__main__':unittest.main()
