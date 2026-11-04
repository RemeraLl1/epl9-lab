"""Reject unsafe logging contracts using synthetic memory; no firmware required."""
import unittest

from epl9_completion_audit import DiagnosticSink, read_cstring
from epl9_job_probe import BASE, STACK, SP
from mn103_calls import CallMachine
from mn103_subset import Memory, Region, Fault


def fixture(text=b'format\0'):
    return CallMachine({},Memory([Region(BASE,bytearray(text)),
        Region(STACK,bytearray(16384),True)]),{'sp':SP})


class CompletionAuditTests(unittest.TestCase):
    def test_format_sink_requires_rom_string_and_exact_frame(self):
        m=fixture(); sink=DiagnosticSink('format')
        m.memory.write(SP+4,STACK,4)
        with self.assertRaises(Fault): sink.validate(m,0,12)
        m.memory.write(SP+4,BASE,4)
        with self.assertRaises(Fault): sink.validate(m,0,8)
        sink.validate(m,0,12)
        m.r['sp']-=12
        detail=sink.apply(m)
        self.assertEqual(detail['text'],'format')
        self.assertFalse(detail['pixels_completed'])

    def test_string_reader_is_bounded(self):
        with self.assertRaises(Fault): read_cstring(fixture(b'x'*128),BASE)

    def test_owner_sink_rejects_unknown_call_site_and_source(self):
        m=fixture(); sink=DiagnosticSink('owner'); m.r['d1']=0x5b0081
        with self.assertRaises(Fault): sink.validate(m,0xf0,172)
        m.trace.append(0x607cfee2); m.r['d1']=0
        with self.assertRaises(Fault): sink.validate(m,0xf0,172)
        m.r['d1']=0x5b0081
        sink.validate(m,0xf0,172)
        before=bytes(m.memory.regions[1].data)
        self.assertTrue(sink.apply(m)['logging_only'])
        self.assertEqual(before,bytes(m.memory.regions[1].data))


if __name__=='__main__':
    unittest.main()
