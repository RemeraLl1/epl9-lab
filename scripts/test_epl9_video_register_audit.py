"""Guard against attributing a requested cadence to a fallback TG template."""
import struct
import unittest

from epl9_video_register_audit import (
    read_mode_table, select_mode, camera_output_nominal_hz,
    sensor_model_time, rebased_marker_offset, ordinary_center_gate, mux_nominal_video_timing,
)


class RegisterAuditTests(unittest.TestCase):
    def test_mux_timescale_and_duration_match_native_truncation(self):
        self.assertEqual(mux_nominal_video_timing(5994),(180000,3003))
        self.assertEqual(mux_nominal_video_timing(5000),(180000,3600))
        self.assertEqual(mux_nominal_video_timing(2997),(90000,3003))
        self.assertEqual(mux_nominal_video_timing(2500),(90000,3600))
        self.assertEqual(mux_nominal_video_timing(2400),(360000,15000))
        self.assertEqual(mux_nominal_video_timing(2397),(360000,15015))
        with self.assertRaises(ValueError):
            mux_nominal_video_timing(6000)

    def test_center_gate_at_60_resets_accumulator_and_returns_one(self):
        for rate in (0,30,59,60):
            for flag53,flag54,flag700 in ((0,0,0),(1,0,0),(0,1,1)):
                self.assertEqual(ordinary_center_gate(rate,3,flag53,flag54,flag700),
                                 (True,0))

    def test_center_gate_high_rate_decimation_and_flag_bypass(self):
        self.assertEqual(ordinary_center_gate(120,0,1),(False,2))
        self.assertEqual(ordinary_center_gate(120,2,1),(True,0))
        self.assertEqual(ordinary_center_gate(240,0,0,1,0),(True,0))
        self.assertEqual(ordinary_center_gate(240,0,0,1,1),(False,1))
        self.assertEqual(ordinary_center_gate(120,0xffff,1),(False,1))

    def test_sensor_model_conversion_retains_integer_and_register_width_rules(self):
        self.assertEqual(sensor_model_time(0x9000,1536*1564),16682)
        self.assertEqual(sensor_model_time(0x9000,1776*3550),43783)
        self.assertEqual(sensor_model_time(0x9000,1),0)
        self.assertEqual(sensor_model_time(0x9000,0x80000000),0)
        with self.assertRaises(ValueError):
            sensor_model_time(127,100)

    def test_marker_rebase_is_not_just_half_the_period(self):
        self.assertEqual(rebased_marker_offset(16683,1000,200),9041)
        self.assertEqual(rebased_marker_offset(100,101,0),0x80000064)
        with self.assertRaises(ValueError):
            rebased_marker_offset(100,10,0x10000)

    def test_camout_clock_words_use_encoded_divisors(self):
        # Firmware selection 8 uses /2 followed by /8, not /0 and /3.
        self.assertEqual(camera_output_nominal_hz(0x23300015,0,3),36000000)
        self.assertEqual(camera_output_nominal_hz(0x23300015,0,1),72000000)
        # CLKCAMDS selection 6 uses the same PLL getter with divider word 0.
        self.assertEqual(camera_output_nominal_hz(0x23300015,0,0),144000000)
        # Bit 2 changes the PLL factor branch; preserve its separate /2.
        self.assertEqual(camera_output_nominal_hz(0x23300011,0,3),18000000)
        # Native integer division occurs before multiplication by 2.4 MHz.
        self.assertEqual(camera_output_nominal_hz(0x23010025,0,0),1800000)
        with self.assertRaises(ValueError):
            camera_output_nominal_hz(0x23300015,-1,3)

    def test_mode_lookup_stops_at_sentinel_before_next_table(self):
        blob = b''.join(struct.pack('<IIHH',*row) for row in [
            (27,8,0,0),(36,0,0,0),(0,8,60,0),
        ])
        self.assertEqual(read_mode_table(blob,0,base=0),[(27,8,0,0)])
        with self.assertRaises(ValueError):
            read_mode_table(blob[:13],0,base=0)
        with self.assertRaises(ValueError):
            read_mode_table(blob,0,base=0,limit=1)

    def test_requested_60_is_not_reported_as_an_explicit_full_60_match(self):
        primary = [(0,0,60,0),(27,8,0,0)]
        fallback = [(27,8,0,0)]
        self.assertEqual(select_mode(primary,fallback,8,60,0),
                         dict(result=27,source='fallback_ignores_rate',table_rate=0))
        self.assertEqual(select_mode(primary,fallback,0,60,0),
                         dict(result=0,source='primary',table_rate=60))
        self.assertEqual(select_mode(primary,fallback,8,60,1),
                         dict(result=36,source='unmatched',table_rate=None))


if __name__ == '__main__':
    unittest.main()
