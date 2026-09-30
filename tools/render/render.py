#!/usr/bin/env python3
"""Offline ReShade 4.5.4 renderer for the Warzone presets.

Runs a preset's real effect chain on a captured game frame, the way ReShade's
OpenGL runtime does it (same compiler, same GLSL, same pass/texture/uniform rules),
on headless Mesa OpenGL 4.5.

    python3 render.py PRESET.ini FRAME.png OUT.png [--frames 30] [--shaders DIR] [--textures DIR]

FRAME.png must be the untouched game frame (ReShade off), ideally 800x600.
Temporal effects (adaptation, blink timers) settle over --frames frames at 60 fps.
"""
import argparse, json, os, re, subprocess, sys, hashlib, random, datetime
os.environ.setdefault("PYOPENGL_PLATFORM", "egl")
import numpy as np
from PIL import Image
import moderngl
from OpenGL import GL

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
FXDUMP = os.path.join(HERE, "fxdump")
CACHE = os.path.join(os.environ.get("TMPDIR", "/tmp"), "wz_render_cache")

FMT = {1: GL.GL_R8, 2: GL.GL_R16F, 3: GL.GL_R32F, 4: GL.GL_RG8, 5: GL.GL_RG16, 6: GL.GL_RG16F, 7: GL.GL_RG32F,
       8: GL.GL_RGBA8, 9: GL.GL_RGBA16, 10: GL.GL_RGBA16F, 11: GL.GL_RGBA32F, 12: GL.GL_RGB10_A2}
ADDR = {1: GL.GL_REPEAT, 2: GL.GL_MIRRORED_REPEAT, 3: GL.GL_CLAMP_TO_EDGE, 4: GL.GL_CLAMP_TO_BORDER}
FILT = {0: (GL.GL_NEAREST_MIPMAP_NEAREST, GL.GL_NEAREST), 1: (GL.GL_NEAREST_MIPMAP_LINEAR, GL.GL_NEAREST),
        4: (GL.GL_NEAREST_MIPMAP_NEAREST, GL.GL_LINEAR), 5: (GL.GL_NEAREST_MIPMAP_LINEAR, GL.GL_LINEAR),
        0x10: (GL.GL_LINEAR_MIPMAP_NEAREST, GL.GL_NEAREST), 0x11: (GL.GL_LINEAR_MIPMAP_LINEAR, GL.GL_NEAREST),
        0x14: (GL.GL_LINEAR_MIPMAP_NEAREST, GL.GL_LINEAR), 0x15: (GL.GL_LINEAR_MIPMAP_LINEAR, GL.GL_LINEAR)}
BLEND_FUNC = {0: GL.GL_ZERO, 1: GL.GL_ONE, 2: GL.GL_SRC_COLOR, 3: GL.GL_SRC_ALPHA, 4: GL.GL_ONE_MINUS_SRC_COLOR,
              5: GL.GL_ONE_MINUS_SRC_ALPHA, 6: GL.GL_DST_COLOR, 7: GL.GL_DST_ALPHA, 8: GL.GL_ONE_MINUS_DST_COLOR,
              9: GL.GL_ONE_MINUS_DST_ALPHA}
BLEND_OP = {1: GL.GL_FUNC_ADD, 2: GL.GL_FUNC_SUBTRACT, 3: GL.GL_FUNC_REVERSE_SUBTRACT, 4: GL.GL_MIN, 5: GL.GL_MAX}


# ------------------------------------------------------------------ preset
def read_ini(path):
    txt = open(path, "rb").read().decode("latin-1").replace("\r", "")
    top, sections, cur = {}, {}, None
    for line in txt.split("\n"):
        line = line.strip()
        if not line or line.startswith(";"):
            continue
        m = re.match(r"^\[(.+)\]$", line)
        if m:
            cur = sections.setdefault(m.group(1), {})
            continue
        if "=" in line:
            k, v = line.split("=", 1)
            (cur if cur is not None else top)[k.strip()] = v.strip()
    return top, sections


def split_defs(s):
    out, cur, q = [], "", False
    for ch in s:
        if ch == '"':
            q = not q
        if ch == "," and not q:
            out.append(cur); cur = ""
        else:
            cur += ch
    if cur:
        out.append(cur)
    return [d.strip() for d in out if d.strip()]


# ------------------------------------------------------------------ compile
def include_dirs(shaders):
    dirs = [shaders]
    for sub in ("PD80", "Pirate", "qUINT", "Depth3D", "OtisFX", "Daodan", "Fubax"):
        p = os.path.join(shaders, sub)
        if os.path.isdir(p):
            dirs.append(p)
    return dirs


def all_fx(shaders):
    out = []
    for d in include_dirs(shaders):
        out += [os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(".fx")]
    return out


def dump(fx, defs, shaders, w, h):
    os.makedirs(CACHE, exist_ok=True)
    key = hashlib.sha1((open(fx, "rb").read().hex() + "|" + "|".join(defs) + f"|{w}x{h}|" + fx).encode()).hexdigest()[:16]
    prefix = os.path.join(CACHE, os.path.basename(fx) + "." + key)
    if not os.path.exists(prefix + ".json"):
        args = [FXDUMP, fx, prefix, str(w), str(h)] + ["-D" + d for d in defs] + ["-I" + d for d in include_dirs(shaders)]
        r = subprocess.run(args, capture_output=True, text=True)
        if r.returncode != 0:
            return None, r.stderr
    return (json.load(open(prefix + ".json")), open(prefix + ".glsl").read()), ""


# ------------------------------------------------------------------ runtime
class Runtime:
    def __init__(self, w, h, textures_dir):
        self.ctx = moderngl.create_standalone_context(backend="egl", require=450)
        self.w, self.h, self.textures_dir = w, h, textures_dir
        self.textures = {}   # unique name -> dict(id, srgb_id, levels, w, h)
        # back buffer: sRGB-capable, like ReShade's RBO_COLOR (GL_SRGB8_ALPHA8)
        self.back = self._tex(w, h, GL.GL_SRGB8_ALPHA8, 1)
        self.back_copy = self._tex(w, h, GL.GL_RGBA8, 1)
        self.back_copy_srgb = GL.glGenTextures(1)
        GL.glTextureView(self.back_copy_srgb, GL.GL_TEXTURE_2D, self.back_copy, GL.GL_SRGB8_ALPHA8, 0, 1, 0, 1)
        self.depth = self._tex(1, 1, GL.GL_R32F, 1)
        GL.glTextureSubImage2D(self.depth, 0, 0, 0, 1, 1, GL.GL_RED, GL.GL_FLOAT, np.zeros(1, np.float32))
        self.fbo_back = GL.glGenFramebuffers(1)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.fbo_back)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, self.back, 0)
        self.fbo_blit = GL.glGenFramebuffers(1)
        GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.fbo_blit)
        GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0, GL.GL_TEXTURE_2D, self.back_copy, 0)
        self.fbo_pass = GL.glGenFramebuffers(1)
        self.vao = GL.glGenVertexArrays(1)
        self.effects = []
        self.frame = 0
        self.time_ms = 0.0

    def _tex(self, w, h, fmt, levels):
        t = GL.glGenTextures(1)
        GL.glBindTexture(GL.GL_TEXTURE_2D, t)
        GL.glTexStorage2D(GL.GL_TEXTURE_2D, levels, fmt, w, h)
        return t

    def set_frame(self, rgb):
        # GL convention: row 0 = bottom
        img = np.ascontiguousarray(np.flipud(rgb))
        rgba = np.concatenate([img, np.full(img.shape[:2] + (1,), 255, np.uint8)], 2)
        GL.glTextureSubImage2D(self.back, 0, 0, 0, self.w, self.h, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, rgba)

    def read_back(self):
        GL.glDisable(GL.GL_FRAMEBUFFER_SRGB)
        GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, self.fbo_back)
        data = GL.glReadPixels(0, 0, self.w, self.h, GL.GL_RGBA, GL.GL_UNSIGNED_BYTE)
        a = np.frombuffer(data, np.uint8).reshape(self.h, self.w, 4)
        return np.flipud(a[..., :3]).copy()

    # ---- effect setup
    def add_effect(self, name, mod, code, values):
        errors = []
        ubo_size = (mod["total_uniform_size"] + 15) & ~15
        eff = dict(name=name, uniforms=mod["uniforms"], data=bytearray(ubo_size), ubo=None, techniques={}, samplers=[])
        # textures
        for t in mod["textures"]:
            if t["semantic"] or t["name"] in self.textures:
                continue
            fmt = FMT.get(t["format"], GL.GL_RGBA8)
            tid = self._tex(t["w"], t["h"], fmt, t["levels"])
            srgb = None
            if fmt == GL.GL_RGBA8:
                srgb = GL.glGenTextures(1)
                GL.glTextureView(srgb, GL.GL_TEXTURE_2D, tid, GL.GL_SRGB8_ALPHA8, 0, t["levels"], 0, 1)
            rec = dict(id=tid, srgb=srgb, levels=t["levels"], w=t["w"], h=t["h"])
            self.textures[t["name"]] = rec
            src = t["ann"].get("source", {}).get("value", {}).get("s")
            if src:
                cands = [os.path.join(d, src) for d in self.textures_dir.split(os.pathsep)]
                p = next((c for c in cands if os.path.exists(c)), None)
                if p:
                    im = Image.open(p).convert("RGBA").resize((t["w"], t["h"]))
                    a = np.ascontiguousarray(np.flipud(np.asarray(im)))
                    GL.glTextureSubImage2D(tid, 0, 0, 0, t["w"], t["h"], GL.GL_RGBA, GL.GL_UNSIGNED_BYTE, a)
                    if t["levels"] > 1:
                        GL.glGenerateTextureMipmap(tid)
                else:
                    errors.append(f"missing texture {src}")
            else:
                zero = np.zeros((t["h"], t["w"], 4), np.float32)
                GL.glTextureSubImage2D(tid, 0, 0, 0, t["w"], t["h"], GL.GL_RGBA, GL.GL_FLOAT, zero)
        tex_sem = {t["name"]: t["semantic"] for t in mod["textures"]}
        # samplers
        for s in mod["samplers"]:
            sid = GL.glGenSamplers(1)
            mn, mg = FILT.get(s["filter"], FILT[0x15])
            GL.glSamplerParameteri(sid, GL.GL_TEXTURE_MIN_FILTER, mn)
            GL.glSamplerParameteri(sid, GL.GL_TEXTURE_MAG_FILTER, mg)
            GL.glSamplerParameteri(sid, GL.GL_TEXTURE_WRAP_S, ADDR.get(s["au"], GL.GL_CLAMP_TO_EDGE))
            GL.glSamplerParameteri(sid, GL.GL_TEXTURE_WRAP_T, ADDR.get(s["av"], GL.GL_CLAMP_TO_EDGE))
            GL.glSamplerParameterf(sid, GL.GL_TEXTURE_LOD_BIAS, s["lod_bias"])
            GL.glSamplerParameterf(sid, GL.GL_TEXTURE_MIN_LOD, max(s["min_lod"], -1000.0))
            GL.glSamplerParameterf(sid, GL.GL_TEXTURE_MAX_LOD, min(s["max_lod"], 1000.0))
            sem = tex_sem.get(s["texture"], "")
            eff["samplers"].append(dict(binding=s["binding"], sampler=sid, texture=s["texture"], semantic=sem, srgb=s["srgb"]))
        # uniforms
        for u in mod["uniforms"]:
            self._write_uniform(eff, u, self._initial(u, values))
        if ubo_size:
            eff["ubo"] = GL.glGenBuffers(1)
            GL.glBindBuffer(GL.GL_UNIFORM_BUFFER, eff["ubo"])
            GL.glBufferData(GL.GL_UNIFORM_BUFFER, ubo_size, bytes(eff["data"]), GL.GL_DYNAMIC_DRAW)
        # programs
        shaders = {}
        for ep in mod["entry_points"]:
            pre = "#version 430\n#define ENTRY_POINT_%s 1\n" % ep["name"]
            if not ep["ps"]:
                pre += "#define discard\n#define dFdx(x) x\n#define dFdy(y) y\n#define fwidth(p) p\n"
            sh = GL.glCreateShader(GL.GL_FRAGMENT_SHADER if ep["ps"] else GL.GL_VERTEX_SHADER)
            GL.glShaderSource(sh, pre + "#line 1 0\n" + code)
            GL.glCompileShader(sh)
            if not GL.glGetShaderiv(sh, GL.GL_COMPILE_STATUS):
                errors.append(f"{name}:{ep['name']}: " + GL.glGetShaderInfoLog(sh).decode()[:500])
                return errors
            shaders[ep["name"]] = sh
        for tech in mod["techniques"]:
            passes = []
            for p in tech["passes"]:
                prog = GL.glCreateProgram()
                GL.glAttachShader(prog, shaders[p["vs"]])
                GL.glAttachShader(prog, shaders[p["ps"]])
                GL.glLinkProgram(prog)
                if not GL.glGetProgramiv(prog, GL.GL_LINK_STATUS):
                    errors.append(f"{name}:{tech['name']} link: " + GL.glGetProgramInfoLog(prog).decode()[:300])
                passes.append(dict(p, program=prog))
            eff["techniques"][tech["name"]] = passes
        self.effects.append(eff)
        return errors

    def _initial(self, u, values):
        key = u["name"]
        short = key.split("::")[-1]
        v = values.get(key, values.get(short))
        if v is not None:
            parts = [x.strip() for x in v.split(",")]
            try:
                return [float(x) for x in parts]
            except ValueError:
                pass
        base = u["type"]["base"]
        n = max(1, u["type"]["rows"]) * max(1, u["type"]["cols"])
        if base == 4:
            return u["init"]["f"][:n]
        return [float(x) for x in u["init"]["i"][:n]]

    def _write_uniform(self, eff, u, vals):
        base = u["type"]["base"]
        rows, cols = max(1, u["type"]["rows"]), max(1, u["type"]["cols"])
        n = rows * cols
        vals = (list(vals) + [0.0] * n)[:n]
        if cols > 1:  # matrix, std140 column_major: each column padded to vec4
            buf = np.zeros(cols * 4, np.float32)
            for c in range(cols):
                for r in range(rows):
                    buf[c * 4 + r] = vals[r * cols + c]
            b = buf.tobytes()
        elif base == 4:
            b = np.array(vals, np.float32).tobytes()
        elif base == 3:
            b = np.array([max(0, int(x)) for x in vals], np.uint32).tobytes()
        else:
            b = np.array([int(x) for x in vals], np.int32).tobytes()
        o = u["offset"]
        eff["data"][o:o + len(b)] = b

    def _specials(self, eff, dt_ms):
        for u in eff["uniforms"]:
            src = u["ann"].get("source", {}).get("value", {}).get("s")
            if not src:
                continue
            if src == "frametime":
                self._write_uniform(eff, u, [dt_ms])
            elif src == "framecount":
                self._write_uniform(eff, u, [self.frame % 2 == 0] if u["type"]["base"] == 1 else [self.frame])
            elif src == "timer":
                self._write_uniform(eff, u, [float(int(self.time_ms))])
            elif src == "random":
                mn = u["ann"].get("min", {}).get("value", {}).get("i", [0])[0]
                mx = u["ann"].get("max", {}).get("value", {}).get("i", [0])[0]
                self._write_uniform(eff, u, [mn + random.randint(0, max(0, mx - mn))])
            elif src == "date":
                d = datetime.datetime(2026, 9, 30, 21, 0, 0)
                self._write_uniform(eff, u, [d.year, d.month, d.day, 21 * 3600])
            elif src == "pingpong":
                self._write_uniform(eff, u, [0.5, 1.0])
            # key / mouse*: stay at 0

    # ---- rendering
    def run_technique(self, eff, passes, dt_ms):
        GL.glDisable(GL.GL_CULL_FACE); GL.glDisable(GL.GL_DEPTH_TEST); GL.glDisable(GL.GL_SCISSOR_TEST)
        GL.glBindVertexArray(self.vao)
        self._specials(eff, dt_ms)
        if eff["ubo"]:
            GL.glBindBufferBase(GL.GL_UNIFORM_BUFFER, 0, eff["ubo"])
            GL.glBufferSubData(GL.GL_UNIFORM_BUFFER, 0, len(eff["data"]), bytes(eff["data"]))
        for s in eff["samplers"]:
            GL.glActiveTexture(GL.GL_TEXTURE0 + s["binding"])
            if s["semantic"] == "COLOR":
                tid = self.back_copy_srgb if s["srgb"] else self.back_copy
            elif s["semantic"] == "DEPTH":
                tid = self.depth
            else:
                rec = self.textures.get(s["texture"])
                tid = (rec["srgb"] if s["srgb"] and rec["srgb"] else rec["id"]) if rec else 0
            GL.glBindTexture(GL.GL_TEXTURE_2D, tid)
            GL.glBindSampler(s["binding"], s["sampler"])
        for p in passes:
            # copy back buffer for this pass
            GL.glDisable(GL.GL_FRAMEBUFFER_SRGB)
            GL.glBindFramebuffer(GL.GL_READ_FRAMEBUFFER, self.fbo_back)
            GL.glBindFramebuffer(GL.GL_DRAW_FRAMEBUFFER, self.fbo_blit)
            GL.glBlitFramebuffer(0, 0, self.w, self.h, 0, 0, self.w, self.h, GL.GL_COLOR_BUFFER_BIT, GL.GL_NEAREST)
            targets = [t for t in p["rt"] if t]
            if targets:
                GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.fbo_pass)
                for k in range(8):
                    GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0 + k, GL.GL_TEXTURE_2D, 0, 0)
                vw = vh = 0
                for k, t in enumerate(targets):
                    rec = self.textures[t]
                    tid = rec["srgb"] if p["srgb"] and rec["srgb"] else rec["id"]
                    GL.glFramebufferTexture2D(GL.GL_FRAMEBUFFER, GL.GL_COLOR_ATTACHMENT0 + k, GL.GL_TEXTURE_2D, tid, 0)
                    vw, vh = rec["w"], rec["h"]
                GL.glDrawBuffers(len(targets), [GL.GL_COLOR_ATTACHMENT0 + k for k in range(len(targets))])
            else:
                GL.glBindFramebuffer(GL.GL_FRAMEBUFFER, self.fbo_back)
                GL.glDrawBuffers(1, [GL.GL_COLOR_ATTACHMENT0])
                vw, vh = self.w, self.h
            GL.glViewport(0, 0, p["vw"] or vw, p["vh"] or vh)
            GL.glUseProgram(p["program"])
            if p["blend"]:
                GL.glEnable(GL.GL_BLEND)
                GL.glBlendFuncSeparate(BLEND_FUNC[p["src"]], BLEND_FUNC[p["dst"]], BLEND_FUNC[p["src_a"]], BLEND_FUNC[p["dst_a"]])
                GL.glBlendEquationSeparate(BLEND_OP[p["blend_op"]], BLEND_OP[p["blend_op_a"]])
            else:
                GL.glDisable(GL.GL_BLEND)
            (GL.glEnable if p["srgb"] else GL.glDisable)(GL.GL_FRAMEBUFFER_SRGB)
            m = p["mask"]
            GL.glColorMask(bool(m & 1), bool(m & 2), bool(m & 4), bool(m & 8))
            if p["clear"]:
                for k in range(len(targets) or 1):
                    GL.glClearBufferfv(GL.GL_COLOR, k, [0.0, 0.0, 0.0, 0.0])
            GL.glDrawArrays(GL.GL_TRIANGLES, 0, p["verts"])
            GL.glColorMask(True, True, True, True)
            for t in targets:
                rec = self.textures[t]
                if rec["levels"] > 1:
                    GL.glGenerateTextureMipmap(rec["id"])
        GL.glDisable(GL.GL_FRAMEBUFFER_SRGB)
        GL.glDisable(GL.GL_BLEND)


def technique_order(top):
    enabled = [t for t in top.get("Techniques", "").split(",") if t]
    sorting = [t for t in top.get("TechniqueSorting", "").split(",") if t]
    order = [t for t in sorting if t in enabled] + [t for t in enabled if t not in sorting]
    return order


def render(preset, frames_in, shaders, textures_dir, n_frames=120, log=print, capture=None, start_ms=5000.0):
    """frames_in: list of RGB uint8 arrays (the same frame repeated is fine). Returns output RGB of the last frame."""
    top, sections = read_ini(preset)
    defs = split_defs(top.get("PreprocessorDefinitions", ""))
    defs += ["RESHADE_DEPTH_LINEARIZATION_FAR_PLANE=1000.0", "RESHADE_DEPTH_INPUT_IS_UPSIDE_DOWN=0",
             "RESHADE_DEPTH_INPUT_IS_REVERSED=1", "RESHADE_DEPTH_INPUT_IS_LOGARITHMIC=0"]
    h, w = frames_in[0].shape[:2]
    order = technique_order(top)
    rt = Runtime(w, h, textures_dir)
    # find which file defines each technique
    tech_file, loaded, problems = {}, {}, []
    for fx in all_fx(shaders):
        res, err = dump(fx, defs, shaders, w, h)
        if res is None:
            continue
        for t in res[0]["techniques"]:
            tech_file.setdefault(t["name"], (fx, res))
    for t in order:
        if t not in tech_file:
            problems.append(f"technique {t} not found")
            continue
        fx, (mod, code) = tech_file[t]
        if fx not in loaded:
            values = sections.get(os.path.basename(fx), {})
            errs = rt.add_effect(os.path.basename(fx), mod, code, values)
            problems += errs
            loaded[fx] = rt.effects[-1] if not errs else None
    plan = [(t, loaded.get(tech_file[t][0])) for t in order if t in tech_file]
    plan = [(t, e) for t, e in plan if e]
    out = None
    dt = 1000.0 / 60.0
    for i in range(n_frames):
        rt.set_frame(frames_in[i % len(frames_in)])
        rt.frame, rt.time_ms = i, start_ms + i * dt
        for t, eff in plan:
            rt.run_technique(eff, eff["techniques"][t], dt)
        GL.glFinish()
        if capture is not None and i >= n_frames - capture[0] * capture[1] and (n_frames - 1 - i) % capture[1] == 0:
            capture[2].append(rt.read_back())
    out = rt.read_back()
    for p in problems:
        log("  ! " + p)
    return out, [t for t, _ in plan], problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("preset"); ap.add_argument("frame"); ap.add_argument("out")
    ap.add_argument("--frames", type=int, default=120)
    ap.add_argument("--gif", help="also write an animated GIF of the last frames")
    ap.add_argument("--gif-count", type=int, default=40)
    ap.add_argument("--gif-every", type=int, default=6, help="frames between GIF images (6 = 0.1 s)")
    ap.add_argument("--crop", help="x0,y0,x1,y1 crop for the GIF")
    ap.add_argument("--shaders", default=os.path.join(REPO, "game", "reshade-shaders", "Shaders"))
    ap.add_argument("--textures", default=os.pathsep.join([os.path.join(REPO, "game", "reshade-shaders", "Textures"),
                                                           "/mnt/user-data/uploads/reshade-shaders/Textures"]))
    a = ap.parse_args()
    img = np.asarray(Image.open(a.frame).convert("RGB"))
    cap = None
    frames = a.frames
    if a.gif:
        cap = (a.gif_count, a.gif_every, [])
        frames = max(a.frames, a.gif_count * a.gif_every + 60)
    out, chain, problems = render(a.preset, [img], a.shaders, a.textures, frames, capture=cap)
    Image.fromarray(out).save(a.out)
    if a.gif:
        ims = [Image.fromarray(f) for f in cap[2]]
        if a.crop:
            box = tuple(int(v) for v in a.crop.split(","))
            ims = [im.crop(box) for im in ims]
        ims[0].save(a.gif, save_all=True, append_images=ims[1:], duration=a.gif_every * 1000 // 60, loop=0)
    print("chain:", " > ".join(chain))
    sys.exit(1 if problems else 0)


if __name__ == "__main__":
    main()
