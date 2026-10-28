"""Instala o modelo inglês oficial MaaCommonAssets em uma revisão fixada."""

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REVISION = "dabcd4681ac990dc4361de26416d986abd80e4aa"
FILES = {
    "det.onnx": (2423224, "a9cb036094854df191b5d381fcde5dd41ac6d944"),
    "rec.onnx": (8956702, "ebd507e4ddd722c9046529cbc0ac3ba656f16cc3"),
    "keys.txt": (190, "7677d31b9d3f08eef2823c2cf051beeab1f0470b"),
}


def install(name):
    size, expected = FILES[name]
    target = ROOT / "resources/epic-seven/model/ocr/en_us" / name
    url = f"https://raw.githubusercontent.com/MaaXYZ/MaaCommonAssets/{REVISION}/OCR/ppocr_v3/en_us/{name}"
    if target.exists():
        data = target.read_bytes()
    else:
        request = urllib.request.Request(url, headers={"User-Agent": "DriverEpicSeven"})
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read(size+1)
    actual = hashlib.sha1(f"blob {len(data)}\0".encode()+data).hexdigest()
    if len(data) != size or actual != expected:
        raise ValueError("Conteúdo diferente da revisão fixada: "+name)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    return {"file": name, "url": url, "bytes": len(data), "git_blob": actual,
            "sha256": hashlib.sha256(data).hexdigest()}


if __name__ == "__main__":
    with ThreadPoolExecutor(max_workers=3) as pool:
        files = list(pool.map(install, FILES))
    report = {"source": "MaaXYZ/MaaCommonAssets", "revision": REVISION,
              "model": "ppocr_v3/en_us", "files": files,
              "license_url": f"https://github.com/MaaXYZ/MaaCommonAssets/blob/{REVISION}/LICENSE"}
    output = ROOT / "assets/ocr-provenance.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
