"""Explicit two-slot native recipe inputs, separate from historical v0/v2 drafts.

This transport schema is not a recipe, an approval record or a camera result.
No numerical v3 definition is distributed here. Every native field must be
supplied, and the caller must pin the exact input bytes before assembly.
"""
from dataclasses import dataclass
import hashlib
import json
import re

from epl9_color_extension import KEYS, controls as color_controls
from epl9_tonal_drafts import validate_curve
from epl9_wb_extension import controls as wb_controls

SCHEMA = 'epl9-native-film-inputs-v1'
NAMES = ('gold200-v3', 'portra400-v3')


def require(ok, message):
    if not ok:
        raise ValueError(message)


def unique_fields(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, 'duplicate JSON field: '+key)
        out[key] = value
    return out


def validate(document):
    """Reject incomplete inputs rather than borrowing missing v2 coefficients."""
    require(type(document) is dict and set(document) == {
        'schema', 'model', 'build', 'recipe_revision', 'source_definition_sha256', 'recipes'},
        'unexpected native recipe input fields')
    require(document['schema'] == SCHEMA, 'unsupported native recipe input schema')
    require(document['model'] == 'Olympus E-PL9' and document['build'] == '1101',
            'native inputs require Olympus E-PL9 build 1101')
    require(document['recipe_revision'] == 'v3', 'native inputs must explicitly identify v3; no v2 fallback')
    require(type(document['source_definition_sha256']) is str and
            re.fullmatch('[0-9a-f]{64}', document['source_definition_sha256']) is not None,
            'requires SHA-256 of the originating frozen recipe definition')
    rows = document['recipes']
    require(type(rows) is list and len(rows) == 2, 'requires exactly two accepted recipe slots')
    by_key = {}
    for row in rows:
        require(type(row) is dict and set(row) == {
            'name', 'watercolor_key', 'native_hsl', 'picture_mode_contrast', 'tone_level',
            'native_rgb_curves', 'native_wb_gain_q10', 'matrix_delta', 'six_axis'},
            'each recipe requires all explicit native fields')
        key = row['watercolor_key']
        require(type(key) is str and key in KEYS and key not in by_key,
                'wrong or duplicate Watercolor binding')
        require(row['name'] == NAMES[KEYS.index(key)], 'recipe name does not match its v3 slot')
        hsl = row['native_hsl']
        require(type(hsl) is list and len(hsl) == 12, 'requires twelve physical H/S/L records')
        for values in hsl:
            require(type(values) is list and len(values) == 3 and all(type(v) is int for v in values),
                    'H/S/L records require three integers')
            require(-1000 <= values[0] <= 1000 and -240 <= values[1] <= 240 and -100 <= values[2] <= 100,
                    'H/S/L outside the existing qualified experiment bounds')
        contrast, tone = row['picture_mode_contrast'], row['tone_level']
        require(type(contrast) is int and -2 <= contrast <= 2, 'contrast must be an integer in -2..2')
        require(type(tone) is dict and set(tone) == {'highlights', 'midtones', 'shadows'} and
                all(type(v) is int and -7 <= v <= 7 for v in tone.values()),
                'requires explicit integer highlights/midtones/shadows in -7..7')
        curves = row['native_rgb_curves']
        if curves != 'stock':
            require(type(curves) is list and len(curves) == 3 and all(type(c) is list for c in curves),
                    'native RGB must be stock or three native-order arrays')
            for curve in curves:
                validate_curve(curve)
        gains = row['native_wb_gain_q10']
        require(gains == 'stock' or type(gains) is list, 'native WB must be stock or two Q10 gains')
        by_key[key] = row
    ordered = [by_key[key] for key in KEYS]
    # Reuse qualified matrix, six-axis and Q10 bounds. No physical channel
    # names or automatic desktop-permille conversion are inferred here.
    color = dict(schema='epl9-native-color-controls-v1', recipes=[
        {k: row[k] for k in ('watercolor_key', 'matrix_delta', 'six_axis')} for row in ordered])
    color_controls(color)
    wb = dict(schema='epl9-native-wb-controls-v1', recipes=[
        dict(watercolor_key=row['watercolor_key'], gain_q10=[1024, 1024]
             if row['native_wb_gain_q10'] == 'stock' else row['native_wb_gain_q10']) for row in ordered])
    wb_controls(wb)
    return dict(rows=ordered, color_document=color if any(
        r['matrix_delta'] is not None or r['six_axis'] is not None for r in ordered) else None,
        wb_document=wb if any(r['native_wb_gain_q10'] != 'stock' for r in ordered) else None)


@dataclass(frozen=True)
class NativeRecipeInputs:
    """Retain pinned immutable bytes; return a fresh decoded copy for each use."""
    raw: bytes
    expected_sha256: str

    def __post_init__(self):
        require(type(self.raw) is bytes, 'recipe inputs must be immutable bytes')
        require(type(self.expected_sha256) is str and
                re.fullmatch('[0-9a-f]{64}', self.expected_sha256) is not None,
                'requires an explicit lowercase input SHA-256')
        require(hashlib.sha256(self.raw).hexdigest() == self.expected_sha256,
                'native recipe input SHA-256 mismatch')
        self.decoded()

    def decoded(self):
        document = json.loads(self.raw.decode('utf-8'), object_pairs_hook=unique_fields)
        return document, validate(document)

    def binding(self):
        document, _ = self.decoded()
        return dict(schema=SCHEMA, recipe_revision=document['recipe_revision'],
            input_sha256=self.expected_sha256,
            source_definition_sha256=document['source_definition_sha256'],
            historical_draft_fallback_used=False, source_definition_content_verified=False,
            owner_acceptance_independently_verified=False)


def midtone_bias(rows, register, label):
    """Keep historical equal-bias machine code; select unequal explicit inputs."""
    gold, portra = (r['tone_level']['midtones'] for r in rows)
    if gold == portra:
        return f' add {gold},d0'
    return '\n'.join([f' cmp 1,{register}', f' beq {label}_gold', f' add {portra},d0',
        f' bra {label}_done', f'{label}_gold:', f' add {gold},d0', f'{label}_done:'])


def bind_midtone_bias(source, rows, register, label):
    prefix = ' movhu (6,a1),d0\n exth d0\n'
    boundary = prefix+' add 1,d0\n'
    require(source.count(boundary) == 1, 'review native midtone insertion boundary')
    return source.replace(boundary, prefix+midtone_bias(rows, register, label)+'\n')
