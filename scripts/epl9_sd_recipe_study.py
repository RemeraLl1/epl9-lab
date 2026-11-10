"""Compare experimental SD records with frozen v3 data and native setters.

All files are simulated under ignored local/. Native tests execute color
configuration helpers and a read backend with declared host services. No file
loader hook or hardware image processing is supplied by this experiment.
"""
import argparse
import hashlib
import json
from pathlib import Path
import struct

from epl9_sd_recipes import (ROOT, BASE, MAIN, MAIN_SHA, FILE_BYTES, CARD_DIRECTORY,
    Slot, compile_author, load_session, materialize, pack_recipe, unpack_recipe, require)
from epl9_integrated_probe import native, attempt, RETURN
from epl9_offline_prototype import OUTPUT, SP, check_packing
from mn103_subset import Region, parse_listing
from epl9_wifi_prototype import Evidence, NativeReader

CANDIDATE_SHA = '501707d09a0eb648e46196752b7ece17cd5368f6d54dbabce7c73e9806f65686'
COLOR_TEMPLATE = 0x608ee360
RAM_TABLE, RAM_GAMMA = 0x18000000, 0x18000bd8
HSL_POINTERS = (3124,3128,3132,3136,3140,3144,3148,3152,3156,3160)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def configure(image, code, table, gamma, table_address, gamma_addresses, ram):
    output = bytearray(5200)
    regions = [Region(OUTPUT,output,True,'configuration')]
    if ram:
        regions += [Region(table_address,bytearray(table),False,'retained RAM HSL fixture'),
                    Region(gamma_addresses[0],bytearray(gamma),False,'retained RAM curve fixture')]
    machine = native(image,code,regions,dict(a0=table_address,a1=OUTPUT,
        d0=struct.unpack_from('<H',table,3024)[0]))
    result = attempt(machine,0x6079e50e,0xf0,80)
    require(result.get('pc') == RETURN and machine.r['sp'] == SP,'HSL helper failed')
    check_packing(output,table,[struct.unpack_from('<h',table,n*28+14)[0] for n in range(12)],
                  table_address=table_address)
    before = bytearray(output)
    struct.pack_into('<I',before,4,struct.unpack_from('<I',before,4)[0] & ~0x1000)
    struct.pack_into('<3I',before,2596,*gamma_addresses)
    machine.r.update(a0=OUTPUT,a1=gamma_addresses[0],d0=gamma_addresses[1],d1=gamma_addresses[2])
    result = attempt(machine,0x6079d7a0,0xa0,8)
    require(result.get('pc') == RETURN and machine.r['sp'] == SP and output == before,'gamma setter failed')
    normalized = bytearray(output)
    for at in (*HSL_POINTERS,2596,2600,2604):
        normalized[at:at+4] = bytes(4)
    for pointer in gamma_addresses:
        content = bytes(machine.memory.read(pointer+n,1) for n in range(512))
        require(content == gamma,'native gamma pointer content mismatch')
    return dict(native_instructions=len(machine.trace),configuration_bytes_checked=5200,
                normalized_sha256=sha(normalized),native_return=True,
                source='host-declared retained RAM' if ram else 'frozen embedded module')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--native-listings',type=Path,required=True)
    ap.add_argument('--read-listings',type=Path,required=True,
                    help='existing byte-checked Wi-Fi read-backend listings')
    ap.add_argument('--out',type=Path,required=True)
    args = ap.parse_args()
    require(not args.out.exists() and args.out.resolve().is_relative_to((ROOT/'local').resolve()),'new local output required')
    image=MAIN.read_bytes()
    require(len(image)==26214336 and sha(image)==MAIN_SHA,'wrong stock main')
    candidate_path=ROOT/'local/epl9-native-film-curves-probe-20261107/main-with-module-OFFLINE-ONLY.decoded.bin'
    candidate=candidate_path.read_bytes()
    require(len(candidate)==26214336 and sha(candidate)==CANDIDATE_SHA,'wrong frozen v3 candidate')
    read_evidence=Evidence(args.read_listings)
    code,listing_hashes={},{}
    for name,start,end in (('color_consumer',0x6079e50e,0x6079e6a0),('gamma_setter',0x6079d7a0,0x6079d7da)):
        listing=(args.native_listings/(name+'.tsv')).read_text(encoding='utf-8')
        parsed=parse_listing(listing,image,BASE)
        require(start in parsed and all(start<=pc<end for pc in parsed),'wrong helper window')
        parse_listing(listing,candidate,BASE)  # v3 must retain these exact native helpers
        code.update(parsed)
        listing_hashes[name]=sha(listing.encode())
    source_paths=[ROOT/'recipes'/n for n in ('epl9-film-drafts-v0.json','epl9-film-drafts-v1.json',
        'epl9-film-drafts-v2.json','epl9-native-wb-trial-v1.json')]
    hsl,curve,tone,wb=[json.loads(p.read_text())['recipes'] for p in source_paths]
    require(all([r['watercolor_key'] for r in rows]==[r['watercolor_key'] for r in hsl] for rows in (curve,tone,wb)),
            'recipe source ordering differs')
    args.out.mkdir(parents=True)
    recipes,checks=[],[]
    for n,name in enumerate(('Gold 200 v3','Portra 400 v3')):
        author=dict(schema='epl9-sd-recipe-author-v0',recipe_id=1001+n,name=name,
                    native_hsl=hsl[n]['native_hsl'],contrast=tone[n]['picture_mode_contrast'],
                    tone=tone[n]['tone_level'],wb_q10=wb[n]['gain_q10'],gamma_knots=curve[n]['tone_knots'])
        recipe=compile_author(author,image)
        packed=pack_recipe(recipe)
        decoded=unpack_recipe(packed)
        require(decoded==recipe,'recipe transport mismatch')
        file_reader=NativeReader(read_evidence,packed,'r')
        native_file_bytes=file_reader.read(FILE_BYTES+1)
        require(native_file_bytes==packed and unpack_recipe(native_file_bytes)==recipe,
                'native read backend changed recipe data')
        require(file_reader.read(1)==b'','native read backend did not stop at EOF')
        table,gamma=materialize(decoded,image[COLOR_TEMPLATE-BASE:COLOR_TEMPLATE-BASE+3028])
        table_address=0x604a1300+(0x1000 if n==0 else 0x2000)
        gamma_address=0x604a1300+(0x3000 if n==0 else 0x3600)
        require(table==candidate[table_address-BASE:table_address-BASE+3028],'HSL differs from frozen v3')
        require(all(gamma==candidate[gamma_address-BASE+i*512:gamma_address-BASE+(i+1)*512] for i in range(3)),
                'shared gamma differs from frozen v3')
        embedded=configure(candidate,code,table,gamma,table_address,tuple(gamma_address+i*512 for i in range(3)),False)
        loaded=configure(candidate,code,table,gamma,RAM_TABLE,(RAM_GAMMA,)*3,True)
        require(embedded['normalized_sha256']==loaded['normalized_sha256'],'non-pointer configuration differs')
        (args.out/f'recipe-{n+1}-author.json').write_text(json.dumps(author,indent=2)+'\n')
        (args.out/f'recipe-{n+1}-EXPERIMENTAL.RCP').write_bytes(packed)
        recipes.append(recipe)
        checks.append(dict(name=name,file_bytes=len(packed),file_sha256=sha(packed),
            hsl_matches_frozen_v3=True,all_three_gamma_contents_match=True,
            control_inputs_equal_current_definitions=True,embedded=embedded,ram=loaded,
            native_read_backend=dict(exact_file_bytes=True,eof_checked=True,
                counters=dict(file_reader.counts),open_and_storage_metadata='host fixture',
                sd_sector_service='host local-byte model, not hardware'),
            wb_and_tone_instructions_from_file_executed=False))
    slots=(Slot('fixed_gold',recipes[0]),Slot('fixed_portra',recipes[1]),
           Slot('custom1',recipes[0],1),Slot('custom2',recipes[1],2))
    card=args.out/'simulated-card'
    (card/CARD_DIRECTORY).mkdir(parents=True)
    scenarios={'no_card':load_session(slots,None),'no_files':load_session(slots,card)}
    (card/CARD_DIRECTORY/'SLOT01.RCP').write_bytes(pack_recipe(recipes[1]))
    scenarios['one_override']=load_session(slots,card)
    (card/CARD_DIRECTORY/'SLOT02.RCP').write_bytes(b'bad file')
    scenarios['one_bad_neighbor']=load_session(slots,card)
    require(scenarios['one_bad_neighbor'][2].recipe==recipes[1] and
            scenarios['one_bad_neighbor'][3].recipe==recipes[1],'independent fallback failed')
    (card/CARD_DIRECTORY/'SLOT01.RCP').write_bytes(pack_recipe(recipes[0]))
    require(scenarios['one_override'][2].recipe==recipes[1],'published session mutated')
    scenarios['next_power_on_model']=load_session(slots,card)
    report=dict(scope='Host format/resolver, native file-read backend and HSL/gamma helpers; not a native SD loader',
        model='Olympus E-PL9',displayed_version='1.1 (owner report)',downloaded_main_build=1101,
        stock_main=dict(bytes=len(image),sha256=MAIN_SHA),
        candidate=dict(bytes=len(candidate),sha256=CANDIDATE_SHA),
        source_hashes={p.name:sha(p.read_bytes()) for p in source_paths},
        script_sha256=sha(Path(__file__).read_bytes()),native_listing_hashes=listing_hashes,
        read_backend_listing_hashes=read_evidence.hashes,
        codec_sha256=sha((ROOT/'scripts/epl9_sd_recipes.py').read_bytes()),file_bytes=FILE_BYTES,
        recipe_checks=checks,
        scenarios={k:[dict(slot=x.slot_id,recipe=x.recipe.name,source=x.source,status=x.status) for x in v]
                   for k,v in scenarios.items()},
        fallback_names_are_study_examples_not_final_library_selection=True,
        proposed_memory=dict(native_hsl_bytes=3028,shared_gamma_bytes=512,descriptor_allowance=128,
            aligned_slot_bytes=3712,four_slots=14848,aligned_staging_bytes=704,registry_allowance=128,
            total_payload_budget=15680,allocator_class_bytes=16384,allocation_success_unverified=True),
        camera_accessed=False,firmware_modified=False,native_sd_loader_implemented=False,
        full_frame_and_pixel_execution=False,trigger_mount_task_and_dynamic_labels_unverified=True)
    require(sha(candidate_path.read_bytes())==CANDIDATE_SHA,'frozen candidate changed during study')
    (args.out/'study.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(recipe_files=len(checks),native_helper_runs=4,
        file_bytes=FILE_BYTES,scenario_count=len(scenarios),candidate_unchanged=True,camera_accessed=False)))


if __name__ == '__main__':
    main()
