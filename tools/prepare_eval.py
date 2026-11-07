#!/usr/bin/env python3
"""Split the Evaluation Guidebook MDX files into translatable blocks/chunks."""
import json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; APP=ROOT/"app"; WORK=ROOT/"work"; CH=WORK/"chunks"; OUT=WORK/"out"
FILES=[
 "src/content/article.mdx",
 "src/content/chapters/intro.mdx",
 "src/content/chapters/general-knowledge/model-inference-and-evaluation.mdx",
 "src/content/chapters/general-knowledge/2025-evaluations-for-useful-models.mdx",
 "src/content/chapters/troubleshooting/troubleshooting-reproducibility.mdx",
 "src/content/chapters/general-knowledge/picking-your-evaluation.mdx",
 "src/content/chapters/automated-benchmarks/designing-your-automatic-evaluation.mdx",
 "src/content/chapters/human-evaluation/using-human-annotators.mdx",
]
WORD=re.compile(r"[A-Za-z][A-Za-z'’\-]*")
def is_fence(l): return l.lstrip().startswith("```")
def is_blank(l): return not l.strip()
def is_heading(l): return re.match(r"^#{1,6}\s+",l)
def is_list(l): return re.match(r"^\s{0,3}([-*+]|\d+\.)\s+",l)
def is_table(l): return l.lstrip().startswith("|")

def component_end(lines,start,tag):
    if re.search(r"/>\s*$",lines[start]) or tag.lower() in {"img","br","hr","iframe"}: return start
    close=re.compile(r"</"+re.escape(tag)+r"\s*>",re.I)
    for j in range(start,len(lines)):
        if close.search(lines[j]): return j
    return None

def btype(lines,i):
    l=lines[i]
    if is_fence(l): return "code"
    if is_blank(l): return "blank"
    if is_heading(l): return "heading"
    if is_table(l): return "table"
    if is_list(l): return "list"
    if re.match(r"^<([A-Za-z][\w:-]*)(\s|>|/)",l): return "component"
    if l.startswith("<!--"): return "component"
    return "para"

def split_file(path):
    text=path.read_text()
    # prefix: frontmatter + imports up to the last import; else frontmatter up to first heading
    last=0
    for m in re.finditer(r"^import .*?;?\s*$",text,re.M): last=m.end()
    if last:
        prefix=text[:last]+"\n"; body=text[last:]
    else:
        # frontmatter ends at second ---
        lines=text.splitlines(keepends=True); end=0
        if lines and lines[0].strip()=="---":
            for i in range(1,len(lines)):
                if lines[i].strip()=="---": end=i+1; break
        prefix="".join(lines[:end]); body="".join(lines[end:])
    return prefix,body

def main():
    CH.mkdir(parents=True,exist_ok=True); OUT.mkdir(parents=True,exist_ok=True)
    blocks=[]; prefixes={}
    for fi,f in enumerate(FILES):
        prefix,body=split_file(APP/f); prefixes[f]=prefix
        lines=body.splitlines(keepends=True); i=0
        while i<len(lines):
            t=btype(lines,i)
            if t=="blank":
                j=i
                while j<len(lines) and is_blank(lines[j]): j+=1
                blocks.append({"file":f,"type":"blank","text":"".join(lines[i:j]),"trans":False}); i=j; continue
            if t=="code":
                j=i+1
                while j<len(lines) and not (is_fence(lines[i]) and is_fence(lines[j])): j+=1
                j=min(j+1,len(lines))
                blocks.append({"file":f,"type":"code","text":"".join(lines[i:j]),"trans":False}); i=j; continue
            if t=="heading":
                blocks.append({"file":f,"type":"heading","text":lines[i],"trans":True}); i+=1; continue
            if t=="table":
                j=i
                while j<len(lines) and is_table(lines[j]): j+=1
                blocks.append({"file":f,"type":"table","text":"".join(lines[i:j]),"trans":True}); i=j; continue
            if t=="list":
                j=i
                while j<len(lines):
                    if is_blank(lines[j]): break
                    if is_list(lines[j]) or re.match(r"^\s{2,}\S",lines[j]): j+=1
                    else: break
                blocks.append({"file":f,"type":"list","text":"".join(lines[i:j]),"trans":True}); i=j; continue
            if t=="component":
                m=re.match(r"^<([A-Za-z][\w:-]*)",lines[i]); tag=m.group(1) if m else "div"
                j=component_end(lines,i,tag)
                if j is None:
                    j=i
                    while j<len(lines) and not is_blank(lines[j]): j+=1
                    blocks.append({"file":f,"type":"component","text":"".join(lines[i:j]),"trans":False})
                    i=j; continue
                raw="".join(lines[i:j+1]); low=raw.lower()
                trans=not any(x in low for x in ("<canvas","<script","<style","<svg"))
                blocks.append({"file":f,"type":"component","text":raw,"trans":trans}); i=j+1; continue
            j=i
            while j<len(lines) and not is_blank(lines[j]) and not (is_heading(lines[j]) or is_table(lines[j]) or is_list(lines[j]) or is_fence(lines[j])):
                j+=1
            k=i+1
            while k<j:
                if re.match(r"^<([A-Za-z][\w:-]*)(\s|>|/)",lines[k]): j=k; break
                k+=1
            blocks.append({"file":f,"type":"para","text":"".join(lines[i:j]),"trans":True}); i=j
    for n,b in enumerate(blocks):
        b["id"]=f"b{n:04d}"
        b["words"]=len(WORD.findall(re.sub(r"<[^>]+>"," ",b["text"]))) if b["trans"] else 0
    chunks=[]; cur=[]; cw=0
    for b in blocks:
        if not b["trans"]: continue
        if cur and cw+b["words"]>1200: chunks.append(cur); cur=[]; cw=0
        cur.append(b); cw+=b["words"]
    if cur: chunks.append(cur)
    man=[]
    for n,ch in enumerate(chunks,1):
        cid=f"chunk-{n:03d}"; out=[]
        for b in ch: out += [f"<<<BLOCK {b['id']}>>>", b["text"].rstrip("\n")]
        out.append("<<<END>>>")
        (CH/f"{cid}.txt").write_text("\n".join(out)+"\n")
        man.append({"id":cid,"blocks":[b["id"] for b in ch],"words":sum(b["words"] for b in ch),
                    "file":str(CH/f"{cid}.txt"),"out":str(OUT/f"{cid}.txt")})
    (WORK/"blocks.json").write_text(json.dumps(blocks,ensure_ascii=False,indent=1))
    (WORK/"prefixes.json").write_text(json.dumps(prefixes,ensure_ascii=False,indent=1))
    (WORK/"manifest.json").write_text(json.dumps(man,ensure_ascii=False,indent=2))
    print(len(blocks),"blocks",len(chunks),"chunks",sum(c["words"] for c in man),"words")
    from collections import Counter
    print(Counter(b["type"] for b in blocks))
    for c in man[:5]: print(c["id"],c["words"],len(c["blocks"]))

if __name__=="__main__": main()
