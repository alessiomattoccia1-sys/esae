from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from hashlib import sha256


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class Finding:
    file: str
    line: int
    column: int
    severity: str
    category: str
    rule_id: str
    source_tool: str
    message: str
    evidence: dict = field(default_factory=dict)
    confidence_type: str = "static_analysis"
    verification_status: str = "reported_by_tool_not_manually_verified"
    ai_explanation: dict | None = None
    id: str = ""
    scan_id: str = ""
    tool_reports: list[dict] = field(default_factory=list)

    def dict(self):
        return asdict(self)


def category(rule: str, message: str) -> str:
    value = (rule + " " + message).lower()
    for name, terms in [
        ("null_pointer", ("nullpointer", "null pointer", "null dereference", "core.nulldereference")),
        ("bounds", ("outofbounds", "out of bounds", "arrayindex", "array-bounds", "buffer overflow")),
        ("uninitialized", ("uninit", "uninitialized", "garbage value")),
        ("memory_leak", ("memleak", "memory leak", "potential leak")),
        ("resource", ("resourceleak", "resource leak", "doublefree", "useafterfree", "use-after-free")),
        ("overflow", ("overflow", "shifttoolarge", "integer-overflow")),
        ("unreachable", ("unreachable", "deadcode")),
        ("portability", ("portability", "sizeofpointer", "narrowing")),
    ]:
        if any(t in value for t in terms):
            return name
    return "suspicious_operation"


def deduplicate(findings: list[Finding], scan_id: str) -> list[Finding]:
    """Merge exact duplicate rules or specific cross-tool problems at same column.

    Sharing a line alone is insufficient. Problem grouping is not manual proof.
    All contributing tool reports are retained, even after an exact duplicate.
    """
    out = {}
    for f in findings:
        specific = {'null_pointer','bounds','uninitialized','memory_leak','resource','overflow'}
        semantic = (f.file,f.line,f.column,f.category,f.confidence_type)
        key = (*semantic,f.rule_id)
        cross_key = next((k for k,v in out.items() if k[:5]==semantic and f.category in specific
                          and f.confidence_type=='static_analysis' and f.source_tool not in {r['tool'] for r in v.tool_reports}),None)
        if cross_key is not None:key=cross_key
        report = {"tool": f.source_tool, "rule_id": f.rule_id, "message": f.message,
                  "severity": f.severity, "evidence": f.evidence}
        if key in out:
            out[key].tool_reports.append(report)
            ranks={'high':3,'medium':2,'low':1,'info':0}
            if ranks.get(f.severity,0)>ranks.get(out[key].severity,0):out[key].severity=f.severity
            continue
        f.scan_id = scan_id
        f.id = sha256((scan_id + repr(key)).encode()).hexdigest()[:24]
        f.tool_reports = [report]
        out[key] = f
    return sorted(out.values(), key=lambda f: (f.file, f.line, f.column, f.rule_id))
