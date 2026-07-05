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

        # ── Extract node results ──
        node_results = {}
        for name, node in model.nodes.items():
            nr = NodeResult(
                node_id=name,
                dx=node.DX.get(primary_combo, 0.0),
                dy=node.DY.get(primary_combo, 0.0),
                dz=node.DZ.get(primary_combo, 0.0),
                rx=node.RX.get(primary_combo, 0.0),
                ry=node.RY.get(primary_combo, 0.0),
                rz=node.RZ.get(primary_combo, 0.0),
                rxn_fx=node.RxnFX.get(primary_combo, 0.0),
                rxn_fy=node.RxnFY.get(primary_combo, 0.0),
                rxn_fz=node.RxnFZ.get(primary_combo, 0.0),
                rxn_mx=node.RxnMX.get(primary_combo, 0.0),
                rxn_my=node.RxnMY.get(primary_combo, 0.0),
                rxn_mz=node.RxnMZ.get(primary_combo, 0.0),
            )
            node_results[name] = nr

        # ── Extract member results (20 segments for diagrams) ──
        member_results = {}
        for name, member in model.members.items():
            segments = []
            try:
                shear = member.shear_results(primary_combo, 20)
                moment = member.moment_results(primary_combo, 20)
                if shear and moment:
                    for i in range(20):
                        segments.append({
                            'x': i / 19,
                            'axial': shear['Fx'][i],
                            'shear_y': shear['Fy'][i],
                            'shear_z': shear['Fz'][i],
                            'torsion': shear['Mx'][i],
                            'moment_y': moment['My'][i],
                            'moment_z': moment['Mz'][i],
                        })
            except Exception:
                pass

            member_results[name] = MemberResult(member_id=name, segments=segments)

        return AnalysisResult(
            success=True,
            load_case_name=primary_combo,
            node_results=node_results,
            member_results=member_results,
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
    combo_names = list(doc.load_cases.keys())
    return run_analysis(model, combo_names)
