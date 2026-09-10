"""
Carga do dataset no Supabase pela funcao temporaria bulk_ingest_questions.

Existe porque a chave service_role nao esta disponivel neste ambiente. A funcao
e `security definer` e protegida por token, e deve ser removida assim que a
carga terminar (ver README). Quando a service_role estiver no .env, prefira
push_db.py, que dispensa qualquer funcao extra no banco.

Uso:
    python load_via_rpc.py out/questions_rw.jsonl [out/questions.jsonl ...]
"""
import io
import json
import pathlib
import shutil
import sys

import requests

HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE / "out" / "assets"
WEB_FIGURES = HERE.parent / "web" / "public" / "figures"

URL = "https://ejxawoztyqeoxvgjcjuo.supabase.co"
ANON = "sb_publishable_So0CM43jYKKG6c56s0_Trg_kh5a_Fmg"
TOKEN = "k7Qm2xR9vLpZ4TnW8sYc3BdF6HjA5gEu"
BATCH = 25


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
    paths = sys.argv[1:] or ["out/questions_rw.jsonl"]

    rows = []
    for p in paths:
        f = pathlib.Path(p)
        if not f.exists():
            print(f"  ignorando {p}: nao existe")
            continue
        n = 0
        for line in f.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
                n += 1
        print(f"  {n} de {f.name}")

    if not rows:
        sys.exit("nada para carregar")

    # figuras -> estaticos do Next
    WEB_FIGURES.mkdir(parents=True, exist_ok=True)
    copied = 0
    for r in rows:
        for a in r.get("assets") or []:
            src = ASSETS / a["file"]
            if src.exists():
                shutil.copy2(src, WEB_FIGURES / a["file"])
                copied += 1
    print(f"{copied} figuras copiadas para web/public/figures")

    headers = {
        "apikey": ANON,
        "Authorization": f"Bearer {ANON}",
        "Content-Type": "application/json",
    }

    total = 0
    for i in range(0, len(rows), BATCH):
        chunk = rows[i:i + BATCH]
        resp = requests.post(
            f"{URL}/rest/v1/rpc/bulk_ingest_questions",
            headers=headers,
            data=json.dumps(
                {"p_token": TOKEN, "p_rows": chunk}, ensure_ascii=False
            ).encode("utf-8"),
            timeout=180,
        )
        if resp.status_code >= 300:
            print(f"\nFALHOU no lote {i}: {resp.status_code}")
            print(resp.text[:900])
            sys.exit(1)
        total += resp.json()
        print(f"  {min(i + BATCH, len(rows))}/{len(rows)}", flush=True)

    print(f"\n{total} questoes gravadas.")


if __name__ == "__main__":
    main()
