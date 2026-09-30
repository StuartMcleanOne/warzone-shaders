// fxdump: compile a ReShade 4.5.4 .fx file with ReShade's own compiler and dump
//   <out>.glsl  - the generated GLSL module (as the OpenGL runtime would receive it)
//   <out>.json  - textures, samplers, uniforms, techniques, passes, entry points
// Usage: fxdump <file.fx> <out_prefix> <width> <height> [-DNAME=VALUE ...] [-Iinclude_dir ...]
// Exit code 0 on success; errors go to stderr.
#include "effect_parser.hpp"
#include "effect_preprocessor.hpp"
#include "effect_codegen.hpp"
#include <fstream>
#include <iostream>
#include <sstream>
#include <cmath>
static double fin(float v){ return std::isfinite(v) ? v : 0.0; }

using namespace reshadefx;

static std::string esc(const std::string &s)
{
    std::string o;
    for (char c : s) {
        switch (c) {
        case '"': o += "\\\""; break;
        case '\\': o += "\\\\"; break;
        case '\n': o += "\\n"; break;
        case '\r': break;
        case '\t': o += "\\t"; break;
        default:
            if ((unsigned char)c < 0x20) { char b[8]; snprintf(b, 8, "\\u%04x", c); o += b; }
            else o += c;
        }
    }
    return o;
}

static std::string type_json(const type &t)
{
    std::ostringstream s;
    s << "{\"base\":" << int(t.base) << ",\"rows\":" << t.rows << ",\"cols\":" << t.cols << ",\"array\":" << t.array_length << "}";
    return s.str();
}

static std::string const_json(const type &t, const constant &c)
{
    std::ostringstream s;
    s << "{\"s\":\"" << esc(c.string_data) << "\",\"f\":[";
    for (int i = 0; i < 16; i++) s << (i ? "," : "") << fin(c.as_float[i]);
    s << "],\"i\":[";
    for (int i = 0; i < 16; i++) s << (i ? "," : "") << c.as_int[i];
    s << "],\"arr\":[";
    for (size_t k = 0; k < c.array_data.size(); k++) s << (k ? "," : "") << const_json(t, c.array_data[k]);
    s << "]}";
    return s.str();
}

static std::string ann_json(const std::vector<annotation> &a)
{
    std::ostringstream s;
    s << "{";
    for (size_t i = 0; i < a.size(); i++)
        s << (i ? "," : "") << "\"" << esc(a[i].name) << "\":{\"type\":" << type_json(a[i].type) << ",\"value\":" << const_json(a[i].type, a[i].value) << "}";
    s << "}";
    return s.str();
}

int main(int argc, char **argv)
{
    if (argc < 5) { std::cerr << "usage: fxdump file.fx out_prefix width height [-DN=V] [-Idir]\n"; return 2; }
    std::string file = argv[1], out = argv[2], w = argv[3], h = argv[4];
    preprocessor pp;
    pp.add_macro_definition("__RESHADE__", "40504");
    pp.add_macro_definition("__RESHADE_PERFORMANCE_MODE__", "0");
    pp.add_macro_definition("__VENDOR__", "0x10005");   // Mesa
    pp.add_macro_definition("__DEVICE__", "0");
    pp.add_macro_definition("__RENDERER__", "0x14500"); // OpenGL 4.5
    pp.add_macro_definition("__APPLICATION__", "0");
    pp.add_macro_definition("BUFFER_WIDTH", w);
    pp.add_macro_definition("BUFFER_HEIGHT", h);
    pp.add_macro_definition("BUFFER_RCP_WIDTH", "(1.0 / BUFFER_WIDTH)");
    pp.add_macro_definition("BUFFER_RCP_HEIGHT", "(1.0 / BUFFER_HEIGHT)");
    pp.add_macro_definition("BUFFER_COLOR_BIT_DEPTH", "8");
    for (int i = 5; i < argc; i++) {
        std::string a = argv[i];
        if (a.rfind("-I", 0) == 0) pp.add_include_path(a.substr(2));
        else if (a.rfind("-D", 0) == 0) {
            auto eq = a.find('=');
            if (eq == std::string::npos) pp.add_macro_definition(a.substr(2), "1");
            else pp.add_macro_definition(a.substr(2, eq - 2), a.substr(eq + 1));
        }
    }
    if (!pp.append_file(file)) { std::cerr << pp.errors(); return 1; }
    std::unique_ptr<codegen> cg(create_codegen_glsl(false, false));
    parser ps;
    if (!ps.parse(std::move(pp.output()), cg.get())) { std::cerr << pp.errors() << ps.errors(); return 1; }
    module m;
    cg->write_result(m);

    std::ofstream(out + ".glsl") << m.hlsl;
    std::ofstream j(out + ".json");
    j << "{\"total_uniform_size\":" << m.total_uniform_size << ",\n\"entry_points\":[";
    for (size_t i = 0; i < m.entry_points.size(); i++)
        j << (i ? "," : "") << "{\"name\":\"" << esc(m.entry_points[i].name) << "\",\"ps\":" << (m.entry_points[i].is_pixel_shader ? "true" : "false") << "}";
    j << "],\n\"textures\":[";
    for (size_t i = 0; i < m.textures.size(); i++) {
        const auto &t = m.textures[i];
        j << (i ? ",\n" : "") << "{\"name\":\"" << esc(t.unique_name) << "\",\"semantic\":\"" << esc(t.semantic) << "\",\"w\":" << t.width << ",\"h\":" << t.height
          << ",\"levels\":" << t.levels << ",\"format\":" << int(t.format) << ",\"ann\":" << ann_json(t.annotations) << "}";
    }
    j << "],\n\"samplers\":[";
    for (size_t i = 0; i < m.samplers.size(); i++) {
        const auto &s = m.samplers[i];
        j << (i ? ",\n" : "") << "{\"name\":\"" << esc(s.unique_name) << "\",\"binding\":" << s.binding << ",\"texture\":\"" << esc(s.texture_name)
          << "\",\"filter\":" << int(s.filter) << ",\"au\":" << int(s.address_u) << ",\"av\":" << int(s.address_v)
          << ",\"min_lod\":" << fin(s.min_lod) << ",\"max_lod\":" << (std::isfinite(s.max_lod)?s.max_lod:1000.0f) << ",\"lod_bias\":" << fin(s.lod_bias) << ",\"srgb\":" << int(s.srgb) << "}";
    }
    j << "],\n\"uniforms\":[";
    for (size_t i = 0; i < m.uniforms.size(); i++) {
        const auto &u = m.uniforms[i];
        j << (i ? ",\n" : "") << "{\"name\":\"" << esc(u.name) << "\",\"type\":" << type_json(u.type) << ",\"size\":" << u.size << ",\"offset\":" << u.offset
          << ",\"has_init\":" << (u.has_initializer_value ? "true" : "false") << ",\"init\":" << const_json(u.type, u.initializer_value) << ",\"ann\":" << ann_json(u.annotations) << "}";
    }
    j << "],\n\"techniques\":[";
    for (size_t i = 0; i < m.techniques.size(); i++) {
        const auto &t = m.techniques[i];
        j << (i ? ",\n" : "") << "{\"name\":\"" << esc(t.name) << "\",\"ann\":" << ann_json(t.annotations) << ",\"passes\":[";
        for (size_t k = 0; k < t.passes.size(); k++) {
            const auto &p = t.passes[k];
            j << (k ? "," : "") << "{\"vs\":\"" << esc(p.vs_entry_point) << "\",\"ps\":\"" << esc(p.ps_entry_point) << "\",\"rt\":[";
            for (int r = 0; r < 8; r++) j << (r ? "," : "") << "\"" << esc(p.render_target_names[r]) << "\"";
            j << "],\"clear\":" << int(p.clear_render_targets) << ",\"srgb\":" << int(p.srgb_write_enable) << ",\"blend\":" << int(p.blend_enable)
              << ",\"blend_op\":" << int(p.blend_op) << ",\"blend_op_a\":" << int(p.blend_op_alpha)
              << ",\"src\":" << int(p.src_blend) << ",\"dst\":" << int(p.dest_blend) << ",\"src_a\":" << int(p.src_blend_alpha) << ",\"dst_a\":" << int(p.dest_blend_alpha)
              << ",\"mask\":" << int(p.color_write_mask) << ",\"verts\":" << p.num_vertices << ",\"vw\":" << p.viewport_width << ",\"vh\":" << p.viewport_height
              << ",\"stencil\":" << int(p.stencil_enable) << "}";
        }
        j << "]}";
    }
    j << "]}\n";
    std::cerr << pp.errors() << ps.errors();
    return 0;
}
