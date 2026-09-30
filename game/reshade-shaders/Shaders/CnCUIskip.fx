//Before/After based shader for isolating the C&C engine sidebar.
//Author: tomsons26
//To use place UI_Before before your effects, enable it, place UI_After after your effects, enable it

#include "ReShade.fxh"
#include "ReShadeUI.fxh"

uniform bool Isolate_UI <
> = true;

texture UI_Before { Width = BUFFER_WIDTH; Height = BUFFER_HEIGHT; };
sampler UI_Before_sampler { Texture = UI_Before; };

float4 PS_UI_Before(float4 pos : SV_Position, float2 texcoord : TEXCOORD) : SV_Target
{
    return tex2D(ReShade::BackBuffer, texcoord);
}

float4 PS_UI_After(float4 pos : SV_Position, float2 texcoord : TEXCOORD) : SV_Target
{
    if (Isolate_UI) {
        // why 22.... it should be 16 but something is making a offset, adjust the 22 if needed
        float2 viewport;
        viewport.x = (BUFFER_WIDTH - 168) * ReShade::PixelSize;
        viewport.y = 22 * ReShade::PixelSize;
        if (texcoord.x > viewport.x || texcoord.y < viewport.y) {
            return tex2D(UI_Before_sampler, texcoord);
        }
    }
    //effect not enabled, return the before
    return tex2D(ReShade::BackBuffer, texcoord);
    
}

technique UI_Before < ui_label = "0_ UI Before"; ui_tooltip = "Always the FIRST effect in a chain. Hides the sidebar from everything below it so only the playfield is graded. Pair with UI Before/After and set Isolate_UI=1."; >
{
    pass {
        VertexShader = PostProcessVS;
        PixelShader = PS_UI_Before;
        RenderTarget = UI_Before;
    }
}

technique UI_After < ui_label = "0_ UI After"; ui_tooltip = "Always the LAST effect in a chain. Puts the sidebar back untouched after all the effects above it."; >
{
    pass {
        VertexShader = PostProcessVS;
        PixelShader = PS_UI_After;
    }
}