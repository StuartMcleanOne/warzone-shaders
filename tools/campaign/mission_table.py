"""Reads every campaign mission map and writes docs/CAMPAIGN_LIGHTING.md:
lighting, theater, ion storms, mid-mission lighting changes, and which Campaign preset fits."""
import glob, os, re, sys

MISSIONS = sys.argv[1] if len(sys.argv) > 1 else "/mnt/user-data/uploads/TW_Warzone_Fin/Maps/Missions"
ORDER = (["gdi1a", "gdi2a", "gdi3a", "gdi3b", "gdi4a", "gdi5a", "gdi5b", "gdi5c", "gdi6a", "gdi6b", "gdi7a", "gdi8a",
          "gdi9a", "gdi9b", "gdi9c", "gdi9d", "gdi10a", "gdi10b", "gdi11a", "gdi12a"],
         ["nod1a", "nod2a", "nod3a", "nod3b", "nod4a", "nod4b", "nod5a", "nod6a", "nod6b", "nod6c", "nod7a", "nod7b",
          "nod8a", "nod9a", "nod9b", "nod10a", "nod11a", "nod12a", "nod12b"],
         [f"fsgdi0{i}" for i in range(1, 10)], [f"fsnod0{i}" for i in range(1, 10)])
TITLES = ("Tiberian Sun - GDI", "Tiberian Sun - Nod", "Firestorm - GDI", "Firestorm - Nod")


def sections(t):
    d, cur = {}, None
    for l in t.split("\n"):
        l = l.split(";")[0].strip()
        m = re.match(r"^\[(.+)\]$", l)
        if m:
            cur = d.setdefault(m.group(1), {}); continue
        if cur is not None and "=" in l:
            k, v = l.split("=", 1); cur[k.strip()] = v.strip()
    return d


def actions(s):
    out = []
    for v in s.get("Actions", {}).values():
        p = v.split(",")
        try:
            n = int(p[0])
        except ValueError:
            continue
        for i in range(n):
            q = p[1 + i * 8: 9 + i * 8]
            if q:
                out.append(q)
    return out


def classify(r):
    if r["theater"] == "SNOW":
        return "WZ_Snow_Day" if r["amb"] >= 0.55 else "WZ_Snow_Night"
    if r["ion"]:
        return "WZ_Ion_Storm"
    if r["R"] >= 1.2 and r["R"] > r["B"] + 0.15:
        return "WZ_Burning_Dusk"
    if r["amb"] <= 0.46:
        return "WZ_Night"
    if r["amb"] <= 0.66:
        return "WZ_Overcast"
    if r["amb"] <= 0.84:
        return "WZ_Day"
    return "WZ_Baked_Day"


def main():
    rows = {}
    for f in glob.glob(os.path.join(MISSIONS, "*.map")):
        s = sections(open(f, encoding="latin-1").read().replace("\r", ""))
        L = s.get("Lighting", {})
        acts = actions(s)
        g = lambda k, d=1.0: float(L.get(k, d))
        r = dict(file=os.path.basename(f)[:-4].lower(), name=s.get("Basic", {}).get("Name", ""),
                 theater=s.get("Map", {}).get("Theater", "").upper(), amb=g("Ambient"), R=g("Red"), G=g("Green"), B=g("Blue"),
                 ion=any(a[0] == "44" for a in acts) or s.get("SpecialFlags", {}).get("IonStorms", "no").lower() == "yes",
                 targets=sorted({int(a[2]) for a in acts if a[0] == "73" and a[2].lstrip("-").isdigit()}))
        r["look"] = classify(r)
        rows[r["file"]] = r
    out = ["# Campaign lighting table", "",
           "Read straight from the mission maps in `Maps\\Missions` (each mission sets its own lighting; the launcher's",
           "lighting option does not apply to the campaign). Ambient 1.0 = full daylight. Tint is the map's red/green/blue light.",
           "\"Changes to\" = the mission's triggers fade the light to that level during play (e.g. night falls).", ""]
    counts = {}
    for title, order in zip(TITLES, ORDER):
        out += [f"## {title}", "", "| # | Mission | Theater | Ambient | Tint (R/G/B) | Ion storm | Changes to | Preset |", "|---|---|---|---|---|---|---|---|"]
        for i, k in enumerate(order, 1):
            r = rows.get(k)
            if not r:
                continue
            counts[r["look"]] = counts.get(r["look"], 0) + 1
            tint = f"{r['R']:.2f}/{r['G']:.2f}/{r['B']:.2f}"
            ch = ", ".join(f"{t}%" for t in r["targets"]) or "-"
            out.append(f"| {i} | {r['name']} (`{k}`) | {r['theater'].title()} | {r['amb']:.2f} | {tint} | {'yes' if r['ion'] else '-'} | {ch} | {r['look']} |")
        out.append("")
    out += ["## Presets needed", ""] + [f"- **{k}**: {v} missions" for k, v in sorted(counts.items(), key=lambda x: -x[1])]
    out += ["", "Rules: Snow theater splits at ambient 0.55; ion storm missions get Ion Storm; strong red tint = Burning Dusk;",
            "otherwise ambient <= 0.46 Night, <= 0.66 Overcast, <= 0.84 Day, above that Baked Day."]
    open(os.path.join(os.path.dirname(__file__), "..", "..", "docs", "CAMPAIGN_LIGHTING.md"), "w").write("\n".join(out) + "\n")
    print("\n".join(out))


if __name__ == "__main__":
    main()
