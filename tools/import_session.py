"""Importa conhecimento e recortes da sessão anterior, sem alterar os originais."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--session", required=True, type=Path)
    args = parser.parse_args()
    source = args.session.resolve()
    captures = source / "outputs/teste_maaframework"
    previous = source / "outputs/teste_janela_epic7"
    definitions = {
        "orbis_button": (captures / "04_interface_restaurada.png", [827, 593, 876, 659]),
        "lobby_label": (captures / "04_interface_restaurada.png", [1081, 420, 1174, 448]),
        "orbis_header": (previous / "09_abrir_orbis_depois.png", [63, 64, 205, 91]),
        "tavern_wall": (captures / "03_apos_mover_cursor.png", [930, 110, 1000, 210]),
        "tavern_shelf": (captures / "03_apos_mover_cursor.png", [598, 100, 646, 138]),
    }
    images = ROOT / "resources/epic-seven/image"
    images.mkdir(parents=True, exist_ok=True)
    manifest = {"origin": "screen_crop", "reference_size": [1212, 682], "templates": {}}
    for name, (path, box) in definitions.items():
        target = images / f"{name}.png"
        Image.open(path).crop(tuple(box)).save(target)
        manifest["templates"][name] = {"source_file": path.name, "crop_xyxy": box,
            "source_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
            "purpose": "runtime_template", "pack_texture": False}
    (ROOT / "assets").mkdir(exist_ok=True)
    (ROOT / "assets/template-provenance.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    fixtures = ROOT / "tests/fixtures/local"
    fixtures.mkdir(parents=True, exist_ok=True)
    cases = [(captures/"04_interface_restaurada.png", "lobby"),
             (captures/"background_4_after.png", "orbis_guide"),
             (captures/"03_apos_mover_cursor.png", "lobby_idle"),
             (previous/"07_escape_depois.png", "unknown"),
             (captures/"covered_01_desktop.png", "unknown")]
    fixture_manifest = []
    for i, (path,state) in enumerate(cases):
        name = f"{i:02d}_{state}.png"
        shutil.copy2(path,fixtures/name)
        fixture_manifest.append({"file":name,"expected_state":state})
    (fixtures / "manifest.json").write_text(json.dumps(fixture_manifest,indent=2),encoding="utf-8")
    catalogs = ROOT / "data/catalogs"
    catalogs.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source/"outputs/roteiro_demo_steam/plano_agente.json", catalogs/"steam-demo-quests.json")
    layouts = ROOT / "data/layouts"
    layouts.mkdir(parents=True, exist_ok=True)
    for name in ("battle_ready", "result_base", "growth_masterbook", "growth_masterbook_quest_item"):
        original = json.loads((source/"work/architecture"/f"{name}.layout.json").read_text(encoding="utf-8"))
        (layouts/f"{name}.json").write_text(json.dumps(original,ensure_ascii=False,indent=2),encoding="utf-8")
    evidence = ROOT / "assets/local/baseline"
    evidence.mkdir(parents=True, exist_ok=True)
    for name in ("comparison_maa.json", "comparison_native.json", "covered_and_background.json"):
        shutil.copy2(captures/name,evidence/name)
    print(json.dumps({"templates":len(definitions),"fixtures":len(cases),"catalog_imported":True}))


if __name__ == "__main__":
    main()
