#!/bin/sh
cd grammar
#antlr4 -o .. -no-listener -Dlanguage=Python3 stlLexer.g4 stlParser.g4
antlr4 -o .. -no-listener -visitor -Dlanguage=Python3 stlLexer.g4 stlParser.g4
