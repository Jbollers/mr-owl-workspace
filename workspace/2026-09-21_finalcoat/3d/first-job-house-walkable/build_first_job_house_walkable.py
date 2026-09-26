"""Build the walkable FinalCoat first-job house: the accepted exterior with a two-floor interior.

Headless:  blender -b --factory-startup --python build_first_job_house_walkable.py -- --render
In an open Blender: Scripting tab > open this file > Run Script (clears the scene).

Outputs next to this script: SM_FirstJobHouse_Walkable.blend/.fbx, one FBX per door leaf type
(SM_FJH_Door_*.fbx), door_placements.json, build_report.json, Textures/T_*.png and, with
--render, preview PNGs.

Conventions: 1 Blender unit = 1 m (imports as 100 cm), Z up, front door faces -Y, house pivot at
ground level in the centre of the main footprint, door-leaf pivots on the hinge edge at the leaf
bottom. UV0 = tiling world-scale material UVs, UV1 = non-overlapping lightmap UVs. UCX_ meshes
are convex collision.

The floor plan (images/first-job-floorplan-v1.png) is a proposal at roughly 8 x 10 m; the accepted
exterior is 8 x 7.5 m plus a 0.5 m front bay, so rooms keep the plan's arrangement, not its sizes.
"""
import bpy, bmesh, math, os, sys, json
import numpy as np
from mathutils import Vector

FALLBACK = r"D:\Documents\AI\mr-owl-workspace\workspace\2026-09-21_finalcoat\3d\first-job-house-walkable"
_here = globals().get("__file__")
OUT = os.path.dirname(os.path.abspath(_here)) if _here and os.path.isfile(_here) else FALLBACK
TEX = os.path.join(OUT, "Textures")
os.makedirs(TEX, exist_ok=True)
os.makedirs(os.path.join(OUT, "previews"), exist_ok=True)
ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
NAME = "SM_FirstJobHouse_Walkable"

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



def tex_wallpaint():
    """2 m tile, tired flat paint over plaster: mottling, vertical roller streaks, faint stains."""
    m = fbm(80, 500)
    fine = noise(1.5, seed=501)
    roll = noise(3, 120, 502)
    stain = sstep(1.0, 2.4, fbm(120, 510))
    col = np.array([0.68, 0.64, 0.55]) * (1 + 0.035 * m + 0.02 * fine + 0.02 * roll)[..., None]
    col = lerp(col, [0.52, 0.47, 0.35], stain * 0.35)
    h = 0.5 * fine + 0.15 * m + 0.3 * roll
    return save_png("T_WallPaint_BC", col), save_normals("T_WallPaint", blur(h, 0.8), 0.35)


def tex_wallpaper():
    """2 m tile, faded two-tone stripe wallpaper, 20 stripes, a seam every 0.5 m."""
    period = N / 20
    su = (U % period) / period
    stripe = sstep(0.47, 0.53, su) * (1 - sstep(0.97, 1.0, su))
    thin = np.abs(su - 0.25) < 0.025
    seam = ((U + 1) % (N / 4)) < 2
    fine = noise(1.5, seed=531)
    col = lerp(np.array([[[0.63, 0.61, 0.52]]]) * np.ones((N, N, 1)), [0.55, 0.57, 0.49], stripe)
    col = np.where(thin[..., None], col * 0.9, col)
    col *= (1 + 0.05 * fbm(100, 520) + 0.02 * fine)[..., None]
    col = lerp(col, [0.46, 0.41, 0.29], sstep(0.9, 2.2, fbm(130, 530)) * 0.4)
    col = np.where(seam[..., None], col * 0.8, col)
    h = 0.2 * fine - 1.0 * seam
    return save_png("T_Wallpaper_BC", col), save_normals("T_Wallpaper", blur(h, 0.7), 0.5)


def tex_ceiling():
    fine = noise(1.2, seed=541)
    col = np.array([0.80, 0.79, 0.74]) * (1 + 0.03 * fbm(90, 540) + 0.015 * fine)[..., None]
    col = lerp(col, [0.62, 0.55, 0.40], sstep(1.4, 2.6, fbm(140, 545)) * 0.3)
    return save_png("T_Ceiling_BC", col), save_normals("T_Ceiling", blur(fine, 0.8), 0.3)


def tex_woodfloor():
    """2 m tile, twelve 0.167 m boards running along v, 1 m board lengths with staggered joints."""
    bw = N / 12
    b = np.floor(U / bw).astype(int)
    ub = (U % bw) / bw
    rr = np.random.default_rng(551)
    jo = rr.uniform(0, N, 12)[b]
    vv = (V - jo) % N
    seg = np.floor(vv / (N / 2)).astype(int)
    joint = (vv % (N / 2)) < 2
    tone = rr.normal(0, 0.08, (12, 2))[b, seg]
    grain = noise(1.2, 45, 552)
    wear = sstep(0.4, 1.9, fbm(100, 553))
    col = np.array([0.34, 0.22, 0.13]) * (1 + tone + 0.1 * grain)[..., None]
    col = lerp(col, [0.45, 0.36, 0.26], wear * 0.35)
    edge = (ub < 0.015) | (ub > 0.985) | joint
    col = np.where(edge[..., None], col * 0.45, col)
    h = 0.3 * grain - 2.0 * edge
    return save_png("T_WoodFloor_BC", col), save_normals("T_WoodFloor", blur(h, 0.7), 0.8)


def tex_tilefloor():
    """1 m tile, 4 x 4 checker of 0.25 m linoleum tiles, cream and grey-green, grime in the joints."""
    t = N / 4
    chk = ((np.floor(U / t) + np.floor(V / t)) % 2)
    tu, tv = (U % t) / t, (V % t) / t
    grout = (tu < 0.012) | (tu > 0.988) | (tv < 0.012) | (tv > 0.988)
    fine = noise(1.5, seed=561)
    col = lerp(np.array([[[0.72, 0.69, 0.60]]]) * np.ones((N, N, 1)), [0.40, 0.45, 0.40], chk)
    col *= (1 + 0.04 * fbm(70, 562) + 0.02 * fine)[..., None]
    col = lerp(col, [0.40, 0.37, 0.28], sstep(0.6, 2.0, fbm(110, 563)) * 0.35)
    col = np.where(grout[..., None], col * 0.5, col)
    h = 0.2 * fine - 1.5 * grout
    return save_png("T_TileFloor_BC", col), save_normals("T_TileFloor", blur(h, 0.7), 0.6)


def tex_brass():
    """0.25 m tile, old brass: soft brown tarnish clouds over a dulled base, faint fine wear."""
    tarn = sstep(-0.4, 1.6, fbm(160, 570))
    fine = noise(1.0, seed=572)
    col = np.array([0.50, 0.40, 0.22]) * (1 + 0.03 * fine)[..., None]
    col = lerp(col, [0.31, 0.25, 0.15], tarn * 0.45)
    h = 0.2 * fine
    return save_png("T_Brass_BC", col), save_normals("T_Brass", blur(h, 0.6), 0.3)


# --------------------------------------------------------------------------- materials
(SID, TRIM, ROOF, CONC, DOOR, GLASS, METAL, WALLI, PAINT_L, PAINT_D, PAINT_E, CEIL, WOOD,
 FLTILE, BRASS) = range(15)
TILING = {SID: 2.0, TRIM: 1.0, ROOF: 2.0, CONC: 2.0, DOOR: 1.0, GLASS: 1.0, METAL: 1.0, WALLI: 2.0,
          PAINT_L: 2.0, PAINT_D: 2.0, PAINT_E: 2.0, CEIL: 2.0, WOOD: 2.0, FLTILE: 1.0, BRASS: 0.25}


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
    br = tex_brass()
    wp, wl, ce, wf, tf = tex_wallpaint(), tex_wallpaper(), tex_ceiling(), tex_woodfloor(), tex_tilefloor()
    glass = make_mat("M_Glass", color=(0.03, 0.035, 0.04), rough=0.05)
    next(n for n in glass.node_tree.nodes if n.type == "BSDF_PRINCIPLED").inputs["Alpha"].default_value = 0.55
    return [
        make_mat("M_Siding", *s, color=(0.18, 0.26, 0.22), rough=0.8),
        make_mat("M_Trim", *t, color=(0.7, 0.66, 0.55), rough=0.75),
        make_mat("M_Roof", *r, color=(0.03, 0.035, 0.045), rough=0.9),
        make_mat("M_Concrete", *c, color=(0.3, 0.3, 0.28), rough=0.9),
        make_mat("M_Door", *d, color=(0.09, 0.04, 0.02), rough=0.7),
        glass,
        make_mat("M_MetalDark", color=(0.03, 0.03, 0.03), rough=0.5, metal=0.8),
        make_mat("M_Wallpaper", *wl, color=(0.36, 0.35, 0.26), rough=0.85),
        make_mat("M_WallPaint_Living", *wp, color=(0.42, 0.38, 0.29), rough=0.85),
        make_mat("M_WallPaint_Dining", *wp, color=(0.42, 0.38, 0.29), rough=0.85),
        make_mat("M_WallPaint_Entry", *wp, color=(0.42, 0.38, 0.29), rough=0.85),
        make_mat("M_Ceiling", *ce, color=(0.6, 0.59, 0.53), rough=0.9),
        make_mat("M_WoodFloor", *wf, color=(0.1, 0.05, 0.02), rough=0.6),
        make_mat("M_TileFloor", *tf, color=(0.35, 0.35, 0.3), rough=0.5),
        make_mat("M_BrassAged", *br, color=(0.42, 0.30, 0.14), rough=0.42, metal=1.0),
    ]


# --------------------------------------------------------------------------- geometry helpers
HEX = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
S = {}          # current bmesh and its piece layer
_piece = [0]
SMOOTH = set()   # piece ids shaded smooth (turned hardware)
COLLISION = []  # point sets for the house's convex collision hulls


def begin_mesh():
    b = bmesh.new()
    S["bm"], S["piece"] = b, b.faces.layers.int.new("piece")
    return b


def poly(pts, faces, mats):
    _piece[0] += 1
    b = S["bm"]
    vs = [b.verts.new(p) for p in pts]
    mats = mats if isinstance(mats, (list, tuple)) else [mats] * len(faces)
    for f, m in zip(faces, mats):
        face = b.faces.new([vs[i] for i in f])
        face.material_index = m
        face[S["piece"]] = _piece[0]


def hexa(pts, mats):
    """8 points: bottom quad then matching top quad. mats: one or [bottom, top, -y, +x, +y, -x]."""
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
EW = 0.2  # exterior wall thickness


def fbox(F, u0, u1, z0, z1, w0, w1, m):
    ax, p, s = F
    a, b = p + s * w0, p + s * w1
    lo, hi = min(a, b), max(a, b)
    if ax == "y":
        box(u0, u1, lo, hi, z0, z1, m)
    else:
        box(lo, hi, u0, u1, z0, z1, m)


def window(F, uc, z0, z1, w, muntins=1):
    """Glass in the wall opening, exterior sash and trim, interior casing and stool."""
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
    # interior: casing, stool and apron on the room face (w = -EW)
    ic, iw = 0.07, -EW
    fbox(F, uc - hw - ic, uc - hw, z0, z1, iw - 0.02, iw, TRIM)
    fbox(F, uc + hw, uc + hw + ic, z0, z1, iw - 0.02, iw, TRIM)
    fbox(F, uc - hw - ic, uc + hw + ic, z1, z1 + 0.1, iw - 0.025, iw, TRIM)
    fbox(F, uc - hw - ic - 0.03, uc + hw + ic + 0.03, z0 - 0.035, z0, iw - 0.07, iw, TRIM)
    fbox(F, uc - hw - ic, uc + hw + ic, z0 - 0.115, z0 - 0.035, iw - 0.018, iw, TRIM)


def door_exterior_trim(F, uc, z0, w=0.95, h=2.1):
    hw, c = w / 2, 0.14
    fbox(F, uc - hw - c, uc - hw, z0, z0 + h, 0, 0.05, TRIM)
    fbox(F, uc + hw, uc + hw + c, z0, z0 + h, 0, 0.05, TRIM)
    fbox(F, uc - hw - c - 0.03, uc + hw + c + 0.03, z0 + h, z0 + h + 0.18, 0, 0.06, TRIM)
    fbox(F, uc - hw - c - 0.06, uc + hw + c + 0.06, z0 + h + 0.18, z0 + h + 0.23, 0, 0.09, TRIM)
    fbox(F, uc - hw - 0.03, uc + hw + 0.03, z0, z0 + 0.03, 0, 0.07, TRIM)


def vent(F, uc, zc, w=0.42, h=0.5):
    fbox(F, uc - w / 2, uc + w / 2, zc - h / 2, zc + h / 2, 0.0, 0.008, METAL)
    b = 0.07
    fbox(F, uc - w / 2 - b, uc - w / 2, zc - h / 2 - b, zc + h / 2 + b, 0, 0.04, TRIM)
    fbox(F, uc + w / 2, uc + w / 2 + b, zc - h / 2 - b, zc + h / 2 + b, 0, 0.04, TRIM)
    fbox(F, uc - w / 2, uc + w / 2, zc + h / 2, zc + h / 2 + b, 0, 0.04, TRIM)
    fbox(F, uc - w / 2, uc + w / 2, zc - h / 2 - b, zc - h / 2, 0, 0.04, TRIM)
    for i in range(4):
        z = zc - h / 2 + h * (i + 0.6) / 4.2
        fbox(F, uc - w / 2, uc + w / 2, z, z + 0.045, 0, 0.03, TRIM)


# --------------------------------------------------------------------------- plan
# Metres, before centring. Main body x 0..8, y 0..7.5 (front = y 0); front bay x 0..3.8 projects to
# y -0.5; porch x 3.9..8.0 projects to y -2.4. Grade z 0, foundation top 0.6.
EAVE = 6.2
G0, G1 = 0.9, 3.5      # ground floor, ground ceiling (2.6 m clear)
U0, U1 = 3.7, 6.05     # upper floor, upper ceiling (2.35 m clear, limited by the eave)
LEVELS = (G0, G1, U0, U1)
T1, T2 = math.tan(math.radians(40)), math.tan(math.radians(50))
TH1, TH2 = 0.18 / math.cos(math.radians(40)), 0.18 / math.cos(math.radians(50))

# Straight stair along the living-room partition, rising rearward from the entry to the landing.
ST_X0, ST_X1, ST_Y0 = 4.8, 5.75, 1.25
RISERS, RISE, GOING = 14, 0.2, 0.25          # 14 x 0.2 = 2.8 m = U0 - G0; 13 treads x 0.25 m
ST_Y1 = ST_Y0 + (RISERS - 1) * GOING         # 4.5, the landing edge
WELL = (ST_X0, ST_X1, 1.95, ST_Y1)           # upper-floor opening over the stair


def nosing_z(y):
    """Line through the stair nosings (also the walkable collision ramp)."""
    return G0 + RISE / GOING * (y - (ST_Y0 - GOING))


def room(name, rects, level, wall, floor, paint=False):
    z = (0.6, G1) if level == 0 else (G1, EAVE)
    return {"name": name, "rects": rects, "z": z, "level": level, "wall": wall, "floor": floor,
            "paint": paint}


LIV = [(0.2, 3.6, -0.3, 4.38), (3.6, 4.68, 0.2, 4.38)]
ROOMS = [
    room("Utility cupboard", [(7.0, 7.8, 6.5, 7.3)], 0, WALLI, FLTILE),
    room("Kitchen", [(3.7, 7.8, 4.5, 6.4), (3.7, 6.9, 6.4, 7.3)], 0, WALLI, FLTILE),
    room("Living room", LIV, 0, PAINT_L, WOOD, True),
    room("Entry and stair hall", [(4.8, 7.8, 0.2, 4.38)], 0, PAINT_E, WOOD, True),
    room("Dining room", [(0.2, 3.58, 4.5, 7.3)], 0, PAINT_D, WOOD, True),
    room("Stairwell", [WELL], 1, WALLI, None),
    room("Bedroom", LIV, 1, WALLI, WOOD),
    room("Locked room", [(4.8, 7.8, 0.2, 1.83), (5.87, 7.8, 1.83, 4.38)], 1, WALLI, WOOD),
    room("Landing", [(3.3, 7.8, 4.5, 5.6)], 1, WALLI, WOOD),
    room("Spare room", [(0.2, 3.18, 4.5, 7.3)], 1, WALLI, WOOD),
    room("Bathroom", [(3.3, 7.8, 5.72, 7.3)], 1, WALLI, FLTILE),
]


def room_at(x, y, z):
    for r in ROOMS:
        if r["z"][0] <= z < r["z"][1] and any(a < x < b and c < y < d for a, b, c, d in r["rects"]):
            return r
    return None


# Every wall face coordinate, so each wall is split wherever the room on either side changes.
XB = sorted({0.2, 3.18, 3.3, 3.58, 3.6, 3.7, 3.8, 4.68, 4.8, 5.75, 5.87, 6.9, 7.0, 7.8})
YB = sorted({-0.3, 0.0, 0.2, 1.83, 1.95, 4.38, 4.5, 5.6, 5.72, 6.4, 6.5, 7.3})
EPS = 1e-6


def P(run, u, w, z):
    return (u, w, z) if run == "x" else (w, u, z)


def wall(run, u0, u1, w0, w1, z0, z1, ops=(), a="R", b="R", end=TRIM):
    """Wall running along run ('x' or 'y') from u0 to u1, thickness w0..w1, with rectangular
    openings ops = [(u0, u1, z0, z1, kind)]. a/b: material of the -w/+w faces, or 'R' for the
    wall material of the room on that side. end: material of exposed ends outside any room."""
    brk = XB if run == "x" else YB
    ops = [o for o in ops if o[0] < u1 and o[1] > u0 and o[2] < z1 and o[3] > z0]
    us = sorted({u0, u1} | {v for v in brk if u0 < v < u1} | {e for o in ops for e in o[:2] if u0 < e < u1})
    zs = sorted({z0, z1} | {v for v in LEVELS if z0 < v < z1} | {e for o in ops for e in o[2:4] if z0 < e < z1})
    columns = []
    for ua, ub in zip(us, us[1:]):
        uc = (ua + ub) / 2
        solid = [(za, zb) for za, zb in zip(zs, zs[1:])
                 if not any(o[0] < uc < o[1] and o[2] < (za + zb) / 2 < o[3] for o in ops)]
        cells, runs = [], []
        for za, zb in solid:
            level = any(abs(za - l) < EPS for l in LEVELS)
            if cells and abs(cells[-1][1] - za) < EPS and not level:
                cells[-1][1] = zb
            else:
                cells.append([za, zb])
            if runs and abs(runs[-1][1] - za) < EPS:
                runs[-1][1] = zb
            else:
                runs.append([za, zb])
        for za, zb in cells:
            wall_cell(run, ua, ub, w0, w1, za, zb, ops, a, b, end)
        if columns and columns[-1][2] == runs:
            columns[-1][1] = ub
        else:
            columns.append([ua, ub, runs])
    for ua, ub, runs in columns:
        for za, zb in runs:
            x0, y0, _ = P(run, ua, w0, 0)
            x1, y1, _ = P(run, ub, w1, 0)
            COLLISION.append(box_pts(x0, x1, y0, y1, za, zb))


def wall_cell(run, ua, ub, w0, w1, za, zb, ops, a, b, end):
    uc, wc, zc = (ua + ub) / 2, (w0 + w1) / 2, (za + zb) / 2

    def side(spec, w):
        if spec != "R":
            return spec
        r = room_at(*P(run, uc, w, zc))
        return r["wall"] if r else WALLI

    def cap(u):
        if any(o[0] < u < o[1] and o[2] < zb and o[3] > za for o in ops):
            return TRIM  # jamb
        r = room_at(*P(run, u, wc, zc))
        return r["wall"] if r else end

    top = CEIL
    for o in ops:
        if o[0] < uc < o[1] and abs(o[2] - zb) < EPS:
            if o[4] == "window":
                top = TRIM
            else:
                r = room_at(*P(run, uc, w0 - 0.3, zb + 0.1)) or room_at(*P(run, uc, w1 + 0.3, zb + 0.1))
                top = r["floor"] if r and r["floor"] is not None else WOOD
    bot = TRIM if any(o[0] < uc < o[1] and abs(o[3] - za) < EPS for o in ops) else CEIL
    mA, mB = side(a, w0 - 0.05), side(b, w1 + 0.05)
    lo, hi = cap(ua - 0.05), cap(ub + 0.05)
    if run == "x":
        box(ua, ub, w0, w1, za, zb, [bot, top, mA, hi, mB, lo])
    else:
        box(w0, w1, ua, ub, za, zb, [bot, top, lo, mB, hi, mA])


def casing(run, u0, u1, wc, t, z0, h, sides=(-1, 1)):
    """Interior door casing on one or both faces of a wall."""
    c = 0.07
    for s in sides:
        wf = wc + s * t / 2
        for (ua, ub, za, zb, d) in [(u0 - c, u0, z0, z0 + h, 0.02), (u1, u1 + c, z0, z0 + h, 0.02),
                                    (u0 - c, u1 + c, z0 + h, z0 + h + 0.08, 0.025)]:
            wa, wb = sorted((wf, wf + s * d))
            x0, y0, _ = P(run, ua, wa, 0)
            x1, y1, _ = P(run, ub, wb, 0)
            box(x0, x1, y0, y1, za, zb, TRIM)


EXT_WINDOWS = [
    (F_BAY, 1.9, 4.25, 5.65, 1.1, 1), (F_BAY, 1.9, 1.5, 3.05, 1.7, 2),
    (F_FRONT, 5.95, 4.4, 5.6, 1.0, 1),
    (F_RIGHT, 2.3, 4.3, 5.6, 0.85, 1), (F_RIGHT, 2.0, 1.5, 2.95, 0.75, 1),
    (F_RIGHT, 3.3, 1.5, 2.95, 0.75, 1), (F_RIGHT, 5.8, 1.5, 2.95, 0.75, 1),
    # moved from y 4.0 to 3.85 so the bedroom/spare-room partition clears its casing
    (F_LEFT, 3.85, 4.3, 5.6, 0.85, 1), (F_LEFT, 2.5, 1.5, 2.95, 0.75, 1), (F_LEFT, 5.2, 1.5, 2.95, 0.75, 1),
    (F_BACK, 2.0, 4.3, 5.6, 0.95, 1), (F_BACK, 2.0, 1.5, 2.95, 0.95, 1),
    (F_BACK, 6.0, 4.3, 5.6, 0.95, 1), (F_BACK, 6.0, 1.5, 2.95, 0.95, 1),
]
FRONT_DOOR = (5.95, 0.95, 2.1)


def openings_for(F):
    return [(uc - w / 2, uc + w / 2, z0, z1, "window") for FF, uc, z0, z1, w, _ in EXT_WINDOWS if FF is F]


# Door leaves: name, type, wall run, opening u0..u1, wall centre, wall thickness, floor, opening
# height, hinge end, swing direction (+/- along the wall normal), locked.
DOORS = [
    ("Front", "Front", "x", 5.475, 6.425, 0.06, EW, G0, 2.1, "u0", 1, False),
    ("Living", "Interior", "y", 0.28, 1.18, 4.74, 0.12, G0, 2.1, "u0", -1, False),
    ("Kitchen", "Interior", "x", 6.4, 7.3, 4.44, 0.12, G0, 2.1, "u1", 1, False),
    ("DiningKitchen", "Interior", "y", 5.4, 6.3, 3.64, 0.12, G0, 2.1, "u1", 1, False),
    ("Utility", "Cupboard", "x", 7.08, 7.68, 6.45, 0.1, G0, 2.0, "u1", -1, False),
    ("Bedroom", "Interior", "x", 3.5, 4.4, 4.44, 0.12, U0, 2.1, "u0", -1, False),
    ("Locked", "Interior", "x", 6.6, 7.5, 4.44, 0.12, U0, 2.1, "u1", -1, True),
    ("Spare", "Interior", "y", 4.6, 5.5, 3.24, 0.12, U0, 2.1, "u0", -1, False),
    ("Bathroom", "Interior", "x", 4.3, 5.2, 5.66, 0.12, U0, 2.1, "u0", 1, False),
]
ARCH = ("x", 0.9, 3.1, 4.44, 0.12, G0, 2.3)   # living -> dining cased opening, no leaf
DOOR_GAP = 0.005
DOOR_TYPES = {"Front": 0.045, "Interior": 0.04, "Cupboard": 0.035}


def door_ops(run, wc):
    ops = [(d[3], d[4], d[7], d[7] + d[8], "door") for d in DOORS
           if d[2] == run and abs(d[5] - wc) < 0.02 and d[0] != "Front"]
    if ARCH[0] == run and abs(ARCH[3] - wc) < 0.02:
        ops.append((ARCH[1], ARCH[2], ARCH[5], ARCH[5] + ARCH[6], "arch"))
    return ops


# --------------------------------------------------------------------------- the house
def build_exterior():
    # foundation and solid attic gables (the attic is not accessible)
    box(-0.03, 8.03, -0.03, 7.53, 0, 0.62, CONC)
    box(-0.03, 3.83, -0.53, -0.03, 0, 0.62, CONC)
    prism([(0, EAVE), (7.5, EAVE), (3.75, EAVE + 3.75 * T1)], 0, 8, "x", SID)
    prism([(0, EAVE), (3.8, EAVE), (1.9, EAVE + 1.9 * T2)], -0.5, 2.5, "y", SID)

    # hollow exterior walls with window and door openings
    uc, dw, dh = FRONT_DOOR
    front_ops = openings_for(F_FRONT) + [(uc - dw / 2, uc + dw / 2, G0, G0 + dh, "door")]
    wall("x", 0.2, 3.8, -0.5, -0.3, 0.6, EAVE, openings_for(F_BAY), a=SID, end=SID)
    wall("y", -0.3, 0.2, 3.6, 3.8, 0.6, EAVE, b=SID, end=SID)
    wall("x", 3.8, 7.8, 0.0, 0.2, 0.6, EAVE, front_ops, a=SID, end=SID)
    wall("y", 0.0, 7.5, 7.8, 8.0, 0.6, EAVE, openings_for(F_RIGHT), b=SID, end=SID)
    wall("y", -0.5, 7.5, 0.0, 0.2, 0.6, EAVE, openings_for(F_LEFT), a=SID, end=SID)
    wall("x", 0.2, 7.8, 7.3, 7.5, 0.6, EAVE, openings_for(F_BACK), b=SID, end=SID)

    # skirt board, corner boards, frieze
    s = 0.04
    for b in [(-s, 3.8 + s, -0.5 - s, -0.5), (3.8 + s, 8, -s, 0), (8, 8 + s, -s, 7.5),
              (0, 8 + s, 7.5, 7.5 + s), (-s, 0, -0.5, 7.5 + s), (3.8, 3.8 + s, -0.5, 0)]:
        box(*b, 0.6, 0.8, TRIM)
    k = 0.09
    for cx, cy in [(0, -0.5), (3.8, -0.5), (8, 0), (8, 7.5), (0, 7.5)]:
        box(cx - k, cx + k, cy - k, cy + k, 0.62, EAVE, TRIM)
    for b in [(k, 3.8 - k, -0.53, -0.5), (3.8, 8 - k, -0.03, 0), (k, 8 - k, 7.5, 7.53), (8, 8.03, k, 7.5 - k),
              (-0.03, 0, -0.5 + k, 7.5 - k)]:
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
    box(x0 - 0.02, x1 + 0.02, 3.6, 3.9, ridge - 0.14, ridge + 0.06, ROOF)

    # front cross gable over the bay (ridge along y), trimmed to meet the main roof
    zc = lambda x: EAVE + T2 * min(x, 3.8 - x)
    yv = lambda x: (T2 * min(x, 3.8 - x) + TH2 - TH1) / T1
    cross = []
    for xa, xb in [(-0.32, 1.9), (4.12, 1.9)]:
        pts = [(xa, -0.85, zc(xa)), (xb, -0.85, zc(xb)), (xb, yv(xb), zc(xb)), (xa, yv(xa), zc(xa))]
        pts += [(x, y, z + TH2) for x, y, z in pts]
        hexa(pts, [TRIM, ROOF, TRIM, ROOF, ROOF, TRIM])
        cross += pts
    COLLISION.append(cross)
    cr = zc(1.9) + TH2
    box(1.75, 2.05, -0.87, yv(1.9), cr - 0.14, cr + 0.05, ROOF)
    for bx in (-0.12, 3.72):  # eave brackets
        box(bx, bx + 0.2, -0.75, -0.5, EAVE - 0.35, EAVE - 0.05, TRIM)

    # pent roof over the bay's ground-floor window
    pts = [(-0.15, -0.5, 3.5), (3.8, -0.5, 3.5), (3.8, -1.2, 3.2), (-0.15, -1.2, 3.2)]
    pts += [(x, y, z + 0.13) for x, y, z in pts]
    hexa(pts, [TRIM, ROOF, TRIM, TRIM, TRIM, TRIM])
    COLLISION.append(pts)
    box(-0.03, 3.8, -0.53, -0.5, 3.3, 3.5, TRIM)

    # porch: deck, steps, piers, columns, beams, railings, roof
    box(3.9, 8.0, -2.4, 0, 0, 0.84, CONC)
    box(3.88, 8.02, -2.42, 0, 0.84, 0.9, CONC)
    for k in (1, 2, 3):
        box(4.6, 7.3, -2.4 - (4 - k) * 0.3, -2.4 - (3 - k) * 0.3, 0, k * 0.225, CONC)
    for cx in (4.25, 7.65):
        cy = -2.05
        box(cx - 0.38, cx + 0.38, cy - 0.38, cy + 0.38, 0, 1.8, CONC)
        box(cx - 0.4, cx + 0.4, cy - 0.4, cy + 0.4, 1.8, 1.9, TRIM)
        a, b = 0.24, 0.17
        hexa([(cx - a, cy - a, 1.9), (cx + a, cy - a, 1.9), (cx + a, cy + a, 1.9), (cx - a, cy + a, 1.9),
              (cx - b, cy - b, 3.1), (cx + b, cy - b, 3.1), (cx + b, cy + b, 3.1), (cx - b, cy + b, 3.1)], TRIM)
        box(cx - 0.24, cx + 0.24, cy - 0.24, cy + 0.24, 3.1, 3.2, TRIM)
        box(cx - 0.12, cx + 0.12, -1.8, 0, 3.25, 3.55, TRIM)
        COLLISION.append(box_pts(cx - 0.35, cx + 0.35, cy - 0.35, cy + 0.35, 0, 3.2))
        box(cx - 0.05, cx + 0.05, -1.7, 0, 1.75, 1.85, TRIM)
        box(cx - 0.04, cx + 0.04, -1.7, 0, 0.98, 1.05, TRIM)
        for i in range(8):
            y = -1.6 + i * 0.2
            box(cx - 0.025, cx + 0.025, y - 0.025, y + 0.025, 1.05, 1.75, TRIM)
        COLLISION.append(box_pts(cx - 0.06, cx + 0.06, -1.7, 0, 0.9, 1.85))
    box(3.85, 8.05, -2.3, -1.8, 3.2, 3.55, TRIM)
    B = [(3.75, -2.7, 3.55), (8.25, -2.7, 3.55), (8.25, 0, 3.55), (3.75, 0, 3.55)]
    Pk = [(4.6, -1.5, 4.05), (7.4, -1.5, 4.05), (4.6, 0, 4.05), (7.4, 0, 4.05)]
    poly(B + Pk, [(3, 2, 1, 0), (0, 1, 5, 4), (3, 0, 4, 6), (1, 2, 7, 5), (6, 4, 5, 7), (2, 3, 6, 7)],
         [TRIM, ROOF, ROOF, ROOF, ROOF, TRIM])
    COLLISION.append(B + Pk)
    box(3.65, 8.35, -2.75, -2.65, 3.4, 3.6, TRIM)
    box(3.65, 3.75, -2.65, 0, 3.4, 3.6, TRIM)
    box(8.25, 8.35, -2.65, 0, 3.4, 3.6, TRIM)
    COLLISION.append(box_pts(3.9, 8.0, -2.4, 0, 0, 0.9))
    COLLISION.append([(4.6, -3.3, 0), (7.3, -3.3, 0), (4.6, -2.4, 0), (7.3, -2.4, 0),
                      (4.6, -2.4, 0.9), (7.3, -2.4, 0.9)])
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
        box(x - 0.04, x + 0.04, y0, y1, zt - 0.12, zt, TRIM)

    # windows (glass also blocks the player) and the front-door frame
    for F, u, z0, z1, w, mu in EXT_WINDOWS:
        window(F, u, z0, z1, w, mu)
        ax, p, s = F
        a, b = sorted((p, p - s * EW))
        COLLISION.append(box_pts(u - w / 2, u + w / 2, a, b, z0, z1) if ax == "y"
                         else box_pts(a, b, u - w / 2, u + w / 2, z0, z1))
    door_exterior_trim(F_FRONT, uc, G0, dw, dh)
    casing("x", uc - dw / 2, uc + dw / 2, 0.1, EW, G0, dh, sides=(1,))
    vent(F_RIGHT, 3.75, 8.2)
    vent(F_LEFT, 3.75, 8.2)


def build_interior():
    # floors, the upper slab (ground ceiling underneath) and the upper ceiling
    for r in ROOMS:
        if r["floor"] is None:
            continue
        z0, z1 = (0.62, G0) if r["level"] == 0 else (G1, U0)
        bottom = CONC if r["level"] == 0 else CEIL
        for x0, x1, y0, y1 in r["rects"]:
            box(x0, x1, y0, y1, z0, z1, [bottom, r["floor"], TRIM, TRIM, TRIM, TRIM])
            COLLISION.append(box_pts(x0, x1, y0, y1, z0, z1))
    for x0, x1, y0, y1 in [(0.2, 7.8, 0.2, 7.3), (0.2, 3.6, -0.3, 0.2)]:
        box(x0, x1, y0, y1, U1, EAVE, [CEIL, CEIL, TRIM, TRIM, TRIM, TRIM])
        COLLISION.append(box_pts(x0, x1, y0, y1, U1, EAVE))

    # ground-floor partitions (the living/entry wall runs full height beside the stairwell)
    wall("y", 0.2, 4.38, 4.68, 4.8, 0.62, U1, door_ops("y", 4.74))
    wall("x", 0.2, 4.8, 4.38, 4.5, 0.62, G1, door_ops("x", 4.44))
    wall("x", 5.75, 7.8, 4.38, 4.5, 0.62, G1, door_ops("x", 4.44))
    wall("y", 4.5, 7.3, 3.58, 3.7, 0.62, G1, door_ops("y", 3.64))
    wall("y", 6.5, 7.3, 6.9, 7.0, 0.62, G1)
    wall("x", 6.9, 7.8, 6.4, 6.5, 0.62, G1, door_ops("x", 6.45))
    # upper partitions (wall() ignores openings outside its own span and height)
    wall("x", 0.2, 4.8, 4.38, 4.5, G1, U1, door_ops("x", 4.44))
    wall("x", 5.75, 7.8, 4.38, 4.5, G1, U1, door_ops("x", 4.44))
    wall("y", 1.83, 4.38, 5.75, 5.87, G1, U1)
    wall("x", 4.8, 5.75, 1.83, 1.95, G1, U1)
    wall("y", 4.5, 7.3, 3.18, 3.3, G1, U1, door_ops("y", 3.24))
    wall("x", 3.3, 7.8, 5.6, 5.72, G1, U1, door_ops("x", 5.66))

    for name, _t, run, u0, u1, wc, t, fl, h, _h, _s, _l in DOORS:
        if name != "Front":
            casing(run, u0, u1, wc, t, fl, h)
    casing(ARCH[0], ARCH[1], ARCH[2], ARCH[3], ARCH[4], ARCH[5], ARCH[6])

    # stair: solid stepped blocks, top tread continues over the kitchen wall head
    for k in range(1, RISERS):
        ya = ST_Y0 + (k - 1) * GOING
        yb = min(ya + GOING, 4.38)
        box(ST_X0, ST_X1, ya, yb, 0.62, G0 + k * RISE, [CEIL, WOOD, TRIM, TRIM, TRIM, TRIM])
    box(ST_X0, ST_X1, 4.38, 4.5, 0.62, G1, [CEIL, WOOD, TRIM, TRIM, WALLI, TRIM])
    COLLISION.append([(ST_X0, ST_Y0 - GOING, G0), (ST_X1, ST_Y0 - GOING, G0),
                      (ST_X0, ST_Y1, U0), (ST_X1, ST_Y1, U0),
                      (ST_X0, ST_Y1, G0), (ST_X1, ST_Y1, G0)])

    # balustrade on the open hall side: newel, sloped rail, two balusters per tread
    rail = lambda y: nosing_z(y) + 0.9
    box(5.64, 5.76, 1.1, 1.24, G0, 2.1, TRIM)
    box(5.62, 5.78, 1.08, 1.26, 2.1, 2.16, TRIM)
    ya, yb = 1.24, 4.4
    hexa([(5.665, ya, rail(ya)), (5.735, ya, rail(ya)), (5.735, yb, rail(yb)), (5.665, yb, rail(yb)),
          (5.665, ya, rail(ya) + 0.06), (5.735, ya, rail(ya) + 0.06), (5.735, yb, rail(yb) + 0.06),
          (5.665, yb, rail(yb) + 0.06)], TRIM)
    for k in range(1, RISERS):
        for f in (0.25, 0.75):
            y = ST_Y0 + (k - 1 + f) * GOING
            box(5.685, 5.715, y - 0.015, y + 0.015, G0 + k * RISE, rail(y), TRIM)
    COLLISION.append([(5.66, ya, nosing_z(ya)), (5.75, ya, nosing_z(ya)), (5.66, yb, nosing_z(yb)),
                      (5.75, yb, nosing_z(yb)), (5.66, ya, rail(ya) + 0.06), (5.75, ya, rail(ya) + 0.06),
                      (5.66, yb, rail(yb) + 0.06), (5.75, yb, rail(yb) + 0.06)])


def build_leaf(w, h, t):
    """Six-panel door leaf in local space: hinge edge on x = 0, faces at y = +/- t/2, bottom z = 0."""
    box(0, w, -t / 2, t / 2, 0, h, DOOR)
    st = 0.12 if w > 0.7 else 0.1
    pw = (w - 3 * st) / 2
    zb, zt, gap = 0.22, h - 0.12, 0.11
    avail = zt - zb - 2 * gap
    for s in (-1, 1):
        f0 = s * t / 2
        z = zb
        for frac in (0.34, 0.30, 0.36):
            hh = avail * frac
            for ci in range(2):
                u0 = st + ci * (pw + st)
                box(u0, u0 + pw, *sorted((f0, f0 + s * 0.006)), z, z + hh, DOOR)
                box(u0 + 0.04, u0 + pw - 0.04, *sorted((f0 + s * 0.006, f0 + s * 0.014)), z + 0.04, z + hh - 0.04, DOOR)
            z += hh + gap
        door_knob(w - KNOB_BACKSET, KNOB_Z, f0, s, plate=w > 0.92)


KNOB_BACKSET, KNOB_Z = 0.065, 0.97   # knob centre from the latch edge, and above the leaf bottom


def lathe(profile, cx, cz, f0, s, segs, mat, smooth):
    """Turned solid on an axis normal to the door face: profile = [(distance out, radius)], the
    first ring sits on the face and the last point may have radius 0 (a tip)."""
    pts, faces, rings = [], [], []
    for d, r in profile:
        if r <= 0:
            rings.append([len(pts)])
            pts.append((cx, f0 + s * d, cz))
            continue
        ring = []
        for i in range(segs):
            a = 2 * math.pi * i / segs
            ring.append(len(pts))
            pts.append((cx + r * math.cos(a), f0 + s * d, cz + r * math.sin(a)))
        rings.append(ring)
    faces.append(tuple(reversed(rings[0])))
    for ra, rb in zip(rings, rings[1:]):
        if len(rb) == 1:
            faces += [(ra[i], ra[(i + 1) % segs], rb[0]) for i in range(segs)]
        else:
            faces += [(ra[i], ra[(i + 1) % segs], rb[(i + 1) % segs], rb[i]) for i in range(segs)]
    if len(rings[-1]) > 1:
        faces.append(tuple(rings[-1]))
    poly(pts, faces, mat)
    if smooth:
        SMOOTH.add(_piece[0])


def door_knob(cx, cz, f0, s, plate=False):
    """Aged-brass knob: a turned rosette (or a long backplate on the front door), a slim neck and
    a flattened ball, plus a keyhole escutcheon below it."""
    if plate:
        # front door: bevelled backplate carrying the knob and the keyhole
        box(cx - 0.029, cx + 0.029, *sorted((f0, f0 + s * 0.004)), cz - 0.17, cz + 0.07, BRASS)
        box(cx - 0.025, cx + 0.025, *sorted((f0 + s * 0.004, f0 + s * 0.007)), cz - 0.166, cz + 0.066, BRASS)
        base = 0.007
    else:
        lathe([(0, 0.029), (0.004, 0.029), (0.007, 0.025), (0.009, 0.016)], cx, cz, f0, s, 32, BRASS, False)
        base = 0.009
    lathe([(base - 0.002, 0.0085), (base + 0.012, 0.0075), (base + 0.02, 0.0095),
           (base + 0.026, 0.017), (base + 0.033, 0.025), (base + 0.042, 0.028),
           (base + 0.051, 0.026), (base + 0.058, 0.019), (base + 0.062, 0.010), (base + 0.063, 0)],
          cx, cz, f0, s, 24, BRASS, True)
    # keyhole: escutcheon with a dark slot (on the plate for the front door)
    kz = cz - 0.12
    if not plate:
        lathe([(0, 0.016), (0.003, 0.016), (0.004, 0.013)], cx, kz, f0, s, 20, BRASS, False)
    top = (0.007 if plate else 0.004) + 0.0005
    lathe([(0, 0.0045), (top, 0.0045)], cx, kz + 0.004, f0, s, 8, METAL, False)
    box(cx - 0.0018, cx + 0.0018, *sorted((f0, f0 + s * top)), kz - 0.009, kz + 0.002, METAL)


def door_transform(d, opened):
    """Pivot (hinge, leaf bottom) and yaw for a door in pre-centre coordinates."""
    name, typ, run, u0, u1, wc, t, fl, h, hinge, swing, locked = d
    hu, du = (u0 + DOOR_GAP, 1) if hinge == "u0" else (u1 - DOOR_GAP, -1)
    if run == "x":
        pivot, leaf_dir, swing_dir = (hu, wc, fl + DOOR_GAP), (du, 0), (0, swing)
        yaw = 0 if du > 0 else 180
    else:
        pivot, leaf_dir, swing_dir = (wc, hu, fl + DOOR_GAP), (0, du), (swing, 0)
        yaw = 90 if du > 0 else -90
    open_delta = 90 if leaf_dir[0] * swing_dir[1] - leaf_dir[1] * swing_dir[0] > 0 else -90
    return pivot, yaw, open_delta


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


def get_coll(name, parent=None):
    c = bpy.data.collections.new(name)
    (parent or bpy.context.scene.collection).children.link(c)
    return c


def remove_coincident(b):
    """Delete pairs of identical, opposite-facing faces (the hidden joins between wall cells)."""
    groups = {}
    for f in b.faces:
        key = tuple(sorted(tuple(round(c, 4) + 0.0 for c in v.co) for v in f.verts))
        groups.setdefault(key, []).append(f)
    kill = []
    for fs in groups.values():
        if len(fs) == 2 and fs[0].normal.dot(fs[1].normal) < -0.99:
            kill += fs
    bmesh.ops.delete(b, geom=kill, context="FACES_ONLY")
    return len(kill)


def tri_samples(pts, spacing):
    """Points strictly inside a convex polygon: centroids of a regular subdivision of each fan
    triangle, at most `spacing` apart."""
    out = []
    for i in range(1, len(pts) - 1):
        p0, p1, p2 = pts[0], pts[i], pts[i + 1]
        edge = max(np.linalg.norm(p1 - p0), np.linalg.norm(p2 - p1), np.linalg.norm(p0 - p2))
        n = int(min(max(math.ceil(edge / spacing), 1), 600))
        ii, jj = np.meshgrid(np.arange(n), np.arange(n), indexing="ij")
        up = ii + jj < n
        dn = ii + jj < n - 1
        a = np.concatenate([(ii[up] + 1 / 3) / n, (ii[dn] + 2 / 3) / n])
        c = np.concatenate([(jj[up] + 1 / 3) / n, (jj[dn] + 2 / 3) / n])
        out.append(p0 + a[:, None] * (p1 - p0) + c[:, None] * (p2 - p0))
    return np.concatenate(out)


def remove_hidden(b, layer):
    """Delete faces no camera can see: every sample just in front of the face lies inside another
    solid piece (glass excluded, it is see-through), or the face points down onto the ground."""
    pieces = {}
    for f in b.faces:
        pieces.setdefault(f[layer], []).append(f)
    occ = []
    for pid, fs in pieces.items():
        if all(f.material_index == GLASS for f in fs):
            continue
        nrm = np.array([f.normal[:] for f in fs])
        dst = np.array([f.normal.dot(f.verts[0].co) for f in fs])
        vs = np.array([v.co[:] for f in fs for v in f.verts])
        occ.append((pid, nrm, dst, vs.min(0), vs.max(0)))
    lo = np.array([o[3] for o in occ])
    hi = np.array([o[4] for o in occ])
    pids = np.array([o[0] for o in occ])

    def covered(smp, cands):
        left = smp
        for k in cands:
            _, nrm, dst, _, _ = occ[k]
            inside = np.all(left @ nrm.T - dst < 1e-6, axis=1)
            left = left[~inside]
            if len(left) == 0:
                return True
        return False

    kill, ground = [], 0
    for f in b.faces:
        n = np.array(f.normal[:])
        pts = [np.array(v.co[:]) for v in f.verts]
        if n[2] < -0.999 and max(p[2] for p in pts) < 1e-4:
            kill.append(f)
            ground += 1
            continue
        fmin, fmax = np.min(pts, 0) - 0.003, np.max(pts, 0) + 0.003
        cands = np.nonzero(np.all(lo <= fmax, 1) & np.all(hi >= fmin, 1) & (pids != f[layer]))[0]
        if len(cands) == 0:
            continue
        if covered(tri_samples(pts, 0.1) + n * 0.001, cands) and                 covered(tri_samples(pts, 0.01) + n * 0.001, cands):
            kill.append(f)
    bmesh.ops.delete(b, geom=kill, context="FACES_ONLY")
    return len(kill), ground


def zfight_candidates(b, layer):
    """Visible faces of different pieces sharing a plane and facing the same way with real
    overlapping area: they would flicker in the engine."""
    planes = {}
    for f in b.faces:
        key = (tuple(round(x, 3) + 0.0 for x in f.normal), round(f.normal.dot(f.verts[0].co), 4) + 0.0)
        planes.setdefault(key, []).append(f)
    found = []
    for fs in planes.values():
        if len(fs) < 2:
            continue
        for i, f in enumerate(fs):
            smp = tri_samples([np.array(v.co[:]) for v in f.verts], 0.01)
            for g in fs[i + 1:]:
                if g[layer] == f[layer]:
                    continue
                gv = [np.array(v.co[:]) for v in g.verts]
                n = np.array(g.normal[:])
                inside = np.ones(len(smp), bool)
                for k in range(len(gv)):
                    e = gv[(k + 1) % len(gv)] - gv[k]
                    inside &= (smp - gv[k]) @ np.cross(n, e) > 1e-5
                if inside.any():
                    c = smp[inside].mean(0)
                    found.append({"at": [round(x, 3) for x in c], "samples": int(inside.sum()),
                                  "mats": [f.material_index, g.material_index]})
    return found


def finish_mesh(b, name, mats, coll, offset, lightmap=True):
    bmesh.ops.translate(b, verts=b.verts[:], vec=-offset)
    bmesh.ops.recalc_face_normals(b, faces=b.faces[:])
    b.normal_update()
    faces_in, tris_in = len(b.faces), sum(len(f.verts) - 2 for f in b.faces)
    layer = b.faces.layers.int.get("piece")
    # occlusion first, while every piece is still a closed solid; then any leftover coincident pairs
    hidden, ground = remove_hidden(b, layer)
    doubles = remove_coincident(b)
    b.normal_update()
    zf = zfight_candidates(b, layer)
    removed = {"faces_before": faces_in, "triangles_before": tris_in,
               "double_faces_removed": doubles, "occluded_faces_removed": hidden - ground,
               "ground_contact_faces_removed": ground,
               "faces_after": len(b.faces), "triangles_after": sum(len(f.verts) - 2 for f in b.faces),
               "zfight_candidates": zf}
    print("CLEANUP", name, {k: v for k, v in removed.items() if k != "zfight_candidates"},
          "zfight", len(zf), zf[:20])
    uv = b.loops.layers.uv.new("UVMap")
    offs = {}
    rng = np.random.default_rng(5)
    for f in b.faces:
        n = f.normal
        t = Vector((1, 0, 0)) if abs(n.z) > 0.999 else Vector((0, 0, 1)).cross(n).normalized()
        if f.material_index == BRASS:  # one continuous projection across turned hardware
            t = Vector((1, 0, 0))
        bt = Vector((0, 0, 1)) if f.material_index == BRASS else n.cross(t)
        sc = TILING[f.material_index]
        o = (0.0, 0.0)
        if f.material_index in (TRIM, CONC, DOOR):  # decorrelate small pieces
            o = offs.setdefault(f[layer], tuple(rng.random(2)))
        for l in f.loops:
            p = l.vert.co
            l[uv].uv = (p.dot(t) / sc + o[0], p.dot(bt) / sc + o[1])
    for f in b.faces:
        f.smooth = f[layer] in SMOOTH
    b.faces.layers.int.remove(layer)
    used = sorted({f.material_index for f in b.faces})
    remap = {m: i for i, m in enumerate(used)}
    for f in b.faces:
        f.material_index = remap[f.material_index]
    me = bpy.data.meshes.new(name)
    b.to_mesh(me)
    b.free()
    for m in used:
        me.materials.append(mats[m])
    ob = bpy.data.objects.new(name, me)
    coll.objects.link(ob)
    if lightmap:
        lm = me.uv_layers.new(name="Lightmap")
        me.uv_layers.active = lm
        bpy.context.view_layer.objects.active = ob
        for o in bpy.context.view_layer.objects:
            o.select_set(o == ob)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=0.003, area_weight=0.0,
                                 correct_aspect=True, scale_to_bounds=False)
        bpy.ops.object.mode_set(mode="OBJECT")
        me.uv_layers.active = me.uv_layers["UVMap"]
        me.uv_layers["UVMap"].active_render = True
    return ob, removed


def build_collision(sets, mesh_name, coll, offset):
    obs = []
    for i, pts in enumerate(sets):
        b = bmesh.new()
        vs = [b.verts.new(Vector(p) - offset) for p in pts]
        res = bmesh.ops.convex_hull(b, input=vs)
        loose = {g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)}
        bmesh.ops.delete(b, geom=list(loose), context="VERTS")
        bmesh.ops.recalc_face_normals(b, faces=b.faces[:])
        name = f"UCX_{mesh_name}_{i:02d}"
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
    # one warm ceiling light per room, for interior previews only
    lights = []
    for r in ROOMS:
        if r["floor"] is None:
            continue
        x0, x1, y0, y1 = max(r["rects"], key=lambda q: (q[1] - q[0]) * (q[3] - q[2]))
        ceil = G1 if r["level"] == 0 else U1
        ld = bpy.data.lights.new("RoomLight_" + r["name"], "POINT")
        ld.energy = 120 if (x1 - x0) * (y1 - y0) > 4 else 50
        ld.color = (1.0, 0.86, 0.7)
        ld.shadow_soft_size = 0.15
        lo = bpy.data.objects.new(ld.name, ld)
        lo.location = Vector(((x0 + x1) / 2, (y0 + y1) / 2, ceil - 0.35)) - CENTRE
        coll.objects.link(lo)
        lights.append(lo)
    cam_d = bpy.data.cameras.new("Camera")
    cam_d.lens = 35
    cam = bpy.data.objects.new("Camera", cam_d)
    coll.objects.link(cam)
    s.camera = cam
    s.render.resolution_x, s.render.resolution_y = 1536, 1024
    return cam, sun, lights


def aim(cam, loc, target):
    cam.location = loc
    cam.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()


def export_fbx(obs, filename):
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
    print("EXPORTING", filename, len(bpy.context.selected_objects), "objects")
    bpy.ops.export_scene.fbx(
        filepath=os.path.join(OUT, filename), use_selection=True, object_types={"MESH"},
        apply_unit_scale=True, apply_scale_options="FBX_SCALE_UNITS", mesh_smooth_type="FACE",
        use_tspace=True, use_mesh_modifiers=True, add_leaf_bones=False, bake_anim=False,
        path_mode="RELATIVE", axis_forward="-Z", axis_up="Y")
    for node, gl, dx in swaps:
        node.image = gl
        if dx.users == 0:
            bpy.data.images.remove(dx)


def tris(ob):
    return sum(len(p.vertices) - 2 for p in ob.data.polygons)


def stair_headroom():
    """Smallest vertical clearance from a tread to the ground-floor ceiling above it."""
    worst = 99.0
    for k in range(1, RISERS):
        ya, yb = ST_Y0 + (k - 1) * GOING, ST_Y0 + k * GOING
        covered = ya < WELL[2] - EPS
        if covered:
            worst = min(worst, G1 - (G0 + k * RISE))
    return round(worst, 3)


def report(house, cols, removed, door_meshes):
    rooms = []
    for r in ROOMS:
        if r["floor"] is None:
            continue
        area = sum((x1 - x0) * (y1 - y0) for x0, x1, y0, y1 in r["rects"])
        rooms.append({"room": r["name"], "floor": "ground" if r["level"] == 0 else "upper",
                      "area_m2": round(area, 2), "paint_target": r["paint"],
                      "wall_material": MAT_NAMES[r["wall"]], "floor_material": MAT_NAMES[r["floor"]]})
    info = {
        "mesh": NAME, "triangles": tris(house), "vertices": len(house.data.vertices),
        "materials": [m.name for m in house.data.materials],
        "uv_layers": [u.name for u in house.data.uv_layers],
        "size_m": [round(d, 3) for d in house.dimensions],
        "collision_hulls": len(cols),
        "collision_triangles": sum(tris(c) for c in cols),
        "cleanup": removed,
        "levels_m": {"ground_floor": G0, "ground_ceiling": G1, "upper_floor": U0, "upper_ceiling": U1},
        "clear_height_m": {"ground": round(G1 - G0, 2), "upper": round(U1 - U0, 2)},
        "stair": {"risers": RISERS, "rise_m": RISE, "treads": RISERS - 1, "going_m": GOING,
                  "width_m": round(ST_X1 - ST_X0, 2),
                  "pitch_deg": round(math.degrees(math.atan(RISE / GOING)), 1),
                  "min_headroom_m": stair_headroom()},
        "rooms": rooms,
        "doors": [{"door": d[0], "mesh": "SM_FJH_Door_" + d[1], "clear_width_m": round(d[4] - d[3], 3),
                   "clear_height_m": d[8], "locked": d[11]} for d in DOORS],
        "door_meshes": door_meshes,
    }
    with open(os.path.join(OUT, "build_report.json"), "w") as f:
        json.dump(info, f, indent=2)
    print("BUILD_REPORT", json.dumps({k: info[k] for k in ("triangles", "size_m", "collision_hulls", "stair")}))


MAT_NAMES = []


def main():
    clear_scene()
    mats = build_materials()
    MAT_NAMES[:] = [m.name for m in mats]
    # house
    begin_mesh()
    build_exterior()
    build_interior()
    export_coll = get_coll(NAME)
    house, removed = finish_mesh(S["bm"], NAME, mats, export_coll, CENTRE)
    cols = build_collision(COLLISION, NAME, export_coll, CENTRE)
    # door leaves: one mesh per type at the origin, instanced into place
    doors_coll = get_coll("Doors_Placed")
    door_meshes, placements, leaf_meshes = {}, [], {}
    for typ, t in DOOR_TYPES.items():
        d = next(d for d in DOORS if d[1] == typ)
        w, h = d[4] - d[3] - 2 * DOOR_GAP, d[8] - 2 * DOOR_GAP
        begin_mesh()
        build_leaf(w, h, t)
        tmp = get_coll("tmp_" + typ)
        ob, _ = finish_mesh(S["bm"], "SM_FJH_Door_" + typ, mats, tmp, Vector((0, 0, 0)))
        leaf_meshes[typ] = (ob, [box_pts(0, w, -t / 2, t / 2, 0, h)], tmp)
        door_meshes["SM_FJH_Door_" + typ] = {"width_m": round(w, 3), "height_m": round(h, 3),
                                             "thickness_m": t, "triangles": tris(ob)}
    for d in DOORS:
        pivot, yaw, delta = door_transform(d, False)
        mesh = leaf_meshes[d[1]][0].data
        o = bpy.data.objects.new("Door_" + d[0], mesh)
        o.location = Vector(pivot) - CENTRE
        opened = d[0] not in ("Front", "Locked", "Utility")
        o.rotation_euler = (0, 0, math.radians(yaw + (delta * 80 / 90 if opened else 0)))
        doors_coll.objects.link(o)
        loc = Vector(pivot) - CENTRE
        placements.append({"door": d[0], "mesh": "SM_FJH_Door_" + d[1], "locked": d[11],
                           "blender_location_m": [round(v, 4) for v in loc],
                           "blender_yaw_closed_deg": yaw, "open_yaw_delta_deg": delta,
                           "blender_yaw_in_saved_scene_deg": round(yaw + (delta * 80 / 90 if opened else 0), 1)})
    with open(os.path.join(OUT, "door_placements.json"), "w") as f:
        json.dump({"note": "Blender coordinates relative to the house pivot. Rotate about Z at the "
                           "pivot (hinge edge, leaf bottom); add open_yaw_delta_deg to open. "
                           "Unreal conversion is not yet verified; expected: X cm = x*100, "
                           "Y cm = -y*100, Z cm = z*100, yaw = -blender_yaw.",
                   "doors": placements}, f, indent=2)
    prev = get_coll("Preview_NotExported")
    cam, sun, lights = setup_preview(prev)
    report(house, cols, removed, door_meshes)
    export_fbx([house] + cols, NAME + ".fbx")
    for typ, (ob, sets, tmp) in leaf_meshes.items():
        dcols = build_collision(sets, ob.name, tmp, Vector((0, 0, 0)))
        export_fbx([ob] + dcols, ob.name + ".fbx")
        for c in dcols:
            bpy.data.objects.remove(c, do_unlink=True)
        bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.collections.remove(tmp)
    s = bpy.context.scene
    try:
        s.render.engine = "BLENDER_EEVEE"
    except TypeError:
        s.render.engine = "BLENDER_EEVEE_NEXT"
    try:
        s.eevee.taa_render_samples = 48
    except Exception:
        pass
    for m in list(bpy.data.materials):
        if m.users == 0:
            bpy.data.materials.remove(m)
    ext = {"front_three_quarter": ((13.0, -19.0, 6.0), (0.3, -1.0, 4.0)),
           "back_left": ((-15.0, 18.0, 7.0), (0.0, 0.5, 4.0)),
           "front": ((0.0, -24.0, 4.5), (0.0, 0.0, 4.2))}
    C = lambda x, y, z: tuple(Vector((x, y, z)) - CENTRE)
    inside = {"interior_entry": (C(7.35, 0.45, 2.45), C(4.9, 4.2, 2.3)),
              "interior_living": (C(4.4, 0.4, 2.5), C(1.4, 6.0, 1.7)),
              "interior_landing": (C(7.5, 5.3, 5.25), C(3.6, 4.4, 4.3))}
    ld = next(d for d in DOORS if d[0] == "Locked")
    piv, yaw, _ = door_transform(ld, False)
    w_ld = ld[4] - ld[3] - 2 * DOOR_GAP
    a = math.radians(yaw)
    kx, ky = w_ld - KNOB_BACKSET, DOOR_TYPES["Interior"] / 2
    knob = Vector((piv[0] + kx * math.cos(a) - ky * math.sin(a),
                   piv[1] + kx * math.sin(a) + ky * math.cos(a), piv[2] + KNOB_Z)) - CENTRE
    closeup = (tuple(knob + Vector((0.28, 0.42, 0.12))), tuple(knob + Vector((0.0, 0.02, -0.03))))
    aim(cam, *ext["front_three_quarter"])
    for l in lights:
        l.hide_render = True
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, NAME + ".blend"), relative_remap=True, copy=False)
    if "--render" in ARGS:
        out = lambda n: os.path.join(OUT, "previews", f"{NAME}_{n}.png")
        for name, (loc, tgt) in ext.items():
            aim(cam, loc, tgt)
            s.render.filepath = out(name)
            bpy.ops.render.render(write_still=True)
        for l in lights:
            l.hide_render = False
        cam.data.lens = 16
        for name, (loc, tgt) in inside.items():
            aim(cam, loc, tgt)
            s.render.filepath = out(name)
            bpy.ops.render.render(write_still=True)
        cam.data.lens = 50
        aim(cam, *closeup)
        s.render.filepath = out("door_knob")
        bpy.ops.render.render(write_still=True)
        # plan cutaways: orthographic top view clipped just below each ceiling
        sun.data.use_shadow = False
        cam.data.type = "ORTHO"
        cam.data.ortho_scale = 11.5
        s.render.resolution_x = s.render.resolution_y = 1400
        cam.location, cam.rotation_euler = (0.0, -0.6, 30.0), (0, 0, 0)
        for name, cut in (("plan_ground", 2.6), ("plan_upper", 5.4)):
            cam.data.clip_start, cam.data.clip_end = 30.0 - cut, 60.0
            s.render.filepath = out(name)
            bpy.ops.render.render(write_still=True)
        cam.data.type, cam.data.lens = "PERSP", 35
        cam.data.clip_start, cam.data.clip_end = 0.1, 1000
        s.render.resolution_x, s.render.resolution_y = 1536, 1024
        sun.data.use_shadow = True
        for l in lights:
            l.hide_render = True
        aim(cam, *ext["front_three_quarter"])
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, NAME + ".blend"), relative_remap=True)
    blend1 = os.path.join(OUT, NAME + ".blend1")
    if os.path.exists(blend1):
        os.remove(blend1)


main()
