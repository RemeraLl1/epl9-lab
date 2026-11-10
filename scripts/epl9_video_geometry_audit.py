"""Offline geometry override candidates for exact E-PL9 1.1/build 1101.

Executes only bounded, verified native fragments in host memory.
Does not open the encoder, create a firmware patch or touch a camera.
"""

from mn103_tooling import default_reader, verify_reader
import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess

from epl9_video_audit import (
    ROOT, BASE, MAIN_NAME, MAIN_SHA, STOCK_SHA, verified_input,
    checked_listing, local_output,
)
from mn103_subset import Machine, Memory, Region, parse_listing
from mn103_calls import CallMachine


WINDOWS = {
    'progressive_class': (0x6169f34a, 0x6169f43e),
    'progressive_configuration': (0x6169f43e, 0x6169f4ee),
    'progressive_driver_call': (0x6169f4ee, 0x6169f506),
    'driver_preset_selection': (0x616a2814, 0x616a288e),
    'driver_geometry_alignment': (0x616a2a3e, 0x616a2acc),
    'driver_class_consumer': (0x616a2fba, 0x616a2fc8),
    'rate_control_class_dispatch': (0x616a42a8, 0x616a4339),
    'rate_control_high_class_budget': (0x616a4395, 0x616a43b4),
    'application_geometry_names': (0x607bd6fb, 0x607bd73b),
    'application_geometry_selection': (0x607bb56f, 0x607bb625),
    'application_output_rate': (0x607bb6e8, 0x607bb73c),
    'record_open_range_selection': (0x607b9b70, 0x607b9b91),
    'avm_open_dispatch': (0x6164c46b, 0x6164c483),
    'avm_video_source_parameters': (0x616602b3, 0x616602e2),
    'avm_video_encoder_parameters': (0x616603f6, 0x61660444),
    'video_source_aspect_and_size': (0x616b031f, 0x616b0372),
    'conditional_render_raster': (0x60725560, 0x607255c5),
    'conditional_render_planes': (0x607255eb, 0x60725650),
    'intermediate_raster_layout': (0x6074d9fd, 0x6074da48),
    'intermediate_fill_registers': (0x6073a393, 0x6073a438),
    'aspect_ratio_selector': (0x60749187, 0x607491bf),
    'aspect_crop_geometry': (0x6074fd86, 0x6074fdf6),
    'image_dimension_classifier': (0x607a3c9e, 0x607a3d47),
    'image_dimension_selection': (0x607509cd, 0x60750ada),
    'image_dimension_wrapper': (0x60750ada, 0x60750afc),
    'processing_type_from_sensor': (0x60708d80, 0x60708f4a),
    'processing_kind_getter': (0x6070899c, 0x607089a5),
    'processing_kind_setter': (0x60708993, 0x6070899c),
    'processing_kind_enable_a': (0x60726f25, 0x60726f2e),
    'processing_kind_enable_b': (0x60727aed, 0x60727af7),
    'processing_kind_disable_a': (0x60727eb5, 0x60727ebd),
    'processing_kind_disable_b': (0x60728fb4, 0x60728fbc),
    'processing_operation_mapper': (0x607031f0, 0x60703260),
    'processing_context_mapper': (0x6071d49d, 0x6071d50e),
    'processing_fit_dimensions': (0x60750830, 0x6075088e),
    'processing_fit_size_selector': (0x607491d5, 0x607491e9),
    'processing_type_output_copy': (0x607066de, 0x607066ec),
    'processing_context_output_copy': (0x60706642, 0x6070665b),
    'processing_ratio_context_copy': (0x60706775, 0x60706787),
    'processing_api_copy': (0x6071b7ac, 0x6071b7e4),
    'processing_job_parameter_copy': (0x6074e02f, 0x6074e03c),
    'camera_frame_header_pack': (0x6091a167, 0x6091a1cc),
    'camera_frame_header_publish': (0x606fc9ff, 0x606fca13),
    'camera_frame_header_load': (0x606fca3f, 0x606fca55),
    'camera_header_owner_adapter': (0x6091a079, 0x6091a0ba),
    'processing_record_header_receive': (0x606ffe3c, 0x606ffe72),
    'processing_record_operation_input': (0x60701b01, 0x60701b1c),
    'capture_flag_selector': (0x60925b0a, 0x60925b30),
    'capture_flag_cache': (0x6091b397, 0x6091b3a4),
    'capture_flag_snapshot': (0x6091b63c, 0x6091b645),
    'capture_flag_forward': (0x6091b66d, 0x6091b672),
    'capture_request_identity_copy': (0x6091b81c, 0x6091b834),
    'capture_flag_owner_copy': (0x6091b840, 0x6091b848),
    'capture_flag_ring_copy': (0x60701a4d, 0x60701a59),
    'processing_flag_extract': (0x60715d3f, 0x60715d8e),
    'processing_flag_publish': (0x606ff259, 0x606ff263),
    'processing_dispatch_selection': (0x60715009, 0x60715050),
    'processing_dispatch_calls': (0x60723625, 0x607236b3),
    'processing_enable_request_gate': (0x607247cd, 0x60724821),
    'processing_owner_render_calls': (0x60724a05, 0x60724a18),
    'processing_owner_scaler_call': (0x60724f4b, 0x60724f53),
    'processing_raster_acceptance': (0x607254e0, 0x60725560),
    'processing_pool_initialization': (0x60719c60, 0x60719c8a),
    'processing_pool_address': (0x60719ccb, 0x60719cee),
    'capture_aux_dispatch_input': (0x6091b7b8, 0x6091b7db),
    'capture_aux_is_first_kind': (0x6091dff2, 0x6091dffd),
    'capture_aux_dispatch_mapper': (0x6091c079, 0x6091c098),
    'capture_aux_owner_copy': (0x6091b83b, 0x6091b840),
    'capture_aux_ring_copy': (0x607017d4, 0x607017e1),
    'processing_settings_initializer': (0x606fe8c5, 0x606fe8da),
    'processing_settings_bind_properties': (0x60715da0, 0x60715dc9),
    'processing_settings_copy_properties': (0x60715dce, 0x60715e5f),
    'processing_settings_to_header': (0x60701025, 0x6070103e),
    'processing_header_pointer': (0x60700fe2, 0x60701000),
    'processing_display_mode_snapshot': (0x606ff27b, 0x606ff287),
    'processing_display_mode_getter': (0x6071a1b9, 0x6071a1c5),
    'display_open_mask_getter': (0x605f0f9f, 0x605f0fa8),
    'processing_dispatch_inputs': (0x60714ff2, 0x60715009),
    'capture_movie_parameter_gate': (0x609237c6, 0x60923829),
    'display_device_dispatch': (0x605f0c5c, 0x605f0c8f),
    'display_aspect_device_aliases': (0x60557d62, 0x60557d91),
    'q_pool_stride_and_capacity': (0x60727cba, 0x60727cf6),
    'mov_sample_entry_dimensions': (0x6168c1ff, 0x6168c20d),
    'mov_avcc_initialization': (0x6168c238, 0x6168c265),
    'mov_sps_header_ingress': (0x6168aee9, 0x6168af57),
    'source_config_from_processing_record': (0x60728227, 0x607282bc),
    'source_live_parameters_from_record': (0x6072843a, 0x6072846d),
    'source_config_publication': (0x60714652, 0x607146b7),
    'source_live_parameter_publication': (0x6071475c, 0x6071479d),
    'source_live_context_getter': (0x607147a6, 0x607147b0),
    'source_pool_gate_input': (0x6072c14a, 0x6072c167),
    'source_pool_gate_store': (0x60710c74, 0x60710c94),
    'source_special_preset_selector': (0x60715ee5, 0x60715f25),
    'source_special_rate_query': (0x60715ed0, 0x60715ee5),
    'source_header_pool_selector': (0x60701148, 0x60701158),
    'source_destination_branch': (0x6071184a, 0x60711868),
    'source_destination_resource_class': (0x607118fa, 0x6071191d),
    'source_config_getter': (0x60714c3a, 0x60714c43),
    'source_pool_fhd_initialization': (0x607c4e79, 0x607c4ea0),
    'source_pool_uhd_initialization': (0x607c5e13, 0x607c5e3a),
    'source_pool_constructor_arguments': (0x607c756e, 0x607c758f),
    'source_pool_base_constructor': (0x607c6d44, 0x607c6d84),
    'source_pool_derived_vtable': (0x607c758f, 0x607c75a1),
    'source_pool_virtual_address': (0x607c7737, 0x607c777c),
    'source_pool_slot_state': (0x607c75e3, 0x607c7608),
    'source_movie_family_snapshot': (0x6070108a, 0x60701090),
    'source_movie_family_forward': (0x606ff223, 0x606ff22b),
    'source_config_send_call': (0x6072848e, 0x6072849b),
    'source_config_message_fields': (0x60723d35, 0x60723d65),
    'source_command_to_event': (0x6072af5b, 0x6072af8b),
    'source_config_event': (0x6072afd1, 0x6072afdc),
    'source_state_event_dispatch': (0x6072b209, 0x6072b231),
    'source_config_receive_call': (0x6072bef1, 0x6072befe),
    'source_config_publish_call': (0x60713889, 0x6071388f),
    'source_config_producer_call': (0x6072a2e5, 0x6072a2ea),
    'resource_class_allocate': (0x607c5453, 0x607c553e),
    'resource_class_address': (0x607c56b5, 0x607c5793),
    'resource_diagnostic_gate': (0x607c4671, 0x607c4695),
    'resource_object_diagnostic_flag': (0x607c713d, 0x607c7143),
    'resource_free_count': (0x607c7094, 0x607c709a),
    'resource_object_allocate': (0x607c6dcd, 0x607c6ea7),
    'resource_slot_acquire': (0x607c78e7, 0x607c7913),
    'resource_slot_query_entry': (0x607c75e1, 0x607c75e3),
    'recording_source_prepare_command': (0x6067b070, 0x6067b081),
    'processing_command16_mapping': (0x6072374f, 0x6072375c),
    'processing_state_table_select': (0x60723a96, 0x60723ab1),
    'processing_second_callback': (0x60723b23, 0x60723b32),
    'processing_ready_state2': (0x60728e83, 0x60728e89),
    'resource_class_release': (0x607c554a, 0x607c5637),
    'resource_object_release': (0x607c6ea7, 0x607c6f5f),
    'resource_slot_release': (0x607c7913, 0x607c7954),
    'image_work_mode_busy_count': (0x607c6075, 0x607c6093),
    'image_work_object_busy_count': (0x607c3fef, 0x607c3ffb),
    'image_work_mode_table_select': (0x607c6130, 0x607c6141),
    'image_work_mode_constructors': (0x607c6405, 0x607c6443),
    'source_return_reference_gate': (0x607116e9, 0x60711724),
    'source_eligible_slot_sweep': (0x60711b32, 0x60711b78),
    'codec_conditional_count': (0x6169e6a9, 0x6169e6e2),
    'source_final_sweep_gate': (0x60711c5f, 0x60711c7f),
    'source_stop_prepare_call': (0x6072c820, 0x6072c82d),
    'source_stop_processing_call': (0x6072c84d, 0x6072c85a),
    'source_stop_cleanup_call': (0x6072c87a, 0x6072c887),
}
ANCHORS = {
    0x6169f34e: 'mov\t(a2),d0',
    0x6169f34f: 'cmp\t135000000,d0',
    0x6169f35b: 'cmp\t50000000,d0',
    0x6169f37d: 'cmp\t20000000,d0',
    0x6169f395: 'cmp\t1920,d0',
    0x6169f39d: 'mov\t(52,a0),d0',
    0x6169f3a0: 'cmp\t5000,d0',
    0x6169f3a6: 'bra\t0x6169f40c',
    0x6169f377: 'mov\t7,d0',
    0x6169f3f6: 'mov\t8,d0',
    0x6169f411: 'mov\t6,d0',
    0x6169f43d: 'mov\td0,(a1)',
    0x6169f443: 'add\t1116,a3',
    0x6169f456: 'mov\t(a0),d1',
    0x6169f457: 'mov\t(4,a0),d0',
    0x6169f45a: 'mov\td1,(a2)',
    0x6169f45b: 'mov\td0,(4,a2)',
    0x6169f465: 'mov\td0,(16,a3)',
    0x6169f48f: 'mov\t(a1),d0',
    0x6169f490: 'mov\td0,(40,a3)',
    0x6169f501: 'call\t0x616a27a3,[d2,d3,a2,a3],240',
    0x616a2818: 'mov\t(16,a0),d0',
    0x616a281b: 'cmp\t3000,d0',
    0x616a2828: 'cmp\t2160,d0',
    0x616a283e: 'mov\t1648082896,d0',
    0x616a285a: 'mov\t1648080604,d0',
    0x616a2868: 'mov\t1648082132,d0',
    0x616a2830: 'mov\t1648081368,d0',
    0x616a2a40: 'mov\t16,d3',
    0x616a2a45: 'mov\t(8,a0),d0',
    0x616a2a4a: 'divu\td3,d0',
    0x616a2a7d: 'mov\td0,(a0)',
    0x616a2a85: 'mov\t(12,a0),d0',
    0x616a2aba: 'mov\td1,(a0)',
    0x616a2ac3: 'udf01\td1,d0',
    0x616a2ac8: 'mov\td0,(3612,a0)',
    0x616a2fbe: 'mov\t(40,a0),d0',
    0x616a2fc1: 'cmp\t7,d0',
    0x616a42b4: 'mov\t(40,a0),d0',
    0x616a42c8: 'jmp\t(a0)',
    0x616a42ee: 'mov\t522240,a2',
    0x616a42f6: 'mov\t589824,a2',
    0x616a4300: 'mov\t983040,a2',
    0x616a430c: 'cmp\t2160,d0',
    0x616a4312: 'mov\t2,d3',
    0x616a439e: 'cmp\t7,d0',
    0x616a43a5: 'mov\t(3612,a0),d1',
    0x616a43af: 'divu\td3,d1',
    0x616a43b1: 'asl\t3,d1',
    0x607bd6fb: 'mov\t(16,a2),d1',
    0x607bd70b: 'mov\t(20,a2),d1',
    0x607bd71b: 'mov\t(24,a2),d1',
    0x607bd72b: 'mov\t(28,a2),d1',
    0x607bb571: 'movbu\t(a0),d0',
    0x607bb59d: 'mov\t3840,d0',
    0x607bb5ed: 'mov\t1920,d0',
    0x607bb5f3: 'mov\t1080,d0',
    0x607bb5ff: 'mov\td0,(56,a2)',
    0x607bb60e: 'mov\t4096,d0',
    0x607bb61c: 'mov\td0,(24,a2)',
    0x607bb622: 'mov\td0,(28,a2)',
    0x607bb727: 'mov\t5994,d0',
    0x607bb72a: 'mov\td0,(60,a2)',
    0x607bb739: 'mov\td0,(64,a2)',
    0x607b9b70: 'movbu\t(2,a2),d0',
    0x607b9b73: 'cmp\t6,d0',
    0x6164c46b: 'sub\td3,d1',
    0x6164c476: 'jmp\t(a0)',
    0x6164c47b: 'call\t0x6164c619,[a2,a3],12',
    0x616602d8: 'mov\t(16,a1),d0',
    0x616602db: 'mov\td0,(32,sp)',
    0x616602dd: 'mov\t(20,a1),d0',
    0x616602e0: 'mov\td0,(36,sp)',
    0x616603f6: 'mov\t(56,a0),d0',
    0x616603fb: 'mov\t(60,a0),d0',
    0x61660435: 'mov\t(24,a0),d0',
    0x6166043a: 'mov\t(28,a0),d0',
    0x616b0336: 'sub\td1,d0',
    0x616b033a: 'beq\t0x616b035b',
    0x616b036a: 'mov\td0,(88,sp)',
    0x616b036e: 'mov\td0,(84,sp)',
    0x616b0370: 'mov\ta2,(112,sp)',
    0x6072557b: 'mov\t1920,d0',
    0x60725580: 'mov\t1080,d0',
    0x60725585: 'mov\t2088960,d0',
    0x607255c1: 'mov\td0,(20,sp)',
    0x607255f5: 'mov\td0,(116,sp)',
    0x607255fc: 'mov\td0,(124,sp)',
    0x6072562d: 'movhu\td0,(142,sp)',
    0x6074da0b: 'and\t-32,d2',
    0x6074da14: 'movhu\td2,(222,sp)',
    0x6074da1c: 'movhu\td0,(226,sp)',
    0x6074da3b: 'add\td2,d2',
    0x6074da3c: 'mov\td2,(284,sp)',
    0x6073a39e: 'mov\td0,(0x9cb00380)',
    0x6073a41a: 'mov\td0,(0x9cb00084)',
    0x6073a42b: 'mov\td0,(0x9cb0036c)',
    0x60749192: 'mov\t1619783724,a0',
    0x6074919a: 'mov\t1619783730,a0',
    0x607491b1: 'udfu01\t6,d0',
    0x607491b6: 'add\t1619783736,a0',
    0x6074fd98: 'cmp\t4,d0',
    0x6074fda4: 'cmp\t7,d0',
    0x6074fdc4: 'call\t0x60749187,[],0',
    0x6074fdcd: 'call\t0x60749187,[],0',
    0x6074fdde: 'movhu\td2,(a3)',
    0x6074fdf1: 'movhu\td0,(a1)',
    0x607509d7: 'call\t0x607a3c9e,[d2],4',
    0x607509fd: 'call\t0x60749187,[],0',
    0x60750a60: 'mov\t1920,d0',
    0x60750a67: 'mov\t1080,d0',
    0x60750ae7: 'movbu\t(18,a0),d2',
    0x60750af3: 'call\t0x607509cd,[d2,d3,a2,a3],24',
    0x6091a1c3: 'movbu\t(3,a1),d0',
    0x6091a1c6: 'movbu\td0,(30,a0)',
    0x606fca00: 'mov\t-1565600396,a1',
    0x606fca3f: 'mov\t-1565600396,a1',
    0x60708d87: 'call\t0x6070899c,[],0',
    0x60708d97: 'cmp\t6,d0',
    0x60708db1: 'mov\t4,d2',
    0x60708e05: 'mov\t(a1),d0',
    0x60708e6b: 'mov\t48,a3',
    0x60708f45: 'movhu\td2,(a0)',
    0x60706650: 'call\t0x6071d49d,[],16',
    0x60706659: 'movbu\td0,(a3)',
    0x607066e9: 'movbu\td0,(18,a0)',
    0x60706784: 'movbu\td0,(21,a0)',
    0x6071b7ac: 'movhu\t(16,a2),d0',
    0x6071b7d8: 'movbu\t(24,a2),d0',
    0x6071b7de: 'movbu\t(25,a2),d0',
    0x6071b7e1: 'movbu\td0,(66,sp)',
    0x60750aec: 'movbu\t(30,a0),d2',
    0x607509d4: 'movbu\t(36,sp),d1',
    0x6074e02f: 'mov\td2,a3',
    0x60708993: 'mov\td0,(0x62a24d14)',
    0x60726f25: 'mov\t1,d0',
    0x60726f27: 'call\t0x60708993,[],0',
    0x60727aee: 'mov\t1,d0',
    0x60727af0: 'call\t0x60708993,[],0',
    0x60727eb5: 'clr\td0',
    0x60727eb6: 'call\t0x60708993,[],0',
    0x60728fb4: 'clr\td0',
    0x60728fb5: 'call\t0x60708993,[],0',
    0x6091a095: 'mov\t34,a0',
    0x6091a099: 'call\t0x6091a167,[],0',
    0x606ffe68: 'mov\t844,a0',
    0x606ffe6d: 'call\t0x606fca3f,[],0',
    0x6075083e: 'mov\t3,d0',
    0x60750841: 'call\t0x60749187,[],0',
    0x60701b03: 'call\t0x607031f0,[d2],32',
    0x60701b18: 'movbu\td0,(902,a0)',
    0x60925b0a: 'movbu\t(0x6261ea26),d0',
    0x60925b1d: 'call\t0x6043e62b,[d2,d3],12',
    0x6091b397: 'call\t0x60925b0a,[],4',
    0x6091b39e: 'movbu\td0,(0x62616d62)',
    0x6091b63c: 'movbu\t(0x62616d62),d0',
    0x6091b670: 'mov\td2,(16,sp)',
    0x6091b831: 'mov\td0,(4,a0)',
    0x6091b844: 'mov\td0,(332,a0)',
    0x60701a4f: 'mov\t(332,a0),d0',
    0x60701a55: 'mov\td0,(172,a0)',
    0x60715d3f: 'mov\t(172,a0),d0',
    0x606ff25c: 'mov\td0,(a2)',
    0x60715034: 'clr\td0',
    0x6072367f: 'call\t0x607246e1,[d2,d3,a2,a3],236',
    0x607247d7: 'cmp\t3,d0',
    0x607247f2: 'call\t0x60726d49,[d2,d3,a2,a3],16',
    0x60724a13: 'call\t0x60724e3d,[d2,d3,a2,a3],80',
    0x60724f4e: 'call\t0x60725229,[d2,d3,a2,a3],176',
    0x607254e4: 'cmp\t2,d0',
    0x6072554f: 'call\t0x6071184a,[d2,d3,a2,a3],156',
    0x60719c7a: 'mov\td0,(0xa2af4a00)',
    0x60719ce4: 'add\t-1537244480,d2',
    0x6091b7cd: 'call\t0x6091c079,[],0',
    0x6091b83d: 'movbu\td3,(20,a0)',
    0x607017dd: 'movbu\td0,(268,a0)',
    0x60701037: 'call\t0x60715dce,[d2,d3,a2,a3],56',
    0x60715df1: 'mov\t(4,a0),d0',
    0x60715dff: 'mov\t(d2,a1),a1',
    0x60715e1d: 'movbu\td0,(a2)',
    0x606ff280: 'call\t0x6071a1b9,[a2],8',
    0x6071a1ba: 'call\t0x605f0f9f,[],0',
    0x605f0f9f: 'mov\t(0xa2ae7b40),d0',
    0x60714ff2: 'movbu\t(800,a0),d2',
    0x60714ff6: 'movbu\t(268,a0),d0',
    0x60714ffa: 'mov\t(896,a0),d1',
    0x609237d0: 'mov\t34129,d0',
    0x609237e6: 'mov\t61473,d0',
    0x609237f7: 'mov\t61489,d0',
    0x605f0c77: 'call\t0x605f221d,[d2,d3,a2,a3],116',
    0x605f0c7e: 'call\t0x605f1262,[],4',
    0x60557d7e: 'mov\t2,d2',
    0x60727cbb: 'movbu\t(805,a3),d0',
    0x60727cc9: 'mov\t353280,d0',
    0x60727cd1: 'mov\t1382400,d0',
    0x60727cd9: 'mov\t3133440,d0',
    0x60727cdf: 'mov\td0,(0x62a25ca4)',
    0x60727ce5: 'mov\t119439360,d1',
    0x60727cee: 'divu\td0,d1',
    0x60727cf0: 'movhu\td1,(0x62a25ca8)',
    0x6168c1ff: 'mov\t(76,a3),d0',
    0x6168c204: 'movhu\td0,(16,a2)',
    0x6168c207: 'mov\t(72,a3),d0',
    0x6168c20a: 'movhu\td0,(18,a2)',
    0x6168c240: 'mov\td0,(a2)',
    0x6168c245: 'call\t0x604baf40,[a2,a3],8',
    0x6168c24c: 'movbu\td3,(a2)',
    0x6168c255: 'movbu\td0,(3,a2)',
    0x6168aeeb: 'cmp\t7,d0',
    0x6168af18: 'call\t0x604baf40,[a2,a3],8',
    0x6168af42: 'movbu\td0,(a1)',
    0x6168af49: 'movbu\td0,(a1)',
    0x6168af50: 'movbu\td0,(3,a0)',
    0x60728230: 'movbu\td0,(0x62a25cfc)',
    0x60728242: 'movbu\td0,(0x62a25cfd)',
    0x60728458: 'movhu\t(10,a0),d0',
    0x60714782: 'movhu\td0,(0xa2af3eb6)',
    0x6072c15c: 'movhu\t(58,a1),d1',
    0x60710c8e: 'mov\td1,(0xa2af3c80)',
    0x60715ee7: 'cmp\t8,d0',
    0x60715ef2: 'mov\t120,d2',
    0x60715ef8: 'mov\t240,d2',
    0x60715eff: 'mov\t480,d2',
    0x60711911: 'mov\t12032,d0',
    0x607c4e92: 'mov\t3133440,d1',
    0x607c4e98: 'mov\t12032,a1',
    0x607c5e2c: 'mov\t13271040,d1',
    0x607c7766: 'udf01\td0,d2',
    0x60728496: 'call\t0x60723d11,[d2,d3],84',
    0x60723d46: 'mov\td1,(72,sp)',
    0x60723d4a: 'mov\t16,d0',
    0x60723d4e: 'movhu\t(0x60421336),d0',
    0x6072af66: 'clr\td3',
    0x6072af81: 'mov\t1619766436,a0',
    0x6072b20b: 'mov\t1619762468,d0',
    0x6072b211: 'udfu01\t224,d1',
    0x6072bef3: 'mov\t(12,a0),a2',
    0x6072bef7: 'call\t0x6071382b,[d2,a2,a3],60',
    0x6071388a: 'call\t0x60714652,[],0',
    0x6072a2e5: 'call\t0x60728192,[d2,d3,a2,a3],84',
    0x6067b078: 'mov\t16,d1',
    0x6072374f: 'mov\t2,d3',
    0x60723a9b: 'udfu01\t304,d1',
    0x607c54b8: 'call\t0x607c6dcd,[d2,d3,a2,a3],40',
    0x607c6e53: 'movhu\td1,(a0)',
    0x607c6e5c: 'calls\t(a1)',
    0x607c6079: 'cmp\t2,d1',
    0x607c6080: 'mov\t1620085880,a0',
    0x607c608a: 'call\t0x607c3fef,[],0',
    0x607c3ff2: 'movhu\t(80,a0),d1',
    0x607c6131: 'cmp\t1,d3',
    0x607c6416: 'mov\t206209024,d1',
    0x607c6435: 'mov\t77328384,d1',
    0x607116f3: 'cmp\t1,d0',
    0x60711703: 'mov\td0,(8,a1)',
    0x60711715: 'add\t-1,d0',
    0x60711b4a: 'cmp\t1,d0',
    0x60711b55: 'call\t0x607195a6,[d2,d3,a2,a3],80',
    0x60711b74: 'cmp\t9,d3',
    0x6169e6bd: 'mov\t6,d0',
    0x6169e6ce: 'mov\t2,d0',
    0x60711c70: 'movhu\t(a2),d0',
    0x60711c7a: 'call\t0x607195a6,[d2,d3,a2,a3],80',
    0x6072c87a: 'call\t0x60711c3c,[d2,d3,a2,a3],64',
}

RATE_CLASS_TABLE = 0x617013f0
AVM_OPEN_WORDS = {
    0x6041cc2c: 0x1048, 0x6041cc38: 0x6164c388,
    0x616fac48: 0x6164c478, 0x616fd230: 0x61660cd1,
    0x616fd2f0: 0x6165ffa2, 0x61701600: 0x616a7e49,
}
IMAGE_JOB_WORDS = {
    0x608bae90: 0x6072fd27, 0x608bb0d8: 0x60734479,
    0x608baec0: 0x6072fdd6, 0x608b4850: 0x606fbcf1,
}
DIMENSION_SWITCH_WORDS = {
    0x608f2118: 0x607509f8, 0x608f211c: 0x60750a78,
    0x608f2120: 0x60750a7a, 0x608f2124: 0x60750a7a,
    0x608f2128: 0x60750a13, 0x608f212c: 0x60750a1e,
    0x608f2130: 0x60750a47, 0x608f2134: 0x60750a6e,
    0x608f2138: 0x60750a7a, 0x608f213c: 0x60750a7a,
}
PROCESSING_CONTEXT_WORDS = {
    0x608b8204: 0x6071d4b8,  # J+902=6 -> classifier context 14
    0x608b8208: 0x6071d4bc,  # J+902=7 -> classifier context 16
    0x608b8220: 0x6071d4dc,  # J+902=13 -> classifier context 21
}
SOURCE_RESOURCE_WORDS = {
    0x608baca4: 0x6072afd1,  # MoRS command 1 -> event 0
    0x608b9d24: 0x6072beb8,  # source state 0/event 0 -> configuration handler
    0x608b8b20: 0x6072a2e0,  # processing state-table handler -> G producer
    0x60908ad4: 0x2f00, 0x60908ad8: 0xa2a5a220,
    0x60908c0c: 0x5600, 0x60908c10: 0xa2a5ba78,
    0x60908f8c: 0x607c7737,  # resource virtual +8: address from handle
    0x608b9ad4: 0x60723740,  # public command 16 -> event 2
    0x608b8b1c: 0,           # state 2/event 2 first callback
    0x60908f94: 0x607c7094,
    0x60908fb0: 0x607c75e1,
    0x60908fb4: 0x607c78e7,
    0x6092c684: 0x607c4df1, # FHD pool constructor group
    0x6092c694: 0x607c5deb, # 4K pool constructor group
    0x60908fb8: 0x607c7913,
    0x60908c78: 0xa2a5c0ac,
    0x60908c7c: 0xa2a5c100,
    0x608ba448: 0x6072c7f6, # source state 8/event 4 second callback
}


def probe_source_configuration(code, preset, rate_property, layout):
    """Join source setup copies on shared memory, with explicit property input.

    These are supplied J/metadata values, not a reconstructed FHD60 session.
    RTOS dispatch, hardware and resource allocation are outside this probe.
    """
    sp, state, metadata, start_params = 0x10001000, 0x10002000, 0x10003000, 0x10004000
    config, live, flags = 0x62a25cfc, 0xa2af3e7c, 0xa2af3e6a
    mem = Memory([
        Region(sp-512,bytearray(1024),True,'host native stack'),
        Region(state,bytearray(1020),True,'synthetic J'),
        Region(metadata,bytearray(108),True,'synthetic movie metadata'),
        Region(start_params,bytearray(32),True,'synthetic source start request'),
        Region(config,bytearray(136),True,'host source configuration G'),
        Region(0xa2af3ab8,bytearray(2048),True,'host source/live globals'),
    ])
    mem.write(metadata+29,3,1)  # Explicit family, not inferred from fps.
    mem.write(state+794,preset,1)
    mem.write(state+874,layout,1)
    mem.write(state+822,2,2)
    mem.write(state+824,1,1)
    mem.write(state+798,100,2)  # Neutral test value: units not asserted.
    mem.write(state+291,1,1)
    mem.write(state+292,2,1)
    stages = []

    def fragment(entry,stop,registers):
        m = CallMachine(code,mem,dict(sp=sp,**registers))
        result = m.run(entry,[stop])
        if result['status'] != 'stop' or m.r['sp'] != sp:
            raise ValueError(f'source configuration fragment {entry:#x}: {result}')
        stages.append(dict(entry=hex(entry),stop=hex(stop),trace=[hex(pc) for pc in m.trace]))
        return m

    fragment(0x6070108a,0x60701090,dict(a3=metadata,a2=state+690))
    fragment(0x606ff223,0x606ff22b,dict(a0=state+690,a2=state+808,d2=state))
    m = CallMachine(code,mem,dict(sp=sp,a2=state+660,a3=state+794,d3=0))
    result = m.run(0x60701148,[0x60701158])
    queried = result['status'] == 'external_call'
    if queried:
        if (result['pc'],result['target'],m.r['d0'],m.r['d1']) != (
                0x60715eda,0x6043e62b,0xf072,8):
            raise ValueError(f'unexpected special-preset property boundary: {result}')
        # The property service is not emulated; inject its declared return.
        m.r['d0'] = rate_property
        result = m.run(0x60715ee1,[0x60701158])
    if result['status'] != 'stop' or m.r['sp'] != sp:
        raise ValueError(f'special-preset selector did not return: {result}')
    selector = {25:120,12:240,6:480}[rate_property] if preset == 8 else 0
    if mem.read(state+670,2) != selector or queried != (preset == 8):
        raise ValueError('preset-to-pool selector changed')
    stages.append(dict(entry='0x60701148',property_return_injected=queried,
                       trace=[hex(pc) for pc in m.trace]))

    mem.write(sp+28,state,4)
    mem.write(sp+36,state+660,4)
    fragment(0x60728227,0x60728294,{})
    # Family 3 follows this direct halfword copy; family 1 has another service.
    fragment(0x607282b3,0x607282bc,dict(a1=state+808))
    fragment(0x60714652,0x607146b4,dict(a0=config))
    fragment(0x6072843a,0x6072846d,dict(a3=state+690))
    fragment(0x6071475c,0x6071479a,dict(a0=sp+52))
    m = fragment(0x6072c14a,0x6072c160,dict(a2=start_params))
    if m.r['d1'] != selector:
        raise ValueError('live context selector not forwarded to source start')
    fragment(0x60710c74,0x60710c94,dict(d0=m.r['d0'],d1=m.r['d1'],a0=m.r['a0']))
    m = Machine(code,mem,dict(sp=sp,a0=start_params,d0=0))
    result = m.run(0x6071184a,[0x60711868,0x607118e6])
    cyclic = result['pc'] == 0x60711868
    if result['status'] != 'stop' or cyclic != bool(selector):
        raise ValueError('source destination pool branch changed')
    resource_class = None
    if not cyclic:
        m = fragment(0x607118fa,0x60711918,{})
        resource_class = mem.read(sp+84,2)
        if resource_class != (0x5600 if layout == 8 else 0x2f00):
            raise ValueError('source resource class changed')

    # Conditional raster consumer uses the same F published above.
    mem.write(sp+32,flags,4)
    mem.write(sp+108,0x20000000,4)
    mem.write(sp+76,0x21000000,4)
    fragment(0x60725560,0x607255c3,{})
    fragment(0x607255eb,0x60725650,{})
    raster = [mem.read(sp+offset,2) for offset in (132,134)]
    delta = mem.read(sp+116,4)-mem.read(sp+112,4)
    if (raster,delta) != (([3840,2160],8294400) if layout == 8 else ([1920,1080],2088960)):
        raise ValueError('published source configuration did not reach raster')
    return dict(synthetic_preset=preset,synthetic_f051_family=3,
                synthetic_f072_return=rate_property if queried else None,
                synthetic_camera_header_kind=layout,property_service_executed=False,
                selector=selector,j670=mem.read(state+670,2),
                live58=mem.read(live+58,2),pool_gate=mem.read(0xa2af3c80,4),
                f0=mem.read(flags,1),f1=mem.read(flags+1,1),
                cyclic_pool_selected=cyclic,resource_class=resource_class,
                conditional_raster=raster,luma_plane_delta=delta,stages=stages,
                raster_acceptance_gates_executed=False,rtos_dispatch_executed=False,
                ordinary_fhd60_binding_verified=False,allocation_executed=False)


def probe_resource_pool_definition(code, resource_class, key):
    """Native constructor arguments/field stores and virtual address method.

    Stops before the constructor's memset dependency, then runs a separate
    native vtable-store fragment. Slot occupancy is a synthetic input.
    """
    sp, output = 0x10001000, 0x10002000
    obj = 0xa2a5a220 if resource_class == 0x2f00 else 0xa2a5ba78
    mem = Memory([Region(sp-512,bytearray(1024),True,'host native stack'),
                  Region(obj,bytearray(476),True,'host resource object'),
                  Region(output,bytearray(4),True,'host address output')])
    m = Machine(code,mem,dict(sp=sp))
    entry,stop = ((0x607c4e79,0x607c4e9b) if resource_class == 0x2f00 else
                  (0x607c5e13,0x607c5e35))
    if m.run(entry,[stop])['status'] != 'stop':
        raise ValueError('resource pool initializer did not reach constructor')
    args = dict(base=m.r['d0'],stride=m.r['d1'],kind=m.r['a1'],count=mem.read(sp+4,2))
    if m.r['a0'] != obj or args != dict(base=0xa45f82c0,
            stride=3133440 if resource_class == 0x2f00 else 13271040,
            kind=resource_class,count=9):
        raise ValueError('resource pool constructor arguments changed')
    constructor = CallMachine(code,mem,dict(sp=sp,**{k:m.r[k] for k in ('a0','a1','d0','d1')}))
    result = constructor.run(constructor.enter(0x607c756e,0x0badf00d,0xa0,32),[0x607c6d83])
    if result['status'] != 'stop':
        raise ValueError(f'resource base constructor failed: {result}')
    if (mem.read(obj+8,4),mem.read(obj+12,4),mem.read(obj+22,2),mem.read(obj+24,2)) != (
            args['base'],args['stride'],resource_class,9):
        raise ValueError('resource pool base constructor fields changed')
    derived = Machine(code,mem,dict(a0=obj))
    if derived.run(0x607c758f,[0x607c75a1])['status'] != 'stop':
        raise ValueError('resource pool derived vtable store failed')
    mem.write(obj+64,(1 << (key-1)) if 1 <= key <= 9 else 0,4)
    address = CallMachine(code,mem,dict(sp=sp,a0=obj,a1=output,d0=resource_class+key))
    result = address.run(address.enter(0x607c773c,0x0badf00d,0xb0,16),[0x0badf00d])
    # This method can calculate an address with status 2 for an unowned or
    # out-of-count slot. Only status 0 denotes the supplied allocated slot.
    expected = args['base']+(key-1)*args['stride'] if 1 <= key <= 192 else 0
    expected_status = 0 if 1 <= key <= 9 else 2 if expected else 4
    if result['status'] != 'stop' or address.r['d0'] != expected_status or mem.read(output,4) != expected:
        raise ValueError('native resource slot address/bounds changed')
    return dict(resource_class=hex(resource_class),object=hex(obj),**args,
                synthetic_slot=key,address=hex(mem.read(output,4)),
                native_address_status=address.r['d0'],
                initializer_trace=[hex(pc) for pc in m.trace],
                constructor_trace=[hex(pc) for pc in constructor.trace],
                address_trace=[hex(pc) for pc in address.trace],
                full_constructor_executed=False,allocation_executed=False,
                ordinary_fhd60_binding_verified=False,
                packed_1920x1440_yuv420_bytes=4147200,
                target_tight_frame_fits_stride=4147200 <= args['stride'])


def probe_resource_alias_allocation(code, image, order, image_work_mode=0):
    """Execute the real manager/virtual allocation with host constructor state.

    No RTOS startup, mutex, pixel writes or physical recording is modeled.
    Both initialized objects are deliberately made available together to
    determine whether these allocator leaves enforce cross-class exclusion.
    """
    sp, output = 0x10001000, 0x10003000
    rom = 0x6090895c
    objects = {0x2f00:0xa2a5a220,0x5600:0xa2a5ba78}
    strides = {0x2f00:3133440,0x5600:13271040}
    mem = Memory([
        Region(sp-2048,bytearray(4096),True,'host native call stack'),
        Region(output,bytearray(8),True,'host handle/address outputs'),
        Region(rom,bytearray(image[rom-BASE:0x60908fc0-BASE]),False,'verified registry/vtable'),
        Region(0xa2a58524,bytearray(8),True,'host diagnostic flags disabled'),
        Region(0xa2a5c0a4,bytearray(8),True,'host image-work mode snapshot'),
        *[Region(obj,bytearray(476),True,'host initialized resource object') for obj in objects.values()],
    ])
    mem.write(0xa2a5c0a4,image_work_mode,2)
    mem.write(0xa2a5c0a6,image_work_mode,2)
    # Explicit snapshots of fields checked by probe_resource_pool_definition.
    # Zero bitmap/reference bytes correspond to the constructor's clear state.
    for kind,obj in objects.items():
        for offset,value,size in ((0,0x60908f84,4),(8,0xa45f82c0,4),
                                  (12,strides[kind],4),(20,9,2),(22,kind,2),(24,9,2)):
            mem.write(obj+offset,value,size)
    rows = []
    for kind in order:
        allocation = CallMachine(code,mem,dict(sp=sp,a0=output,d0=kind))
        result = allocation.run(allocation.enter(0x607c5453,0x0badf00d,0xf0,40),[0x0badf00d])
        if result['status'] != 'stop' or allocation.r['d0']:
            raise ValueError(f'resource allocation failed: {result}')
        handle = mem.read(output,2)
        address = CallMachine(code,mem,dict(sp=sp,d0=handle))
        result = address.run(address.enter(0x607c56b5,0x0badf00d,0xf0,40),[0x0badf00d])
        if result['status'] != 'stop' or address.r['d0'] == 0:
            raise ValueError(f'resource address resolution failed: {result}')
        slot = (handle & 255)-1
        expected = 0xa45f82c0+slot*strides[kind]
        if address.r['d0'] != expected:
            raise ValueError('resource manager resolved unexpected slot address')
        rows.append(dict(resource_class=hex(kind),handle=hex(handle),address=hex(expected),
                         slot_stride=strides[kind],free_count=mem.read(objects[kind]+20,2),
                         allocation_trace=[hex(pc) for pc in allocation.trace],
                         address_trace=[hex(pc) for pc in address.trace]))
    if rows[0]['address'] != rows[1]['address']:
        raise ValueError('expected independent class bitmaps to allocate the shared base')
    release_rows = []
    for row in reversed(rows):
        kind,handle = int(row['resource_class'],16),int(row['handle'],16)
        release = CallMachine(code,mem,dict(sp=sp,d0=handle,a0=output+4))
        result = release.run(release.enter(0x607c554a,0x0badf00d,0xf0,36),[0x0badf00d])
        if result['status'] != 'stop' or release.r['d0'] or mem.read(objects[kind]+20,2) != 9:
            raise ValueError(f'resource release failed: {result}')
        release_rows.append(dict(handle=hex(handle),free_count=9,
                                 trace=[hex(pc) for pc in release.trace]))
    return dict(synthetic_class_order=[hex(k) for k in order],allocations=rows,
                synthetic_image_work_mode=image_work_mode,
                releases=release_rows,
                both_allocations_succeeded=True,first_slots_alias=True,
                cross_class_exclusion_in_these_leaves=False,
                initialized_objects_are_host_snapshots=True,
                ordinary_session_coallocation_observed=False,pixels_written=False,
                lifecycle_and_external_exclusion_verified=False)


def probe_source_return_reference(code,refs,selected,index):
    table=0xa2af3ac8
    mem=Memory([Region(table,bytearray(108),True,'host nine source records'),
                Region(0xa2af3c64,bytearray(10),True,'host source references/selection')])
    mem.write(table+index*12+8,2,4)
    mem.write(0xa2af3c64+index,refs,1)
    mem.write(0xa2af3c6d,selected,1)
    m=Machine(code,mem,dict(a1=table+index*12,a2=index,d1=index))
    result=m.run(0x607116e9,[0x60711724])
    expected_refs=max(0,refs-1)
    expected_flag=1 if refs<=1 and index!=selected else 2
    if result['status']!='stop' or mem.read(0xa2af3c64+index,1)!=expected_refs or mem.read(table+index*12+8,4)!=expected_flag:
        raise ValueError('source last-return/retained-frame condition changed')
    return dict(synthetic_refs=refs,synthetic_index=index,synthetic_selected=selected,
                remaining_refs=expected_refs,record_flag=expected_flag,
                eligible_for_sweep=expected_flag==1,
                trace=[hex(pc) for pc in m.trace],ordinary_fhd60_binding_verified=False)


def probe_source_release_sweep(code,index,flag):
    sp,table=0x10001000,0xa2af3ac8
    mem=Memory([Region(sp,bytearray(128),True,'host sweep stack'),
                Region(table,bytearray(108),True,'host source records')])
    for i in range(9):
        mem.write(table+i*12,0x2f01+i,2)
        mem.write(table+i*12+8,2,4)
    mem.write(table+index*12+8,flag,4)
    m=Machine(code,mem,dict(sp=sp))
    result=m.run(0x60711b32,[0x60711b55,0x60711b78])
    eligible=result['pc']==0x60711b55
    if eligible!=(flag==1): raise ValueError('source sweep release gate changed')
    if eligible and mem.read(sp+38,2)!=0x2f01+index:
        raise ValueError('source sweep selected a different handle')
    return dict(synthetic_index=index,synthetic_record_flag=flag,
                native_release_call_reached=eligible,
                trace=[hex(pc) for pc in m.trace],release_service_executed=False)


def probe_codec_conditional_count(code,c200,c100,c168,c156,c56,c216):
    obj=0x10001000
    mem=Memory([Region(obj,bytearray(224),True,'host codec configuration')])
    for offset,value in ((200,c200),(100,c100),(168,c168),(156,c156),(56,c56),(216,c216)):
        mem.write(obj+offset,value,4)
    m=Machine(code,mem,dict(a0=obj))
    result=m.run(0x6169e6a9,[0x6169e6df])
    expected=(2 if not c168 and c156==1 and c56==0 else 6) if c200==1 and c100!=2 else 0
    expected*=2 if c216==1 else 1
    if result['status']!='stop' or m.r['d0']!=expected:
        raise ValueError('codec conditional count changed')
    return dict(synthetic_fields={str(k):v for k,v in ((200,c200),(100,c100),(168,c168),(156,c156),(56,c56),(216,c216))},
                returned_count=expected,count_is_raw_input_hold_bound_verified=False)


def probe_source_final_cleanup_gate(code,flag,refs):
    sp,table=0x10001000,0xa2af3ac8
    mem=Memory([Region(sp,bytearray(128),True,'host cleanup stack'),
                Region(table,bytearray(108),True,'host source records'),
                Region(0xa2af3c64,bytearray(10),True,'host references/retained index')])
    mem.write(table,0x2f01,2);mem.write(table+8,flag,4)
    mem.write(0xa2af3c64,refs,1);mem.write(0xa2af3c6d,0,1)
    m=Machine(code,mem,dict(sp=sp))
    result=m.run(0x60711c5f,[0x60711c7a])
    if result['status']!='stop' or mem.read(sp+34,2)!=0x2f01:
        raise ValueError('final source cleanup gate changed')
    return dict(synthetic_record_flag=flag,synthetic_refs=refs,selected_slot=0,
                native_release_call_reached=True,checks_refs_or_selected_before_release=False,
                release_service_executed=False,trace=[hex(pc) for pc in m.trace])


def probe_repacked_fhd_pool(code):
    """Candidate only: native leaf lifecycle with six host-configured slots.

    This changes host object fields, not firmware instructions. It does not
    prove the movie pipeline accepts six in-flight buffers or a 1440 raster.
    """
    sp,obj,out = 0x10001000,0x10003000,0x10004000
    mem=Memory([Region(sp-2048,bytearray(4096),True,'host call stack'),
                Region(obj,bytearray(476),True,'candidate FHD pool snapshot'),
                Region(out,bytearray(8),True,'host native outputs'),
                Region(0x60908f84,bytearray(64),True,'verified virtual methods')])
    for offset,method in ((16,0x607c7094),(44,0x607c75e1),
                          (48,0x607c78e7),(52,0x607c7913)):
        mem.write(0x60908f84+offset,method,4)
    for offset,value,size in ((0,0x60908f84,4),(8,0xa45f82c0,4),(12,4147200,4),
                              (20,6,2),(22,0x2f00,2),(24,6,2)):
        mem.write(obj+offset,value,size)
    def run(entry,mask,frame,**regs):
        m=CallMachine(code,mem,dict(sp=sp,**regs))
        result=m.run(m.enter(entry,0x0badf00d,mask,frame),[0x0badf00d])
        if result['status']!='stop' or m.r['sp']!=sp:
            raise ValueError(f'candidate pool native fragment failed: {result}')
        return m
    handles,addresses=[],[]
    for i in range(7):
        m=run(0x607c6dcd,0xf0,40,a0=obj,a1=out)
        if m.r['d0'] != (0 if i<6 else 1):
            raise ValueError('candidate pool capacity control changed')
        if i<6:
            handle=mem.read(out,2);handles.append(handle)
            run(0x607c773c,0xb0,16,a0=obj,a1=out+4,d0=handle)
            addresses.append(mem.read(out+4,4))
    if handles != list(range(0x2f01,0x2f07)):
        raise ValueError('candidate FHD handles changed')
    for handle in handles:
        m=run(0x607c6ea7,0xc0,36,a0=obj,a1=0,d0=handle)
        if m.r['d0']:
            raise ValueError('candidate FHD native release failed')
    if mem.read(obj+20,2)!=6 or mem.read(obj+64,4):
        raise ValueError('candidate FHD pool was not fully released')
    m=run(0x607c6dcd,0xf0,40,a0=obj,a1=out)
    if m.r['d0'] or mem.read(out,2)!=0x2f01:
        raise ValueError('candidate FHD pool did not recycle first slot')
    target_end=addresses[-1]+4147200
    stock_end=0xa45f82c0+9*3133440
    if target_end>stock_end:
        raise ValueError('candidate extends the original FHD footprint')
    return dict(candidate_only=True,host_stride=4147200,host_count=6,
                native_handles=[hex(v) for v in handles],
                native_addresses=[hex(v) for v in addresses],
                seventh_allocation_native_status=1,release_and_recycle_passed=True,
                target_extent=24883200,stock_extent=28200960,
                unused_stock_extent=stock_end-target_end,
                movie_accepts_six_slots_verified=False,full_field_60_verified=False,
                external_ownership_verified=False,firmware_modified=False)


def probe_image_work_busy(code,image,index,busy):
    sp=0x10001000
    rom=0x60908c78
    mem=Memory([Region(sp-64,bytearray(128),True,'host stack'),
                Region(rom,bytearray(image[rom-BASE:rom-BASE+8]),False,'verified image-work pointers'),
                Region(0xa2a5c0ac,bytearray(168),True,'host ART/ISO working objects')])
    for obj in (0xa2a5c0ac,0xa2a5c100):
        mem.write(obj+16,12,2);mem.write(obj+80,12-busy,2)
    m=CallMachine(code,mem,dict(sp=sp,d0=index))
    result=m.run(m.enter(0x607c6075,0x0badf00d,0x80,8),[0x0badf00d])
    expected=busy if index<2 else 0
    if result['status']!='stop' or m.r['d0']!=expected:
        raise ValueError('image-work busy-count semantics changed')
    return dict(synthetic_index=index,synthetic_busy=busy,returned_count=m.r['d0'],
                trace=[hex(pc) for pc in m.trace],checks_video_class_bitmaps=False)


def probe_tft_recording_control(code, image, state_value):
    """Bind a public recording command to the MaRS second callback boundary."""
    sp, state = 0x10001000, 0x10002000
    table_at = 0x608b88ac
    mem = Memory([Region(sp,bytearray(256),True,'host fragment stack'),
                  Region(state,bytearray(64),True,'host MaRS state'),
                  Region(table_at,bytearray(image[table_at-BASE:table_at-BASE+4*304]),False,'verified MaRS ROM'),
                  Region(0x60421332,bytearray(2),True,'host queue ID')])
    mem.write(0x60421332,123,2)
    mem.write(state,state_value,2)
    sender = Machine(code,mem,dict(sp=sp,a3=state))
    if sender.run(0x6067b070,[0x6067b07a])['status'] != 'stop' or sender.r['d1'] != 16:
        raise ValueError('recording prepare command changed')
    mapper = Machine(code,mem,dict(sp=sp))
    if mapper.run(0x6072374f,[0x60723751])['status'] != 'stop' or mapper.r['d3'] != 2:
        raise ValueError('recording event mapping changed')
    select = Machine(code,mem,dict(sp=sp,d3=state,d2=mapper.r['d3']))
    if select.run(0x60723a96,[0x60723ab1,0x60723ad1])['status'] != 'stop':
        raise ValueError('MaRS state selection failed')
    first = select.r['d0']
    second = Machine(code,mem,dict(sp=sp,a2=select.r['a2']))
    if second.run(0x60723b23,[0x60723b29,0x60723b5b])['status'] != 'stop':
        raise ValueError('MaRS second callback selection failed')
    expected = 0x6072a2e0 if state_value == 2 else 0
    if first or second.r['d0'] != expected:
        raise ValueError('recording source setup callback/state guard changed')
    return dict(synthetic_state=state_value,command=16,event=2,
                first_callback=hex(first),second_callback=hex(second.r['d0']),
                actual_property_values_verified=False,ordinary_fhd60_binding_verified=False)


def probe_dispatch_producers(code, image, aux_kind, f161, display_mask):
    """Replay actual J+268/+800/+896 producers using host property cells.

    The property registry's pointers, descriptor and device mask are explicit
    inputs. Camera callbacks and physical display setup do not execute.
    """
    sp, state, owner, auxiliary = 0x10001000, 0x10002000, 0x10003000, 0x10004000
    cells, table_at, pointers = 0x10005000, 0x608b5afc, 0xa2aefe7c
    table = image[table_at-BASE:table_at-BASE+25*8]
    mem = Memory([
        Region(sp-1024,bytearray(2048),True,'host native call stack'),
        Region(state,bytearray(1020),True,'synthetic J'),
        Region(owner,bytearray(400),True,'synthetic P'),
        Region(auxiliary,bytearray(80),True,'synthetic D+8 record'),
        Region(cells,bytearray(25*4),True,'host scalar property values'),
        Region(table_at,bytearray(table),False,'verified settings-copy ROM'),
        Region(pointers,bytearray(25*4),True,'host property registry pointers'),
        Region(0xa2ae7b40,bytearray(4),True,'host display-open device mask'),
    ])
    for index in range(25):
        mem.write(pointers+index*4,cells+index*4,4)
    mem.write(cells+20*4,f161,1)
    mem.write(0xa2ae7b40,display_mask,4)
    mem.write(sp+20,0 if aux_kind is None else auxiliary,4)
    if aux_kind is not None:
        mem.write(auxiliary+74,aux_kind,1)
    stages = []

    def fragment(entry,stop,registers):
        m = CallMachine(code,mem,dict(sp=sp,**registers))
        outcome = m.run(entry,[stop])
        if outcome['status'] != 'stop' or m.r['sp'] != sp:
            raise ValueError(f'J producer fragment {entry:#x}: {outcome}')
        stages.append(dict(entry=hex(entry),stop=hex(stop),trace=[hex(pc) for pc in m.trace]))
        return m

    m = fragment(0x6091b7b8,0x6091b7db,{})
    mem.write(sp+4,owner,4)
    fragment(0x6091b83b,0x6091b840,dict(d3=m.r['d3']))
    mem.write(sp+24,owner,4)
    mem.write(sp+28,state,4)
    fragment(0x607017d4,0x607017e1,{})
    # This caller executes the unchanged table-driven native copy helper.
    fragment(0x60701025,0x6070103e,dict(a0=state+660,a1=auxiliary))
    fragment(0x606ff27b,0x606ff287,dict(a3=state))
    sentinel = 0x0badf00d
    m = CallMachine(code,mem,dict(sp=sp,a0=state))
    outcome = m.run(m.enter(0x60714ff2,sentinel,0x80,8),[sentinel])
    if outcome['status'] != 'stop' or m.r['sp'] != sp:
        raise ValueError(f'J native dispatcher call failed: {outcome}')
    stages.append(dict(entry='0x60714ff2',trace=[hex(pc) for pc in m.trace]))
    j268 = {1:0,2:1,3:2}.get(aux_kind,3)
    if (mem.read(state+268,1),mem.read(state+800,1),mem.read(state+896,4)) != (
            j268,f161,display_mask):
        raise ValueError('native J dispatch producer association changed')
    expected = (1 if j268 == 0 else 2 if j268 in (1,2) else 3) if (
        f161 and display_mask == 2) else (3 if j268 in (0,1) else 0)
    if m.r['d0'] != expected:
        raise ValueError('native J producer-to-dispatch comparison changed')
    return dict(synthetic_auxiliary_kind=aux_kind,synthetic_property_f161=f161,
                synthetic_display_mask=display_mask,j268=j268,j800=mem.read(state+800,1),
                j896=mem.read(state+896,4),dispatch_case=m.r['d0'],stages=stages,
                property_registry_constructed=False,callback_acceptance_executed=False,
                ordinary_fhd60_binding_verified=False,physical_display_opened=False)


def probe_movie_property_gate(code, property_value, explicit_flag):
    """Keep the property service as a boundary; test only native selection."""
    sp, auxiliary = 0x10001000, 0x10002000
    mem = Memory([
        Region(sp,bytearray(128),True,'host fragment stack'),
        Region(auxiliary,bytearray(80),True,'synthetic explicit capture flag'),
    ])
    mem.write(sp+28,auxiliary,4)
    mem.write(auxiliary+53,explicit_flag,1)
    m = Machine(code,mem,dict(sp=sp))
    outcome = m.run(0x609237c6,[0x609237d9,0x609237ef])
    query = outcome['pc'] == 0x609237d9
    if query:
        if m.r['d0'] != 0x8551:
            raise ValueError('capture movie-parameter property key changed')
        # Explicit service-return injection, not a native property evaluation.
        m.r['d0'] = property_value
        outcome = m.run(0x609237e0,[0x609237ef,0x60923825])
    selected = outcome['pc'] == 0x609237ef
    if selected != (explicit_flag == 1 or property_value == 1):
        raise ValueError('capture movie-parameter gate changed')
    if selected and m.r['d0'] != 0xf021:
        raise ValueError('movie preset lookup key changed')
    return dict(synthetic_property_8551=property_value,synthetic_explicit_flag=explicit_flag,
                property_query_reached=query,movie_preset_query_reached=selected,
                stop=hex(outcome['pc']),property_service_executed=False,
                trace=[hex(pc) for pc in m.trace],ordinary_fhd60_binding_verified=False)


def probe_processing_pool(code, key):
    mem = Memory([Region(0xa2af49fc,bytearray(12),True,'host processing-pool globals')])
    initial = Machine(code,mem)
    if initial.run(0x60719c60,[0x60719c87])['status'] != 'stop':
        raise ValueError('processing pool initialization failed')
    m = Machine(code,mem,dict(d0=key))
    if m.run(0x60719ccb,[0x60719ceb])['status'] != 'stop':
        raise ValueError('processing pool address failed')
    expected = 0xa45f82c0+(key-1)*1382400 if 1 <= key <= 86 else 0
    if m.r['d0'] != expected:
        raise ValueError('processing pool bounds/address changed')
    return dict(synthetic_key=key,stride=mem.read(0xa2af4a00,4),
                count=mem.read(0xa2af4a04,2),address=hex(m.r['d0']),
                slot_is_whole_video_frame_verified=False,
                ordinary_fhd60_binding_verified=False)


def probe_capture_flag_source(code, source_flag):
    sp = 0x10001000
    mem = Memory([
        Region(sp-1024,bytearray(2048),True,'host native stack'),
        Region(0x6261ea24,bytearray(4),True,'synthetic source state'),
        Region(0x62616d60,bytearray(8),True,'host cached camera flags'),
    ])
    mem.write(0x6261ea26,source_flag,1)
    m = CallMachine(code,mem,dict(sp=sp))
    outcome = m.run(0x6091b397,[0x60925b1d,0x6091b3a4])
    expected_stop = 0x6091b3a4 if source_flag == 1 else 0x60925b1d
    if outcome['status'] != 'stop' or outcome['pc'] != expected_stop:
        raise ValueError(f'capture flag source changed: {outcome}')
    if source_flag == 1:
        if mem.read(0x62616d62,1) != 1 or m.r['sp'] != sp:
            raise ValueError('capture forced flag/cache copy changed')
    elif (m.r['d0'],m.r['a0'],m.r['d1']) != (0x8551,0,0):
        raise ValueError('capture property query arguments changed')
    return dict(synthetic_source_flag=source_flag,stop=hex(expected_stop),
                cached_flag=1 if source_flag == 1 else None,
                property_query_reached=source_flag != 1,
                property_service_executed=False,trace=[hex(pc) for pc in m.trace],
                ordinary_fhd60_binding_verified=False)


def probe_capture_state(code, cached_flag, operation):
    """Replay the newly located field producers, with explicit stage arguments.

    The callback's acceptance tests, owner allocation and RTOS are omitted.
    cached_flag and D+0 are host inputs, not observed recording values.
    """
    sp, source, owner, result = 0x10001000, 0x10003000, 0x10004000, 0x10005000
    state = 0xa2aed68c
    mem = Memory([
        Region(sp-1024,bytearray(2048),True,'host stage stack'),
        Region(source,bytearray(80),True,'synthetic acquisition descriptor D'),
        Region(owner,bytearray(400),True,'synthetic work subobject P'),
        Region(result,bytearray(4),True,'synthetic ring cursor zero'),
        Region(state,bytearray(1020),True,'synthetic processing ring slot J'),
        Region(0x62616d60,bytearray(8),True,'host cached camera flags'),
    ])
    mem.write(source,operation,4)
    mem.write(source+48,1234,4)
    mem.write(0x62616d62,cached_flag,1)
    stages = []

    def fragment(entry,stop,registers):
        m = CallMachine(code,mem,dict(sp=sp,**registers))
        outcome = m.run(entry,[stop])
        if outcome['status'] != 'stop' or m.r['sp'] != sp:
            raise ValueError(f'capture field fragment {entry:#x}: {outcome}')
        stages.append(dict(entry=hex(entry),stop=hex(stop),
                           trace=[hex(pc) for pc in m.trace]))

    fragment(0x6091b63c,0x6091b645,{})
    fragment(0x6091b66d,0x6091b672,{})
    mem.write(sp+12,source,4)
    fragment(0x6091b81c,0x6091b834,dict(d2=owner-60))
    fragment(0x6091b840,0x6091b848,{})
    mem.write(sp+24,owner,4)
    mem.write(sp+28,state,4)
    fragment(0x60701a4d,0x60701a59,{})
    fragment(0x60715d3f,0x60715d5f,dict(a0=state,a2=sp+8))
    fragment(0x606ff259,0x606ff263,dict(a2=state+808))
    mem.write(sp+32,result,4)
    fragment(0x60701b01,0x60701b1c,{})
    expected = (1,3,5,8 if cached_flag == 0 else 9,6,4,13,12)[operation]
    values = (mem.read(owner+4,4),mem.read(owner+332,4),
              mem.read(state+172,4),mem.read(state+808,4),mem.read(state+902,1))
    if values != (operation,cached_flag,cached_flag,cached_flag,expected):
        raise ValueError(f'capture-state propagation changed: {values}')
    return dict(synthetic_cached_flag=cached_flag,synthetic_request_kind=operation,
                p4=values[0],p332=values[1],j172=values[2],j808=values[3],j902=values[4],
                capture_sequence=mem.read(owner,4),stages=stages,
                callback_acceptance_executed=False,ordinary_fhd60_binding_verified=False)


def probe_processing_dispatch(code, kind, auxiliary, mode):
    """Native dispatch classification; numeric inputs have no movie-mode label."""
    m = Machine(code,Memory([]),dict(d0=kind,a0=auxiliary,d1=mode))
    outcome = m.run(0x60715009,[0x6071504c])
    if outcome['status'] != 'stop':
        raise ValueError(f'processing dispatch failed: {outcome}')
    if kind in (0,1):
        expected = (1 if kind == 0 else 2) if auxiliary and mode == 2 else 3
    elif kind == 2:
        expected = 2 if auxiliary and mode == 2 else 0
    else:
        expected = 3 if auxiliary and mode == 2 else 0
    if m.r['d0'] != expected:
        raise ValueError('native processing dispatcher classification changed')
    return dict(synthetic_j268=kind,synthetic_j800=auxiliary,synthetic_j896=mode,
                dispatch_case=m.r['d0'],trace=[hex(pc) for pc in m.trace],
                ordinary_fhd60_binding_verified=False)


def probe_processing_route(code, image, frame_kind, operation=4, processing_kind=1,
                           full_height_shadow=False, height_override=None):
    """Join bounded native fragments on shared host memory, not a running RTOS.

    Frame header, operation and J+808 are synthetic inputs. Stage arguments
    are supplied by the harness; intervening event/constructor services do
    not execute. No firmware bytes or instruction listings are patched.
    """
    sp, state, settings = 0x10001000, 0x10002000, 0x10003000
    sensor, descriptor, wire = 0x10004000, 0x10005000, 0x10006000
    job, dimensions, render = 0x10007000, 0x10008000, 0x10009000
    table_at = 0x608bf02c
    table = bytearray(image[table_at-BASE:0x608bf07a-BASE])
    if full_height_shadow:
        struct.pack_into('<H',table,0x608bf04a-table_at+2,3456)
    mem = Memory([
        Region(sp-1024,bytearray(2048),True,'host call stack'),
        Region(state,bytearray(1020),True,'synthetic processing record J'),
        Region(settings,bytearray(400),True,'synthetic acquisition settings'),
        Region(sensor,bytearray(32),True,'synthetic camera plane record'),
        Region(descriptor,bytearray(32),True,'camera header output'),
        Region(wire,bytearray(28),True,'processing API configuration'),
        Region(job,bytearray(40),True,'constructor header output'),
        Region(dimensions,bytearray(4),True,'dimension output'),
        Region(render,bytearray(128),True,'render header output'),
        Region(0xa2aed574,bytearray(32),True,'host frame-header mailbox'),
        Region(0x62a24d14,bytearray(4),True,'host processing-kind cell'),
        Region(table_at,table,False,'host aspect table'),
        Region(0x608bf07a,bytearray(image[0x608bf07a-BASE:0x608bf08a-BASE]),
               False,'fit dimension table'),
        Region(0x608f2118,bytearray(image[0x608f2118-BASE:0x608f2140-BASE]),
               False,'dimension switch'),
        Region(0x608b81ec,bytearray(image[0x608b81ec-BASE:0x608b8234-BASE]),
               False,'context conversion switch'),
    ])
    mem.write(sensor+3,frame_kind,1)
    mem.write(settings+4,operation,4)
    mem.write(state+808,1,4)
    stages = []
    sentinel = 0x0badf00d

    def call(entry,mask,frame,registers):
        m = CallMachine(code,mem,dict(sp=sp,**registers))
        result = m.run(m.enter(entry,sentinel,mask,frame),[sentinel])
        if result['status'] != 'stop' or m.r['sp'] != sp:
            raise ValueError(f'processing route call {entry:#x}: {result}')
        stages.append(dict(entry=hex(entry),instructions=len(m.trace),
                           trace=[hex(pc) for pc in m.trace]))
        return m

    def fragment(entry,end,registers):
        m = CallMachine(code,mem,dict(sp=sp,**registers))
        result = m.run(entry,[end])
        if result['status'] != 'stop' or m.r['sp'] != sp:
            raise ValueError(f'processing route fragment {entry:#x}: {result}')
        stages.append(dict(entry=hex(entry),stop=hex(end),instructions=len(m.trace),
                           trace=[hex(pc) for pc in m.trace]))
        return m

    call(0x60708993,0,0,dict(d0=processing_kind))
    call(0x6091a167,0,0,dict(a0=descriptor,a1=sensor))
    # Publish stops before the diagnostic call, after all 32 bytes are copied.
    fragment(0x606fc9ff,0x606fca13,dict(a0=descriptor))
    call(0x606fca3f,0,0,dict(a0=state+844))
    mapped = call(0x607031f0,0x80,32,dict(a0=settings))
    mem.write(state+902,mapped.r['d0'],1)
    call(0x60708d80,0xf0,60,dict(a0=state,a1=wire+16,d0=wire+19))
    mem.write(sp+8,render,4)
    fragment(0x607066de,0x607066ec,dict(a2=wire+16,a3=wire+19,d2=wire))
    mem.write(sp+12,state,4)
    fragment(0x60706642,0x6070665b,dict(d2=wire))
    fragment(0x60706775,0x60706787,dict(d2=wire))
    # Producer's native stores, followed by the constructor's eight-word copy.
    fragment(0x6071b7ac,0x6071b7e4,dict(a2=wire))
    fragment(0x6074e02f,0x6074e03c,dict(a2=sp+36,d2=job))
    params = job+4
    classified = call(0x607a3c9e,0x80,4,
                      dict(d0=mem.read(params+16,2),d1=mem.read(params+30,1)))
    mem.write(dimensions,1920,2)
    mem.write(dimensions+2,1440,2)
    m = CallMachine(code,mem,dict(sp=sp,a0=params,a1=dimensions,d0=dimensions+2))
    first = m.run(m.enter(0x60750ada,sentinel,0xa0,24),
                  [sentinel,0x60750a6a] if height_override is not None else [sentinel])
    if height_override is not None:
        if first != dict(status='stop',pc=0x60750a6a,instructions=len(m.trace)):
            raise ValueError(f'height override did not reach FHD store: {first}')
        m.r['d0'] = height_override
        first = m.run(0x60750a6a,[sentinel])
    if first['status'] != 'stop' or m.r['sp'] != sp:
        raise ValueError(f'dimension wrapper did not finish: {first}')
    stages.append(dict(entry='0x60750ada',instructions=len(m.trace),
                       trace=[hex(pc) for pc in m.trace]))
    if (mem.read(state+874,1) != frame_kind or mem.read(params+16,2) != mem.read(wire+16,2)
            or mem.read(params+30,1) != mem.read(wire+25,1)):
        raise ValueError('native processing/header copy association changed')
    return dict(frame_header_kind=frame_kind,operation_input=operation,
                synthetic_processing_kind=processing_kind,synthetic_j808=1,
                j874=mem.read(state+874,1),j902=mem.read(state+902,1),
                parameter_type_word=hex(mem.read(params+16,2)),
                parameter_aspect=mem.read(params+18,1),
                parameter_ratio_context=mem.read(params+21,1),
                parameter_classifier_context=mem.read(params+30,1),
                image_dimension_class=classified.r['d0'],
                output_dimensions=[mem.read(dimensions,2),mem.read(dimensions+2,2)],
                full_height_host_table_shadow=full_height_shadow,
                host_height_register_override=height_override,
                stages=stages,uninterrupted_runtime_chain_executed=False,
                ordinary_fhd60_binding_verified=False,full_field_verified=False,
                pixels_processed=False)


def probe_aspect_geometry(code, image, aspect, kind=None, context=0,
                          full_height_shadow=False, bypass_mode=0):
    """Run native ratio/crop or dimension selection, with no software callees.

    The optional ratio change affects only a synthetic table copy in host RAM.
    Numeric kind/context values are caller contracts, not recording mode names.
    """
    sp, request, dimensions = 0x10001000, 0x10002000, 0x10006000
    ratios_at = 0x608bf02c
    ratios = bytearray(image[ratios_at-BASE:0x608bf07a-BASE])
    if full_height_shadow:
        struct.pack_into('<H', ratios, 0x608bf04a-ratios_at+2, 3456)
    mem = Memory([
        Region(sp-1024, bytearray(2048), True, 'host native call stack'),
        Region(request, bytearray(11000), True, 'host image request'),
        Region(dimensions, bytearray(4), True, 'host width and height'),
        Region(ratios_at, ratios, False, 'host copy of aspect ROM'),
        Region(0x608f2118, bytearray(image[0x608f2118-BASE:0x608f2140-BASE]),
               False, 'dimension switch ROM'),
    ])
    mem.write(dimensions, 1920, 2)
    mem.write(dimensions+2, 1440, 2)
    saved = dict(d2=0x22222222, d3=0x33333333, a2=0x44444444, a3=0x55555555)
    machine = CallMachine(code, mem, dict(sp=sp, a0=request,
        a1=dimensions, d0=dimensions+2, **saved))
    if kind is None:
        mem.write(request+23, aspect, 1)
        mem.write(request+10417, bypass_mode, 1)
        entry, mask, frame = 0x6074fd86, 0xf0, 20
    else:
        mem.write(request+16, kind, 2)
        mem.write(request+18, aspect, 1)
        mem.write(request+21, context, 1)
        entry, mask, frame = 0x60750ada, 0xa0, 24
    return_pc = 0x0badf00d
    result = machine.run(machine.enter(entry, return_pc, mask, frame), [return_pc])
    if (result['status'] != 'stop' or machine.r['sp'] != sp
            or any(machine.r[name] != value for name, value in saved.items())):
        raise ValueError(f'aspect fragment did not return with saved state: {result}')
    return dict(aspect_id=aspect, kind=kind, context=context, bypass_mode=bypass_mode,
                full_height_host_table_shadow=full_height_shadow,
                initial_dimension_cells=[1920,1440],
                input_dimensions=[1920,1440] if kind is None else None,
                output_dimensions=[mem.read(dimensions,2),mem.read(dimensions+2,2)],
                entry=hex(entry), instructions=len(machine.trace),
                trace=[hex(pc) for pc in machine.trace],
                calls=[hex(e['target']) for e in machine.events if e['op']=='call'],
                pixels_processed=False, ordinary_fhd60_binding_verified=False)


def probe_received_video(code, height, max_code_size):
    """Replay checked local payload copies and the source aspect classifier."""
    sp, block, receiver = 0x10000000, 0x10002000, 0x10004000
    video = block+96
    mem = Memory([Region(sp, bytearray(256), True, 'host receiver stack'),
                  Region(block, bytearray(284), True, 'host video block'),
                  Region(receiver, bytearray(64), True, 'host receiver')])
    for offset, value in ((8, 5994), (16, 1920), (20, height), (24, 1920),
                          (28, height), (56, max_code_size), (60, 5994), (72, 1)):
        mem.write(video+offset, value, 4)
    mem.write(sp+12, block, 4)
    source = Machine(code, mem, {'sp': sp, 'a3': receiver})
    result = source.run(0x616602b3, stops=[0x616602e2], limit=32)
    if result['status'] != 'stop':
        raise ValueError(f'AVM source copy did not complete: {result}')
    for offset in (0, 4, 8, 12, 16):
        mem.write(sp+132+offset, mem.read(sp+20+offset, 4), 4)
    aspect = Machine(code, mem, {'sp': sp})
    result = aspect.run(0x616b031f, stops=[0x616b0372], limit=40)
    if result['status'] != 'stop':
        raise ValueError(f'video source aspect calculation did not complete: {result}')
    active = [mem.read(sp+offset, 4) for offset in (84, 88)]
    aspect_key = mem.read(sp+112, 4)
    encoder = Machine(code, mem, {'sp': sp, 'a0': video})
    result = encoder.run(0x616603f6, stops=[0x61660444], limit=36)
    if result['status'] != 'stop':
        raise ValueError(f'AVM encoder copy did not complete: {result}')
    return dict(active=active, source_aspect_key=aspect_key,
                maximum=[mem.read(sp+offset, 4) for offset in (72, 76)],
                max_code_size=mem.read(sp+20, 4), output_rate_key=mem.read(sp+52, 4),
                trace=[hex(pc) for m in (source, aspect, encoder) for pc in m.trace])


def probe_record_open_range(code, request_kind):
    request = 0x10000000
    mem = Memory([Region(request, bytearray(4), True, 'host recording request')])
    mem.write(request+2, request_kind, 1)
    machine = Machine(code, mem, {'a2': request})
    result = machine.run(0x607b9b70, stops=[0x607b9b91], limit=12)
    if result['status'] != 'stop':
        raise ValueError(f'recording range selection did not complete: {result}')
    return dict(request_kind=request_kind,
                arguments=[hex(machine.r[reg]) for reg in ('d0', 'd1')])


def probe_render_layout(code, key, synthetic_height=None):
    """Build the conditional image request, stopping before submission."""
    sp, key_cell = 0x10000000, 0x10002000
    bases = (0x20000000, 0x21000000)
    mem = Memory([Region(sp, bytearray(192), True, 'host render stack'),
                  Region(key_cell, bytearray(2), True, 'host render selector')])
    for offset, value in ((32, key_cell), (108, bases[0]), (76, bases[1])):
        mem.write(sp+offset, value, 4)
    mem.write(key_cell+1, key, 1)
    machine = Machine(code, mem, {'sp': sp})
    result = machine.run(0x60725560, stops=[0x607255c3], limit=32)
    if result['status'] != 'stop':
        raise ValueError(f'render raster selection did not complete: {result}')
    width = mem.read(sp+24, 4)
    if synthetic_height is not None:
        mem.write(sp+28, synthetic_height, 4)
        mem.write(sp+20, width*synthetic_height, 4)
    result = machine.run(0x607255eb, stops=[0x60725650], limit=64)
    if result['status'] != 'stop':
        raise ValueError(f'render plane descriptor did not complete: {result}')
    pairs = [mem.read(sp+offset, 4) for offset in (112, 116, 120, 124)]
    return dict(key=key, synthetic_height=synthetic_height,
                raster=[mem.read(sp+offset, 2) for offset in (132, 134)],
                half_raster=[mem.read(sp+offset, 2) for offset in (140, 142)],
                plane_deltas=[pairs[1]-pairs[0], pairs[3]-pairs[2]],
                trace=[hex(pc) for pc in machine.trace])


def probe_intermediate_fill(code, width, height):
    """Replay the optional intermediate layout and fill stores in host memory."""
    sp, job, base = 0x10000000, 0x10002000, 0x20000000
    shadow_mmio = 0x9cb00000
    mem = Memory([Region(sp, bytearray(320), True, 'host intermediate layout'),
                  Region(job, bytearray(36), True, 'host fill job'),
                  Region(shadow_mmio, bytearray(0x400), True, 'host register shadow')])
    layout = Machine(code, mem, {'sp': sp, 'd3': width, 'a2': height})
    result = layout.run(0x6074d9fd, stops=[0x6074da48], limit=40)
    if result['status'] != 'stop':
        raise ValueError(f'intermediate layout did not complete: {result}')
    size = mem.read(sp+284, 4)
    for offset, value in ((20, base), (24, size), (28, 0x80008000)):
        mem.write(job+offset, value, 4)
    fill = Machine(code, mem, {'a0': job})
    result = fill.run(0x6073a393, stops=[0x6073a438], limit=32)
    if result['status'] != 'stop':
        raise ValueError(f'intermediate fill register stores did not complete: {result}')
    return dict(requested_raster=[width, height],
                intermediate_raster=[mem.read(sp+offset, 2) for offset in (224, 226)],
                aligned_pitch_samples=mem.read(sp+222, 2), size_bytes=size,
                fill_address=hex(mem.read(shadow_mmio+0x84, 4)),
                fill_size=mem.read(shadow_mmio+0x36c, 4),
                fill_pattern=hex(mem.read(shadow_mmio+0x380, 4)),
                trace=[hex(pc) for machine in (layout, fill) for pc in machine.trace])


def probe_application_geometry(code, geometry_key, nominal_rate):
    """Run the stock raster and output rate switches of the video API builder."""
    sp, config = 0x10000000, 0x10002000
    mem = Memory([Region(sp, bytearray(128), True, 'host builder stack'),
                  Region(config, bytearray(112), True, 'host video configuration')])
    mem.write(sp+4, sp+100, 4)
    mem.write(sp+20, sp+102, 4)
    mem.write(sp+100, geometry_key, 1)
    mem.write(sp+102, nominal_rate, 2)
    machine = Machine(code, mem, {'sp': sp, 'a2': config})
    for start, stop in ((0x607bb56f, 0x607bb625), (0x607bb6e8, 0x607bb73c)):
        result = machine.run(start, stops=[stop], limit=32)
        if result['status'] != 'stop':
            raise ValueError(f'application video builder did not complete: {result}')
    return dict(geometry_key=geometry_key, nominal_rate=nominal_rate,
                active=[mem.read(config+offset, 4) for offset in (16, 20)],
                maximum=[mem.read(config+offset, 4) for offset in (24, 28)],
                max_code_size=mem.read(config+56, 4),
                output_rate_key=mem.read(config+60, 4),
                ivop_interval=mem.read(config+64, 4),
                trace=[hex(pc) for pc in machine.trace])


def probe_q_pool(code, q_format, stride_override=None):
    """Run the conditional Q sizing fragment before any pool access."""
    request, sizing = 0x10000000, 0x62a25ca4
    mem = Memory([Region(request, bytearray(824), True, 'host Q record'),
                  Region(sizing, bytearray(6), True, 'host Q sizing globals')])
    mem.write(request+805, q_format, 1)
    if stride_override is None:
        machine = Machine(code, mem, {'a0': request})
        entry = 0x60727cba
    else:
        machine = Machine(code, mem, {'d0': stride_override})
        entry = 0x60727cdf
    result = machine.run(entry, stops=[0x60727cf6], limit=32)
    if result['status'] != 'stop':
        raise ValueError(f'Q pool sizing did not complete: {result}')
    stride = mem.read(sizing, 4)
    count = mem.read(sizing+4, 2)
    return dict(q_format=q_format, synthetic_stride_override=stride_override,
                stride_bytes=stride, slot_count=count,
                trailing_bytes=119439360-stride*count,
                trace=[hex(pc) for pc in machine.trace])


def probe_mov_headers(code, width, height, sps_header):
    """Check independent dimension and SPS byte copies before serialization."""
    sp, track, packet = 0x10000000, 0x10002000, 0x10004000
    mem = Memory([Region(sp, bytearray(128), True, 'host stack'),
                  Region(track, bytearray(1024), True, 'host MOV track'),
                  Region(packet, bytearray(8), True, 'host NAL prefix')])
    mem.write(track+96, width, 4)
    mem.write(track+92, height, 4)
    dimensions = Machine(code, mem, {'a3': track+20, 'a2': track+620})
    size_result = dimensions.run(0x6168c1ff, stops=[0x6168c20d], limit=12)
    # The preceding SPS branch has located a four-byte start code and
    # copied the NAL. Model the input pointers at the following byte loads.
    avcc = track+700
    mem.write(avcc, 1, 1)
    mem.write(packet+4, int.from_bytes(sps_header, 'little'), 4)
    buffer_cell = sp+100
    mem.write(buffer_cell, packet, 4)
    for offset, value in ((8, buffer_cell), (12, 0), (24, avcc+2),
                          (44, avcc), (52, avcc+1)):
        mem.write(sp+offset, value, 4)
    sps = Machine(code, mem, {'sp': sp, 'd2': 4})
    sps_result = sps.run(0x6168af34, stops=[0x6168af53], limit=24)
    if size_result['status'] != 'stop' or sps_result['status'] != 'stop':
        raise ValueError('MOV header copy did not complete')
    written = [mem.read(track+offset, 2) for offset in (636, 638)]
    avcc_prefix = mem.read(avcc, 4).to_bytes(4, 'little')
    if written != [width, height] or avcc_prefix != b'\x01'+sps_header[1:]:
        raise ValueError('MOV header byte copy changed')
    return dict(sample_entry_dimensions=written, sps_header=sps_header.hex(),
                avcc_prefix=avcc_prefix.hex(),
                trace=[hex(pc) for machine in (dimensions, sps) for pc in machine.trace])


def probe_rate_class(code, table, geometry, rate_class):
    """Trace the selected rate-control branch with a host-owned configuration."""
    sp, ctx, cfg = 0x10000000, 0x10002000, 0x10004000
    mem = Memory([Region(sp, bytearray(1024), True, 'host stack'),
                  Region(ctx, bytearray(8192), True, 'host rate control'),
                  Region(cfg, bytearray(64), True, 'host configuration'),
                  Region(RATE_CLASS_TABLE, bytearray(table), False, 'ROM jump table')])
    mem.write(sp+64, ctx, 4)
    mem.write(ctx+4772, cfg, 4)
    mem.write(cfg+40, rate_class, 4)
    mem.write(ctx+3592, geometry['padded_geometry'][1], 4)
    blocks = geometry['native_macroblocks_per_frame']
    mem.write(ctx+3612, blocks, 4)
    machine = Machine(code, mem, {'sp': sp})
    result = machine.run(0x616a42a8, stops=[0x616a4339], limit=100)
    if result['status'] != 'stop':
        raise ValueError(f'rate control dispatch did not reach the selected branch: {result}')
    nominal_budget = machine.r['a2']
    divisor = machine.r['d3']
    frame_value = None
    if rate_class >= 7:
        result = machine.run(0x616a43a2, stops=[0x616a43b4], limit=25)
        if result['status'] != 'stop':
            raise ValueError(f'high-class frame arithmetic did not complete: {result}')
        frame_value = machine.r['d1']
    return dict(width=geometry['width'], height=geometry['height'], rate_key=geometry['rate_key'],
                rate_class=rate_class, synthetic_class_override=rate_class != geometry['native_class'],
                macroblocks_per_second=blocks*geometry['rate_key']/100,
                nominal_table_macroblock_rate=nominal_budget,
                native_divisor=divisor, high_class_frame_value=frame_value,
                trace=[hex(pc) for pc in machine.trace])


def probe_geometry(code, width, height, rate, bitrate):
    """Native fragment results, never an encoder acceptance/capacity test."""
    if any(type(v) is not int or not 0 < v < 1 << 31
           for v in (width, height, rate, bitrate)):
        raise ValueError('probe inputs must be positive signed 32-bit integers')
    sp, obj, holder, ctx = 0x10000000, 0x10002000, 0x10004000, 0x10006000
    mem = Memory([Region(sp, bytearray(1024), True, 'host stack'),
                  Region(obj, bytearray(2048), True, 'host progressive object'),
                  Region(holder, bytearray(4), True, 'host pointer cell'),
                  Region(ctx, bytearray(8192), True, 'host driver object')])
    mem.write(sp+20, obj, 4)
    for offset, value in ((16,width),(20,height),(32,bitrate),(52,rate)):
        mem.write(obj+offset, value, 4)
    m = Machine(code, mem, {'sp': sp})
    first = m.run(0x6169f34a, stops=[0x6169f4ee], limit=500)
    if first['status'] != 'stop':
        raise ValueError(f'progressive probe crossed a call/unsupported boundary: {first}')
    cfg = obj+1116
    copied = [mem.read(cfg+offset,4) for offset in (8,12,16)]
    if copied != [width,height,rate]:
        raise ValueError('native progressive configuration changed geometry/rate')
    # The exact following driver fragment uses a pointer cell at stack +64.
    # It is intentionally entered after setup, with only host-owned objects.
    mem.write(sp+52,ctx,4)
    mem.write(sp+64,holder,4)
    mem.write(holder,cfg,4)
    n = Machine(code,mem,{'sp':sp})
    second = n.run(0x616a2a3e,stops=[0x616a2acc],limit=250)
    if second['status'] != 'stop':
        raise ValueError(f'alignment probe crossed a call/unsupported boundary: {second}')
    padded = [mem.read(ctx+offset,4) for offset in (3588,3592)]
    blocks = mem.read(ctx+3612,4)
    expected = [((x+15)//16)*16 for x in (width,height)]
    if padded != expected or blocks != (expected[0]//16)*(expected[1]//16):
        raise ValueError('native driver alignment disagrees with independent arithmetic')
    # Execute the preset selector separately; stop before later tuning writes.
    p = Machine(code,mem,{'sp':sp})
    third = p.run(0x616a2814,stops=[0x616a2873,0x616a288e],limit=100)
    if third['status'] != 'stop':
        raise ValueError(f'preset probe crossed a boundary: {third}')
    return dict(width=width,height=height,rate_key=rate,bitrate_argument=bitrate,
                native_class=mem.read(obj+1008,4),
                configuration_width=copied[0],configuration_height=copied[1],
                configuration_rate=copied[2],padded_geometry=padded,
                native_macroblocks_per_frame=blocks,
                tightly_packed_yuv420_bytes=(width*height*3)//2
                if not (width%2 or height%2) else None,
                preset_pointer=hex(mem.read(ctx+4016,4)),
                native_fragments_executed=[first,second,third],
                trace=[hex(pc) for machine in (m,n,p) for pc in machine.trace],
                driver_open_executed=False,pixels_processed=False,
                sensor_full_field_verified=False,recording_verified=False)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out',type=Path,required=True)
    parser.add_argument('--reader',type=Path,
                        default=default_reader())
    parser.add_argument('--listing-dir',type=Path,
                        help='Use saved NAME.tsv windows; still verify all input bytes and anchors')
    args = parser.parse_args()
    out = local_output(args.out)
    stock = verified_input(ROOT/'firmware/OLY_E_133_1101_0000_0000.BIN',
                           104552480,STOCK_SHA)
    path = ROOT/'local/epl9-1101-analysis/decoded'/MAIN_NAME
    data = verified_input(path,26214336,MAIN_SHA)
    decoded, code, listings = {}, {}, {}
    for name,(start,stop) in WINDOWS.items():
        if args.listing_dir is not None:
            listing = (args.listing_dir/(name+'.tsv')).read_text(encoding='utf-8')
        else:
            verify_reader(args.reader)
            listing = subprocess.check_output([str(args.reader.resolve()),str(path),
                                               hex(BASE),hex(start-BASE),hex(stop-BASE)],text=True)
        decoded.update(checked_listing(listing,data,start,stop))
        code.update(parse_listing(listing,data,BASE))
        listings[name] = listing
    for at,expected in ANCHORS.items():
        if decoded.get(at) != expected:
            raise ValueError(f'geometry anchor {at:#x} changed')
    for at, expected in (AVM_OPEN_WORDS | IMAGE_JOB_WORDS | DIMENSION_SWITCH_WORDS
                         | PROCESSING_CONTEXT_WORDS | SOURCE_RESOURCE_WORDS).items():
        if struct.unpack_from('<I', data, at-BASE)[0] != expected:
            raise ValueError(f'ROM routing word {at:#x} changed')
    rows = [probe_geometry(code,*case) for case in (
        (1920,1080,5994,30000000), (1920,1440,5994,30000000),
        (1920,1440,6000,30000000), (1920,1440,5994,60000000),
        (3840,2160,2997,100000000), (1920,1440,2997,30000000),
        (1536,1152,5994,30000000), (1921,1441,5994,30000000),
    )]
    if [r['native_class'] for r in rows] != [6,6,6,7,8,5,5,5]:
        raise ValueError('native classification regression')
    start = RATE_CLASS_TABLE-BASE
    table = data[start:start+36]
    rate_probes = [probe_rate_class(code,table,rows[index],rate_class)
                   for index,rate_class in ((0,6),(2,6),(2,7),(2,8),(4,8))]
    actual = [(r['nominal_table_macroblock_rate'], r['native_divisor'],
               r['high_class_frame_value']) for r in rate_probes]
    if actual != [(522240,4,None),(522240,4,None),(589824,2,16588800),
                  (983040,2,16588800),(983040,4,24883200)]:
        raise ValueError('native rate control class comparison changed')
    q_probes = [probe_q_pool(code, mode) for mode in (0, 16, 17)]
    q_probes.append(probe_q_pool(code, 0, rows[2]['tightly_packed_yuv420_bytes']))
    if [(r['stride_bytes'], r['slot_count']) for r in q_probes] != [
        (3133440, 38), (1382400, 86), (353280, 338), (4147200, 28)
    ]:
        raise ValueError('conditional Q pool sizing changed')
    mov_probes = [probe_mov_headers(code, 1920, 1080, bytes.fromhex('6764002a')),
                  probe_mov_headers(code, 1920, 1440, bytes.fromhex('67640033'))]
    application_probes = [probe_application_geometry(code, key, rate) for key, rate in (
        (0, 60), (1, 60), (2, 60), (3, 30), (4, 30), (5, 30), (6, 30),
    )]
    actual_application = [(*p['active'], *p['maximum'], p['output_rate_key'],
                           p['ivop_interval']) for p in application_probes]
    if actual_application != [
        (1920,1080,1920,1080,5994,30), (1920,1080,1920,1080,5994,30),
        (1280,720,1920,1080,5994,30), (640,480,1920,1080,2997,15),
        (640,360,1920,1080,2997,15), (4096,2160,4096,2160,2997,15),
        (3840,2160,4096,2160,2997,15),
    ]:
        raise ValueError('application geometry or output cadence changed')
    for probe in application_probes:
        width, height = probe['active']
        blocks = ((width+15)//16)*((height+15)//16)
        if probe['max_code_size'] != 96*blocks:
            raise ValueError('application max code size no longer matches padded raster')
    received_probes = [probe_received_video(code, 1080, 783360),
                       probe_received_video(code, 1440, 1036800)]
    for probe, height, aspect, cap in zip(received_probes, (1080, 1440),
                                          (2, 1), (783360, 1036800)):
        if (probe['active'], probe['maximum'], probe['source_aspect_key'],
            probe['max_code_size'], probe['output_rate_key']) != (
                [1920, height], [1920, height], aspect, cap, 5994):
            raise ValueError('receiver geometry, aspect or encoder payload changed')
    range_probes = [probe_record_open_range(code, kind) for kind in (1, 6)]
    if [p['arguments'] for p in range_probes] != [
        ['0xb1e51000', '0xb937a000'], ['0xa9facc00', '0xaf0c5dc0']
    ]:
        raise ValueError('first-stream recording range selection changed')
    render_probes = [probe_render_layout(code, 5), probe_render_layout(code, 6),
                     probe_render_layout(code, 8), probe_render_layout(code, 5, 1440)]
    if [(p['raster'], p['half_raster'], p['plane_deltas']) for p in render_probes] != [
        ([1920,1080], [960,540], [2088960]*2),
        ([1920,1080], [960,540], [2088960]*2),
        ([3840,2160], [1920,1080], [8294400]*2),
        ([1920,1440], [960,720], [2764800]*2),
    ]:
        raise ValueError('conditional render request layout changed')
    intermediate_probes = [probe_intermediate_fill(code, width, height)
                           for width, height in ((1920,1080), (1920,1440), (1921,1440))]
    for probe, pitch, size in zip(intermediate_probes, (1920, 1920, 1952),
                                  (4147200, 5529600, 5621760)):
        if (probe['aligned_pitch_samples'], probe['size_bytes'], probe['fill_size'],
            probe['fill_address'], probe['fill_pattern']) != (
                pitch, size, size, '0x20000000', '0x80008000'):
            raise ValueError('intermediate layout or fill register values changed')
    aspect_probes = [
        probe_aspect_geometry(code,data,1),
        probe_aspect_geometry(code,data,3),
        probe_aspect_geometry(code,data,3,full_height_shadow=True),
        *[probe_aspect_geometry(code,data,3,bypass_mode=mode) for mode in (4,5,6,7)],
        probe_aspect_geometry(code,data,1,kind=0),
        probe_aspect_geometry(code,data,3,kind=0),
        probe_aspect_geometry(code,data,3,kind=0,full_height_shadow=True),
        probe_aspect_geometry(code,data,1,kind=0,context=1),
        probe_aspect_geometry(code,data,1,kind=0,context=2),
        probe_aspect_geometry(code,data,3,kind=0,context=2),
        probe_aspect_geometry(code,data,3,kind=0,context=2,full_height_shadow=True),
        probe_aspect_geometry(code,data,1,kind=4),
        probe_aspect_geometry(code,data,3,kind=4),
        probe_aspect_geometry(code,data,3,kind=4,full_height_shadow=True),
        probe_aspect_geometry(code,data,1,kind=5),
    ]
    if [p['output_dimensions'] for p in aspect_probes] != [
        [1920,1440], [1920,1080], [1920,1440],
        *([[1920,1440]]*4),
        [4608,3456], [4608,2592], [4608,3456],
        [1824,1024], [1920,1080], [1920,1080], [1920,1080],
        [1920,1080], [1920,1080], [1920,1080], [3840,2160],
    ]:
        raise ValueError('native aspect/dimension comparison changed')
    aspect_rows = [dict(address=hex(at), words=list(struct.unpack_from('<3H',data,at-BASE)))
                   for at in range(0x608bf02c,0x608bf07a,6)]
    processing_routes = [
        *[probe_processing_route(code,data,kind) for kind in (3,4,6,7,8,9)],
        probe_processing_route(code,data,6,full_height_shadow=True),
        probe_processing_route(code,data,4,full_height_shadow=True),
        probe_processing_route(code,data,6,height_override=1440),
        probe_processing_route(code,data,6,operation=6),
        probe_processing_route(code,data,6,processing_kind=0),
        probe_processing_route(code,data,4,processing_kind=0),
    ]
    if [(p['parameter_type_word'],p['parameter_aspect'],p['image_dimension_class'],
         p['output_dimensions']) for p in processing_routes] != [
        ('0x2003',3,5,[1280,720]), ('0x2002',1,5,[1280,720]),
        ('0x2004',3,6,[1920,1080]), ('0x2002',1,5,[1280,720]),
        ('0x2005',3,7,[3840,2160]), ('0x2005',10,7,[3840,2160]),
        ('0x2004',3,6,[1920,1080]), ('0x2002',1,5,[1280,720]),
        ('0x2004',3,6,[1920,1440]), ('0x2004',3,6,[1920,1080]),
        ('0x34',3,6,[640,360]), ('0x32',1,6,[640,360]),
    ]:
        raise ValueError('processing producer/dimension comparison changed')
    fit_size_rows = [list(struct.unpack_from('<2H',data,at-BASE))
                     for at in range(0x608bf07a,0x608bf08a,4)]
    if fit_size_rows != [[640,480],[640,480],[800,600],[1024,768]]:
        raise ValueError('fit dimension rows changed')
    capture_states = [probe_capture_state(code,flag,operation)
                      for flag in (0,1) for operation in range(8)]
    capture_flag_sources = [probe_capture_flag_source(code,flag) for flag in (0,1,2)]
    processing_pool_addresses = [probe_processing_pool(code,key) for key in (0,1,2,86,87)]
    settings_copy_rows = [dict(address=hex(0x608b5afc+index*8),
                              fields=list(struct.unpack_from('<HBBI',data,0x608b5afc-BASE+index*8)))
                          for index in range(25)]
    if settings_copy_rows[20]['fields'] != [0xf161,2,0,140]:
        raise ValueError('J+800 property-copy descriptor changed')
    object_defaults = {}
    for at,key in ((0x60478874,0x8551),(0x6049b464,0xf161)):
        row = list(struct.unpack_from('<HHI',data,at-BASE))
        if row != [key,1,0]:
            raise ValueError(f'property object default changed: {at:#x}')
        object_defaults[hex(key)] = dict(address=hex(at),kind=row[0],count=row[1],value=0)
    dispatch_producers = [probe_dispatch_producers(code,data,aux,f161,display)
                          for aux in (None,0,1,2,3,4) for f161 in (0,1)
                          for display in (1,2,3)]
    movie_property_gates = [probe_movie_property_gate(code,prop,flag)
                           for prop in (0,1) for flag in (0,1)]
    source_configurations = [probe_source_configuration(code,preset,rate,layout)
                             for preset,rate in ((0,25),(1,25),(7,25),(9,25),
                                                 (8,25),(8,12),(8,6))
                             for layout in (5,6,8)]
    source_resource_pools = [probe_resource_pool_definition(code,kind,key)
                             for kind in (0x2f00,0x5600) for key in (0,1,2,9,10)]
    resource_alias_allocations = [probe_resource_alias_allocation(code,data,order,mode)
                                  for mode in (0,1,2)
                                  for order in ((0x2f00,0x5600),(0x5600,0x2f00))]
    repacked_fhd_pool = probe_repacked_fhd_pool(code)
    source_return_refs=[probe_source_return_reference(code,refs,selected,index)
                        for refs in (1,2,3) for selected in (0,8) for index in (0,5,8)]
    source_release_sweeps=[probe_source_release_sweep(code,index,flag)
                           for index in (0,5,8) for flag in (0,1,2)]
    codec_counts=[probe_codec_conditional_count(code,*fields) for fields in (
        (0,0,0,1,0,0),(1,2,0,1,0,0),(1,0,0,1,0,0),
        (1,0,0,1,1,0),(1,0,1,1,0,0),(1,0,0,0,0,0),
        (1,0,0,1,0,1),(1,0,1,1,0,1))]
    source_final_cleanup=[probe_source_final_cleanup_gate(code,flag,refs)
                          for flag in (0,1,2) for refs in (0,1,3)]
    image_work_busy = [probe_image_work_busy(code,data,index,busy)
                       for index in (0,1,2) for busy in (0,5)]
    recording_control = [probe_tft_recording_control(code,data,state) for state in range(4)]
    dispatch_states = [probe_processing_dispatch(code,kind,auxiliary,mode)
                       for kind in range(4) for auxiliary in (0,1)
                       for mode in (0,1,2)]
    # These are descriptor rows. Runtime sensor mode, field coverage and cadence
    # must be established separately; none is asserted by a dimension match.
    geometry_rows = []
    for index in (0,4,5,14,15,27):
        at = 0x608bece4 + 24*index
        words = struct.unpack_from('<12H',data,at-BASE)
        geometry_rows.append(dict(index=index,address=hex(at),words=list(words),
                                  halfwords_8_through_14=list(words[4:8]),
                                  active_dimension_candidates=list(words[8:10])))
    if [r['active_dimension_candidates'] for r in geometry_rows] != [
        [4608,3456],[1536,1152],[1728,1296],[2304,1296],[2304,1296],[1728,1296]
    ]:
        raise ValueError('sensor geometry comparison rows changed')
    report = dict(
        model='Olympus PEN E-PL9',model_id='1330',displayed_version='1.1',build='1101',
        stock_bytes=len(stock),stock_sha256=STOCK_SHA,main_bytes=len(data),main_sha256=MAIN_SHA,
        analysis_base=hex(BASE),
        reader_sha256=None if args.listing_dir is not None else
            verify_reader(args.reader),
        listing_source='predecoded, byte-checked windows' if args.listing_dir is not None else
            'native reader invoked',
        listing_sha256={name:hashlib.sha256(value.encode('utf-8')).hexdigest()
                        for name,value in listings.items()},
        scope='host execution of isolated video geometry, setup, sizing and header fragments',
        object_join_from_application_params_verified=False,
        native_class_is_avc_level_verified=False,preset_is_memory_capacity_verified=False,
        whole_encoder_acceptance_verified=False,full_field_60_verified=False,
        camera_commands_sent=False,firmware_image_modified=False,
        anchors=len(ANCHORS),windows=len(WINDOWS),probes=rows,
        upstream_geometry_rows=geometry_rows,rate_control_probes=rate_probes,
        rate_control_class_table=hex(RATE_CLASS_TABLE),q_pool_probes=q_probes,
        q_pool_used_for_ordinary_60_verified=False,mov_header_probes=mov_probes,
        application_geometry_probes=application_probes,
        avm_receiver_probes=received_probes,record_open_range_probes=range_probes,
        conditional_render_layout_probes=render_probes,
        intermediate_fill_probes=intermediate_probes,
        aspect_geometry_probes=aspect_probes,aspect_geometry_rom_rows=aspect_rows,
        processing_route_probes=processing_routes,
        processing_fit_size_rows=fit_size_rows,
        capture_state_probes=capture_states,processing_dispatch_probes=dispatch_states,
        capture_flag_source_probes=capture_flag_sources,
        processing_pool_address_probes=processing_pool_addresses,
        processing_dispatch_producer_probes=dispatch_producers,
        processing_settings_copy_rom_rows=settings_copy_rows,
        processing_property_rom_defaults=object_defaults,
        movie_property_gate_probes=movie_property_gates,
        source_configuration_probes=source_configurations,
        source_resource_pool_probes=source_resource_pools,
        resource_alias_allocation_probes=resource_alias_allocations,
        candidate_repacked_fhd_pool=repacked_fhd_pool,
        source_return_reference_probes=source_return_refs,
        source_release_sweep_probes=source_release_sweeps,
        codec_conditional_count_probes=codec_counts,
        source_final_cleanup_gate_probes=source_final_cleanup,
        image_work_busy_probes=image_work_busy,
        recording_control_probes=recording_control,
        source_resource_rom_words={hex(at):hex(value) for at,value in SOURCE_RESOURCE_WORDS.items()},
        capture_flag_property_semantics_verified=False,
        processing_context_rom_words={hex(at):hex(value) for at,value in PROCESSING_CONTEXT_WORDS.items()},
        dimension_switch_rom_words={hex(at):hex(value) for at,value in DIMENSION_SWITCH_WORDS.items()},
        avm_open_rom_words={hex(at): hex(value) for at,value in AVM_OPEN_WORDS.items()},
        image_job_rom_words={hex(at): hex(value) for at,value in IMAGE_JOB_WORDS.items()},
        ordinary_60_scaler_and_pixel_pool_binding_verified=False,
        encoder_sps_generation_verified=False)
    out.mkdir(parents=True)
    for name,listing in listings.items():
        (out/(name+'.tsv')).write_text(listing,encoding='utf-8')
    (out/'audit.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(out=str(out),anchors=len(ANCHORS),windows=len(WINDOWS),
                         probes=len(rows),aspect_probes=len(aspect_probes),
                         processing_routes=len(processing_routes),
                         capture_states=len(capture_states),dispatch_states=len(dispatch_states),
                         dispatch_producers=len(dispatch_producers),
                         movie_property_gates=len(movie_property_gates),
                         source_configurations=len(source_configurations),
                         source_resource_pools=len(source_resource_pools))))


if __name__ == '__main__':
    main()
