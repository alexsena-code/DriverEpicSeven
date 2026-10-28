"""Bounded, offline inspection of Cocos Studio 2.1 CSB declarations.

Wire fields checked against cocos2d-x-3.17.2/CSParseBinary_generated.h.
This tool never imports the driver, connects to the game, or executes callbacks.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

SCHEMA_URL = 'https://github.com/cocos2d/cocos2d-x/blob/cocos2d-x-3.17.2/cocos/editor-support/cocostudio/CSParseBinary_generated.h'
SCHEMA_SHA256 = '9512c62f41f701cd32a530765c34c76c63d67f2263d07fe553958fd2522fd80f'
SUPPORTED = {'Node', 'Widget', 'SingleNode', 'Button', 'CheckBox', 'ImageView', 'Sprite',
             'Text', 'Panel', 'ScrollView', 'ListView', 'PageView', 'LoadingBar',
             'Slider', 'TextBMFont', 'TextField'}


class CSB:
    def __init__(self, data):
        if not 8 <= len(data) <= 8 * 1024 * 1024:
            raise ValueError('CSB size outside inspection limit')
        self.data = data

    def read(self, fmt, pos):
        if pos < 0 or pos + struct.calcsize(fmt) > len(self.data):
            raise ValueError('Field outside CSB')
        values = struct.unpack_from(fmt, self.data, pos)
        if any(isinstance(v, float) and not math.isfinite(v) for v in values):
            raise ValueError('Non-finite CSB value')
        return values[0] if len(values) == 1 else list(values)

    def field(self, table, slot):
        if table is None:
            return None
        vt = table - self.read('<i', table)
        length = self.read('<H', vt)
        if length < 4 or length % 2 or vt + length > len(self.data):
            raise ValueError('Invalid vtable')
        if slot >= length:
            return None
        offset = self.read('<H', vt + slot)
        return table + offset if offset else None

    def pointer(self, table, slot):
        pos = self.field(table, slot)
        return self.indirect(pos) if pos is not None else None

    def indirect(self, pos):
        target = pos + self.read('<I', pos)
        if target <= pos or target >= len(self.data):
            raise ValueError('Invalid forward pointer')
        return target

    def string_at(self, pos):
        if pos is None:
            return ''
        length = self.read('<I', pos)
        if length > 1024 * 1024 or pos + 4 + length >= len(self.data):
            raise ValueError('Invalid string length')
        if self.data[pos + 4 + length] != 0:
            raise ValueError('String missing terminator')
        return self.data[pos + 4:pos + 4 + length].decode('utf-8')

    def string(self, table, slot):
        return self.string_at(self.pointer(table, slot))

    def value(self, table, slot, fmt, default=None):
        pos = self.field(table, slot)
        return self.read(fmt, pos) if pos is not None else default

    def vector(self, table, slot, allow_null=False):
        pos = self.pointer(table, slot)
        if pos is None:
            return []
        count = self.read('<I', pos)
        if count > 10000 or pos + 4 + count * 4 > len(self.data):
            raise ValueError('Invalid vector length')
        return [None if allow_null and self.read('<I', pos + 4 + i * 4) == 0
                else self.indirect(pos + 4 + i * 4) for i in range(count)]

    def resource(self, table, slot):
        obj = self.pointer(table, slot)
        if obj is None:
            return None
        return {'path': self.string(obj, 4), 'plist': self.string(obj, 6),
                'resource_type': self.value(obj, 8, '<i', 0)}

    def details(self, kind, data):
        out = {}
        resources = {
            'Button': {'normal': 6, 'pressed': 8, 'disabled': 10, 'font': 12},
            'CheckBox': {'background': 6, 'background_selected': 8, 'checkmark': 10,
                         'background_disabled': 12, 'checkmark_disabled': 14},
            'ImageView': {'image': 6}, 'Sprite': {'image': 6},
            'Text': {'font': 6}, 'Panel': {'background': 6},
            'ScrollView': {'background': 6}, 'ListView': {'background': 6},
            'PageView': {'background': 6}, 'LoadingBar': {'image': 6},
            'TextBMFont': {'font': 6}, 'TextField': {'font': 6},
            'Slider': {'bar': 6, 'thumb_normal': 8, 'thumb_pressed': 10,
                       'thumb_disabled': 12, 'progress': 14},
        }
        if kind in resources:
            out['resources'] = {name: self.resource(data, slot)
                                for name, slot in resources[kind].items()}
        if kind in ('Button', 'Text'):
            text_slot, font_slot, size_slot, local_slot = ((14, 16, 18, 46) if kind == 'Button'
                                                        else (12, 8, 10, 42))
            out.update(text=self.string(data, text_slot), font_name=self.string(data, font_slot),
                       font_size=self.value(data, size_slot, '<i', 0),
                       localized=bool(self.value(data, local_slot, '<B', 0)))
        if kind == 'CheckBox':
            out.update(selected=bool(self.value(data, 16, '<B', 1)),
                       display_state=bool(self.value(data, 18, '<B', 1)),
                       selected_field_present=self.field(data, 16) is not None)
        if kind == 'Button':
            out['display_state'] = bool(self.value(data, 28, '<B', 1))
        if kind == 'LoadingBar':
            out.update(percent=self.value(data, 8, '<i', 80), direction=self.value(data, 10, '<i', 0))
        if kind == 'Slider':
            out.update(percent=self.value(data, 16, '<i', 50),
                       display_state=bool(self.value(data, 18, '<B', 1)))
        if kind == 'TextBMFont':
            out.update(text=self.string(data, 8), localized=bool(self.value(data, 10, '<B', 0)))
        if kind == 'TextField':
            out.update(text=self.string(data, 12), placeholder=self.string(data, 14),
                       font_name=self.string(data, 8), font_size=self.value(data, 10, '<i', 0),
                       password_enabled=bool(self.value(data, 16, '<B', 0)),
                       max_length_enabled=bool(self.value(data, 20, '<B', 0)),
                       max_length=self.value(data, 22, '<i', 0),
                       localized=bool(self.value(data, 30, '<B', 0)))
        if kind in ('Button', 'ImageView', 'Panel', 'ScrollView', 'ListView', 'PageView'):
            cap, size, enabled = (8, 10, 12) if kind == 'ImageView' else (22, 24, 26)
            out['scale9'] = {'enabled': bool(self.value(data, enabled, '<B', 0)),
                             'cap_insets': self.value(data, cap, '<ffff'),
                             'size': self.value(data, size, '<ff')}
        if kind in ('Panel', 'ScrollView', 'ListView', 'PageView'):
            out['clip_enabled'] = bool(self.value(data, 8, '<B', 0))
        if kind in ('ScrollView', 'ListView'):
            out.update(inner_size=self.value(data, 28, '<ff'),
                       direction=self.value(data, 30, '<i', 0),
                       bounce_enabled=bool(self.value(data, 32, '<B', 0)))
        return out

    def layout_component(self, widget):
        obj = self.pointer(widget, 44)
        if obj is None:
            return None
        specs = [('position_x_percent_enabled', 4, '<B'), ('position_y_percent_enabled', 6, '<B'),
                 ('position_x_percent', 8, '<f'), ('position_y_percent', 10, '<f'),
                 ('size_x_percent_enabled', 12, '<B'), ('size_y_percent_enabled', 14, '<B'),
                 ('size_x_percent', 16, '<f'), ('size_y_percent', 18, '<f'),
                 ('stretch_horizontal', 20, '<B'), ('stretch_vertical', 22, '<B'),
                 ('left_margin', 28, '<f'), ('right_margin', 30, '<f'),
                 ('top_margin', 32, '<f'), ('bottom_margin', 34, '<f')]
        out = {name: self.value(obj, slot, fmt, 0) for name, slot, fmt in specs}
        out.update(horizontal_edge=self.string(obj, 24), vertical_edge=self.string(obj, 26))
        return out

    def nodes(self):
        root = self.read('<I', 0)
        version = self.string(root, 4)
        if version != '2.1.0.0':
            raise ValueError('Unverified CSB version: ' + version)
        node_root = self.pointer(root, 10)
        if node_root is None:
            raise ValueError('Missing node tree')
        rows = []

        def walk(node, parent=None, path='', ancestors=()):
            if len(ancestors) > 100 or len(rows) >= 30000 or node in ancestors:
                raise ValueError('Node traversal limit or cycle')
            kind = self.string(node, 4)
            if kind not in SUPPORTED:
                # Retain base information, explicitly mark unparsed class options.
                supported = False
            else:
                supported = True
            data = self.pointer(self.pointer(node, 8), 4)
            widget = data if kind in ('Node', 'Widget') else self.pointer(data, 4)
            if widget is None:
                raise ValueError('Missing widget options')
            name = self.string(widget, 4)
            index = len(rows)
            path += '/' + name
            rows.append({
                'node_index': index, 'parent_index': parent, 'name': name, 'class': kind, 'path': path,
                'class_options_supported': supported,
                'declared_local_position': self.value(widget, 18, '<ff', [0, 0]),
                'declared_size': self.value(widget, 26, '<ff', [0, 0]),
                'declared_scale': self.value(widget, 20, '<ff', [1, 1]),
                'declared_anchor': self.value(widget, 22, '<ff', [0, 0]),
                'declared_rotation_skew': self.value(widget, 8, '<ff', [0, 0]),
                'declared_visible': bool(self.value(widget, 12, '<B', 1)),
                'declared_touch_enabled': bool(self.value(widget, 34, '<B', 0)),
                'declared_alpha': self.value(widget, 14, '<B', 255),
                'declared_color_argb': self.value(widget, 24, '<BBBB'),
                'declared_action_tag': self.value(widget, 6, '<i', 0),
                'declared_z_order': self.value(widget, 10, '<i', 0),
                'declared_callback': {'type': self.string(widget, 40), 'name': self.string(widget, 42)},
                'declared_layout': self.layout_component(widget),
                'declared_options': self.details(kind, data) if supported else None,
            })
            for child in self.vector(node, 6):
                walk(child, index, path, ancestors + (node,))

        walk(node_root)
        action = self.pointer(root, 12)
        timelines = []
        for timeline in self.vector(action, 8):
            property_name = self.string(timeline, 4)
            if property_name == 'FrameDuration':
                pos = self.pointer(timeline, 8)
                count = self.read('<I', pos) if pos is not None else 0
                if count > 10000 or (pos is not None and pos + 4 + count * 4 > len(self.data)):
                    raise ValueError('Invalid FrameDuration vector')
                values = [self.read('<I', pos + 4 + i * 4) for i in range(count)]
                timelines.append({'property': property_name, 'action_tag': self.value(timeline, 6, '<i', 0),
                                  'frame_count': None, 'declared_vector_count': count,
                                  'raw_uint32_values': values,
                                  'encoding': 'unresolved_vector_words_preserved_without_time_conversion'})
                continue
            frames = self.vector(timeline, 8, allow_null=True)
            timelines.append({'property': property_name,
                              'action_tag': self.value(timeline, 6, '<i', 0),
                              'frame_count': len(frames),
                              'null_frame_slots': [i for i, frame in enumerate(frames) if frame is None]})
        animations = [{'name': self.string(a, 4), 'start_frame': self.value(a, 6, '<i', 0),
                       'end_frame': self.value(a, 8, '<i', 0)} for a in self.vector(root, 14)]
        return {'schema_version': 1, 'version': version, 'source_sha256': hashlib.sha256(self.data).hexdigest(),
                'schema_reference': SCHEMA_URL, 'schema_reference_sha256': SCHEMA_SHA256,
                'scope': 'Static declarations and schema defaults; never runtime visibility, selected state, enabled state or screen coordinates.',
                'limitations': ['Class options not listed as supported remain unparsed.',
                                'Timeline frame values, world transforms and runtime bindings are not evaluated.'],
                'nodes': rows,
                'textures': [self.string_at(p) for p in self.vector(root, 6)],
                'texture_pngs': [self.string_at(p) for p in self.vector(root, 8)],
                'action': {'duration_frames': self.value(action, 4, '<i', 0),
                           'speed': self.value(action, 6, '<f', 0), 'timelines': timelines},
                'animations': animations}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', required=True, type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    if args.source.resolve() == args.out.resolve():
        raise ValueError('Output must differ from source')
    if args.source.stat().st_size > 8 * 1024 * 1024:
        raise ValueError('CSB exceeds inspection limit')
    result = CSB(args.source.read_bytes()).nodes()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'nodes': len(result['nodes']), 'output': str(args.out)}))


if __name__ == '__main__':
    main()
