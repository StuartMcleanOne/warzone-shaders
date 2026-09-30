#include "effect_parser.hpp"
#include "effect_preprocessor.hpp"
#include "effect_codegen.hpp"
#include <iostream>
int main(int argc,char**argv){
  std::filesystem::path p=argv[1]; int rc=0;
  for(int mode=0;mode<2;mode++){
    reshadefx::preprocessor pp;
    for(int i=2;i<argc;i++) pp.add_include_path(argv[i]);
    pp.add_macro_definition("__RESHADE__","40504");
    pp.add_macro_definition("__RESHADE_PERFORMANCE_MODE__","1");
    pp.add_macro_definition("__VENDOR__","0"); pp.add_macro_definition("__DEVICE__","0");
    pp.add_macro_definition("__RENDERER__", mode==0?"45312":"73728");
    pp.add_macro_definition("__APPLICATION__","1");
    pp.add_macro_definition("BUFFER_WIDTH","800"); pp.add_macro_definition("BUFFER_HEIGHT","600");
    pp.add_macro_definition("BUFFER_RCP_WIDTH","(1.0 / BUFFER_WIDTH)"); pp.add_macro_definition("BUFFER_RCP_HEIGHT","(1.0 / BUFFER_HEIGHT)");
    pp.add_macro_definition("BUFFER_COLOR_BIT_DEPTH","8");
    bool ok=pp.append_file(p);
    std::unique_ptr<reshadefx::codegen> cg(mode==0?reshadefx::create_codegen_hlsl(41,true,true):reshadefx::create_codegen_glsl(true,true));
    reshadefx::parser ps;
    bool ok2=ps.parse(std::move(pp.output()),cg.get());
    std::cout<<(mode==0?"[hlsl] ":"[glsl] ")<<(ok&&ok2?"OK":"FAIL")<<"\n"<<pp.errors()<<ps.errors();
    if(!(ok&&ok2)) rc=1;
  }
  return rc;}
