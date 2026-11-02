"""Opt-in CALL/RET layer for the bounded subset, following pinned GNU igen.

Only d2/d3/a2/a3 save masks are supported. External calls stop by default.
Optional software models must declare and validate their specific contracts.
"""
from mn103_subset import Machine, Fault, MASK


class CallMachine(Machine):
    def __init__(self, *args, models=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.events = []
        self.models = dict(models or {})
        if self.models.keys() & self.code.keys():
            raise ValueError('a model may not shadow loaded native code')

    @staticmethod
    def saved(mask):
        if mask & 15:
            raise Fault(f'unsupported register save mask {mask:#x}')
        return [r for bit, r in [(128, 'd2'), (64, 'd3'), (32, 'a2'), (16, 'a3')]
                if mask & bit]

    def enter(self, target, return_pc, mask=0, frame=0):
        """Synthetic caller using native CALL stack convention, not a camera call."""
        names = self.saved(mask)
        sp = self.r['sp']
        self.memory.write(sp, return_pc, 4)
        for i, name in enumerate(names, 1):
            self.memory.write(sp-4*i, self.r[name], 4)
        self.r['sp'] = (sp-frame) & MASK
        self.r['mdr'] = return_pc
        return target

    def run(self, start, stops=(), limit=200000):
        pc = start
        for _ in range(limit):
            if pc in stops:
                return {'status': 'stop', 'pc': pc, 'instructions': len(self.trace)}
            if pc not in self.code:
                return {'status': 'missing_code', 'pc': pc, 'instructions': len(self.trace)}
            raw, op, args = self.code[pc]
            nxt = pc+len(raw)
            if op in ('call', 'calls'):
                target = self.address(args[0]) if args[0].startswith('(') else self.read(args[0])
                if op == 'call':
                    if (raw[0], len(raw)) not in [(0xcd, 5), (0xdd, 7)]:
                        raise Fault('unsupported CALL encoding')
                    mask, frame = raw[-2:]
                else:
                    mask = frame = 0
                    if not (raw[:2] in [bytes([0xf0, 0xf0+i]) for i in range(4)]
                            or (raw[:2], len(raw)) in [(b'\xfa\xff', 4), (b'\xfc\xff', 6)]):
                        raise Fault('unsupported CALLS encoding')
                self.saved(mask)
                if target not in self.code:
                    if target in self.models:
                        model = self.models[target]
                        model.validate(self, mask, frame)
                        original_sp = self.r['sp']
                        self.enter(target, nxt, mask, frame)
                        detail = model.apply(self)
                        if self.r['sp'] != (original_sp-frame) & MASK:
                            raise Fault('software model changed SP')
                        # Model return uses the same stack convention as RET.
                        values = [self.memory.read(original_sp-4*i, 4)
                                  for i in range(1, len(self.saved(mask))+1)]
                        self.r.update(zip(self.saved(mask), values))
                        self.r['sp'] = original_sp
                        pc = self.memory.read(original_sp, 4)
                        if pc != nxt:
                            raise Fault('software model overwrote return address')
                        self.events.append(dict(op='modeled_call', target=target,
                                                pc=nxt-len(raw), model=model.name, **detail))
                        self.trace.append(nxt-len(raw))
                        continue
                    return {'status': 'external_call', 'pc': pc, 'target': target,
                            'instructions': len(self.trace)}
                self.events.append({'op': op, 'pc': pc, 'target': target})
                self.trace.append(pc)
                pc = self.enter(target, nxt, mask, frame)
            elif op in ('ret', 'retf'):
                if len(raw) != 3 or raw[0] != (0xdf if op == 'ret' else 0xde):
                    raise Fault('unsupported return encoding')
                names = self.saved(raw[1])
                sp = (self.r['sp']+raw[2]) & MASK
                target = self.memory.read(sp, 4) if op == 'ret' else self.r['mdr']
                values = [self.memory.read(sp-4*i, 4) for i in range(1, len(names)+1)]
                self.r.update(zip(names, values))
                self.r['sp'] = sp
                self.events.append({'op': op, 'pc': pc, 'target': target})
                self.trace.append(pc)
                pc = target
            elif op == 'movm':
                if len(raw) != 2 or raw[0] not in (0xce, 0xcf):
                    raise Fault('unsupported MOVM encoding')
                names = self.saved(raw[1])
                sp = self.r['sp']
                if raw[0] == 0xcf:
                    for name in names:
                        sp -= 4
                        self.memory.write(sp, self.r[name], 4)
                else:
                    for name in reversed(names):
                        self.r[name] = self.memory.read(sp, 4)
                        sp += 4
                self.r['sp'] = sp & MASK
                self.trace.append(pc)
                pc = nxt
            else:
                pc = super().run(pc, limit=1, single_step=True)['pc']
        raise Fault(f'instruction limit {limit} at {pc:#x}')
