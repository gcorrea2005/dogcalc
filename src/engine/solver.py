"""Solver: runs PyNite FEM analysis and extracts structured results.

PyNite v3.0 API:
  - model.nodes (lowercase)
  - model.members (lowercase)
  - node.DX, node.DY, node.DZ, node.RX, node.RY, node.RZ (displacements)
  - node.RxnFX, node.RxnFY, node.RxnFZ, node.RxnMX, node.RxnMY, node.RxnMZ (reactions)
  - member.shear_results(combo, n_points) → dict with Fx, Fy, Fz, Mx arrays
  - member.moment_results(combo, n_points) → dict with My, Mz arrays
"""

from Pynite import FEModel3D
from src.engine.results import AnalysisResult, NodeResult, MemberResult


def run_analysis(model: FEModel3D, combo_names: list[str]) -> AnalysisResult:
    """Run static analysis on the PyNite model and return structured results.

    Args:
        model: FEModel3D built by bridge.build_pynite_model()
        combo_names: list of load combination names to analyze

    Returns:
        AnalysisResult with node results, member results, and errors.
    """
    if not combo_names:
        return AnalysisResult(success=False, errors=["No load combinations specified"])

    primary_combo = combo_names[0]

    try:
        model.analyze(check_statics=True)

        all_combo_results = {}
        all_nodes = {}
        all_members = {}

        for combo in combo_names:
            node_results = {}
            for name, node in model.nodes.items():
                nr = NodeResult(
                    node_id=name,
                    dx=node.DX.get(combo, 0.0), dy=node.DY.get(combo, 0.0), dz=node.DZ.get(combo, 0.0),
                    rx=node.RX.get(combo, 0.0), ry=node.RY.get(combo, 0.0), rz=node.RZ.get(combo, 0.0),
                    rxn_fx=node.RxnFX.get(combo, 0.0), rxn_fy=node.RxnFY.get(combo, 0.0),
                    rxn_fz=node.RxnFZ.get(combo, 0.0), rxn_mx=node.RxnMX.get(combo, 0.0),
                    rxn_my=node.RxnMY.get(combo, 0.0), rxn_mz=node.RxnMZ.get(combo, 0.0),
                )
                node_results[name] = nr
            member_results = {}
            for name, member in model.members.items():
                segments = []
                try:
                    aa = member.axial_array(20, combo_name=combo)
                    sy = member.shear_array('Fy', 20, combo_name=combo)
                    sz = member.shear_array('Fz', 20, combo_name=combo)
                    my = member.moment_array('My', 20, combo_name=combo)
                    mz = member.moment_array('Mz', 20, combo_name=combo)
                    for i in range(20):
                        segments.append({
                            'x': i / 19,
                            'axial': -aa[1][i], 'shear_y': sy[1][i], 'shear_z': sz[1][i],
                            'torsion': 0.0, 'moment_y': my[1][i], 'moment_z': mz[1][i],
                        })
                except Exception:
                    pass
                member_results[name] = MemberResult(member_id=name, segments=segments)
            all_combo_results[combo] = {'node_results': node_results, 'member_results': member_results}
            all_nodes = node_results
            all_members = member_results

        primary_combo = combo_names[0]
        return AnalysisResult(
            success=True, load_case_name=primary_combo,
            node_results=all_nodes, member_results=all_members,
            combo_results=all_combo_results,
        )

    except Exception as e:
        return AnalysisResult(
            success=False,
            errors=[str(e)],
        )


def run_analysis_for_document(doc) -> AnalysisResult:
    """Convenience: build model from Document and run analysis in one call."""
    from src.engine.bridge import build_pynite_model

    model = build_pynite_model(doc)
    if doc.load_combinations:
        combo_names = list(doc.load_combinations.keys())
        # Also include individual load cases for results viewing
        for lc_id in doc.load_cases.keys():
            if lc_id not in combo_names:
                combo_names.append(lc_id)
    else:
        combo_names = list(doc.load_cases.keys())
    result = run_analysis(model, combo_names)

    # Compute envelopes by re-running per combo (uses model.analyze separately)
    for env in doc.envelopes.values():
        _compute_envelope(model, env, doc)

    return result


def _compute_envelope(model, env, doc) -> None:
    """Compute max/min axial forces across envelope's combos."""
    if not env.combo_ids:
        return
    max_axial = {}
    # Build a fresh model for envelope to not corrupt main results
    from src.engine.bridge import build_pynite_model
    env_model = build_pynite_model(doc)
    for cid in env.combo_ids:
        try:
            env_model.analyze(check_statics=False)
            for mid, member in env_model.members.items():
                try:
                    aa = member.axial_array(2, combo_name=cid)
                    axial = -aa[1][0]  # negate: PyNite positive=compression, we want positive=tension
                except Exception:
                    axial = 0
                if mid not in max_axial or abs(axial) > abs(max_axial.get(mid, 0)):
                    max_axial[mid] = axial
        except Exception:
            pass
    env.max_axial = max_axial
