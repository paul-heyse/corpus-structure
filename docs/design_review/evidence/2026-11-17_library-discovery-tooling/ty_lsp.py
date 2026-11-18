import json, subprocess, sys, pathlib, time
root = pathlib.Path(sys.argv[1]).resolve()
p = subprocess.Popen(["/home/paul/corpus-structure/.venv/bin/ty","server"], cwd=root, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
n=0
def send(m):
    raw=json.dumps({"jsonrpc":"2.0",**m}).encode(); p.stdin.write(b"Content-Length: %d\r\n\r\n"%len(raw)+raw); p.stdin.flush()
def read():
    h={}
    while (l:=p.stdout.readline()) not in (b"\r\n",b"\n"):
        k,v=l.decode().split(":",1); h[k.lower()]=v.strip()
    return json.loads(p.stdout.read(int(h["content-length"])))
def req(method, params):
    global n; n+=1; send({"id":n,"method":method,"params":params})
    while True:
        m=read()
        if m.get("id")==n and "method" not in m: return m.get("result", m.get("error"))
        if "id" in m and "method" in m: send({"id":m["id"],"result":None})
init=req("initialize",{"processId":None,"rootUri":root.as_uri(),"capabilities":{},"initializationOptions":{"diagnosticMode":"off"}})
caps=init["capabilities"]; print("caps:", sorted(k for k,v in caps.items() if v))
send({"method":"initialized","params":{}})
a=(root/"a.py"); send({"method":"textDocument/didOpen","params":{"textDocument":{"uri":a.as_uri(),"languageId":"python","version":1,"text":a.read_text()}}})
# position of Option in line 6 (0-based 5): "def main(name: str = Option("x"))"
line=a.read_text().splitlines()[5]; col=line.index("Option")+1
def short(u): return u.replace(root.as_uri(),"WS").replace("file:///home/paul/corpus-structure/.venv/lib/python3.14/site-packages","SP")
r=req("textDocument/references",{"textDocument":{"uri":a.as_uri()},"position":{"line":5,"character":col},"context":{"includeDeclaration":True}})
print("references:", [(short(x["uri"]), x["range"]["start"]["line"]) for x in (r or [])])
r=req("textDocument/definition",{"textDocument":{"uri":a.as_uri()},"position":{"line":5,"character":col}})
print("definition:", [(short(x.get("uri",x.get("targetUri"))), (x.get("range") or x.get("targetRange"))["start"]["line"]) for x in (r or [])])
r=req("workspace/symbol",{"query":"Option"})
print("workspace/symbol Option:", [(s["name"], short(s["location"]["uri"])) for s in (r or [])][:8])
r=req("textDocument/hover",{"textDocument":{"uri":a.as_uri()},"position":{"line":3,"character":12}})
print("hover typer.Typer:", (json.dumps(r)[:300] if r else r))
req("shutdown",None); send({"method":"exit","params":None})
