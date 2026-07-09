"""Extract analysis results from Warren truss for LaTeX report."""
import sys, os, json

proj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, proj)
os.chdir(proj)

from src.io.staad_file import parse_std
from src.engine.solver import run_analysis_for_document

std_path = 'examples/cercha_warren.std'
doc = parse_std(std_path)

# Build UUID -> label maps
uuid_to_label_m = {m.id: m.label for m in doc.members.values()}
uuid_to_label_n = {n.id: n.label for n in doc.nodes.values()}
# Also build label -> original-staad-id map via the label (N1, N2, ...)
label_to_staad_id = {n.label: int(n.label[1:]) for n in doc.nodes.values()}

print(f"Parsed: {doc.node_count} nodes, {doc.member_count} members", file=sys.stderr)

# Run analysis
result = run_analysis_for_document(doc)
print(f"Analysis success: {result.success}", file=sys.stderr)

# ── Reactions for combo 105 ──
c105 = result.combo_results.get("105", {})
nodes_105 = c105.get("node_results", {})
rxns_by_label = {}
for uuid, nr in nodes_105.items():
    label = uuid_to_label_n.get(uuid, uuid)
    if abs(nr.rxn_fy) > 0.001:
        rxns_by_label[label] = nr.rxn_fy

# Map back to STAAD node numbers
rxns_by_id = {}
for label, fy in rxns_by_label.items():
    nid = label_to_staad_id.get(label, 0)
    rxns_by_id[nid] = fy

# ── Max displacement ──
max_disp = 0.0
for uuid, nr in nodes_105.items():
    d = (nr.dx**2 + nr.dy**2 + nr.dz**2)**0.5
    if d > max_disp:
        max_disp = d

# ── Envelope axial forces ──
env = doc.envelopes.get("1")

def get_member_type(label):
    m = int(label[1:])
    if 1 <= m <= 19 or 78 <= m <= 96:
        return "CS"
    elif 20 <= m <= 38 or 97 <= m <= 115:
        return "CI"
    elif 39 <= m <= 57 or 116 <= m <= 134:
        return "DIAG"
    elif 58 <= m <= 77 or 135 <= m <= 154:
        return "MONT"
    else:
        return "CROSS"

cs_members = []
ci_members = []
diag_members = []
mont_members = []

for uuid, axial in env.max_axial.items():
    label = uuid_to_label_m.get(uuid, uuid)
    mtype = get_member_type(label)
    entry = (label, round(axial, 1))
    if mtype == "CS":
        cs_members.append(entry)
    elif mtype == "CI":
        ci_members.append(entry)
    elif mtype == "DIAG":
        diag_members.append(entry)
    elif mtype == "MONT":
        mont_members.append(entry)

cs_members.sort(key=lambda x: int(x[0][1:]))
ci_members.sort(key=lambda x: int(x[0][1:]))
diag_members.sort(key=lambda x: abs(x[1]), reverse=True)
mont_members.sort(key=lambda x: abs(x[1]), reverse=True)

# Face A only (M1-M77)
cs_face_a = [(l, a) for l, a in cs_members if 1 <= int(l[1:]) <= 19]
ci_face_a = [(l, a) for l, a in ci_members if 20 <= int(l[1:]) <= 38]

# ── Code check ──
from src.engine.code_check import check_all_members
cc_results = check_all_members(doc, env)
passed = sum(1 for r in cc_results if r.status == "OK")
failed = sum(1 for r in cc_results if r.status == "OVERSTRESS")
max_ratio = max((r.ratio for r in cc_results), default=0)
worst = max(cc_results, key=lambda r: r.ratio) if cc_results else None

# ── Build output ──
data = {
    "tributary_width": 0.65,
    "reactions_105": {
        "N21": round(rxns_by_id.get(21, 0), 1),
        "N61": round(rxns_by_id.get(61, 0), 1),
        "N40": round(rxns_by_id.get(40, 0), 1),
        "N80": round(rxns_by_id.get(80, 0), 1),
        "total": round(sum(rxns_by_id.values()), 1),
    },
    "max_disp_mm": round(max_disp * 1000, 1),
    "max_disp_ratio": round(16.52 / max_disp) if max_disp > 0 else 999,
    "cs_axial": cs_face_a,
    "ci_axial": ci_face_a,
    "diag_top7": [(l, a) for l, a in diag_members[:7] if int(l[1:]) <= 134],
    "mont_top7": [(l, a) for l, a in mont_members[:7] if int(l[1:]) <= 154],
    "code_check": {
        "total": len(cc_results),
        "passed": passed,
        "failed": failed,
        "max_ratio": round(max_ratio, 2),
    },
    "worst_member": worst.label if worst else "?",
}

json.dump(data, sys.stdout, indent=2)
