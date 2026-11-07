#!/usr/bin/env python3
"""Put translated blocks back into all guidebook MDX files and add heading anchors."""
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; APP=ROOT/"app"; WORK=ROOT/"work"
def parse_blocks(text):
    d={}; pat=re.compile(r"^<<<BLOCK ([^>\s]+)>>>[ \t]*$",re.M); ms=list(pat.finditer(text))
    for i,m in enumerate(ms):
        end=ms[i+1].start() if i+1<len(ms) else len(text)
        d[m.group(1)]=re.sub(r"\n?<<<END>>>\s*$","",text[m.end():end]).strip("\n")
    return d
def prefix_of(text):
    last=0
    for m in re.finditer(r"^import .*?;?\s*$",text,re.M): last=m.end()
    if last: return text[:last]+"\n"
    lines=text.splitlines(keepends=True); end=0
    if lines and lines[0].strip()=="---":
        for i in range(1,len(lines)):
            if lines[i].strip()=="---": end=i+1; break
    return "".join(lines[:end])
def main():
    blocks=json.loads((WORK/"blocks.json").read_text())
    man=json.loads((WORK/"manifest.json").read_text())
    trans={}
    for c in man:
        p=Path(c["out"])
        if not p.exists(): print("MISSING",p.name); continue
        trans.update(parse_blocks(p.read_text()))
    heads=[b for b in blocks if b["type"]=="heading"]
    hmap=json.loads((WORK/"heading_map.json").read_text())
    aid={heads[i]["id"]:(hmap[i][2] or "") for i in range(len(heads))}
    files=[]
    for b in blocks:
        if b["file"] not in files: files.append(b["file"])
    for f in files:
        p=APP/f; src=p.read_text(); prefix=prefix_of(src)
        parts=[]
        for b in blocks:
            if b["file"]!=f: continue
            if b["id"] in trans: t=trans[b["id"]].strip("\n")
            else: t=b["text"]
            if b["type"]=="heading":
                x=aid.get(b["id"],"")
                if x: t=f'<a id="{x}"></a>\n\n{t}'
            if t and not t.endswith("\n"): t+="\n"
            parts.append(t)
        p.write_text(prefix+"".join(parts))
        print("wrote",f,len(parts),"blocks")
if __name__=="__main__": main()
