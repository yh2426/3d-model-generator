"""Create boundary meshes of unions of axis-aligned boxes. Units: mm, Z up."""
import argparse
import json
import math
from pathlib import Path
import struct


def boxes_for(model):
    d, p = model['dimensions'], model['parameters']
    w, depth, h = (d[k] for k in ('width', 'depth', 'height'))
    if any(not math.isfinite(v) or v <= 0 for v in [*d.values(), *p.values()]):
        raise ValueError('Dimensions and parameters must be finite positive numbers')
    if model['name'] == 'rectangular_bar':
        return [(0, w, 0, depth, 0, h)]
    b = p['base_thickness']
    if not b < h:
        raise ValueError('Base must be thinner than height')
    boxes = [(0, w, 0, depth, 0, b)]
    if model['name'] == 'phone_stand':
        y, t, lip, lt, lh = (p[k] for k in
                              ('back_y', 'back_thickness', 'lip_y', 'lip_thickness', 'lip_height'))
        if not (lip + lt < y and y + t <= depth and b < lh < h):
            raise ValueError('Invalid back plate or lip dimensions')
        boxes += [(0, w, y, y+t, b, h), (0, w, lip, lip+lt, b, lh)]
    elif model['name'] == 'desk_organizer':
        t, x = p['wall_thickness'], p['divider_x']
        if not (2*t < depth and t < x < w-2*t):
            raise ValueError('Walls or divider leave no compartment')
        boxes += [(0, w, 0, t, b, h), (0, w, depth-t, depth, b, h),
                  (0, t, t, depth-t, b, h), (w-t, w, t, depth-t, b, h),
                  (x, x+t, t, depth-t, b, h)]
    else:
        raise ValueError('Unknown model: ' + model['name'])
    return boxes


def mesh_union(boxes):
    axes = [sorted({box[2*a+s] for box in boxes for s in (0, 1)}) for a in range(3)]
    occupied = set()
    for i in range(len(axes[0])-1):
        for j in range(len(axes[1])-1):
            for k in range(len(axes[2])-1):
                mid = [(axes[a][v]+axes[a][v+1])/2 for a, v in enumerate((i,j,k))]
                if any(all(box[2*a] < mid[a] < box[2*a+1] for a in range(3)) for box in boxes):
                    occupied.add((i,j,k))
    vertices, faces, lookup = [], [], {}
    for cell in sorted(occupied):
        for a in range(3):
            u, v = (a+1)%3, (a+2)%3
            for sign in (-1, 1):
                neighbor = list(cell)
                neighbor[a] += sign
                if tuple(neighbor) in occupied:
                    continue
                quad = []
                for du, dv in ((0,0), (1,0), (1,1), (0,1)):
                    idx = list(cell)
                    idx[a] += int(sign > 0)
                    idx[u] += du
                    idx[v] += dv
                    point = tuple(axes[t][idx[t]] for t in range(3))
                    if point not in lookup:
                        lookup[point] = len(vertices)
                        vertices.append(point)
                    quad.append(lookup[point])
                if sign < 0:
                    quad.reverse()
                faces.extend([(quad[0],quad[1],quad[2]), (quad[0],quad[2],quad[3])])
    return vertices, faces


def cross(a, b):
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


def write_stl(path, vertices, faces):
    with path.open('wb') as f:
        f.write(b'Python Model Generator; coordinates in millimeters'.ljust(80, b'\0'))
        f.write(struct.pack('<I', len(faces)))
        for face in faces:
            pts = [vertices[i] for i in face]
            n = cross([pts[1][a]-pts[0][a] for a in range(3)],
                      [pts[2][a]-pts[0][a] for a in range(3)])
            length = math.sqrt(sum(x*x for x in n))
            f.write(struct.pack('<12fH', *(x/length for x in n),
                                *(x for pt in pts for x in pt), 0))


def write_glb(path, vertices, faces, name):
    # Right-handed rotation: source Z up -> glTF Y up; mm -> meters.
    points = [(x/1000, z/1000, -y/1000) for x,y,z in vertices]
    positions = b''.join(struct.pack('<3f', *pt) for pt in points)
    indices = b''.join(struct.pack('<3I', *face) for face in faces)
    blob = positions + indices
    doc = {
        'asset': {'version':'2.0', 'generator':'Python Model Generator'},
        'scene':0, 'scenes':[{'nodes':[0]}], 'nodes':[{'mesh':0, 'name':name}],
        'meshes':[{'primitives':[{'attributes':{'POSITION':0}, 'indices':1, 'material':0}]}],
        'materials':[{'pbrMetallicRoughness':{'baseColorFactor':[0.16,0.55,0.75,1],
                                             'metallicFactor':0, 'roughnessFactor':0.75}}],
        'buffers':[{'byteLength':len(blob)}],
        'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':len(positions),'target':34962},
                       {'buffer':0,'byteOffset':len(positions),'byteLength':len(indices),'target':34963}],
        'accessors':[{'bufferView':0,'componentType':5126,'count':len(points),'type':'VEC3',
                      'min':[min(p[a] for p in points) for a in range(3)],
                      'max':[max(p[a] for p in points) for a in range(3)]},
                     {'bufferView':1,'componentType':5125,'count':len(faces)*3,'type':'SCALAR'}]}
    data = json.dumps(doc, separators=(',', ':')).encode()
    data += b' ' * (-len(data)%4)
    path.write_bytes(struct.pack('<III',0x46546C67,2,28+len(data)+len(blob)) +
                     struct.pack('<II',len(data),0x4E4F534A) + data +
                     struct.pack('<II',len(blob),0x004E4942) + blob)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path(__file__).with_name('samples.json'))
    parser.add_argument('--output', type=Path, default=Path(__file__).with_name('models'))
    args = parser.parse_args()
    config = json.loads(args.config.read_text(encoding='utf-8'))
    if config['units'] != 'mm':
        raise ValueError('Config units must be mm')
    args.output.mkdir(parents=True, exist_ok=True)
    for model in config['models']:
        vertices, faces = mesh_union(boxes_for(model))
        name = model['name']
        write_stl(args.output / (name+'.stl'), vertices, faces)
        write_glb(args.output / (name+'.glb'), vertices, faces, name)
        print(f'{name}: {len(vertices)} vertices, {len(faces)} triangles')


if __name__ == '__main__':
    main()
