// CnCBlast.fx  -  Explosions light the battlefield. For Tiberian War: WarZone (ReShade 4.5)
// The game draws explosions as flat sprites: the ground around them never lights up.
// This shader notices when something suddenly flares up (it compares each frame with the last),
// then:
//   - throws a short burst of hot light onto the ground and units around the blast, fading out,
//   - makes the air shimmer with heat above explosions and burning fires,
//   - optionally gives a quick kick of brightness to the whole field on big blasts.
// Lamps and fire that were already there do not retrigger, only new flashes do.
// Put it after the colour grade and BEFORE "0_ UI After".
// Written for Shell's Warzone preset pack, 2026.

#include "ReShade.fxh"
#include "ReShadeUI.fxh"

uniform float Timer < source = "timer"; >;
uniform float FrameTime < source = "frametime"; >;

uniform float BL_Light < __UNIFORM_SLIDER_FLOAT1 ui_category = "Blast light";
    ui_min = 0.0; ui_max = 3.0; ui_label = "Blast light";
    ui_tooltip = "How strongly a new explosion lights up the ground around it."; > = 1.2;
uniform float BL_Reach < __UNIFORM_SLIDER_FLOAT1 ui_category = "Blast light";
    ui_min = 0.5; ui_max = 3.0; ui_label = "Light reach"; > = 1.4;
uniform float BL_Fade < __UNIFORM_SLIDER_FLOAT1 ui_category = "Blast light";
    ui_min = 0.1; ui_max = 2.0; ui_label = "Fade time (seconds)"; > = 0.6;
uniform float3 BL_Colour < ui_type = "color"; ui_category = "Blast light"; ui_label = "Light colour"; > = float3(1.0, 0.62, 0.28);
uniform float BL_Sensitivity < __UNIFORM_SLIDER_FLOAT1 ui_category = "Blast light";
    ui_min = 0.0; ui_max = 1.0; ui_label = "Sensitivity";
    ui_tooltip = "Higher = smaller flashes (gunfire, sparks) also light things up."; > = 0.5;
uniform float BL_Kick < __UNIFORM_SLIDER_FLOAT1 ui_category = "Blast light";
    ui_min = 0.0; ui_max = 1.0; ui_label = "Big blast screen kick"; > = 0.2;

uniform float BL_FireGlow < __UNIFORM_SLIDER_FLOAT1 ui_category = "Blast light";
    ui_min = 0.0; ui_max = 2.0; ui_label = "Burning fire glow";
    ui_tooltip = "Fires that keep burning cast a flickering light on the ground around them."; > = 0.4;

uniform float BL_Heat < __UNIFORM_SLIDER_FLOAT1 ui_category = "Heat shimmer";
    ui_min = 0.0; ui_max = 2.0; ui_label = "Heat shimmer"; > = 0.8;
uniform float BL_FireHeat < __UNIFORM_SLIDER_FLOAT1 ui_category = "Heat shimmer";
    ui_min = 0.0; ui_max = 1.0; ui_label = "Shimmer over burning fires";
    ui_tooltip = "Also shimmer above fires that keep burning, not only new blasts."; > = 0.5;

uniform int BL_Debug < ui_type = "combo"; ui_items = "Off\0Show blast energy\0"; ui_label = "Debug view"; > = 0;

#define BL_W (BUFFER_WIDTH / 2)
#define BL_H (BUFFER_HEIGHT / 2)
texture BL_CurTex   { Width = BL_W; Height = BL_H; Format = RGBA8; };
texture BL_PrevTex  { Width = BL_W; Height = BL_H; Format = RGBA8; };
texture BL_ETex     { Width = BL_W; Height = BL_H; Format = R16F; };
texture BL_EPrevTex { Width = BL_W; Height = BL_H; Format = R16F; };
texture BL_B1Tex    { Width = BL_W / 2; Height = BL_H / 2; Format = RGBA16F; };
texture BL_B2Tex    { Width = BL_W / 2; Height = BL_H / 2; Format = RGBA16F; };
texture BL_KickTex  { Format = R16F; };
sampler BL_Cur   { Texture = BL_CurTex; };
sampler BL_Prev  { Texture = BL_PrevTex; };
sampler BL_E     { Texture = BL_ETex; };
sampler BL_EPrev { Texture = BL_EPrevTex; };
sampler BL_B1    { Texture = BL_B1Tex; };
sampler BL_B2    { Texture = BL_B2Tex; };
sampler BL_KickS { Texture = BL_KickTex; };

float Luma(float3 c) { return dot(c, float3(0.2126, 0.7152, 0.0722)); }
float InPlay(float2 uv) { return step(uv.x, 1.0 - 168.0 * BUFFER_RCP_WIDTH) * step(22.0 * BUFFER_RCP_HEIGHT, uv.y); }

float Hash(float2 p) { return frac(sin(dot(p, float2(12.9898, 78.233))) * 43758.5453); }
float VNoise(float2 p)
{
    float2 i = floor(p); float2 f = frac(p); f = f * f * (3.0 - 2.0 * f);
    return lerp(lerp(Hash(i), Hash(i + float2(1, 0)), f.x), lerp(Hash(i + float2(0, 1)), Hash(i + float2(1, 1)), f.x), f.y);
}

// "hot": bright, and white or fire-coloured (red >= green >= blue)
float Hot(float3 c)
{
    float mx = max(c.r, max(c.g, c.b));
    float warm = step(c.b, c.g + 0.08) * step(c.g, c.r + 0.08);
    float white = step(0.85, min(c.r, min(c.g, c.b)));
    return smoothstep(0.72 - 0.12 * BL_Sensitivity, 0.95, mx) * max(warm, white);
}

void PS_Down(float4 p : SV_Position, float2 uv : TEXCOORD, out float4 o : SV_Target)
{
    o = float4(tex2D(ReShade::BackBuffer, uv).rgb, 1.0);
}

void PS_Energy(float4 p : SV_Position, float2 uv : TEXCOORD, out float o : SV_Target)
{
    float3 c = tex2D(BL_Cur, uv).rgb;
    float2 px = 1.0 / float2(BL_W, BL_H);
    // brightest the neighbourhood was last frame (tolerates small movement)
    float prevMax = 0.0;
    for (int y = -2; y <= 2; y++)
    for (int x = -2; x <= 2; x++)
        prevMax = max(prevMax, Luma(tex2D(BL_Prev, uv + float2(x, y) * px).rgb));
    float jump = smoothstep(0.18 - 0.1 * BL_Sensitivity, 0.45, Luma(c) - prevMax);
    float trig = Hot(c) * jump * InPlay(uv);
    float dt = clamp(FrameTime * 0.001, 0.0, 0.1);
    float e = tex2D(BL_EPrev, uv).r * exp(-dt * 3.0 / BL_Fade);
    o = max(e, trig);
}

void PS_CopyE(float4 p : SV_Position, float2 uv : TEXCOORD, out float o : SV_Target)  { o = tex2D(BL_E, uv).r; }
void PS_CopyCur(float4 p : SV_Position, float2 uv : TEXCOORD, out float4 o : SV_Target) { o = tex2D(BL_Cur, uv); }

// r = blast energy, g = burning fire (for shimmer)
float4 Src(float2 uv)
{
    float3 c = tex2D(BL_Cur, uv).rgb;
    return float4(tex2D(BL_E, uv).r, Hot(c) * InPlay(uv), 0, 0);
}

float4 Blur(sampler s, float2 uv, float2 dir, bool first)
{
    const float w[6] = { 0.19, 0.17, 0.14, 0.1, 0.07, 0.04 };
    float2 st = dir * BL_Reach * 4.0 / float2(BL_W, BL_H);
    float4 acc = (first ? Src(uv) : tex2D(s, uv)) * w[0];
    for (int i = 1; i < 6; i++)
    {
        acc += (first ? Src(uv + st * i) : tex2D(s, uv + st * i)) * w[i];
        acc += (first ? Src(uv - st * i) : tex2D(s, uv - st * i)) * w[i];
    }
    return acc;
}
void PS_BlurH(float4 p : SV_Position, float2 uv : TEXCOORD, out float4 o : SV_Target) { o = Blur(BL_B2, uv, float2(1, 0), true); }
void PS_BlurV(float4 p : SV_Position, float2 uv : TEXCOORD, out float4 o : SV_Target) { o = Blur(BL_B1, uv, float2(0, 1), false); }

void PS_Kick(float4 p : SV_Position, float2 uv : TEXCOORD, out float o : SV_Target)
{
    // average blast energy over the field, sampled on a coarse grid
    float s = 0.0;
    for (int y = 0; y < 12; y++)
    for (int x = 0; x < 16; x++)
        s += tex2Dlod(BL_B2, float4((x + 0.5) / 16.0, (y + 0.5) / 12.0, 0, 0)).r;
    o = saturate(s / 192.0 * 12.0);
}

float3 PS_Composite(float4 pos : SV_Position, float2 uv : TEXCOORD) : SV_Target
{
    float t = Timer * 0.001;
    float4 L = tex2D(BL_B2, uv);             // r = blast light, g = fire heat
    float blast = saturate(L.r * 10.0);
    float fire = saturate(L.g * 7.5);

    if (BL_Debug == 1)
        return lerp(tex2D(ReShade::BackBuffer, uv).rgb * 0.3, float3(1, 0.5, 0.1), blast) + float3(0, 0, fire * 0.6);

    // heat shimmer: rising, wobbling air above blasts and fires
    float heat = (blast + fire * BL_FireHeat * 0.6) * BL_Heat * InPlay(uv);
    float2 q = pos.xy / float2(7.0, 5.0) + float2(0.0, t * 3.5);
    float2 wob = float2(VNoise(q), VNoise(q + 19.3)) - 0.5;
    float2 suv = uv + wob * heat * 3.0 * BUFFER_PIXEL_SIZE;
    float3 a = tex2D(ReShade::BackBuffer, suv).rgb;

    // blast light: lights the surfaces (multiplies) plus a little glow in the air
    float light = blast * BL_Light * InPlay(uv);
    float flicker = 0.75 + 0.25 * VNoise(float2(t * 9.0, pos.y * 0.01)) + 0.15 * VNoise(float2(t * 23.0, pos.x * 0.02));
    light += fire * BL_FireGlow * 0.5 * flicker * InPlay(uv);
    light *= 1.0 - 0.7 * Hot(a);   // the flash itself is already bright: light the surroundings
    float3 o = a + a * BL_Colour * light * 1.6 + BL_Colour * light * 0.18;

    // whole-field kick on big blasts
    o *= 1.0 + tex2D(BL_KickS, float2(0.5, 0.5)).r * BL_Kick * 0.35 * InPlay(uv);

    return saturate(o);
}

technique CnCBlast < ui_label = "6_ Blast light and heat";
    ui_tooltip = "New explosions light up the ground around them, and the air shimmers with heat. Put it after the colour grade and before UI After."; >
{
    pass Down    { VertexShader = PostProcessVS; PixelShader = PS_Down;    RenderTarget = BL_CurTex; }
    pass Energy  { VertexShader = PostProcessVS; PixelShader = PS_Energy;  RenderTarget = BL_ETex; }
    pass SaveE   { VertexShader = PostProcessVS; PixelShader = PS_CopyE;   RenderTarget = BL_EPrevTex; }
    pass BlurH   { VertexShader = PostProcessVS; PixelShader = PS_BlurH;   RenderTarget = BL_B1Tex; }
    pass BlurV   { VertexShader = PostProcessVS; PixelShader = PS_BlurV;   RenderTarget = BL_B2Tex; }
    pass Kick    { VertexShader = PostProcessVS; PixelShader = PS_Kick;    RenderTarget = BL_KickTex; }
    pass SaveCur { VertexShader = PostProcessVS; PixelShader = PS_CopyCur; RenderTarget = BL_PrevTex; }
    pass Compose { VertexShader = PostProcessVS; PixelShader = PS_Composite; }
}
