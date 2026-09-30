/**
 * Heat Haze
 * by Marty McFly
 *
 * Ported from ReShade Framework
 * to ReShade 3.0+ by mbah.primbon
 *
 */

//-------------------- GUI Settings ----------------------
uniform bool bHeatHazeDebug <
	ui_label = "Heat Haze Debug View";
	ui_tooltip = "Enables raw texture output for debugging purposes. Useful for texture experiments.";
> = false;

uniform float fHeatHazeSpeed <
	ui_type = "drag";
	ui_min = 0.00; ui_max = 10.00;
    ui_label = "Heat Haze Speed";
	ui_tooltip = "Speed of heathaze waves";
> = 1.80;

uniform float fHeatHazeOffset <
	ui_type = "drag";
	ui_min = 0.50; ui_max = 20.00; ui_step = 0.1;
    ui_label = "Heat Haze Offset";
	ui_tooltip = "Amount of image distortion caused by heathaze effect";
> = 4.40;

uniform float fHeatHazeTextureScale <
	ui_type = "drag";
	ui_min = 0.50; ui_max = 8.00; ui_step = 0.1;
    ui_label = "Heat Haze Texture Scale";
	ui_tooltip = "Scale of source texture, affecting the tile size. Use Heathaze debug effect for better visible effect.";
> = 1.00;

uniform float fHeatHazeChromaAmount <
	ui_type = "drag";
	ui_min = 0.00; ui_max = 2.00; ui_step = 0.01;
    ui_label = "Heat Haze Chroma Amount";
	ui_tooltip = "Amount of color shift caused by heat haze. Linearly scales with fHeatHazeOffset.";
> = 0.3;

//------------------------------------------------------------------------
#include "ReShade.fxh"
uniform float Timer < source = "timer"; >;
	
// Textures and samplers
texture texBump <source = "haze.png";> {Width = 512; Height = 512; Format = RGBA8;};
sampler samplerBump {Texture = texBump; MinFilter = LINEAR; MagFilter = LINEAR; MipFilter = LINEAR; AddressU = Repeat; AddressV = Repeat;};

// Pixel shaders
void PS_HeatHaze(float4 vpos : SV_Position, float2 texcoord : TEXCOORD, out float3 color : SV_Target)
{	
	float3 heatnormal = tex2Dlod(samplerBump, float4(texcoord.xy*fHeatHazeTextureScale+float2(0.0,Timer.x*0.0001*fHeatHazeSpeed),0,0)).rgb - 0.5;
	float2 heatoffset = normalize(heatnormal.xy) * pow(length(heatnormal.xy), 0.5);
	
	float3 heathazecolor = 0;

	heathazecolor.y = tex2D(ReShade::BackBuffer, texcoord.xy + heatoffset.xy * 0.001 * fHeatHazeOffset).y;
	heathazecolor.x = tex2D(ReShade::BackBuffer, texcoord.xy + heatoffset.xy * 0.001 * fHeatHazeOffset * (1.0+fHeatHazeChromaAmount)).x;
	heathazecolor.z = tex2D(ReShade::BackBuffer, texcoord.xy + heatoffset.xy * 0.001 * fHeatHazeOffset * (1.0-fHeatHazeChromaAmount)).z;

	color.xyz = heathazecolor;
	if(bHeatHazeDebug) color.xyz = heatnormal.xyz+0.5;
}

// Rendering passes
technique HeatHaze < ui_label = "3_ Heat Haze"; ui_tooltip = "Wobbling heat-shimmer distortion. Good for fire and desert looks.\nGoes in the light stage."; >
{
	pass HeatHazeBEGINNN
	{
		VertexShader = PostProcessVS;
		PixelShader = PS_HeatHaze;
	}
	
}