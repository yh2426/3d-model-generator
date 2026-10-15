"""Bundle the existing UI and model assets into a double-clickable offline HTML."""
import base64
import json
from pathlib import Path

root = Path(__file__).resolve().parent
assets = {'../samples.json': 'data:application/json;base64,' +
          base64.b64encode((root/'samples.json').read_bytes()).decode()}
config = json.loads((root/'samples.json').read_text(encoding='utf-8'))
for model in config['models']:
    for extension in ('stl', 'glb'):
        path = root/'models'/f"{model['name']}.{extension}"
        assets['../models/'+path.name] = 'data:application/octet-stream;base64,' + base64.b64encode(path.read_bytes()).decode()
script = (root/'ui/app.js').read_text(encoding='utf-8-sig')
assert script.count('await fetch(') == 2
script = script.replace('await fetch(', 'await embeddedResponse(')
old = "$(ext).href=`../models/${model.name}.${ext}`;"
assert old in script
script = script.replace(old, "$(ext).href=embeddedAssets[`../models/${model.name}.${ext}`];")
bootstrap = 'const embeddedAssets='+json.dumps(assets)+';\n' + '''
async function embeddedResponse(path) {
  const encoded = embeddedAssets[path];
  if (!encoded) throw Error('Missing bundled asset: '+path);
  const bytes = Uint8Array.from(atob(encoded.split(',')[1]), ch=>ch.charCodeAt(0));
  return {ok:true, json:async()=>JSON.parse(new TextDecoder().decode(bytes)),
          arrayBuffer:async()=>bytes.buffer};
}
'''
html = (root/'ui/index.html').read_text(encoding='utf-8')
assert '<script src="app.js"></script>' in html
html = html.replace('<script src="app.js"></script>', '<script>'+bootstrap+script+'</script>')
destination = root/'Model_Generator_EN.html'
destination.write_text(html, encoding='utf-8')
assert '<script src=' not in html and 'await fetch(' not in html
print(destination)
