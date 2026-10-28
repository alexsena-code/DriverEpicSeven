"""Extração local somente leitura; índice e chave vêm da instalação analisada."""

import argparse
import json
from pathlib import Path

import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pack", required=True, type=Path)
    parser.add_argument("--index", required=True, type=Path)
    parser.add_argument("--key", required=True, type=Path)
    parser.add_argument("--name", required=True)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    entries = json.loads(args.index.read_text(encoding="utf-8"))
    matches = [entry for entry in entries if entry["path"] == args.name]
    if len(matches) != 1:
        raise ValueError("Asset não identificado unicamente no índice.")
    entry = matches[0]
    size, offset = entry["size"], entry["data_offset"]
    if not 0 < size <= 64*1024*1024 or offset < 0 or offset+size > args.pack.stat().st_size:
        raise ValueError("Registro fora dos limites de extração de asset.")
    key = args.key.read_bytes()
    if not key:
        raise ValueError("Chave vazia.")
    with args.pack.open("rb") as stream:
        stream.seek(offset)
        raw = stream.read(size)
    if len(raw) != size:
        raise ValueError("Registro truncado.")
    decoded = np.frombuffer(raw,dtype=np.uint8).copy()
    decoded ^= np.resize(np.roll(np.frombuffer(key,dtype=np.uint8), -(offset%len(key))),size)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_bytes(decoded.tobytes())
    print(json.dumps({"source":args.name,"bytes":size,"output":str(args.out)}))


if __name__ == "__main__":
    main()
