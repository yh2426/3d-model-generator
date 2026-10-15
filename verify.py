"""Read both exported formats back and check size, topology, orientation, and volume."""
from collections import Counter, defaultdict
import json
from pathlib import Path
import struct
from generate import cross


def read_stl(path):
    data = path.read_bytes()
    count, = struct.unpack_from('<I', data, 80)
    assert len(data) == 84+50*count, 'STL length mismatch'
    points, faces, lookup = [], [], {}
    for i in range(count):
        values = struct.unpack_from('<12fH', data, 84+50*i)
        face = []
        for j in range(3):
            p = tuple(values[3+3*j:6+3*j])
            if p not in lookup:
                lookup[p] = len(points)
                points.append(p)
            face.append(lookup[p])
        faces.append(tuple(face))
    return points, faces


def read_glb(path):
    data = path.read_bytes()
    magic, version, length = struct.unpack_from('<III', data)
    assert (magic,version,length) == (0x46546C67,2,len(data))
    size, kind = struct.unpack_from('<II', data, 12)
    assert kind == 0x4E4F534A
    doc = json.loads(data[20:20+size])
    offset = 20+size
    bin_size, kind = struct.unpack_from('<II', data, offset)
    blob = data[offset+8:]
    assert kind == 0x004E4942 and len(blob) == bin_size == doc['buffers'][0]['byteLength']
    p, ix = doc['accessors']
    assert p['componentType'] == 5126 and ix['componentType'] == 5125
    points = list(struct.iter_unpack('<3f', blob[:doc['bufferViews'][0]['byteLength']]))
    assert len(points) == p['count']
    faces = list(struct.iter_unpack('<3I', blob[doc['bufferViews'][1]['byteOffset']:]))
    assert len(faces)*3 == ix['count']
    # Restore source coordinates in millimeters for a direct comparison.
    return [(x*1000,-z*1000,y*1000) for x,y,z in points], faces


def check(points, faces, model):
    edges, directed = Counter(), Counter()
    adjacency = defaultdict(set)
    volume = 0
    for face in faces:
        assert len(set(face)) == 3 and all(0 <= i < len(points) for i in face)
        a,b,c = [points[i] for i in face]
        normal = cross([b[i]-a[i] for i in range(3)], [c[i]-a[i] for i in range(3)])
        assert sum(n*n for n in normal) > 1e-12, 'Degenerate triangle'
        volume += sum(a[i]*cross(b,c)[i] for i in range(3))/6
        for u,v in zip(face, face[1:]+face[:1]):
            edges[tuple(sorted((u,v)))] += 1
            directed[(u,v)] += 1
            adjacency[u].add(v)
            adjacency[v].add(u)
    assert all(n == 2 for n in edges.values()), 'Mesh is not closed manifold'
    assert all(directed[(u,v)] == directed[(v,u)] == 1 for u,v in edges), 'Winding mismatch'
    seen, pending = set(), [0]
    while pending:
        vertex = pending.pop()
        if vertex not in seen:
            seen.add(vertex)
            pending.extend(adjacency[vertex]-seen)
    assert len(seen) == len(points), 'Disconnected mesh'
    assert len(points)-len(edges)+len(faces) == 2, 'Unexpected topology'
    mins = [min(p[i] for p in points) for i in range(3)]
    dims = [max(p[i] for p in points)-mins[i] for i in range(3)]
    expected = [model['dimensions'][k] for k in ('width','depth','height')]
    assert all(abs(a-b)<0.001 for a,b in zip(dims,expected)), 'Size mismatch'
    assert all(abs(v)<0.001 for v in mins), 'Origin mismatch'
    assert abs(volume-model['expected_volume_mm3']) < 0.1, 'Volume mismatch'
    return {'dimensions_mm':dims,'volume_mm3':volume,'vertices':len(points),
            'triangles':len(faces),'closed_manifold':True,'connected':True,'outward_winding':True}


def main():
    root = Path(__file__).parent
    config = json.loads((root/'samples.json').read_text(encoding='utf-8'))
    report = {}
    for model in config['models']:
        name = model['name']
        report[name] = {}
        meshes = []
        for suffix, reader in [('stl',read_stl),('glb',read_glb)]:
            mesh = reader(root/'models'/f'{name}.{suffix}')
            report[name][suffix] = check(*mesh, model)
            meshes.append(mesh)
        triangles = [[tuple(tuple(round(v,3) for v in points[i]) for i in face)
                      for face in faces] for points,faces in meshes]
        assert triangles[0] == triangles[1], 'Export triangle geometry differs'
    (root/'verification.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
