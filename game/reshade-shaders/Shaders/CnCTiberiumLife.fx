// CnCTiberiumLife.fx  -  "Living Tiberium" for Tiberian War: WarZone (ReShade 4.5)
// Finds tiberium crystals by colour (green and blue), then:
//   - makes them richer without clipping to white,
//   - spills their light onto the ground around them,
//   - makes the glow breathe in slow waves that roll across each field,
//   - adds brief twinkling glints on the brightest crystals.
// Put it AFTER the colour grade and BEFORE "0_ UI After", so the sidebar stays untouched.
// Written for Shell's Warzone preset pack, 2026.

#include "ReShade.fxh"
#include "ReShadeUI.fxh"

uniform float Timer < source = "timer"; >;

uniform float TL_Strength < __UNIFORM_SLIDER_FLOAT1
    ui_min = 0.0; ui_max = 1.0; ui_label = "Overall strength";
    ui_tooltip = "0 = off, 1 = full effect."; > = 1.0;
uniform float TL_Richness < __UNIFORM_SLIDER_FLOAT1
    ui_min = 0.0; ui_max = 1.0; ui_label = "Crystal colour richness";
    ui_tooltip = "Deeper, more saturated crystals."; > = 0.35;
uniform float TL_Glow < __UNIFORM_SLIDER_FLOAT1
    ui_min = 0.0; ui_max = 2.0; ui_label = "Ground glow";
    ui_tooltip = "How much light the fields throw onto the ground around them."; > = 0.55;
uniform float TL_GlowSize < __UNIFORM_SLIDER_FLOAT1
    ui_min = 1.0; ui_max = 4.0; ui_label = "Ground glow size"; > = 2.0;
uniform float TL_Pulse < __UNIFORM_SLIDER_FLOAT1
    ui_min = 0.0; ui_max = 1.0; ui_label = "Breathing amount";
    ui_tooltip = "How strongly the glow swells and fades."; > = 0.35;
uniform float TL_PulseSpeed < __UNIFORM_SLIDER_FLOAT1
    ui_min = 0.05; ui_max = 2.0; ui_label = "Breathing speed"; > = 0.6;
uniform float TL_Glint < __UNIFORM_SLIDER_FLOAT1
    ui_min = 0.0; ui_max = 2.0; ui_label = "Glints";
    ui_tooltip = "Tiny sparkles that flicker on the brightest crystals."; > = 0.8;
uniform float TL_GlintRate < __UNIFORM_SLIDER_FLOAT1
    ui_min = 1.0; ui_max = 20.0; ui_label = "Glint speed"; > = 6.0;
uniform float TL_Blue < __UNIFORM_SLIDER_FLOAT1
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

float Luma(float3 c) { return dot(c, float3(0.2126, 0.7152, 0.0722)); }

// returns x = green weight, y = blue weight, z = crystal mask
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

    float lum = Luma(a);
    float3 o = a;

    // richer crystals
    float3 rich = lum + (a - lum) * (1.0 + TL_Richness);
    o = lerp(o, rich, k.z);

    // ground glow, breathing in slow waves across each field
    float4 g = tex2D(TL_GlowS, uv);
    float field = saturate(g.a * 3.0);
    float3 tint = g.rgb / (g.a + 1e-3);
    float t = Timer * 0.001;
    float phase = ValueNoise(pos.xy / 90.0) * 6.2832;
    float pulse = 1.0 + TL_Pulse * sin(t * TL_PulseSpeed * 1.5708 + phase);
    o += tint * field * TL_Glow * pulse * 0.5 * (1.0 - lum);

    // glints on the brightest crystals
    float cell = floor(t * TL_GlintRate);
    cell -= 997.0 * floor(cell / 997.0);
    float r = Hash(floor(pos.xy / 2.0), cell);
    float glint = step(0.992, r) * k.z * smoothstep(0.45, 0.8, RGBtoHSV(a).z) * TL_Glint;
    o += (tint * 0.6 + 0.4) * glint * 3.0;

    // soft shoulder so cores stay coloured instead of clipping to white
    const float knee = 0.85;
    float3 over = max(o - knee, 0.0);
    o = min(o, knee) + over / (1.0 + over / (1.0 - knee));

    return lerp(a, o, TL_Strength);
}

technique TiberiumLife < ui_label = "4_ Living Tiberium"; ui_tooltip = "Tiberium fields glow, breathe and glint. Put it after the colour grade and before UI After."; >
{
    pass Mask    { VertexShader = PostProcessVS; PixelShader = PS_Mask;  RenderTarget = TL_MaskTex; }
    pass BlurH   { VertexShader = PostProcessVS; PixelShader = PS_BlurH; RenderTarget = TL_BlurTex; }
    pass BlurV   { VertexShader = PostProcessVS; PixelShader = PS_BlurV; RenderTarget = TL_GlowTex; }
    pass Compose { VertexShader = PostProcessVS; PixelShader = PS_Composite; }
}
