# Copyright 2026 Alessio Mattoccia
"""Transparent lexical heuristics. Evidence != proof of a runtime defect."""
import re
from .dependencies import mask_comments
from .models import Finding

CALL = re.compile(r'\b([A-Za-z_]\w*)\s*\(')
FUNCTION = re.compile(r'\b([A-Za-z_]\w*)\s*\([^;{}]*\)\s*(?:__attribute__\s*\(\([^{}]*\)\))?\s*\{')
IGNORE = {'if', 'for', 'while', 'switch', 'sizeof', '_Static_assert', 'catch'}
ALLOC = {'malloc', 'calloc', 'realloc', 'aligned_alloc'}
BLOCK = {'sleep', 'usleep', 'nanosleep', 'read', 'recv', 'accept', 'pthread_mutex_lock', 'HAL_Delay', 'vTaskDelay'}

def stripped(text: str):
    text = mask_comments(text)
    return re.sub(r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'', lambda m: ' ' * len(m[0]), text)

def functions(text):
    out = []
    for m in FUNCTION.finditer(text):
        if m[1] in IGNORE: continue
        end, depth = m.end(), 1
        while end < len(text) and depth:
            if text[end] == '{': depth += 1
            elif text[end] == '}': depth -= 1
            end += 1
        out.append((m[1], m.start(), m.end(), end))
    return out

def analyze(files: dict):
    found, definitions = [], {}
    for file, original in files.items():
        text = stripped(original)
        fs = functions(text)
        def add(offset, rule, message, evidence, severity='medium'):
            found.append(Finding(file, text[:offset].count('\n') + 1, offset - text[:offset].rfind('\n'), severity,
                                 'embedded_risk', rule, 'esae-heuristics', message, evidence,
                                 'heuristic_indicator', 'requires_engineering_review'))
        for name, start, body, end in fs:
            calls = [(x[1], body + x.start()) for x in CALL.finditer(text[body:end]) if x[1] not in IGNORE]
            definitions[(file, name)] = {'calls': {x[0] for x in calls}, 'start': start}
            isr = bool(re.search(r'IRQHandler$|_ISR$|_isr$|^ISR_|^isr_|InterruptHandler$', name))
            # The function-name rule is evidence of a naming convention only.
            for call, offset in calls:
                if call in ALLOC:
                    add(offset, 'embedded.dynamic-allocation', f'Dynamic allocation via {call}; review failure handling, lifetime and determinism.', {'function': name, 'call': call})
                if call in BLOCK:
                    add(offset, 'embedded.possibly-blocking-call', f'{call} may block; timing depends on platform and arguments.', {'function': name, 'call': call})
                if isr and call in ALLOC | BLOCK | {'printf', 'fprintf', 'free'}:
                    add(offset, 'embedded.isr-suspicious-call', f'{call} in ISR-named function {name}; confirm ISR role and target constraints.', {'function': name, 'call': call, 'isr_evidence': 'function naming convention only'}, 'high')
            if re.search(r'\bnew\b', text[body:end]):
                offset = body + re.search(r'\bnew\b', text[body:end]).start()
                add(offset, 'embedded.dynamic-allocation', 'C++ new expression candidate; review allocation behavior.', {'function': name})
        for m in re.finditer(r'\b(?:volatile\s+[^;{}\n]+\s+([A-Za-z_]\w*)\s*(?:=[^;]+)?;)', text):
            if not any(start <= m.start() < end for _, start, _, end in fs):
                add(m.start(), 'embedded.shared-volatile-candidate', 'Global volatile object may be shared with interrupts/tasks. Volatile does not prove synchronization or a race.', {'symbol': m[1], 'scope': 'lexically global', 'race_condition_verified': False})
        for m in re.finditer(r'\b(?:__asm__|__asm|asm)\s*\(|\b__attribute__\s*\(\(|\b(?:uint32_t|uintptr_t)\s*\*\s*\)\s*0x[0-9a-fA-F]+', text):
            add(m.start(), 'embedded.platform-specific', 'Platform-specific construct; target/compiler behavior needs review.', {'token': m[0][:80]}, 'low')
        for m in re.finditer(r'\b(?:uint8_t|int8_t|uint16_t|int16_t)\b[^;\n]{0,100}[+*][^;\n]{0,100};', text):
            add(m.start(), 'embedded.narrow-integer-arithmetic', 'Arithmetic assigned to a narrow integer: range/conversion risk candidate, not a proven overflow.', {'expression': original[m.start():m.end()][:240]})
    # File-local direct and mutual recursion only. Name/overload resolution needs AST.
    for (file, name), info in definitions.items():
        todo, seen, cycle = list(info['calls']), set(), False
        while todo:
            callee = todo.pop()
            if callee == name: cycle = True; break
            if callee in seen: continue
            seen.add(callee)
            child = definitions.get((file, callee))
            if child: todo.extend(child['calls'])
        if cycle:
            text = stripped(files[file]); start = info['start']
            found.append(Finding(file, text[:start].count('\n') + 1, start - text[:start].rfind('\n'), 'medium', 'embedded_risk', 'embedded.recursion-candidate', 'esae-heuristics',
                                 f'File-local call-name cycle involving {name}; review stack depth and termination.',
                                 {'function': name, 'resolution': 'lexical names, not AST; macros/overloads can invalidate inference'},
                                 'heuristic_indicator', 'requires_engineering_review'))
    return found
