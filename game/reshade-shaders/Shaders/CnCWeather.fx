// CnCWeather.fx  -  Weather for Tiberian War: WarZone (ReShade 4.5)
// Screen-space weather that sits on top of the game's own lighting:
//   - drifting cloud shadows (and sun patches) that stay locked to the ground while you scroll,
//   - low-lying mist,
//   - rain, heavy storm, snow, blizzard, tiberium rain or sandstorm,
//   - lightning flashes.
// The camera tracker compares each frame with the previous one to work out how far the map scrolled,
// so clouds and mist move with the terrain instead of sliding with the screen.
// Small lights, fire and explosions are protected from the cloud shade.
// Put it after the colour grade and BEFORE "0_ UI After", so the sidebar stays clean.
// Written for Shell's Warzone preset pack, 2026.

#include "ReShade.fxh"
#include "ReShadeUI.fxh"

uniform float Timer < source = "timer"; >;
uniform float FrameTime < source = "frametime"; >;

// ---------------------------------------------------------------- settings
uniform int WX_Type < ui_type = "combo"; ui_category = "Weather";
    ui_items = "Clear\0Rain\0Heavy storm\0Snow\0Blizzard\0Tiberium rain\0Sandstorm\0";
    ui_label = "Weather"; > = 0;
uniform float WX_Precip < __UNIFORM_SLIDER_FLOAT1 ui_category = "Weather";
    ui_min = 0.0; ui_max = 1.0; ui_label = "Rain / snow amount"; > = 0.5;
uniform float WX_Wind < __UNIFORM_SLIDER_FLOAT1 ui_category = "Weather";
    ui_min = -1.0; ui_max = 1.0; ui_label = "Wind"; ui_tooltip = "Slant of rain and snow, and cloud direction."; > = 0.25;
uniform float WX_Wet < __UNIFORM_SLIDER_FLOAT1 ui_category = "Weather";
    ui_min = 0.0; ui_max = 1.0; ui_label = "Wet ground look"; ui_tooltip = "Rain only: darker, richer ground."; > = 0.5;

uniform float WX_Clouds < __UNIFORM_SLIDER_FLOAT1 ui_category = "Clouds";
    ui_min = 0.0; ui_max = 1.0; ui_label = "Cloud shadows"; > = 0.35;
uniform float WX_CloudCover < __UNIFORM_SLIDER_FLOAT1 ui_category = "Clouds";
    ui_min = 0.0; ui_max = 1.0; ui_label = "Cloud cover"; ui_tooltip = "How much of the sky is cloud."; > = 0.45;
uniform float WX_CloudSize < __UNIFORM_SLIDER_FLOAT1 ui_category = "Clouds";
    ui_min = 0.3; ui_max = 3.0; ui_label = "Cloud size"; > = 1.0;
uniform float WX_CloudSpeed < __UNIFORM_SLIDER_FLOAT1 ui_category = "Clouds";
    ui_min = 0.0; ui_max = 3.0; ui_label = "Cloud speed"; > = 0.6;
uniform float WX_Sun < __UNIFORM_SLIDER_FLOAT1 ui_category = "Clouds";
    ui_min = 0.0; ui_max = 1.0; ui_label = "Sun patches"; ui_tooltip = "Warm light where the sun breaks through."; > = 0.25;
uniform float3 WX_SunColour < ui_type = "color"; ui_category = "Clouds"; ui_label = "Sun colour"; > = float3(1.0, 0.92, 0.75);

uniform float WX_Mist < __UNIFORM_SLIDER_FLOAT1 ui_category = "Mist";
    ui_min = 0.0; ui_max = 1.0; ui_label = "Mist"; > = 0.0;
uniform float3 WX_MistColour < ui_type = "color"; ui_category = "Mist"; ui_label = "Mist colour"; > = float3(0.62, 0.68, 0.74);

uniform float WX_Lightning < __UNIFORM_SLIDER_FLOAT1 ui_category = "Lightning";
    ui_min = 0.0; ui_max = 1.0; ui_label = "Lightning"; ui_tooltip = "How often and how bright."; > = 0.0;
uniform float3 WX_BoltColour < ui_type = "color"; ui_category = "Lightning"; ui_label = "Flash colour"; > = float3(0.75, 0.82, 1.0);

uniform bool WX_TrackCamera < ui_category = "Advanced"; ui_label = "Lock clouds to the ground";
    ui_tooltip = "Follows map scrolling so clouds and mist stay on the terrain."; > = true;
uniform int WX_Debug < ui_type = "combo"; ui_category = "Advanced";
    ui_items = "Off\0Show cloud map\0Show camera tracking\0"; ui_label = "Debug view"; > = 0;

// ---------------------------------------------------------------- camera tracker
#define WX_LW 200
#define WX_LH 150
#define WX_R 12
texture WX_CurTex  { Width = WX_LW; Height = WX_LH; Format = R8; };
texture WX_PrevTex { Width = WX_LW; Height = WX_LH; Format = R8; };
texture WX_CostTex { Width = 2 * WX_R + 1; Height = 2 * WX_R + 1; Format = R32F; };
texture WX_PosTex  { Format = RG32F; };
texture WX_PosPrevTex { Format = RG32F; };
sampler WX_Cur  { Texture = WX_CurTex;  MinFilter = POINT; MagFilter = POINT; };
sampler WX_Prev { Texture = WX_PrevTex; MinFilter = POINT; MagFilter = POINT; };
sampler WX_Cost { Texture = WX_CostTex; MinFilter = POINT; MagFilter = POINT; };
sampler WX_CurLin { Texture = WX_CurTex; };
sampler WX_Pos  { Texture = WX_PosTex;  MinFilter = POINT; MagFilter = POINT; };
sampler WX_PosPrev { Texture = WX_PosPrevTex; MinFilter = POINT; MagFilter = POINT; };

float Luma(float3 c) { return dot(c, float3(0.2126, 0.7152, 0.0722)); }

float PlayX() { return 1.0 - 168.0 * BUFFER_RCP_WIDTH; }   // right edge of the battlefield (sidebar is 168 px)
float PlayY() { return 22.0 * BUFFER_RCP_HEIGHT; }         // top strip

void PS_Down(float4 p : SV_Position, float2 uv : TEXCOORD, out float o : SV_Target)
{
    float2 d = BUFFER_PIXEL_SIZE;   // 4 bilinear taps = a 4x4 pixel average
    o = 0.25 * (Luma(tex2D(ReShade::BackBuffer, uv + float2(-d.x, -d.y)).rgb) + Luma(tex2D(ReShade::BackBuffer, uv + float2(d.x, -d.y)).rgb)
              + Luma(tex2D(ReShade::BackBuffer, uv + float2(-d.x,  d.y)).rgb) + Luma(tex2D(ReShade::BackBuffer, uv + float2(d.x,  d.y)).rgb));
}

void PS_Cost(float4 p : SV_Position, float2 uv : TEXCOORD, out float o : SV_Target)
{
    float2 off = floor(p.xy) - WX_R;               // candidate shift in low-res texels
    float2 lp = float2(1.0 / WX_LW, 1.0 / WX_LH);
    float sum = 0.0;
    for (int y = 0; y < 24; y++)
    for (int x = 0; x < 32; x++)
    {
        float2 q = float2(0.06 + 0.66 * (x + 0.5) / 32.0, 0.10 + 0.80 * (y + 0.5) / 24.0);
        q.x *= PlayX() / 0.79;
        sum += abs(tex2Dlod(WX_Cur, float4(q, 0, 0)).r - tex2Dlod(WX_Prev, float4(q + off * lp, 0, 0)).r);
    }
    o = sum / 768.0;
}

void PS_Track(float4 p : SV_Position, float2 uv : TEXCOORD, out float2 o : SV_Target)
{
    float best = 1e9; float2 bo = 0;
    for (int y = 0; y <= 2 * WX_R; y++)
    for (int x = 0; x <= 2 * WX_R; x++)
    {
        float c = tex2Dfetch(WX_Cost, int4(x, y, 0, 0)).r;
        if (c < best) { best = c; bo = float2(x, y) - WX_R; }
    }
    float zero = tex2Dfetch(WX_Cost, int4(WX_R, WX_R, 0, 0)).r;
    // only accept a shift that is clearly better than "no movement"
    if (!(best < zero * 0.8)) bo = 0;
    float2 prev = tex2Dfetch(WX_PosPrev, int4(0, 0, 0, 0)).rg;
    o = prev + bo * float2(BUFFER_WIDTH / (float)WX_LW, BUFFER_HEIGHT / (float)WX_LH);
    // keep numbers small so float precision stays good
    o -= floor(o / 8192.0) * 8192.0;
}

void PS_CopyPos(float4 p : SV_Position, float2 uv : TEXCOORD, out float2 o : SV_Target) { o = tex2Dfetch(WX_Pos, int4(0, 0, 0, 0)).rg; }
void PS_CopyCur(float4 p : SV_Position, float2 uv : TEXCOORD, out float o : SV_Target) { o = tex2D(WX_Cur, uv).r; }

// ---------------------------------------------------------------- noise
float Hash(float2 p) { return frac(sin(dot(p, float2(12.9898, 78.233))) * 43758.5453); }
float Hash3(float2 p, float s) { return frac(sin(dot(p, float2(12.9898, 78.233)) + s * 37.719) * 43758.5453); }

float VNoise(float2 p)
{
    float2 i = floor(p); float2 f = frac(p); f = f * f * (3.0 - 2.0 * f);
    return lerp(lerp(Hash(i), Hash(i + float2(1, 0)), f.x), lerp(Hash(i + float2(0, 1)), Hash(i + float2(1, 1)), f.x), f.y);
}

float FBM(float2 p)
{
    float v = 0.0, a = 0.5;
    for (int i = 0; i < 5; i++) { v += a * VNoise(p); p = p * 2.03 + float2(17.1, 9.7); a *= 0.5; }
    return v;
}

// ---------------------------------------------------------------- precipitation
// streaks falling along the wind; returns brightness 0..1
float Rain(float2 px, float t, float density, float speed, float len, float seed)
{
    float slant = WX_Wind * 0.45;
    float2 q = float2(px.x - px.y * slant, px.y);
    const float cw = 5.0;
    float col = floor(q.x / cw);
    float colSpeed = speed * (0.8 + 0.4 * Hash3(float2(col, 0), seed));
    float y = q.y - t * colSpeed + Hash3(float2(col, 1), seed) * 1000.0;
    float cell = floor(y / len);
    float fy = frac(y / len);
    float exists = step(Hash3(float2(col, cell), seed + 2.0), density);
    float xin = frac(q.x / cw) * cw - (1.0 + 3.0 * Hash3(float2(col, cell), seed + 3.0));
    float streak = saturate(1.0 - abs(xin) * 1.6) * smoothstep(0.0, 0.35, fy) * smoothstep(0.7, 0.45, fy);
    return exists * streak;
}

float Snow(float2 px, float t, float density, float size, float seed, float fall)
{
    const float cs = 22.0;
    float2 q = px + float2(-WX_Wind * t * 30.0, -t * fall);
    float2 cell = floor(q / cs);
    float h = Hash3(cell, seed);
    if (h > density) return 0.0;
    float2 c = cell * cs + 3.0 + float2(Hash3(cell, seed + 1.0), Hash3(cell, seed + 2.0)) * (cs - 6.0);
    c.x += sin(t * (0.8 + h * 1.5) + h * 6.28) * 3.0;
    float d = length(q - c);
    return saturate(1.0 - d / size);
}

// ---------------------------------------------------------------- main
float3 PS_Weather(float4 pos : SV_Position, float2 uv : TEXCOORD) : SV_Target
{
    float3 a = tex2D(ReShade::BackBuffer, uv).rgb;
    float t = Timer * 0.001;
    float2 cam = WX_TrackCamera ? tex2Dfetch(WX_Pos, int4(0, 0, 0, 0)).rg : 0;
    float2 world = pos.xy + cam;

    if (WX_Debug == 2)
    {
        float2 g = frac(world / 64.0);
        float line = step(g.x, 0.03) + step(g.y, 0.03);
        return lerp(a * 0.6, float3(1, 0.2, 0.8), saturate(line));
    }

    float lum = Luma(a);
    // protect self-lit things (fire, lamps, explosions, glowing tiberium cores)
    // = very bright, or clearly brighter than its surroundings (wide bright sand does not count)
    float around = tex2D(WX_CurLin, uv).r;
    float selfLit = max(smoothstep(0.8, 0.95, lum),
                        smoothstep(0.65, 0.9, max(a.r, max(a.g, a.b))) * smoothstep(0.06, 0.2, lum - around));
    float3 o = a;

    // clouds: slow fbm drifting with the wind, locked to the ground
    float2 wind = normalize(float2(1.0, 0.35 + WX_Wind * 0.3)) * sign(WX_Wind + 1e-3);
    float2 cp = (world / (260.0 * WX_CloudSize)) + wind * t * 0.015 * WX_CloudSpeed;
    float n = FBM(cp);
    float cover = 1.0 - WX_CloudCover;
    float cloud = smoothstep(cover - 0.12, cover + 0.12, n);
    float sun = (1.0 - smoothstep(cover - 0.25, cover, n)) * WX_Sun;
    if (WX_Debug == 1) return float3(cloud, sun, 0.0);

    float shade = 1.0 - WX_Clouds * 0.55 * cloud;
    o *= lerp(shade, 1.0, selfLit);
    o += o * WX_SunColour * sun * 0.35 * (1.0 - selfLit);

    // mist: low drifting banks, thicker in the dark, never over lights
    if (WX_Mist > 0.0)
    {
        float m = FBM(world / 180.0 + float2(t * 0.02, t * 0.007) + 31.0);
        m = smoothstep(0.35, 0.8, m) * WX_Mist;
        o = lerp(o, WX_MistColour * (0.5 + 0.5 * lum), m * 0.6 * (1.0 - selfLit));
    }

    // precipitation
    float2 sp = pos.xy;
    float3 pcol = 0; float p = 0;
    if (WX_Type == 1 || WX_Type == 2 || WX_Type == 5)
    {
        float heavy = WX_Type == 2 ? 1.0 : 0.0;
        float dens = WX_Precip * (0.35 + 0.4 * heavy);
        p  = Rain(sp, t, dens, 900.0, 34.0, 1.0) * 0.55;
        p += Rain(sp * 1.3 + 50.0, t, dens * 0.8, 700.0, 24.0, 2.0) * 0.35;
        p += Rain(sp * 1.8 + 90.0, t, dens * 0.6, 520.0, 16.0, 3.0) * 0.22;
        pcol = WX_Type == 5 ? float3(0.55, 1.0, 0.6) : float3(0.78, 0.84, 0.92);
        // wet ground: darker, richer, more contrast
        float wet = WX_Wet * WX_Precip * (1.0 - selfLit);
        float l2 = Luma(o);
        o = lerp(o, (l2 + (o - l2) * 1.25) * 0.82, wet * 0.6);
        if (WX_Type == 5) o += float3(0.0, 0.03, 0.01) * WX_Precip;
    }
    else if (WX_Type == 3 || WX_Type == 4)
    {
        float bl = WX_Type == 4 ? 1.0 : 0.0;
        float dens = WX_Precip * (0.45 + 0.4 * bl);
        p  = Snow(sp, t, dens, 2.4, 1.0, 38.0 + 60.0 * bl);
        p += Snow(sp * 1.4 + 33.0, t, dens, 1.8, 2.0, 30.0 + 50.0 * bl) * 0.75;
        p += Snow(sp * 2.1 + 71.0, t, dens, 1.1, 3.0, 22.0 + 40.0 * bl) * 0.45;
        pcol = float3(0.95, 0.97, 1.0);
        if (bl > 0.0) o = lerp(o, float3(0.82, 0.86, 0.9), 0.18 * WX_Precip * (1.0 - selfLit));
    }
    else if (WX_Type == 6)
    {
        float dens = WX_Precip * 0.5;
        p = Rain(float2(sp.y, sp.x), t, dens, 1100.0, 40.0, 5.0) * 0.25;
        float dust = FBM(world / 120.0 + float2(t * 0.25, t * 0.05) * (1.0 + WX_Wind));
        o = lerp(o, float3(0.78, 0.58, 0.36) * (0.6 + 0.4 * lum), smoothstep(0.3, 0.8, dust) * 0.45 * WX_Precip * (1.0 - selfLit));
        pcol = float3(0.9, 0.72, 0.48);
    }
    o = lerp(o, pcol, saturate(p));

    // lightning: a random strike roughly every 4-20 s (more often when stronger), double flicker
    if (WX_Lightning > 0.0)
    {
        float slot = floor(t / 1.7);
        float fire = step(1.0 - WX_Lightning * 0.35, Hash3(float2(slot, 7.0), 3.0));
        float lt = t - slot * 1.7 - Hash3(float2(slot, 8.0), 3.0) * 0.8;
        float f = 0.0;
        if (lt > 0.0)
        {
            f  = exp(-lt * 18.0);
            f += 0.7 * exp(-max(lt - 0.12, 0.0) * 14.0) * step(0.12, lt);
        }
        f *= fire * (0.5 + 0.5 * Hash3(float2(slot, 9.0), 3.0)) * WX_Lightning;
        float3 bolt = WX_Type == 5 ? float3(0.6, 1.0, 0.65) : WX_BoltColour;
        o += bolt * f * (0.35 + 0.65 * (1.0 - cloud * 0.5)) * (0.4 + lum);
    }

    // keep the sidebar and top strip exactly as they were
    float inPlay = step(uv.x, PlayX()) * step(PlayY(), uv.y);
    return lerp(a, saturate(o), inPlay);
}

technique CnCWeather < ui_label = "5_ Weather (clouds, rain, snow, lightning)";
    ui_tooltip = "Cloud shadows locked to the ground, mist, rain, snow, storms and lightning. Put it after the colour grade and before UI After."; >
{
    pass Down    { VertexShader = PostProcessVS; PixelShader = PS_Down;  RenderTarget = WX_CurTex; }
    pass Cost    { VertexShader = PostProcessVS; PixelShader = PS_Cost;  RenderTarget = WX_CostTex; }
    pass Track   { VertexShader = PostProcessVS; PixelShader = PS_Track; RenderTarget = WX_PosTex; }
    pass SavePos { VertexShader = PostProcessVS; PixelShader = PS_CopyPos; RenderTarget = WX_PosPrevTex; }
    pass SaveCur { VertexShader = PostProcessVS; PixelShader = PS_CopyCur; RenderTarget = WX_PrevTex; }
    pass Weather { VertexShader = PostProcessVS; PixelShader = PS_Weather; }
}
