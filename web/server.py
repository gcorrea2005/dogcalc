"""DogCalC web server — minimal HTTP API + static file serving.

Run: python web/server.py
Open: http://localhost:8765
"""

import json
import sys
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.model.document import Document
from src.model.entities.node import SupportType
from src.model.entities.load_case import LoadCase, NodalLoad
from src.engine.solver import run_analysis_for_document

STATE = {"doc": Document(), "result": None}
STD_PATH = str(Path(__file__).parent.parent / "examples" / "portico_2v_2p.std")


class APIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(Path(__file__).parent), **kwargs)

    def do_GET(self):
        if self.path.startswith("/api/"): self._api_get()
        else: super().do_GET()

    def do_POST(self):
        if self.path.startswith("/api/"): self._api_post()
        else: super().do_POST()

    def do_PATCH(self):
        if self.path.startswith("/api/"): self._api_patch()
        else: self.send_error(404)

    def do_DELETE(self):
        if self.path.startswith("/api/"): self._api_delete()
        else: self.send_error(404)

    def _api_get(self):
        p = self.path.replace("/api", "")
        doc = STATE["doc"]
        if p == "/nodes":
            data = [{"id":n.id,"label":n.label,"x":n.x,"y":n.y,"z":n.z,
                     "support_type":n.support_type.value} for n in doc.nodes.values()]
        elif p == "/members":
            data = []
            for m in doc.members.values():
                si = list(doc.nodes.keys()).index(m.start_node_id)
                ei = list(doc.nodes.keys()).index(m.end_node_id)
                data.append({"id":m.id,"label":m.label,
                            "start_node_id":m.start_node_id,"end_node_id":m.end_node_id,
                            "start_node_idx":si,"end_node_idx":ei})
        else: self.send_error(404); return
        self._json(data)

    def _api_post(self):
        body = self._body()
        p = self.path.replace("/api", "")
        doc = STATE["doc"]
        try:
            if p == "/nodes":
                n = doc.add_node(body.get("x",0),body.get("y",0),body.get("z",0))
                self._json({"id":n.id,"label":n.label})
            elif p == "/members":
                m = doc.add_member(body["start_node_id"],body["end_node_id"])
                self._json({"id":m.id,"label":m.label})
            elif p == "/analyze":
                if doc.member_count == 0:
                    self._json({"success":False,"errors":["No members"]}); return
                if not doc.materials: doc.add_material("Steel",200e9,0.3,7850,275e6)
                if not doc.sections: doc.add_section("IPE300",5380e-6,8360e-8,8360e-8,604e-8,20e-8)
                for m in doc.members.values():
                    if not m.material_id: m.material_id = list(doc.materials.keys())[0]
                    if not m.section_id: m.section_id = list(doc.sections.keys())[0]
                if not doc.load_cases:
                    lc = doc.add_load_case("Default","dead")
                    if doc.nodes:
                        last = list(doc.nodes.keys())[-1]
                        lc.nodal_loads["l"] = NodalLoad(node_id=last, fy=-10)
                STATE["result"] = run_analysis_for_document(doc)
                r = STATE["result"]
                nr = {nid:{"dx":v.dx,"dy":v.dy,"dz":v.dz,
                           "rxn_fx":v.rxn_fx,"rxn_fy":v.rxn_fy,"rxn_fz":v.rxn_fz}
                      for nid,v in r.node_results.items()}
                self._json({"success":r.success,"max_disp":r.max_displacement(),
                            "node_results":nr,"errors":r.errors})
            elif p == "/save":
                from src.io.project_file import save_document
                save_document(doc, "project.dogcalc")
                self._json({"ok":True})
            elif p == "/load":
                from src.io.project_file import load_document
                if Path("project.dogcalc").exists():
                    STATE["doc"] = load_document("project.dogcalc")
                    d = STATE["doc"]
                    self._json({"ok":True,"nodes":d.node_count,"members":d.member_count})
                else: self._json({"ok":False,"error":"No project.dogcalc found"})
            elif p == "/load_std":
                from src.io.staad_file import parse_std
                STATE["doc"] = parse_std(STD_PATH)
                d = STATE["doc"]
                self._json({"ok":True,"nodes":d.node_count,"members":d.member_count})
            elif p == "/save_std":
                from src.io.staad_file import write_std
                write_std(doc, "model.std")
                self._json({"ok":True})
            elif p == "/export":
                if STATE["result"] and STATE["result"].success:
                    from src.io.export import export_results_to_excel
                    export_results_to_excel(doc, STATE["result"], "results.xlsx")
                    self._json({"ok":True})
                else: self._json({"ok":False,"error":"No results"})
            else: self.send_error(404)
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def _api_patch(self):
        body = self._body()
        p = self.path.replace("/api", "")
        if p.startswith("/nodes/"):
            nid = p.split("/nodes/")[1]
            if nid in STATE["doc"].nodes and body.get("support_type"):
                try:
                    STATE["doc"].nodes[nid].support_type = SupportType[body["support_type"].upper()]
                    self._json({"ok":True})
                except KeyError: self._json({"error":"Invalid support type"}, 400)
            else: self.send_error(404)
        else: self.send_error(404)

    def _api_delete(self):
        p = self.path.replace("/api", "")
        if p.startswith("/nodes/"):
            nid = p.split("/nodes/")[1]
            if nid in STATE["doc"].nodes:
                STATE["doc"].delete_entity(nid)
                self._json({"ok":True})
            else: self.send_error(404)
        else: self.send_error(404)

    def _body(self):
        length = int(self.headers.get("Content-Length", 0))
        return json.loads(self.rfile.read(length)) if length else {}

    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PATCH,DELETE,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def log_message(self, format, *args):
        print(f"[API] {args[0]}")


def main():
    port = 8765
    server = HTTPServer(("0.0.0.0", port), APIHandler)
    print(f"DogCalC: http://localhost:{port}")
    try: server.serve_forever()
    except KeyboardInterrupt:
        print("\nDone."); server.shutdown()

if __name__ == "__main__":
    main()
