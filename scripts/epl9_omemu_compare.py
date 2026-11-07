"""Compare a stock/icons/combined E133 UI run; never treats UI as ISP output."""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image


def compare(stock_dir, icons_dir, combined_dir):
    dirs = [Path(p) for p in (stock_dir, icons_dir, combined_dir)]
    docs = [json.loads((p/'session.json').read_text()) for p in dirs]
    for doc in docs:
        if doc['model'] != 'E133' or doc['error'] or doc.get('close_error') or not doc.get('engine_error_capture'):
            raise ValueError('not a completed E133 UI run')
        if len(doc['frames']) != 41 or any(f['unexpected_engine_errors'] for f in doc['frames']):
            raise ValueError('expected 41 frames without unexpected OSD engine errors')
    if docs[0]['patch'] is not None or docs[1]['patch']['applied'] != 10 or docs[2]['patch']['applied'] != 16:
        raise ValueError('expected stock, ten icons and combined sixteen patches')
    if any(d['actions'] != docs[0]['actions'] for d in docs[1:]):
        raise ValueError('different input sequence')
    rows = []
    observed = set()
    for index, frames in enumerate(zip(*(d['frames'] for d in docs))):
        a, b, c = frames
        if b['engine_errors'] != a['engine_errors'] or c['engine_errors'] != a['engine_errors']:
            raise ValueError(f'OSD engine diagnostics differ from stock at frame {index}')
        if any((f['gui'], f['state'], f['action']) != (a['gui'], a['state'], a['action']) for f in frames[1:]):
            raise ValueError(f'GUI/control mismatch at frame {index}')
        if b['sha256'] != c['sha256']:
            raise ValueError(f'combined module changes UI frame {index}')
        images = [np.asarray(Image.open(d/f['png']).convert('RGB')) for d,f in zip(dirs,frames)]
        if any(im.shape != (480,720,3) for im in images) or not np.array_equal(images[1],images[2]):
            raise ValueError(f'PNG size or combined pixels mismatch at {index}')
        changed = np.any(images[0] != images[1], axis=2)
        allowed = np.zeros((480,720), dtype=bool)
        # List symbols occupy the 44 px icon column, before the unchanged text.
        if b['inline_targets']:
            allowed[67:410,88:132] = True
            observed.update(b['inline_targets'])
        for draw in b['target_draws']:
            x,y,w,h = draw['x'],draw['y'],draw['width'],draw['lines']
            if not (0 <= x < x+w <= 720 and 0 <= y < y+h <= 480):
                raise ValueError('target icon rectangle outside screen')
            allowed[y:y+h,x:x+w] = True
            observed.add(str(draw['id']))
        if np.any(changed & ~allowed):
            raise ValueError(f'pixels outside target icon areas changed at frame {index}')
        ys,xs = np.nonzero(changed)
        box = [int(xs.min()),int(ys.min()),int(xs.max()+1),int(ys.max()+1)] if len(xs) else None
        rows.append(dict(index=index,png=a['png'],changed_pixels=int(changed.sum()),box=box))
    expected = {'@A076@','@A077@','4387','4388','4556','4557'}
    if observed != expected:
        raise ValueError(f'incomplete or unexpected observed icon set: {observed}')
    hits = docs[2]['frames'][-1]['film_site_hits']
    return dict(model='E133',frames_per_run=41,gui_states_equal=True,combined_matches_icons_pixels=True,
        changes_confined_to_icon_regions=True,observed_resources=sorted(observed),
        changed_frames=sum(bool(r['changed_pixels']) for r in rows),rows=rows,
        combined_film_site_hits=hits,hardware_pixel_execution=False,
        engine_error_history_identical_to_stock=True,stock_engine_errors=docs[0]['frames'][-1]['engine_errors'],
        source_sessions=[str(d/'session.json') for d in dirs])


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('stock',type=Path); ap.add_argument('icons',type=Path); ap.add_argument('combined',type=Path)
    a = ap.parse_args()
    print(json.dumps(compare(a.stock,a.icons,a.combined),indent=2))
