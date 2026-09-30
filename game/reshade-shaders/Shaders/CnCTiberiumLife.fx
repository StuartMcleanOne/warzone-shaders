// CnCTiberiumLife.fx  -  "Living Tiberium" v3 for Tiberian War: WarZone (ReShade 4.5)
// Finds tiberium crystals by colour (green and blue), then:
//   - Breathing: the crystals themselves slowly brighten and settle, in waves across each field
//     (no glow needed for it to show),
//   - Glints: single crystals catch the light and fade in and out on their own slow rhythm.
//     Green crystals glint in greens through to white, blue crystals in blues through to white.
//   - Richness and Ground glow are optional extras. Ground glow is off by default and its slider
//     is scaled so the whole range is usable (v1's useful range was the bottom 5%).
// Put it AFTER the colour grade and BEFORE "0_ UI After", so the sidebar stays untouched.
// Written for Shell's Warzone preset pack, 2026.

#include "ReShade.fxh"
#include "ReShadeUI.fxh"

uniform float Timer < source = "timer"; >;

uniform float TL_Strength < __UNIFORM_SLIDER_FLOAT1
    ui_min = 0.0; ui_max = 1.0; ui_label = "Overall strength";
    ui_tooltip = "0 = off, 1 = full effect."; > = 1.0;

uniform float TL_Breath < __UNIFORM_SLIDER_FLOAT1 ui_category = "Breathing";
    ui_min = 0.0; ui_max = 1.0; ui_label = "Breathing amount";
    ui_tooltip = "How much the crystals brighten and settle. Works on the crystals themselves."; > = 0.5;
uniform float TL_BreathSpeed < __UNIFORM_SLIDER_FLOAT1 ui_category = "Breathing";
    ui_min = 0.0; ui_max = 1.0; ui_label = "Breathing speed";
    ui_tooltip = "0 = one breath a minute, 1 = one every 2 seconds."; > = 0.3;
uniform float TL_WaveSize < __UNIFORM_SLIDER_FLOAT1 ui_category = "Breathing";
    ui_min = 0.0; ui_max = 1.0; ui_label = "Wave size";
    ui_tooltip = "0 = the whole field breathes together, 1 = small patches breathe on their own."; > = 0.5;

uniform float TL_Glints < __UNIFORM_SLIDER_FLOAT1 ui_category = "Glints";
    ui_min = 0.0; ui_max = 1.0; ui_label = "Glint brightness"; > = 0.5;
uniform float TL_GlintAmount < __UNIFORM_SLIDER_FLOAT1 ui_category = "Glints";
    ui_min = 0.0; ui_max = 1.0; ui_label = "How many glints";
    ui_tooltip = "How many crystals carry a glint. They never all light at once."; > = 0.35;
uniform float TL_GlintFade < __UNIFORM_SLIDER_FLOAT1 ui_category = "Glints";
    ui_min = 0.0; ui_max = 1.0; ui_label = "Fade time";
    ui_tooltip = "0 = quick sparkle (about 1 second), 1 = very slow swell (about 8 seconds)."; > = 0.5;
uniform float TL_GlintWhite < __UNIFORM_SLIDER_FLOAT1 ui_category = "Glints";
    ui_min = 0.0; ui_max = 1.0; ui_label = "Colour to white";
    ui_tooltip = "0 = glints stay in the crystal's own colour family, 1 = mostly white."; > = 0.4;
uniform float TL_GlintHue < __UNIFORM_SLIDER_FLOAT1 ui_category = "Glints";
    ui_min = 0.0; ui_max = 1.0; ui_label = "Colour spread";
    ui_tooltip = "How far the shades wander inside the family (lime to emerald, sky to deep blue)."; > = 0.5;

uniform float TL_Richness < __UNIFORM_SLIDER_FLOAT1 ui_category = "Extras";
    ui_min = 0.0; ui_max = 1.0; ui_label = "Crystal colour richness"; > = 0.1;
uniform float TL_Glow < __UNIFORM_SLIDER_FLOAT1 ui_category = "Extras";
    ui_min = 0.0; ui_max = 1.0; ui_label = "Ground glow";
    ui_tooltip = "Light spilling onto the ground. Off by default; 0.3 is subtle, 1 is strong."; > = 0.0;
uniform float TL_GlowSize < __UNIFORM_SLIDER_FLOAT1 ui_category = "Extras";
    ui_min = 1.0; ui_max = 4.0; ui_label = "Ground glow size"; > = 1.5;
uniform float TL_Blue < __UNIFORM_SLIDER_FLOAT1 ui_category = "Extras";
    ui_min = 0.0; ui_max = 1.0; ui_label = "Blue tiberium";
    ui_tooltip = "0 = only green fields come alive, 1 = blue ones too."; > = 1.0;
uniform int TL_Debug < ui_type = "combo"; ui_items = "Off\0Show crystal mask\0";
    ui_label = "Debug view"; > = 0;

texture TL_MaskTex { Width = BUFFER_WIDTH / 2; Height = BUFFER_HEIGHT / 2; Format = RGBA8; };
texture TL_BlurTex { Width = BUFFER_WIDTH / 2; Height = BUFFER_HEIGHT / 2; Format = RGBA8; };
texture TL_GlowTex { Width = BUFFER_WIDTH / 2; Height = BUFFER_HEIGHT / 2; Format = RGBA8; };
sampler TL_Mask { Texture = TL_MaskTex; };
sampler TL_Blur { Texture = TL_BlurTex; };
sampler TL_GlowS { Texture = TL_GlowTex; };

float3 RGBtoHSV(float3 c)
{
    float mx = max(c.r, max(c.g, c.b));
    float mn = min(c.r, min(c.g, c.b));
    float d = mx - mn + 1e-6;
    float h;
    if (mx == c.r)      h = (c.g - c.b) / d;
    else if (mx == c.g) h = (c.b - c.r) / d + 2.0;
    else                h = (c.r - c.g) / d + 4.0;
    h = frac(h / 6.0 + 1.0);
    return float3(h, (mx - mn) / (mx + 1e-6), mx);
}

float3 HSVtoRGB(float h, float s, float v)
{
    float3 k = frac(h + float3(1.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0;
    return v * lerp(1.0, saturate(abs(k) - 1.0), s);
}

float Luma(float3 c) { return dot(c, float3(0.2126, 0.7152, 0.0722)); }

// x = green weight, y = blue weight, z = crystal mask
float3 Crystal(float2 uv)
{
    float3 c = tex2D(ReShade::BackBuffer, uv).rgb;
    float3 hsv = RGBtoHSV(c);
    float green = smoothstep(0.02, 0.06, 0.12 - abs(hsv.x - 0.36));
    float blue  = smoothstep(0.02, 0.06, 0.10 - abs(hsv.x - 0.63)) * TL_Blue;
    float2 px = BUFFER_PIXEL_SIZE * 2.0;
    float around = 0.0;
    around += Luma(tex2D(ReShade::BackBuffer, uv + float2( px.x, 0)).rgb);
    around += Luma(tex2D(ReShade::BackBuffer, uv + float2(-px.x, 0)).rgb);
    around += Luma(tex2D(ReShade::BackBuffer, uv + float2(0,  px.y)).rgb);
    around += Luma(tex2D(ReShade::BackBuffer, uv + float2(0, -px.y)).rgb);
    float local = Luma(c) - around * 0.25;
    float m = max(green, blue) * smoothstep(0.25, 0.5, hsv.y) * smoothstep(0.28, 0.5, hsv.z)
            * smoothstep(0.0, 0.06, local + 0.03);
    return float3(green, blue, m);
}

float Hash(float2 p, float t)
{
    return frac(sin(dot(p, float2(12.9898, 78.233)) + t * 37.719) * 43758.5453);
}

float ValueNoise(float2 p)
{
    float2 i = floor(p); float2 f = frac(p); f = f * f * (3.0 - 2.0 * f);
    float a = Hash(i, 0.0), b = Hash(i + float2(1, 0), 0.0);
    float c = Hash(i + float2(0, 1), 0.0), d = Hash(i + float2(1, 1), 0.0);
    return lerp(lerp(a, b, f.x), lerp(c, d, f.x), f.y);
}

void PS_Mask(float4 pos : SV_Position, float2 uv : TEXCOORD, out float4 o : SV_Target)
{
    float3 k = Crystal(uv);
    float3 base = float3(0.20, 1.0, 0.35) * k.x + float3(0.35, 0.55, 1.0) * k.y;
    o = float4(base * k.z, k.z);
}

float4 Blur(sampler s, float2 uv, float2 dir)
{
    const float w[5] = { 0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216 };
    float2 st = dir * BUFFER_PIXEL_SIZE * 2.0 * TL_GlowSize;
    float4 acc = tex2D(s, uv) * w[0];
    for (int i = 1; i < 5; i++)
    {
        acc += tex2D(s, uv + st * i) * w[i];
        acc += tex2D(s, uv - st * i) * w[i];
    }
    return acc;
}

void PS_BlurH(float4 pos : SV_Position, float2 uv : TEXCOORD, out float4 o : SV_Target) { o = Blur(TL_Mask, uv, float2(1, 0)); }
void PS_BlurV(float4 pos : SV_Position, float2 uv : TEXCOORD, out float4 o : SV_Target) { o = Blur(TL_Blur, uv, float2(0, 1)); }

float3 PS_Composite(float4 pos : SV_Position, float2 uv : TEXCOORD) : SV_Target
{
    float3 a = tex2D(ReShade::BackBuffer, uv).rgb;
    float3 k = Crystal(uv);
    if (TL_Debug == 1)
        return lerp(a * 0.25, float3(0.2, 1.0, 0.4) * k.x + float3(0.3, 0.5, 1.0) * k.y + 0.3, k.z);
    if (k.z <= 0.0 && TL_Glow <= 0.0)
        return a;

    float t = Timer * 0.001;
    float lum = Luma(a);
    float3 o = a;

    // richer crystals
    o = lerp(o, lum + (a - lum) * (1.0 + TL_Richness), k.z);

    // breathing on the crystals themselves: slow waves rolling across the field
    float period = lerp(60.0, 2.0, TL_BreathSpeed);                 // seconds per breath
    float scale = lerp(400.0, 60.0, TL_WaveSize);                    // wave size in pixels
    float phase = ValueNoise(pos.xy / scale) * 6.2832;
    float breath = sin(t * 6.2832 / period + phase);                 // -1 .. 1
    o *= 1.0 + k.z * TL_Breath * 0.22 * breath;

    // optional ground glow (scaled: slider 0..1 covers the old useful range 0..0.2), breathes too
    if (TL_Glow > 0.0)
    {
        float4 g = tex2D(TL_GlowS, uv);
        float3 tint = g.rgb / (g.a + 1e-3);
        float field = saturate(g.a * 3.0);
        o += tint * field * (0.2 * TL_Glow * TL_Glow) * 0.5 * (1.0 - lum) * (1.0 + 0.5 * TL_Breath * breath);
    }

    // glints: one possible glint per 6x6 cell, each with its own slow fade in and out
    const float C = 6.0;
    float2 cell = floor(pos.xy / C);
    float h1 = Hash(cell, 1.0);
    if (k.z > 0.0 && h1 < TL_GlintAmount * 0.5)
    {
        float h2 = Hash(cell, 2.0), h3 = Hash(cell, 3.0), h4 = Hash(cell, 4.0);
        float h5 = Hash(cell, 5.0), h6 = Hash(cell, 6.0), h7 = Hash(cell, 7.0);
        float2 centre = cell * C + 1.5 + float2(h5, h6) * (C - 3.0);
        float2 d = pos.xy - centre;
        float fade = lerp(1.0, 8.0, TL_GlintFade) * (0.7 + 0.6 * h2);  // seconds for one glint
        float rest = fade * (1.5 + 3.0 * h3);                           // dark time between glints
        float cyc = frac((t + h4 * 97.0) / (fade + rest)) * (fade + rest);
        float env = cyc < fade ? sin(3.14159 * cyc / fade) : 0.0;       // smooth rise and fall
        env *= env;
        float peak = 0.3 + 0.7 * h7 * h7;                               // some bright, some faint
        float shape = exp(-dot(d, d) / 2.2);
        float L = env * peak * shape * k.z * TL_Glints;

        // colour: inside the crystal's own family, some shades close to white
        bool isGreen = k.x >= k.y;
        float hue = isGreen ? lerp(0.25, 0.42, frac(h2 * 7.13)) : lerp(0.53, 0.69, frac(h2 * 7.13));
        float baseHue = isGreen ? 0.36 : 0.62;
        hue = lerp(baseHue, hue, TL_GlintHue);
        float sat = lerp(0.85, 0.05, saturate(TL_GlintWhite * (0.4 + 1.2 * frac(h3 * 5.7))));
        float3 col = HSVtoRGB(hue, sat, 1.0);
        o += col * L * 1.4;
    }

    // soft shoulder so cores stay coloured instead of clipping to white
    const float knee = 0.85;
    float3 over = max(o - knee, 0.0);
    o = min(o, knee) + over / (1.0 + over / (1.0 - knee));

    return lerp(a, o, TL_Strength);
}

technique TiberiumLife < ui_label = "4_ Living Tiberium"; ui_tooltip = "Tiberium crystals breathe and glint. Put it after the colour grade and before UI After."; >
{
    pass Mask    { VertexShader = PostProcessVS; PixelShader = PS_Mask;  RenderTarget = TL_MaskTex; }
    pass BlurH   { VertexShader = PostProcessVS; PixelShader = PS_BlurH; RenderTarget = TL_BlurTex; }
    pass BlurV   { VertexShader = PostProcessVS; PixelShader = PS_BlurV; RenderTarget = TL_GlowTex; }
    pass Compose { VertexShader = PostProcessVS; PixelShader = PS_Composite; }
}
