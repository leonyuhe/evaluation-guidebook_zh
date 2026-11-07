#!/usr/bin/env python3
import json,re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; WORK=ROOT/"work"
CJK=re.compile(r"[\u4e00-\u9fff]"); WORD=re.compile(r"[A-Za-z][A-Za-z'’\-]*")
TAG=re.compile(r"</?([A-Za-z][\w:-]*)([^>]*)>"); LINK=re.compile(r"\]\(([^)]+)\)")
CITE=re.compile(r"\[\[?@[^\]]+\]\]?"); CODE=re.compile(r"`([^`]+)`")
def parse_blocks(text):
    d={}; order=[]; pat=re.compile(r"^<<<BLOCK ([^>\s]+)>>>[ \t]*$",re.M); ms=list(pat.finditer(text))
    for i,m in enumerate(ms):
        end=ms[i+1].start() if i+1<len(ms) else len(text)
        d[m.group(1)]=re.sub(r"\n?<<<END>>>\s*$","",text[m.end():end]).strip("\n"); order.append(m.group(1))
    return d,order
def attrs(s):
    out=[]
    for m in re.finditer(r"([A-Za-z_:][\w:.-]*)(?:\s*=\s*(?:\"([^\"]*)\"|'([^']*)'))?",s):
        k=m.group(1).lower(); v=m.group(2) if m.group(2) is not None else m.group(3)
        if k in ("title","alt","aria-label","caption","source"): continue
        out.append((k,v))
    return tuple(sorted(out))
def tags(s): return tuple((m.group(1).lower(),attrs(m.group(2))) for m in TAG.finditer(s))
def main():
    blocks={b["id"]:b for b in json.loads((WORK/"blocks.json").read_text())}
    man=json.loads((WORK/"manifest.json").read_text()); bad=0; miss=[]
    for c in man:
        p=Path(c["out"])
        if not p.exists(): miss.append(c["id"]); continue
        tr,order=parse_blocks(p.read_text())
        if order!=c["blocks"]: print(c["id"],"ORDER"); bad+=1; continue
        errs=[]
        for bid in c["blocks"]:
            src=blocks[bid]["text"].strip("\n"); dst=tr.get(bid,"")
            ha=re.match(r"^(#{1,6})\s+",src); hb=re.match(r"^(#{1,6})\s+",dst)
            if bool(ha)!=bool(hb) or (ha and ha.group(1)!=hb.group(1)): errs.append((bid,["heading"]))
            if ha and len(CJK.findall(dst))==0 and not re.fullmatch(r"[\w.\- ]+",dst.lstrip("# ").strip()): errs.append((bid,["heading not Chinese"]))
            if not any(x in src for x in ("<HtmlEmbed","<Image","<Reference","<Wide>")) and tags(src)!=tags(dst): errs.append((bid,["tags"]))
            if sorted(LINK.findall(src))!=sorted(LINK.findall(dst)): errs.append((bid,["links"]))
            if CITE.findall(src)!=CITE.findall(dst): errs.append((bid,["cites"]))
            if set(CODE.findall(src))!=set(CODE.findall(dst)): errs.append((bid,["code"]))
            sa=[l for l in src.splitlines() if l.strip().startswith("|")]; da=[l for l in dst.splitlines() if l.strip().startswith("|")]
            if len(sa)!=len(da) or any(a.count("|")!=b.count("|") for a,b in zip(sa,da)): errs.append((bid,["table"]))
            la=[re.match(r"^(\s*)([-*+]|\d+\.)\s+",l) for l in src.splitlines()]; ld=[re.match(r"^(\s*)([-*+]|\d+\.)\s+",l) for l in dst.splitlines()]
            la=[x for x in la if x]; ld=[x for x in ld if x]
            if len(la)!=len(ld) or any(a.group(2)!=b.group(2) for a,b in zip(la,ld)): errs.append((bid,["list"]))
            cjk=len(CJK.findall(dst)); eng=len(WORD.findall(dst))
            if eng>100 and cjk<eng*0.1 and "```" not in src: errs.append((bid,[f"low zh {cjk}/{eng}"]))
        if errs:
            bad+=1; print(f"\n[{c['id']}]")
            for bid,e in errs[:5]: print(" ",bid,e)
    print(f"\nchecked {len(man)-len(miss)}/{len(man)} bad {bad} missing {miss}")
if __name__=="__main__": main()
