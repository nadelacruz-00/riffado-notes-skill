#!/usr/bin/env python3
"""Render a Markdown note (with ```mermaid blocks) into one standalone HTML file.

The HTML loads marked + mermaid from a CDN (cdnjs, with jsDelivr as fallback), so the
diagrams render in any browser, in a Claude HTML artifact, or from a downloaded file.

Usage:
  python3 render_notes_html.py notes.md notes.html [--title "Riffado notes"]
"""
import argparse, html, json, os, re, sys

CDN = {
    "marked": ["https://cdnjs.cloudflare.com/ajax/libs/marked/12.0.2/marked.min.js",
               "https://cdn.jsdelivr.net/npm/marked@12.0.2/marked.min.js"],
    "mermaid": ["https://cdnjs.cloudflare.com/ajax/libs/mermaid/10.9.1/mermaid.min.js",
                "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"],
}

TEMPLATE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{--bg:#fbfaf7;--fg:#1d1d1b;--muted:#5f5e58;--line:#e3e0d8;--card:#ffffff;--accent:#2f5d8a;--quote:#eef3f8}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){--bg:#17181a;--fg:#e8e6e1;--muted:#a3a19a;--line:#33353a;--card:#1f2124;--accent:#8db7e0;--quote:#1e2a36}}
:root[data-theme="dark"]{--bg:#17181a;--fg:#e8e6e1;--muted:#a3a19a;--line:#33353a;--card:#1f2124;--accent:#8db7e0;--quote:#1e2a36}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif}
main{max-width:860px;margin:0 auto;padding:32px 16px 64px}
h1{font-size:1.75rem;line-height:1.25;margin:0 0 .5rem}
h2{font-size:1.3rem;margin:2.2rem 0 .6rem;padding-top:1rem;border-top:1px solid var(--line)}
h3{font-size:1.05rem;margin:1.4rem 0 .4rem;color:var(--accent)}
p,li{max-width:72ch}
blockquote{margin:1rem 0;padding:.8rem 1rem;background:var(--quote);border-left:4px solid var(--accent);border-radius:6px}
blockquote p{margin:0}
hr{border:0;border-top:1px solid var(--line);margin:2rem 0}
code{font:.9em ui-monospace,SFMono-Regular,Menlo,monospace;background:var(--card);padding:.1em .3em;border-radius:4px}
pre{overflow-x:auto;background:var(--card);padding:12px;border-radius:8px;border:1px solid var(--line)}
table{border-collapse:collapse;width:100%;margin:1rem 0;display:block;overflow-x:auto}
th,td{border:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:top}
th{background:var(--card)}
ul.contains-task-list,li.task-list-item{list-style:none}
li.task-list-item input{margin-right:.5em}
.diagram{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px;margin:1rem 0;overflow-x:auto;text-align:center}
.diagram-error{color:#b42318;font-size:.9em;text-align:left;white-space:pre-wrap}
details{margin-top:1.5rem;background:var(--card);border:1px solid var(--line);border-radius:8px;padding:.6rem 1rem}
summary{cursor:pointer;font-weight:600}
.meta{color:var(--muted)}
</style>
</head>
<body>
<main id="content"><noscript><pre>__ESCAPED_MD__</pre></noscript></main>
<script id="md" type="application/json">__MD_JSON__</script>
<script>
function load(urls){return new Promise(function(res,rej){var i=0;(function next(){if(i>=urls.length)return rej(new Error('load failed: '+urls[0]));var s=document.createElement('script');s.src=urls[i++];s.onload=res;s.onerror=next;document.head.appendChild(s);})();});}
(async function(){
  var md=JSON.parse(document.getElementById('md').textContent);
  var root=document.getElementById('content');
  try{await load(__MARKED__);}catch(e){root.innerHTML='<pre></pre>';root.firstChild.textContent=md;return;}
  root.innerHTML=marked.parse(md,{gfm:true});
  root.querySelectorAll('li').forEach(function(li){if(li.querySelector(':scope > input[type=checkbox]')){li.classList.add('task-list-item');li.parentElement.classList.add('contains-task-list');}});
  var blocks=root.querySelectorAll('pre > code.language-mermaid');
  if(!blocks.length)return;
  var dark=document.documentElement.dataset.theme==='dark'||(!document.documentElement.dataset.theme&&matchMedia('(prefers-color-scheme: dark)').matches);
  try{await load(__MERMAID__);}catch(e){return;}
  mermaid.initialize({startOnLoad:false,theme:dark?'dark':'neutral',securityLevel:'strict',flowchart:{htmlLabels:true,curve:'basis'}});
  for(var i=0;i<blocks.length;i++){
    var code=blocks[i].textContent, box=document.createElement('div');box.className='diagram';
    blocks[i].parentElement.replaceWith(box);
    try{var r=await mermaid.render('d'+i,code);box.innerHTML=r.svg;}
    catch(err){box.innerHTML='<div class="diagram-error"></div><pre></pre>';box.firstChild.textContent='Diagram could not render: '+(err&&err.message||err);box.lastChild.textContent=code;document.body.dataset.diagramErrors=(+document.body.dataset.diagramErrors||0)+1;}
  }
  document.body.dataset.rendered='1';
})();
</script>
</body>
</html>
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("src")
    p.add_argument("dst")
    p.add_argument("--title")
    a = p.parse_args()
    with open(a.src, encoding="utf-8") as f:
        md = f.read()
    m = re.search(r"^#\s+(.+)$", md, re.M)
    title = a.title or (m.group(1).strip() if m else "Riffado notes")
    out = (TEMPLATE
           .replace("__TITLE__", html.escape(title))
           .replace("__ESCAPED_MD__", html.escape(md))
           .replace("__MD_JSON__", json.dumps(md).replace("</", "<\\/"))
           .replace("__MARKED__", json.dumps(CDN["marked"]))
           .replace("__MERMAID__", json.dumps(CDN["mermaid"])))
    with open(a.dst, "w", encoding="utf-8") as f:
        f.write(out)
    n = len(re.findall(r"^```mermaid", md, re.M))
    print(f"wrote {a.dst} ({n} diagram(s))")


if __name__ == "__main__":
    sys.exit(main())
