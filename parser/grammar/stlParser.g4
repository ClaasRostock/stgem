parser grammar stlParser;

options {
    language = Python3;
    tokenVocab = stlLexer;
}

stlSpecification
    : phi EOF ;

phi
    : LPAREN phi RPAREN              #parenPhiExpr
    | VBAR phi VBAR                  #absPhiExpr

    | NEGATION phi                   #opNegExpr
    | NEXTOP phi                     #opNextExpr

    | FUTUREOP      (interval)? phi  #opFutureExpr
    | GLOBALLYOP    (interval)? phi  #opGloballyExpr

    | phi UNTILOP   (interval)? phi  #opUntilExpr

    | phi (ANDOP | OROP) phi         #opLogicalExpr

    | phi (IMPLIESOP | EQUIVOP) phi  #opPropExpr

    | signal RELOP signal            #predicateExpr
    | signal                         #signalExpr
;

signal
    : NUMBER                         #signalNumber
    | NAME                           #signalName
    | (LPAREN) signal (RPAREN)       #signalParenthesisExpr
    | signal (MULT | DIV) signal     #signalMultExpr
    | signal (PLUS | MINUS) signal   #signalSumExpr
;

interval
    : (LPAREN | LBRACK) (NUMBER | INF) COMMA (NUMBER | INF) (RPAREN | RBRACK)
;
