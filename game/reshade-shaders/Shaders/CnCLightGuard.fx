// Fire and Light Pop (file name kept as CnCLightGuard.fx so existing presets still load)
// Makes explosions, weapon fire and small lights (bike lights, headlights, helmet lamps) POP:
// hotter, richer and brighter than the game drew them, whatever the grade or bloom above did to them.
// The game's own picture is only used to FIND fire and lights and as a brightness floor (never dimmer than
// the game drew). The colour you get is the preset's own grade, pushed hotter. It is not a copy of the game.
//
// How to use: LightGuard_Before as the FIRST colour effect after UI_Before, LightGuard_After as the LAST
// colour effect before UI_After. Effects that move pixels (HeatHaze, perspective) go before Before.

#include "ReShade.fxh"

uniform float Fire_Strength <
    ui_type = "slider"; ui_label = "Fire pop: amount";
    ui_tooltip = "How much explosions and weapon fire are boosted. 0 = off.";
    ui_min = 0.0; ui_max = 1.0; ui_step = 0.01;
> = 1.0;

uniform float Fire_Gain <
    ui_type = "slider"; ui_label = "Fire pop: brightness";
    ui_tooltip = "Extra brightness on fire and explosions.";
    ui_min = 0.0; ui_max = 1.0; ui_step = 0.01;
> = 0.25;

uniform float Fire_Saturation <
    ui_type = "slider"; ui_label = "Fire pop: richness";
    ui_tooltip = "Extra colour richness on fire and explosions (deeper oranges and yellows).";
    ui_min = 0.0; ui_max = 1.0; ui_step = 0.01;
> = 0.3;

uniform float Fire_Anchor <
    ui_type = "slider"; ui_label = "Fire pop: keep hot colours";
    ui_tooltip = "How much of the game's own hot orange and yellow is mixed back in, so fire never turns cold or grey under a cold grade. 0 = pure preset colour.";
    ui_min = 0.0; ui_max = 1.0; ui_step = 0.01;
> = 0.35;

uniform float Fire_Reach <
    ui_type = "slider"; ui_label = "Fire pop: how much counts as fire";
    ui_tooltip = "Higher = also catches dimmer, less saturated fire. Raise it if explosions are only partly boosted; lower it if bright sand or rock gets boosted.";
    ui_min = 0.0; ui_max = 1.0; ui_step = 0.01;
> = 0.0;

uniform float Lamp_Strength <
    ui_type = "slider"; ui_label = "Light pop: amount";
    ui_tooltip = "How much small bright lights are boosted. 0 = off.";
    ui_min = 0.0; ui_max = 1.0; ui_step = 0.01;
> = 1.0;

uniform float Lamp_Boost <
    ui_type = "slider"; ui_label = "Light pop: brightness";
    ui_tooltip = "Pushes small lights toward pure bright white.";
    ui_min = 0.0; ui_max = 1.0; ui_step = 0.01;
> = 0.4;

uniform float Lamp_Anchor <
    ui_type = "slider"; ui_label = "Light pop: keep light colour";
    ui_tooltip = "How much of the game's own light colour (warm white, blue white) is kept.";
    ui_min = 0.0; ui_max = 1.0; ui_step = 0.01;
> = 0.5;

uniform float Lamp_Radius <
    ui_type = "slider"; ui_label = "Light pop: size (pixels)";
    ui_tooltip = "How far around a pixel to look when deciding if it is a small light standing out from its surroundings.";
    ui_min = 1.0; ui_max = 8.0; ui_step = 0.5;
> = 3.0;

uniform float Glow_Strength <
    ui_type = "slider"; ui_label = "Glow around lights and fire";
    ui_tooltip = "A soft halo around small lights and fire so they read as light sources. 0 = no halo.";
    ui_min = 0.0; ui_max = 2.0; ui_step = 0.01;
> = 0.7;

uniform float Glow_Size <
    ui_type = "slider"; ui_label = "Glow size";
    ui_tooltip = "How far the halo spreads.";
    ui_min = 0.5; ui_max = 4.0; ui_step = 0.1;
> = 1.6;

uniform int Debug_View <
    ui_type = "combo"; ui_label = "Debug view";
    ui_tooltip = "Off = normal. Show masks = cyan where small lights are found, magenta where fire is found, the rest darkened. Show saved frame = the untouched game picture that was remembered.";
    ui_items = "Off\0Show masks\0Show saved frame\0";
> = 0;

texture LG_Before { Width = BUFFER_WIDTH; Height = BUFFER_HEIGHT; };
sampler LG_Before_sampler { Texture = LG_Before; MagFilter = POINT; MinFilter = POINT; MipFilter = POINT; };
texture LG_Src   { Width = BUFFER_WIDTH; Height = BUFFER_HEIGHT; };
sampler LG_Src_sampler { Texture = LG_Src; };
texture LG_BlurH { Width = BUFFER_WIDTH; Height = BUFFER_HEIGHT; };
sampler LG_BlurH_sampler { Texture = LG_BlurH; };
texture LG_BlurV { Width = BUFFER_WIDTH; Height = BUFFER_HEIGHT; };
sampler LG_BlurV_sampler { Texture = LG_BlurV; };

float LG_Luma(float3 c)
{
    return dot(c, float3(0.2126, 0.7152, 0.0722));
}

// finds small lights and fire in the untouched game picture
void LG_Masks(float2 uv, out float3 orig, out float lampMask, out float fireMask)
{
    orig = tex2D(LG_Before_sampler, uv).rgb;

    float mx  = max(orig.r, max(orig.g, orig.b));
    float mn  = min(orig.r, min(orig.g, orig.b));
    float sat = (mx - mn) / max(mx, 0.0001);
    float lo  = LG_Luma(orig);

    // how much brighter this pixel is than a ring of neighbours: picks out small lights and sparks
    float2 d = ReShade::PixelSize * Lamp_Radius;
    float2 e = d * 0.7071;
    float ring = 0.0;
    ring += LG_Luma(tex2D(LG_Before_sampler, uv + float2( d.x, 0.0)).rgb);
    ring += LG_Luma(tex2D(LG_Before_sampler, uv + float2(-d.x, 0.0)).rgb);
    ring += LG_Luma(tex2D(LG_Before_sampler, uv + float2(0.0,  d.y)).rgb);
    ring += LG_Luma(tex2D(LG_Before_sampler, uv + float2(0.0, -d.y)).rgb);
    ring += LG_Luma(tex2D(LG_Before_sampler, uv + float2( e.x,  e.y)).rgb);
    ring += LG_Luma(tex2D(LG_Before_sampler, uv + float2(-e.x,  e.y)).rgb);
    ring += LG_Luma(tex2D(LG_Before_sampler, uv + float2( e.x, -e.y)).rgb);
    ring += LG_Luma(tex2D(LG_Before_sampler, uv + float2(-e.x, -e.y)).rgb);
    ring *= 0.125;
    float peak = saturate((lo - ring - 0.12) / 0.25);

    // small white or pale lights
    lampMask = peak * smoothstep(0.50, 0.80, lo) * (1.0 - smoothstep(0.30, 0.55, sat));

    // fire: red to yellow, either very bright, or clearly standing out from what is around it
    float warm = step(orig.g, orig.r + 0.01) * step(orig.b, orig.g + 0.01) * saturate((orig.r - orig.b) * 6.0);
    float lowMx = 0.92 - 0.22 * Fire_Reach;
    float lowSat = 0.38 - 0.18 * Fire_Reach;
    float fireBright = smoothstep(lowMx, lowMx + 0.07, mx) * smoothstep(lowSat, lowSat + 0.20, sat);
    float fireEdge   = peak * smoothstep(0.60 - 0.15 * Fire_Reach, 0.85 - 0.15 * Fire_Reach, mx) * smoothstep(0.50 - 0.15 * Fire_Reach, 0.70 - 0.15 * Fire_Reach, sat);
    fireMask = warm * max(fireBright, fireEdge);
}

float4 PS_LG_Before(float4 pos : SV_Position, float2 texcoord : TEXCOORD) : SV_Target
{
    return tex2D(ReShade::BackBuffer, texcoord);
}

// glow source: the lights and fire themselves, in the game's colours
float4 PS_LG_Src(float4 pos : SV_Position, float2 texcoord : TEXCOORD) : SV_Target
{
    float3 orig;
    float lampMask, fireMask;
    LG_Masks(texcoord, orig, lampMask, fireMask);
    float w = saturate(lampMask * Lamp_Strength + fireMask * Fire_Strength * 0.6);
    return float4(saturate(orig * w), 1.0);
}

float4 PS_LG_BlurH(float4 pos : SV_Position, float2 texcoord : TEXCOORD) : SV_Target
{
    float2 s = float2(ReShade::PixelSize.x * Glow_Size, 0.0);
    float3 c = tex2D(LG_Src_sampler, texcoord).rgb * 0.2270;
    c += (tex2D(LG_Src_sampler, texcoord + s).rgb       + tex2D(LG_Src_sampler, texcoord - s).rgb)       * 0.1945;
    c += (tex2D(LG_Src_sampler, texcoord + s * 2.0).rgb + tex2D(LG_Src_sampler, texcoord - s * 2.0).rgb) * 0.1218;
    c += (tex2D(LG_Src_sampler, texcoord + s * 3.0).rgb + tex2D(LG_Src_sampler, texcoord - s * 3.0).rgb) * 0.0540;
    c += (tex2D(LG_Src_sampler, texcoord + s * 4.0).rgb + tex2D(LG_Src_sampler, texcoord - s * 4.0).rgb) * 0.0162;
    return float4(c, 1.0);
}

float4 PS_LG_BlurV(float4 pos : SV_Position, float2 texcoord : TEXCOORD) : SV_Target
{
    float2 s = float2(0.0, ReShade::PixelSize.y * Glow_Size);
    float3 c = tex2D(LG_BlurH_sampler, texcoord).rgb * 0.2270;
    c += (tex2D(LG_BlurH_sampler, texcoord + s).rgb       + tex2D(LG_BlurH_sampler, texcoord - s).rgb)       * 0.1945;
    c += (tex2D(LG_BlurH_sampler, texcoord + s * 2.0).rgb + tex2D(LG_BlurH_sampler, texcoord - s * 2.0).rgb) * 0.1218;
    c += (tex2D(LG_BlurH_sampler, texcoord + s * 3.0).rgb + tex2D(LG_BlurH_sampler, texcoord - s * 3.0).rgb) * 0.0540;
    c += (tex2D(LG_BlurH_sampler, texcoord + s * 4.0).rgb + tex2D(LG_BlurH_sampler, texcoord - s * 4.0).rgb) * 0.0162;
    return float4(c, 1.0);
}

float4 PS_LG_After(float4 pos : SV_Position, float2 texcoord : TEXCOORD) : SV_Target
{
    float3 cur = tex2D(ReShade::BackBuffer, texcoord).rgb;
    float3 orig;
    float lampMask, fireMask;
    LG_Masks(texcoord, orig, lampMask, fireMask);

    if (Debug_View == 2)
        return float4(orig, 1.0);
    if (Debug_View == 1)
    {
        float3 dbg = cur * 0.3;
        dbg = lerp(dbg, float3(0.0, 1.0, 1.0), lampMask);
        dbg = lerp(dbg, float3(1.0, 0.0, 1.0), fireMask);
        return float4(dbg, 1.0);
    }

    float lo = LG_Luma(orig);

    // FIRE POP: the preset's own colour, kept hot, made richer and brighter, never dimmer than the game drew it
    float3 f = lerp(cur, orig, Fire_Anchor);
    float lf = LG_Luma(f);
    f = lf + (f - lf) * (1.0 + Fire_Saturation);
    f *= 1.0 + Fire_Gain;
    f *= clamp(lo / max(LG_Luma(f), 0.05), 1.0, 1.5);
    float3 res = lerp(cur, saturate(f), fireMask * Fire_Strength);

    // LIGHT POP: the light's own colour, pushed toward bright white, never dimmer than the game drew it
    float3 l = lerp(cur, orig, Lamp_Anchor);
    l = l + (1.0 - l) * Lamp_Boost;
    l *= clamp(lo / max(LG_Luma(l), 0.05), 1.0, 1.4);
    res = lerp(res, saturate(l), lampMask * Lamp_Strength);

    // GLOW: a soft halo around lights and fire
    res += tex2D(LG_BlurV_sampler, texcoord).rgb * Glow_Strength;

    return float4(saturate(res), 1.0);
}

technique LightGuard_Before < ui_label = "0_ Fire and Light Pop START"; ui_tooltip = "One half of a pair: keep this FIRST in the list, right after UI Before, and keep Fire and Light Pop END last. It only remembers the untouched game picture; the boost happens in END."; >
{
    pass {
        VertexShader = PostProcessVS;
        PixelShader = PS_LG_Before;
        RenderTarget = LG_Before;
    }
}

technique LightGuard_After < ui_label = "0_ Fire and Light Pop END"; ui_tooltip = "The other half of the pair: keep this LAST, right before UI After. This is where the settings are. Makes explosions, weapon fire and small lights pop, hotter and brighter with a soft glow, whatever the grade did to them."; >
{
    pass {
        VertexShader = PostProcessVS;
        PixelShader = PS_LG_Src;
        RenderTarget = LG_Src;
    }
    pass {
        VertexShader = PostProcessVS;
        PixelShader = PS_LG_BlurH;
        RenderTarget = LG_BlurH;
    }
    pass {
        VertexShader = PostProcessVS;
        PixelShader = PS_LG_BlurV;
        RenderTarget = LG_BlurV;
    }
    pass {
        VertexShader = PostProcessVS;
        PixelShader = PS_LG_After;
    }
}
