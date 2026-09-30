SRC = ../reshadefx
CXXFLAGS = -std=c++17 -O1 -I$(SRC) -include cstdint -include cstring -include cstdio -include algorithm -include limits -w
OBJS = effect_lexer.o effect_parser.o effect_preprocessor.o effect_symbol_table.o effect_expression.o effect_codegen_glsl.o effect_codegen_hlsl.o

all: fxdump fxcheck
%.o: $(SRC)/%.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@
fxdump: fxdump.o $(OBJS)
	$(CXX) -o $@ $^
fxdump.o: fxdump.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@
fxcheck: fxcheck.o $(OBJS)
	$(CXX) -o $@ $^
fxcheck.o: ../fxcheck_main.cpp
	$(CXX) $(CXXFLAGS) -c $< -o $@
clean:
	rm -f *.o fxdump fxcheck
