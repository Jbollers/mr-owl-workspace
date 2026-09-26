"""Build the FinalCoat first-job house as an Unreal-ready static mesh.

Headless:  blender -b --factory-startup --python build_first_job_house.py -- --render
In an open Blender: Scripting tab > open this file > Run Script (clears the scene).

Outputs next to this script: SM_FirstJobHouse.blend, SM_FirstJobHouse.fbx,
Textures/T_*.png (base color, OpenGL normal for Blender, DirectX normal for Unreal)
and, with --render, preview PNGs.

Conventions: 1 Blender unit = 1 m (imports as 100 cm), Z up, front door faces -Y,
pivot at ground level in the centre of the main footprint. UV0 = tiling world-scale
material UVs, UV1 = non-overlapping lightmap UVs. UCX_ meshes are convex collision.
"""
import bpy, bmesh, math, os, sys, json
import numpy as np
from mathutils import Vector

FALLBACK = r"D:\Documents\AI\mr-owl-workspace\workspace\2026-09-21_finalcoat\3d\first-job-house"
_here = globals().get("__file__")
OUT = os.path.dirname(os.path.abspath(_here)) if _here and os.path.isfile(_here) else FALLBACK
TEX = os.path.join(OUT, "Textures")
os.makedirs(TEX, exist_ok=True)
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NAME = "SM_FirstJobHouse"

# --------------------------------------------------------------------------- textures
N = 1024
FX = np.fft.fftfreq(N)[None, :]
FY = np.fft.fftfreq(N)[:, None]
V = np.arange(N, dtype=float)[:, None].repeat(N, 1)   # rows = v (up)
U = np.arange(N, dtype=float)[None, :].repeat(N, 0)   # cols = u (right)


def noise(su, sv=None, seed=0):
    """Tileable gaussian-filtered noise, zero mean / unit std."""
    sv = su if sv is None else sv
    r = np.random.default_rng(seed).standard_normal((N, N))
    h = np.exp(-2 * np.pi ** 2 * ((FX * su) ** 2 + (FY * sv) ** 2))
    n = np.real(np.fft.ifft2(np.fft.fft2(r) * h))
    return (n - n.mean()) / (n.std() + 1e-9)


def fbm(base, seed, octaves=4):
    out = sum(0.55 ** i * noise(base / 2 ** i, seed=seed + i) for i in range(octaves))
    return (out - out.mean()) / out.std()


def blur(a, s):
    h = np.exp(-2 * np.pi ** 2 * s * s * (FX ** 2 + FY ** 2))
    return np.real(np.fft.ifft2(np.fft.fft2(a) * h))


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (np.asarray(b) - a) * t[..., None]


def normal_from_height(h, strength=1.0):
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5 * strength
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5 * strength
    n = np.stack([-dx, -dy, np.ones_like(h)], -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def save_png(name, rgb, non_color=False):
    path = os.path.join(TEX, name + ".png")
    img = bpy.data.images.get(name) or bpy.data.images.new(name, N, N, alpha=False)
    rgba = np.concatenate([np.clip(rgb, 0, 1), np.ones((N, N, 1))], -1).astype(np.float32)
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    img.filepath = path
    if non_color:
        img.colorspace_settings.name = "Non-Color"
    return img


def save_normals(name, h, strength=1.0):
    n = normal_from_height(h, strength)
    gl = n * 0.5 + 0.5
    dx = gl.copy()
    dx[..., 1] = 1 - dx[..., 1]
    img = save_png(name + "_N", gl, True)
    save_png(name + "_N_DX", dx, True)
    return img


def tex_siding():
    """2 m tile, ten 0.2 m lap boards, faded sage paint, mildew and a few peels."""
    bh = N / 10
    row = np.floor(V / bh).astype(int)
    yb = (V % bh) / bh
    rr = np.random.default_rng(11)
    tone = rr.normal(0, 0.035, 10)[row]
    jx = rr.uniform(0, N, 10)[row]
    joint = np.abs(((U - jx + N / 2) % N) - N / 2) < 1.5
    grain = noise(60, 1.2, 21)
    streak = noise(3, 90, 22)
    mottle = fbm(90, 30)
    pn = noise(90, 7, 40) + 0.5 * noise(30, 4, 41)
    peel = sstep(2.0, 2.15, pn / pn.std())
    stain = sstep(0.8, 2.2, fbm(110, 50))
    col = np.array([0.45, 0.51, 0.48]) * (1 + tone + 0.04 * grain + 0.035 * mottle - 0.03 * streak)[..., None]
    col = lerp(col, [0.40, 0.39, 0.22], stain * 0.5)
    col = lerp(col, np.array([0.76, 0.73, 0.66]) * (1 + 0.06 * grain)[..., None], peel)
    shade = 1 - 0.45 * sstep(0.84, 1.0, yb)
    shade = np.where(yb < 0.025, shade * 0.72, shade)
    shade = np.where(joint, shade * 0.55, shade)
    col *= shade[..., None]
    h = (1 - yb) * 6 - 2 * joint - 0.8 * peel + 0.15 * grain
    return save_png("T_Siding_BC", col), save_normals("T_Siding", blur(h, 0.8))


def tex_trim():
    """1 m tile, dirty cream paint peeling to grey wood."""
    grain = noise(50, 1.2, 61)
    pn = noise(70, 18, 60) + 0.6 * noise(28, 8, 62)
    pn /= pn.std()
    peel = sstep(1.25, 1.35, pn)
    edge = sstep(1.0, 1.25, pn) - peel
    dirt = sstep(0.4, 1.8, fbm(80, 70))
    col = np.array([0.87, 0.84, 0.76]) * (1 + 0.03 * fbm(40, 75))[..., None]
    col = lerp(col, [0.62, 0.58, 0.47], dirt * 0.35)
    col = lerp(col, np.array([0.50, 0.48, 0.44]) * (1 + 0.12 * grain)[..., None], peel)
    col *= (1 - 0.22 * edge)[..., None]
    h = (1 - peel) * 2.5 + 0.25 * grain * peel
    return save_png("T_Trim_BC", col), save_normals("T_Trim", blur(h, 0.7))


def tex_roof():
    """2 m tile, sixteen 0.125 m rows of charcoal three-tab asphalt shingles."""
    rows, tabs = 16, 6
    rh, tw = N / rows, N / tabs
    row = np.floor(V / rh).astype(int)
    yb = (V % rh) / rh
    uu = U + (row % 2) * tw * 0.5
    tab = np.floor(uu / tw).astype(int) % tabs
    tu = uu % tw
    gap = (tu < 3) & (yb < 0.62)
    tone = np.random.default_rng(81).normal(0, 0.07, (rows, tabs))[row, tab]
    gran = noise(0.7, seed=82)
    streak = noise(3, 70, 83)
    col = np.array([0.20, 0.22, 0.26]) * (1 + tone + 0.13 * gran - 0.05 * streak)[..., None]
    shade = 1 - 0.5 * sstep(0.8, 1.0, yb)
    shade = np.where(yb < 0.03, shade * 0.7, shade)
    shade = np.where(gap, 0.35, shade)
    col *= shade[..., None]
    h = (1 - yb) * 4 - 3 * gap + 0.3 * gran
    return save_png("T_Roof_BC", col), save_normals("T_Roof", blur(h, 0.7))


def tex_concrete():
    m = fbm(60, 100)
    d = noise(2, seed=200)
    pits = sstep(2.2, 2.8, noise(1.2, seed=300))
    stain = sstep(0.5, 1.8, fbm(120, 310))
    col = np.array([0.58, 0.58, 0.56]) * (1 + 0.07 * m + 0.03 * d)[..., None]
    col = lerp(col, [0.42, 0.40, 0.33], stain * 0.35)
    col *= (1 - 0.3 * pits)[..., None]
    h = 0.6 * m + 0.4 * d - 1.5 * pits
    return save_png("T_Concrete_BC", col), save_normals("T_Concrete", blur(h, 0.8), 0.6)


def tex_door():
    grain = noise(1.2, 50, 400)
    wear = sstep(0.9, 1.5, fbm(30, 410))
    col = np.array([0.27, 0.19, 0.13]) * (1 + 0.12 * grain + 0.05 * fbm(60, 420))[..., None]
    col = lerp(col, [0.40, 0.32, 0.24], wear * 0.5)
    h = 0.5 * grain - 0.8 * wear
    return save_png("T_Door_BC", col), save_normals("T_Door", blur(h, 0.7), 0.8)


# --------------------------------------------------------------------------- materials
SID, TRIM, ROOF, CONC, DOOR, GLASS, METAL = range(7)
TILE = {SID: 2.0, TRIM: 1.0, ROOF: 2.0, CONC: 2.0, DOOR: 1.0, GLASS: 1.0, METAL: 1.0}


def make_mat(name, bc=None, nrm=None, color=(0.5, 0.5, 0.5), rough=0.8, metal=0.0):
    old = bpy.data.materials.get(name)
    if old:
        bpy.data.materials.remove(old)
    m = bpy.data.materials.new(name)
    try:
        m.use_nodes = True
    except Exception:
        pass
    nt = m.node_tree
    bsdf = next(n for n in nt.nodes if n.type == "BSDF_PRINCIPLED")
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Metallic"].default_value = metal
    if bc:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image, t.location = bc, (-600, 250)
        nt.links.new(t.outputs["Color"], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = (*color, 1)
    if nrm:
        t = nt.nodes.new("ShaderNodeTexImage")
        t.image, t.location, t.name = nrm, (-600, -150), "NormalTex"
        nm = nt.nodes.new("ShaderNodeNormalMap")
        nm.location = (-280, -150)
        nt.links.new(t.outputs["Color"], nm.inputs["Color"])
        nt.links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])
    m.diffuse_color = (*color, 1)
    return m


def build_materials():
    s, t, r, c, d = tex_siding(), tex_trim(), tex_roof(), tex_concrete(), tex_door()
    return [
        make_mat("M_Siding", *s, color=(0.18, 0.26, 0.22), rough=0.8),
        make_mat("M_Trim", *t, color=(0.7, 0.66, 0.55), rough=0.75),
        make_mat("M_Roof", *r, color=(0.03, 0.035, 0.045), rough=0.9),
        make_mat("M_Concrete", *c, color=(0.3, 0.3, 0.28), rough=0.9),
        make_mat("M_Door", *d, color=(0.09, 0.04, 0.02), rough=0.7),
        make_mat("M_Glass", color=(0.02, 0.024, 0.028), rough=0.08),
        make_mat("M_MetalDark", color=(0.03, 0.03, 0.03), rough=0.5, metal=0.8),
    ]


# --------------------------------------------------------------------------- geometry helpers
HEX = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
bm = bmesh.new()
piece_layer = bm.faces.layers.int.new("piece")
_piece = [0]
COLLISION = []


def poly(pts, faces, mats):
    _piece[0] += 1
    vs = [bm.verts.new(p) for p in pts]
    mats = mats if isinstance(mats, (list, tuple)) else [mats] * len(faces)
    for f, m in zip(faces, mats):
        face = bm.faces.new([vs[i] for i in f])
        face.material_index = m
        face[piece_layer] = _piece[0]


def hexa(pts, mats):
    """8 points: bottom quad then matching top quad. mats: one or [bottom, top, s01, s12, s23, s30]."""
    poly(pts, HEX, mats)


def box_pts(x0, x1, y0, y1, z0, z1):
    return [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
            (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]


def box(x0, x1, y0, y1, z0, z1, m):
    hexa(box_pts(x0, x1, y0, y1, z0, z1), m)


def prism(tri, a0, a1, axis, m):
    """Triangular prism: tri is three (s, z) points extruded along axis ('x' or 'y') from a0 to a1."""
    def p(s, z, a):
        return (a, s, z) if axis == "x" else (s, a, z)
    pts = [p(s, z, a0) for s, z in tri] + [p(s, z, a1) for s, z in tri]
    poly(pts, [(0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)], m)


# Faces: (axis, plane, outward sign). u runs along the wall, w outward from the wall surface.
F_BAY = ("y", -0.5, -1)
F_FRONT = ("y", 0.0, -1)
F_BACK = ("y", 7.5, 1)
F_RIGHT = ("x", 8.0, 1)
F_LEFT = ("x", 0.0, -1)


def fbox(F, u0, u1, z0, z1, w0, w1, m):
    ax, p, s = F
    a, b = p + s * w0, p + s * w1
    lo, hi = min(a, b), max(a, b)
    if ax == "y":
        box(u0, u1, lo, hi, z0, z1, m)
    else:
        box(lo, hi, u0, u1, z0, z1, m)


def window(F, uc, z0, z1, w, muntins=1):
    hw, c, fr, d = w / 2, 0.12, 0.055, 0.04
    fbox(F, uc - hw, uc + hw, z0, z1, -0.03, 0.005, GLASS)
    fbox(F, uc - hw, uc - hw + fr, z0, z1, 0, d, TRIM)
    fbox(F, uc + hw - fr, uc + hw, z0, z1, 0, d, TRIM)
    fbox(F, uc - hw + fr, uc + hw - fr, z1 - fr, z1, 0, d, TRIM)
    fbox(F, uc - hw + fr, uc + hw - fr, z0, z0 + 0.07, 0, d, TRIM)
    zm = (z0 + z1) / 2
    fbox(F, uc - hw + fr, uc + hw - fr, zm - 0.035, zm + 0.035, 0, d + 0.015, TRIM)
    for i in range(1, muntins + 1):
        mu = uc - hw + fr + (w - 2 * fr) * i / (muntins + 1)
        fbox(F, mu - 0.015, mu + 0.015, zm + 0.035, z1 - fr, 0, 0.025, TRIM)
    fbox(F, uc - hw - c, uc - hw, z0, z1, 0, 0.05, TRIM)
    fbox(F, uc + hw, uc + hw + c, z0, z1, 0, 0.05, TRIM)
    fbox(F, uc - hw - c - 0.03, uc + hw + c + 0.03, z1, z1 + 0.17, 0, 0.055, TRIM)
    fbox(F, uc - hw - c - 0.06, uc + hw + c + 0.06, z1 + 0.17, z1 + 0.22, 0, 0.085, TRIM)
    fbox(F, uc - hw - c - 0.05, uc + hw + c + 0.05, z0 - 0.06, z0, 0, 0.1, TRIM)
    fbox(F, uc - hw - c + 0.02, uc + hw + c - 0.02, z0 - 0.2, z0 - 0.06, 0, 0.04, TRIM)


def door(F, uc, z0, w=0.95, h=2.1):
    hw, st = w / 2, 0.13
    fbox(F, uc - hw, uc + hw, z0, z0 + h, -0.02, 0.03, DOOR)
    pw = (w - 3 * st) / 2
    zb, zt = z0 + 0.25, z0 + h - 0.13
    avail = zt - zb - 2 * 0.12
    z = zb
    for hh in (avail * 0.34, avail * 0.30, avail * 0.36):
        for ci in range(2):
            u0 = uc - hw + st + ci * (pw + st)
            fbox(F, u0, u0 + pw, z, z + hh, 0.03, 0.036, DOOR)
            fbox(F, u0 + 0.04, u0 + pw - 0.04, z + 0.04, z + hh - 0.04, 0.036, 0.05, DOOR)
        z += hh + 0.12
    fbox(F, uc + hw - 0.14, uc + hw - 0.07, z0 + 0.86, z0 + 1.12, 0.03, 0.04, METAL)
    fbox(F, uc + hw - 0.13, uc + hw - 0.08, z0 + 0.95, z0 + 1.01, 0.04, 0.1, METAL)
    c = 0.14
    fbox(F, uc - hw - c, uc - hw, z0, z0 + h, 0, 0.05, TRIM)
    fbox(F, uc + hw, uc + hw + c, z0, z0 + h, 0, 0.05, TRIM)
    fbox(F, uc - hw - c - 0.03, uc + hw + c + 0.03, z0 + h, z0 + h + 0.18, 0, 0.06, TRIM)
    fbox(F, uc - hw - c - 0.06, uc + hw + c + 0.06, z0 + h + 0.18, z0 + h + 0.23, 0, 0.09, TRIM)
    fbox(F, uc - hw - 0.03, uc + hw + 0.03, z0, z0 + 0.03, 0, 0.07, TRIM)


def vent(F, uc, zc, w=0.42, h=0.5):
    fbox(F, uc - w / 2, uc + w / 2, zc - h / 2, zc + h / 2, -0.03, 0.0, METAL)
    b = 0.07
    fbox(F, uc - w / 2 - b, uc - w / 2, zc - h / 2 - b, zc + h / 2 + b, 0, 0.04, TRIM)
    fbox(F, uc + w / 2, uc + w / 2 + b, zc - h / 2 - b, zc + h / 2 + b, 0, 0.04, TRIM)
    fbox(F, uc - w / 2, uc + w / 2, zc + h / 2, zc + h / 2 + b, 0, 0.04, TRIM)
    fbox(F, uc - w / 2, uc + w / 2, zc - h / 2 - b, zc - h / 2, 0, 0.04, TRIM)
    for i in range(4):
        z = zc - h / 2 + h * (i + 0.6) / 4.2
        fbox(F, uc - w / 2, uc + w / 2, z, z + 0.045, 0, 0.03, TRIM)


# --------------------------------------------------------------------------- the house
# Plan (metres, before centring): main body x 0..8, y 0..7.5; front bay x 0..3.8 projects to y -0.5;
# porch x 3.9..8.0 projects to y -2.4. Grade z 0, foundation top 0.6, floor 0.9, eave 6.2.
EAVE = 6.2
T1, T2 = math.tan(math.radians(40)), math.tan(math.radians(50))
TH1, TH2 = 0.18 / math.cos(math.radians(40)), 0.18 / math.cos(math.radians(50))


def build_house():
    # foundation, walls, gable volumes
    box(-0.03, 8.03, -0.03, 7.53, 0, 0.62, CONC)
    box(-0.03, 3.83, -0.53, 0, 0, 0.62, CONC)
    box(0, 8, 0, 7.5, 0.6, EAVE, SID)
    box(0, 3.8, -0.5, 0, 0.6, EAVE, SID)
    prism([(0, EAVE), (7.5, EAVE), (3.75, EAVE + 3.75 * T1)], 0, 8, "x", SID)
    prism([(0, EAVE), (3.8, EAVE), (1.9, EAVE + 1.9 * T2)], -0.5, 2.5, "y", SID)

    # skirt board, corner boards, frieze
    s = 0.04
    for b in [(-s, 3.8 + s, -0.5 - s, -0.5), (3.8, 8 + s, -s, 0), (8, 8 + s, -s, 7.5 + s),
              (-s, 8 + s, 7.5, 7.5 + s), (-s, 0, -0.5 - s, 7.5 + s), (3.8, 3.8 + s, -0.5 - s, 0)]:
        box(*b, 0.6, 0.8, TRIM)
    for cx, cy in [(0, -0.5), (3.8, -0.5), (8, 0), (8, 7.5), (0, 7.5)]:
        box(cx - 0.09, cx + 0.09, cy - 0.09, cy + 0.09, 0.6, EAVE, TRIM)
    for b in [(0, 3.8, -0.53, -0.5), (3.8, 8, -0.03, 0), (0, 8, 7.5, 7.53), (8, 8.03, 0, 7.5), (-0.03, 0, -0.5, 7.5)]:
        box(*b, EAVE - 0.28, EAVE, TRIM)

    # main roof: two slabs with vertical fascia/ridge cuts, ridge along x
    zf = lambda y: EAVE + T1 * y
    zb_ = lambda y: EAVE + T1 * (7.5 - y)
    x0, x1 = -0.3, 8.3
    for ya, yb, zfun in [(-0.4, 3.75, zf), (7.9, 3.75, zb_)]:
        pts = [(x0, ya, zfun(ya)), (x1, ya, zfun(ya)), (x1, yb, zfun(yb)), (x0, yb, zfun(yb))]
        pts += [(x, y, z + TH1) for x, y, z in pts]
        hexa(pts, [TRIM, ROOF, TRIM, TRIM, ROOF, TRIM])
        COLLISION.append(pts)
    ridge = EAVE + 3.75 * T1 + TH1
    box(x0, x1, 3.6, 3.9, ridge - 0.14, ridge + 0.06, ROOF)

    # front cross gable over the bay (ridge along y), trimmed to meet the main roof
    zc = lambda x: EAVE + T2 * min(x, 3.8 - x)
    yv = lambda x: (T2 * min(x, 3.8 - x) + TH2 - TH1) / T1
    cross = []
    for xa, xb in [(-0.3, 1.9), (4.1, 1.9)]:
        pts = [(xa, -0.85, zc(xa)), (xb, -0.85, zc(xb)), (xb, yv(xb), zc(xb)), (xa, yv(xa), zc(xa))]
        pts += [(x, y, z + TH2) for x, y, z in pts]
        hexa(pts, [TRIM, ROOF, TRIM, ROOF, ROOF, TRIM])
        cross += pts
    COLLISION.append(cross)
    cr = zc(1.9) + TH2
    box(1.75, 2.05, -0.85, yv(1.9), cr - 0.14, cr + 0.05, ROOF)
    for bx in (-0.12, 3.72):  # eave brackets
        box(bx, bx + 0.2, -0.75, -0.5, EAVE - 0.35, EAVE - 0.05, TRIM)

    # pent roof over the bay's ground-floor window
    pts = [(-0.15, -0.5, 3.5), (3.8, -0.5, 3.5), (3.8, -1.2, 3.2), (-0.15, -1.2, 3.2)]
    pts += [(x, y, z + 0.13) for x, y, z in pts]
    hexa(pts, [TRIM, ROOF, TRIM, TRIM, TRIM, TRIM])
    COLLISION.append(pts)
    box(-0.03, 3.8, -0.53, -0.5, 3.3, 3.5, TRIM)

    # porch: deck, steps, piers, columns, beams, railings, roof
    box(3.9, 8.0, -2.4, 0, 0, 0.9, CONC)
    box(3.88, 8.02, -2.42, 0, 0.84, 0.9, CONC)
    for k in (1, 2, 3):
        box(4.6, 7.3, -2.4 - (4 - k) * 0.3, -2.4, 0, k * 0.225, CONC)
    for cx in (4.25, 7.65):
        cy = -2.05
        box(cx - 0.35, cx + 0.35, cy - 0.35, cy + 0.35, 0, 1.8, CONC)
        box(cx - 0.4, cx + 0.4, cy - 0.4, cy + 0.4, 1.8, 1.9, TRIM)
        a, b = 0.24, 0.17
        hexa([(cx - a, cy - a, 1.9), (cx + a, cy - a, 1.9), (cx + a, cy + a, 1.9), (cx - a, cy + a, 1.9),
              (cx - b, cy - b, 3.1), (cx + b, cy - b, 3.1), (cx + b, cy + b, 3.1), (cx - b, cy + b, 3.1)], TRIM)
        box(cx - 0.24, cx + 0.24, cy - 0.24, cy + 0.24, 3.1, 3.2, TRIM)
        box(cx - 0.12, cx + 0.12, -1.8, 0, 3.25, 3.55, TRIM)
        COLLISION.append(box_pts(cx - 0.35, cx + 0.35, cy - 0.35, cy + 0.35, 0, 3.2))
        # side railing from pier back to the house wall
        box(cx - 0.05, cx + 0.05, -1.7, 0, 1.75, 1.85, TRIM)
        box(cx - 0.04, cx + 0.04, -1.7, 0, 0.98, 1.05, TRIM)
        for i in range(8):
            y = -1.6 + i * 0.2
            box(cx - 0.025, cx + 0.025, y - 0.025, y + 0.025, 1.05, 1.75, TRIM)
        COLLISION.append(box_pts(cx - 0.06, cx + 0.06, -1.7, 0, 0.9, 1.85))
    box(3.85, 8.05, -2.3, -1.8, 3.2, 3.55, TRIM)
    B = [(3.7, -2.7, 3.55), (8.3, -2.7, 3.55), (8.3, 0, 3.55), (3.7, 0, 3.55)]
    P = [(4.6, -1.5, 4.05), (7.4, -1.5, 4.05), (4.6, 0, 4.05), (7.4, 0, 4.05)]
    poly(B + P, [(3, 2, 1, 0), (0, 1, 5, 4), (3, 0, 4, 6), (1, 2, 7, 5), (6, 4, 5, 7), (2, 3, 6, 7)],
         [TRIM, ROOF, ROOF, ROOF, ROOF, TRIM])
    COLLISION.append(B + P)
    box(3.65, 8.35, -2.75, -2.65, 3.4, 3.6, TRIM)
    box(3.65, 3.75, -2.75, 0, 3.4, 3.6, TRIM)
    box(8.25, 8.35, -2.75, 0, 3.4, 3.6, TRIM)
    COLLISION.append(box_pts(3.9, 8.0, -2.4, 0, 0, 0.9))
    COLLISION.append([(4.6, -3.3, 0), (7.3, -3.3, 0), (4.6, -2.4, 0), (7.3, -2.4, 0),
                      (4.6, -2.4, 0.9), (7.3, -2.4, 0.9)])
    # porch pendant lamp
    lx, ly = 5.95, -1.0
    box(lx - 0.012, lx + 0.012, ly - 0.012, ly + 0.012, 3.34, 3.55, METAL)
    box(lx - 0.11, lx + 0.11, ly - 0.11, ly + 0.11, 3.3, 3.36, METAL)
    box(lx - 0.075, lx + 0.075, ly - 0.075, ly + 0.075, 3.08, 3.3, GLASS)
    box(lx - 0.09, lx + 0.09, ly - 0.09, ly + 0.09, 3.04, 3.08, METAL)

    # gutters and downspouts
    box(3.85, 8.3, -0.53, -0.4, 5.72, 5.86, TRIM)
    box(-0.3, 8.3, 7.9, 8.03, 5.72, 5.86, TRIM)
    box(3.65, 8.35, -2.86, -2.75, 3.38, 3.5, TRIM)
    for x, y0, y1, zt in [(8.07, -0.47, -0.02, 5.72), (8.07, 7.52, 7.97, 5.72), (-0.07, 7.52, 7.97, 5.72)]:
        yc = -0.06 if y0 < 0 else 7.56
        box(x - 0.045, x + 0.045, yc - 0.045, yc + 0.045, 0.05, zt - 0.1, TRIM)
        box(x - 0.045, x + 0.045, y0, y1, zt - 0.12, zt, TRIM)

    # openings
    window(F_BAY, 1.9, 4.25, 5.65, 1.1)
    window(F_BAY, 1.9, 1.5, 3.05, 1.7, 2)
    window(F_FRONT, 5.95, 4.4, 5.6, 1.0)
    door(F_FRONT, 5.95, 0.9)
    window(F_RIGHT, 2.3, 4.3, 5.6, 0.85)
    window(F_RIGHT, 2.0, 1.5, 2.95, 0.75)
    window(F_RIGHT, 3.3, 1.5, 2.95, 0.75)
    window(F_RIGHT, 5.8, 1.5, 2.95, 0.75)
    window(F_LEFT, 4.0, 4.3, 5.6, 0.85)
    window(F_LEFT, 2.5, 1.5, 2.95, 0.75)
    window(F_LEFT, 5.2, 1.5, 2.95, 0.75)
    for x in (2.0, 6.0):
        window(F_BACK, x, 4.3, 5.6, 0.95)
        window(F_BACK, x, 1.5, 2.95, 0.95)
    vent(F_RIGHT, 3.75, 8.2)
    vent(F_LEFT, 3.75, 8.2)

    # simple collision for the walls
    COLLISION.append(box_pts(0, 8, 0, 7.5, 0, EAVE))
    COLLISION.append(box_pts(0, 3.8, -0.5, 0, 0, EAVE))


# --------------------------------------------------------------------------- assembly
CENTRE = Vector((4.0, 3.75, 0.0))


def clear_scene():
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    for me in list(bpy.data.meshes):
        bpy.data.meshes.remove(me)
    s = bpy.context.scene
    s.unit_settings.system = "METRIC"
    s.unit_settings.scale_length = 1.0


def get_coll(name):
    c = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(c)
    return c


def finish_mesh(mats, coll):
    bmesh.ops.translate(bm, verts=bm.verts[:], vec=-CENTRE)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.normal_update()
    uv = bm.loops.layers.uv.new("UVMap")
    offs = {}
    rng = np.random.default_rng(5)
    for f in bm.faces:
        n = f.normal
        t = Vector((1, 0, 0)) if abs(n.z) > 0.999 else Vector((0, 0, 1)).cross(n).normalized()
        b = n.cross(t)
        sc = TILE[f.material_index]
        o = (0.0, 0.0)
        if f.material_index in (TRIM, CONC, DOOR):  # decorrelate small pieces
            o = offs.setdefault(f[piece_layer], tuple(rng.random(2)))
        for l in f.loops:
            p = l.vert.co
            l[uv].uv = (p.dot(t) / sc + o[0], p.dot(b) / sc + o[1])
    bm.faces.layers.int.remove(piece_layer)
    me = bpy.data.meshes.new(NAME)
    bm.to_mesh(me)
    bm.free()
    for m in mats:
        me.materials.append(m)
    for p in me.polygons:
        p.use_smooth = False
    ob = bpy.data.objects.new(NAME, me)
    coll.objects.link(ob)
    # lightmap UVs in channel 1
    lm = me.uv_layers.new(name="Lightmap")
    me.uv_layers.active = lm
    bpy.context.view_layer.objects.active = ob
    for o in bpy.context.view_layer.objects:
        o.select_set(o == ob)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.004, area_weight=0.0,
                             correct_aspect=True, scale_to_bounds=False)
    bpy.ops.object.mode_set(mode="OBJECT")
    me.uv_layers.active = me.uv_layers["UVMap"]
    me.uv_layers["UVMap"].active_render = True
    return ob


def build_collision(coll, wire_parent):
    obs = []
    for i, pts in enumerate(COLLISION):
        b = bmesh.new()
        vs = [b.verts.new(Vector(p) - CENTRE) for p in pts]
        res = bmesh.ops.convex_hull(b, input=vs)
        loose = {g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)}
        bmesh.ops.delete(b, geom=list(loose), context="VERTS")
        bmesh.ops.recalc_face_normals(b, faces=b.faces[:])
        name = f"UCX_{NAME}_{i:02d}"
        me = bpy.data.meshes.new(name)
        b.to_mesh(me)
        b.free()
        ob = bpy.data.objects.new(name, me)
        ob.display_type = "WIRE"
        ob.hide_render = True
        coll.objects.link(ob)
        obs.append(ob)
    return obs


def setup_preview(coll):
    s = bpy.context.scene
    w = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    s.world = w
    try:
        w.use_nodes = True
    except Exception:
        pass
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs["Color"].default_value = (0.9, 0.9, 0.92, 1)
    bg.inputs["Strength"].default_value = 0.75
    sun_d = bpy.data.lights.new("Sun", "SUN")
    sun_d.energy = 3.5
    sun_d.angle = math.radians(3)
    sun = bpy.data.objects.new("Sun", sun_d)
    sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(35))
    coll.objects.link(sun)
    pm = bpy.data.meshes.new("PreviewGround")
    pm.from_pydata([(-40, -40, 0), (40, -40, 0), (40, 40, 0), (-40, 40, 0)], [], [(0, 1, 2, 3)])
    g = bpy.data.objects.new("PreviewGround", pm)
    gm = bpy.data.materials.get("M_PreviewGround") or bpy.data.materials.new("M_PreviewGround")
    try:
        gm.use_nodes = True
    except Exception:
        pass
    next(n for n in gm.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Base Color"].default_value = (0.85, 0.85, 0.85, 1)
    pm.materials.append(gm)
    coll.objects.link(g)
    cam_d = bpy.data.cameras.new("Camera")
    cam_d.lens = 35
    cam = bpy.data.objects.new("Camera", cam_d)
    coll.objects.link(cam)
    s.camera = cam
    s.render.resolution_x, s.render.resolution_y = 1536, 1024
    return cam


def aim(cam, loc, target):
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


def export_fbx(obs):
    # Swap normal textures to DirectX (green-down) for Unreal, export, then restore OpenGL for Blender.
    swaps = []
    for m in bpy.data.materials:
        if m.node_tree and "NormalTex" in m.node_tree.nodes:
            node = m.node_tree.nodes["NormalTex"]
            gl = node.image
            dx = bpy.data.images.load(gl.filepath.replace("_N.png", "_N_DX.png"), check_existing=True)
            dx.colorspace_settings.name = "Non-Color"
            node.image = dx
            swaps.append((node, gl, dx))
    bpy.context.view_layer.update()
    for o in bpy.context.view_layer.objects:
        o.select_set(o in obs)
    print("EXPORTING", sorted(o.name for o in bpy.context.selected_objects))
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(OUT, NAME + ".fbx"), use_selection=True, object_types={"MESH"},
        apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
        use_tspace=True, use_mesh_modifiers=True, add_leaf_bones=False, bake_anim=False,
        path_mode="RELATIVE", axis_forward="-Z", axis_up="Y")
    for node, gl, dx in swaps:
        node.image = gl
        bpy.data.images.remove(dx)


def report(ob, cols):
    me = ob.data
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    dims = ob.dimensions
    info = {"mesh": NAME, "triangles": tris, "vertices": len(me.vertices),
            "materials": [m.name for m in me.materials], "uv_layers": [u.name for u in me.uv_layers],
            "size_m": [round(d, 3) for d in dims], "collision_hulls": len(cols),
            "collision_triangles": sum(sum(len(p.vertices) - 2 for p in c.data.polygons) for c in cols)}
    with open(os.path.join(OUT, "build_report.json"), "w") as f:
        json.dump(info, f, indent=2)
    print("BUILD_REPORT", json.dumps(info))


def main():
    clear_scene()
    mats = build_materials()
    build_house()
    export_coll = get_coll(NAME)
    ob = finish_mesh(mats, export_coll)
    cols = build_collision(export_coll, ob)
    prev = get_coll("Preview_NotExported")
    cam = setup_preview(prev)
    report(ob, cols)
    export_fbx([ob] + cols)
    s = bpy.context.scene
    try:
        s.render.engine = "BLENDER_EEVEE"
    except TypeError:
        s.render.engine = "BLENDER_EEVEE_NEXT"
    aim(cam, (13.0, -19.0, 6.0), (0.3, -1.0, 4.0))
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, NAME + ".blend"), relative_remap=True, copy=False)
    if "--render" in ARGS:
        views = {"front_three_quarter": ((13.0, -19.0, 6.0), (0.3, -1.0, 4.0)),
                 "back_left": ((-15.0, 18.0, 7.0), (0.0, 0.5, 4.0)),
                 "front": ((0.0, -24.0, 4.5), (0.0, 0.0, 4.2))}
        for name, (loc, tgt) in views.items():
            aim(cam, loc, tgt)
            s.render.filepath = os.path.join(OUT, "previews", f"{NAME}_{name}.png")
            bpy.ops.render.render(write_still=True)
        aim(cam, *views["front_three_quarter"])
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, NAME + ".blend"), relative_remap=True)
    blend1 = os.path.join(OUT, NAME + ".blend1")
    if os.path.exists(blend1):
        os.remove(blend1)


main()
