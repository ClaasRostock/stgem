# Generated from stlParser.g4 by ANTLR 4.10.1
# encoding: utf-8
from antlr4 import *
from io import StringIO
import sys
if sys.version_info[1] > 5:
	from typing import TextIO
else:
	from typing.io import TextIO

def serializedATN():
    return [
        4,1,28,88,2,0,7,0,2,1,7,1,2,2,7,2,2,3,7,3,1,0,1,0,1,0,1,1,1,1,1,
        1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,3,1,23,8,1,1,1,1,1,1,1,3,1,28,
        8,1,1,1,1,1,1,1,1,1,1,1,1,1,3,1,36,8,1,1,1,1,1,1,1,3,1,41,8,1,1,
        1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,5,1,53,8,1,10,1,12,1,56,9,
        1,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,1,2,3,2,69,8,2,1,2,1,2,
        1,2,1,2,1,2,1,2,5,2,77,8,2,10,2,12,2,80,9,2,1,3,1,3,1,3,1,3,1,3,
        1,3,1,3,0,2,2,4,4,0,2,4,6,0,7,1,0,13,14,1,0,21,22,1,0,10,11,1,0,
        8,9,2,0,2,2,4,4,2,0,23,23,25,25,2,0,3,3,5,5,101,0,8,1,0,0,0,2,35,
        1,0,0,0,4,68,1,0,0,0,6,81,1,0,0,0,8,9,3,2,1,0,9,10,5,0,0,1,10,1,
        1,0,0,0,11,12,6,1,-1,0,12,13,5,2,0,0,13,14,3,2,1,0,14,15,5,3,0,0,
        15,36,1,0,0,0,16,17,5,12,0,0,17,36,3,2,1,10,18,19,5,15,0,0,19,36,
        3,2,1,9,20,22,5,16,0,0,21,23,3,6,3,0,22,21,1,0,0,0,22,23,1,0,0,0,
        23,24,1,0,0,0,24,36,3,2,1,8,25,27,5,17,0,0,26,28,3,6,3,0,27,26,1,
        0,0,0,27,28,1,0,0,0,28,29,1,0,0,0,29,36,3,2,1,7,30,31,3,4,2,0,31,
        32,7,0,0,0,32,33,3,4,2,0,33,36,1,0,0,0,34,36,3,4,2,0,35,11,1,0,0,
        0,35,16,1,0,0,0,35,18,1,0,0,0,35,20,1,0,0,0,35,25,1,0,0,0,35,30,
        1,0,0,0,35,34,1,0,0,0,36,54,1,0,0,0,37,38,10,6,0,0,38,40,5,18,0,
        0,39,41,3,6,3,0,40,39,1,0,0,0,40,41,1,0,0,0,41,42,1,0,0,0,42,53,
        3,2,1,7,43,44,10,5,0,0,44,45,5,19,0,0,45,53,3,2,1,6,46,47,10,4,0,
        0,47,48,5,20,0,0,48,53,3,2,1,5,49,50,10,3,0,0,50,51,7,1,0,0,51,53,
        3,2,1,4,52,37,1,0,0,0,52,43,1,0,0,0,52,46,1,0,0,0,52,49,1,0,0,0,
        53,56,1,0,0,0,54,52,1,0,0,0,54,55,1,0,0,0,55,3,1,0,0,0,56,54,1,0,
        0,0,57,58,6,2,-1,0,58,69,5,25,0,0,59,69,5,24,0,0,60,61,5,2,0,0,61,
        62,3,4,2,0,62,63,5,3,0,0,63,69,1,0,0,0,64,65,5,6,0,0,65,66,3,4,2,
        0,66,67,5,6,0,0,67,69,1,0,0,0,68,57,1,0,0,0,68,59,1,0,0,0,68,60,
        1,0,0,0,68,64,1,0,0,0,69,78,1,0,0,0,70,71,10,3,0,0,71,72,7,2,0,0,
        72,77,3,4,2,4,73,74,10,2,0,0,74,75,7,3,0,0,75,77,3,4,2,3,76,70,1,
        0,0,0,76,73,1,0,0,0,77,80,1,0,0,0,78,76,1,0,0,0,78,79,1,0,0,0,79,
        5,1,0,0,0,80,78,1,0,0,0,81,82,7,4,0,0,82,83,7,5,0,0,83,84,5,7,0,
        0,84,85,7,5,0,0,85,86,7,6,0,0,86,7,1,0,0,0,9,22,27,35,40,52,54,68,
        76,78
    ]

class stlParser ( Parser ):

    grammarFileName = "stlParser.g4"

    atn = ATNDeserializer().deserialize(serializedATN())

    decisionsToDFA = [ DFA(ds, i) for i, ds in enumerate(atn.decisionToState) ]

    sharedContextCache = PredictionContextCache()

    literalNames = [ "<INVALID>", "<INVALID>", "'('", "')'", "'['", "']'", 
                     "'|'", "','", "'+'", "'-'", "'*'", "'/'", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "<INVALID>", "<INVALID>", 
                     "<INVALID>", "<INVALID>", "'and'", "'or'", "<INVALID>", 
                     "<INVALID>", "'inf'" ]

    symbolicNames = [ "<INVALID>", "WS", "LPAREN", "RPAREN", "LBRACK", "RBRACK", 
                      "VBAR", "COMMA", "PLUS", "MINUS", "MULT", "DIV", "NEGATION", 
                      "RELOP", "EQUALITYOP", "NEXTOP", "FUTUREOP", "GLOBALLYOP", 
                      "UNTILOP", "ANDOP", "OROP", "IMPLIESOP", "EQUIVOP", 
                      "INF", "NAME", "NUMBER", "INT_NUMBER", "FLOAT_NUMBER", 
                      "SCIENTIFIC_NUMBER" ]

    RULE_stlSpecification = 0
    RULE_phi = 1
    RULE_signal = 2
    RULE_interval = 3

    ruleNames =  [ "stlSpecification", "phi", "signal", "interval" ]

    EOF = Token.EOF
    WS=1
    LPAREN=2
    RPAREN=3
    LBRACK=4
    RBRACK=5
    VBAR=6
    COMMA=7
    PLUS=8
    MINUS=9
    MULT=10
    DIV=11
    NEGATION=12
    RELOP=13
    EQUALITYOP=14
    NEXTOP=15
    FUTUREOP=16
    GLOBALLYOP=17
    UNTILOP=18
    ANDOP=19
    OROP=20
    IMPLIESOP=21
    EQUIVOP=22
    INF=23
    NAME=24
    NUMBER=25
    INT_NUMBER=26
    FLOAT_NUMBER=27
    SCIENTIFIC_NUMBER=28

    def __init__(self, input:TokenStream, output:TextIO = sys.stdout):
        super().__init__(input, output)
        self.checkVersion("4.10.1")
        self._interp = ParserATNSimulator(self, self.atn, self.decisionsToDFA, self.sharedContextCache)
        self._predicates = None




    class StlSpecificationContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def phi(self):
            return self.getTypedRuleContext(stlParser.PhiContext,0)


        def EOF(self):
            return self.getToken(stlParser.EOF, 0)

        def getRuleIndex(self):
            return stlParser.RULE_stlSpecification

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitStlSpecification" ):
                return visitor.visitStlSpecification(self)
            else:
                return visitor.visitChildren(self)




    def stlSpecification(self):

        localctx = stlParser.StlSpecificationContext(self, self._ctx, self.state)
        self.enterRule(localctx, 0, self.RULE_stlSpecification)
        try:
            self.enterOuterAlt(localctx, 1)
            self.state = 8
            self.phi(0)
            self.state = 9
            self.match(stlParser.EOF)
        except RecognitionException as re:
            localctx.exception = re
            self._errHandler.reportError(self, re)
            self._errHandler.recover(self, re)
        finally:
            self.exitRule()
        return localctx


    class PhiContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return stlParser.RULE_phi

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)


    class PredicateExprContext(PhiContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a stlParser.PhiContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def signal(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(stlParser.SignalContext)
            else:
                return self.getTypedRuleContext(stlParser.SignalContext,i)

        def RELOP(self):
            return self.getToken(stlParser.RELOP, 0)
        def EQUALITYOP(self):
            return self.getToken(stlParser.EQUALITYOP, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitPredicateExpr" ):
                return visitor.visitPredicateExpr(self)
            else:
                return visitor.visitChildren(self)


    class SignalExprContext(PhiContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a stlParser.PhiContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def signal(self):
            return self.getTypedRuleContext(stlParser.SignalContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSignalExpr" ):
                return visitor.visitSignalExpr(self)
            else:
                return visitor.visitChildren(self)


    class OpFutureExprContext(PhiContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a stlParser.PhiContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def FUTUREOP(self):
            return self.getToken(stlParser.FUTUREOP, 0)
        def phi(self):
            return self.getTypedRuleContext(stlParser.PhiContext,0)

        def interval(self):
            return self.getTypedRuleContext(stlParser.IntervalContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOpFutureExpr" ):
                return visitor.visitOpFutureExpr(self)
            else:
                return visitor.visitChildren(self)


    class ParenPhiExprContext(PhiContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a stlParser.PhiContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(stlParser.LPAREN, 0)
        def phi(self):
            return self.getTypedRuleContext(stlParser.PhiContext,0)

        def RPAREN(self):
            return self.getToken(stlParser.RPAREN, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitParenPhiExpr" ):
                return visitor.visitParenPhiExpr(self)
            else:
                return visitor.visitChildren(self)


    class OpUntilExprContext(PhiContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a stlParser.PhiContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def phi(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(stlParser.PhiContext)
            else:
                return self.getTypedRuleContext(stlParser.PhiContext,i)

        def UNTILOP(self):
            return self.getToken(stlParser.UNTILOP, 0)
        def interval(self):
            return self.getTypedRuleContext(stlParser.IntervalContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOpUntilExpr" ):
                return visitor.visitOpUntilExpr(self)
            else:
                return visitor.visitChildren(self)


    class OpGloballyExprContext(PhiContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a stlParser.PhiContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def GLOBALLYOP(self):
            return self.getToken(stlParser.GLOBALLYOP, 0)
        def phi(self):
            return self.getTypedRuleContext(stlParser.PhiContext,0)

        def interval(self):
            return self.getTypedRuleContext(stlParser.IntervalContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOpGloballyExpr" ):
                return visitor.visitOpGloballyExpr(self)
            else:
                return visitor.visitChildren(self)


    class OpAndExprContext(PhiContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a stlParser.PhiContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def phi(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(stlParser.PhiContext)
            else:
                return self.getTypedRuleContext(stlParser.PhiContext,i)

        def ANDOP(self):
            return self.getToken(stlParser.ANDOP, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOpAndExpr" ):
                return visitor.visitOpAndExpr(self)
            else:
                return visitor.visitChildren(self)


    class OpNextExprContext(PhiContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a stlParser.PhiContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def NEXTOP(self):
            return self.getToken(stlParser.NEXTOP, 0)
        def phi(self):
            return self.getTypedRuleContext(stlParser.PhiContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOpNextExpr" ):
                return visitor.visitOpNextExpr(self)
            else:
                return visitor.visitChildren(self)


    class OpOrExprContext(PhiContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a stlParser.PhiContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def phi(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(stlParser.PhiContext)
            else:
                return self.getTypedRuleContext(stlParser.PhiContext,i)

        def OROP(self):
            return self.getToken(stlParser.OROP, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOpOrExpr" ):
                return visitor.visitOpOrExpr(self)
            else:
                return visitor.visitChildren(self)


    class OpPropExprContext(PhiContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a stlParser.PhiContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def phi(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(stlParser.PhiContext)
            else:
                return self.getTypedRuleContext(stlParser.PhiContext,i)

        def IMPLIESOP(self):
            return self.getToken(stlParser.IMPLIESOP, 0)
        def EQUIVOP(self):
            return self.getToken(stlParser.EQUIVOP, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOpPropExpr" ):
                return visitor.visitOpPropExpr(self)
            else:
                return visitor.visitChildren(self)


    class OpNegExprContext(PhiContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a stlParser.PhiContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def NEGATION(self):
            return self.getToken(stlParser.NEGATION, 0)
        def phi(self):
            return self.getTypedRuleContext(stlParser.PhiContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitOpNegExpr" ):
                return visitor.visitOpNegExpr(self)
            else:
                return visitor.visitChildren(self)



    def phi(self, _p:int=0):
    	_parentctx = self._ctx
    	_parentState = self.state
    	localctx = stlParser.PhiContext(self, self._ctx, _parentState)
    	_prevctx = localctx
    	_startState = 2
    	self.enterRecursionRule(localctx, 2, self.RULE_phi, _p)
    	self._la = 0 # Token type
    	try:
    		self.enterOuterAlt(localctx, 1)
    		self.state = 35
    		self._errHandler.sync(self)
    		la_ = self._interp.adaptivePredict(self._input,2,self._ctx)
    		if la_ == 1:
    			localctx = stlParser.ParenPhiExprContext(self, localctx)
    			self._ctx = localctx
    			_prevctx = localctx

    			self.state = 12
    			self.match(stlParser.LPAREN)
    			self.state = 13
    			self.phi(0)
    			self.state = 14
    			self.match(stlParser.RPAREN)
    		elif la_ == 2:
    			localctx = stlParser.OpNegExprContext(self, localctx)
    			self._ctx = localctx
    			_prevctx = localctx
    			self.state = 16
    			self.match(stlParser.NEGATION)
    			self.state = 17
    			self.phi(10)
    		elif la_ == 3:
    			localctx = stlParser.OpNextExprContext(self, localctx)
    			self._ctx = localctx
    			_prevctx = localctx
    			self.state = 18
    			self.match(stlParser.NEXTOP)
    			self.state = 19
    			self.phi(9)
    		elif la_ == 4:
    			localctx = stlParser.OpFutureExprContext(self, localctx)
    			self._ctx = localctx
    			_prevctx = localctx
    			self.state = 20
    			self.match(stlParser.FUTUREOP)
    			self.state = 22
    			self._errHandler.sync(self)
    			la_ = self._interp.adaptivePredict(self._input,0,self._ctx)
    			if la_ == 1:
    			    self.state = 21
    			    self.interval()


    			self.state = 24
    			self.phi(8)
    		elif la_ == 5:
    			localctx = stlParser.OpGloballyExprContext(self, localctx)
    			self._ctx = localctx
    			_prevctx = localctx
    			self.state = 25
    			self.match(stlParser.GLOBALLYOP)
    			self.state = 27
    			self._errHandler.sync(self)
    			la_ = self._interp.adaptivePredict(self._input,1,self._ctx)
    			if la_ == 1:
    			    self.state = 26
    			    self.interval()


    			self.state = 29
    			self.phi(7)
    		elif la_ == 6:
    			localctx = stlParser.PredicateExprContext(self, localctx)
    			self._ctx = localctx
    			_prevctx = localctx
    			self.state = 30
    			self.signal(0)
    			self.state = 31
    			_la = self._input.LA(1)
    			if _la not in [stlParser.RELOP, stlParser.EQUALITYOP]:
    				self._errHandler.recoverInline(self)
    			else:
    				self._errHandler.reportMatch(self)
    				self.consume()
    			self.state = 32
    			self.signal(0)
    		elif la_ == 7:
    			localctx = stlParser.SignalExprContext(self, localctx)
    			self._ctx = localctx
    			_prevctx = localctx
    			self.state = 34
    			self.signal(0)
    		self._ctx.stop = self._input.LT(-1)
    		self.state = 54
    		self._errHandler.sync(self)
    		_alt = self._interp.adaptivePredict(self._input,5,self._ctx)
    		while _alt not in [2, ATN.INVALID_ALT_NUMBER]:
    			if _alt==1:
    				if self._parseListeners is not None:
    				    self.triggerExitRuleEvent()
    				_prevctx = localctx
    				self.state = 52
    				self._errHandler.sync(self)
    				la_ = self._interp.adaptivePredict(self._input,4,self._ctx)
    				if la_ == 1:
    					localctx = stlParser.OpUntilExprContext(self, stlParser.PhiContext(self, _parentctx, _parentState))
    					self.pushNewRecursionContext(localctx, _startState, self.RULE_phi)
    					self.state = 37
    					if not self.precpred(self._ctx, 6):
    					    from antlr4.error.Errors import FailedPredicateException
    					    raise FailedPredicateException(self, "self.precpred(self._ctx, 6)")
    					self.state = 38
    					self.match(stlParser.UNTILOP)
    					self.state = 40
    					self._errHandler.sync(self)
    					la_ = self._interp.adaptivePredict(self._input,3,self._ctx)
    					if la_ == 1:
    					    self.state = 39
    					    self.interval()


    					self.state = 42
    					self.phi(7)
    				elif la_ == 2:
    					localctx = stlParser.OpAndExprContext(self, stlParser.PhiContext(self, _parentctx, _parentState))
    					self.pushNewRecursionContext(localctx, _startState, self.RULE_phi)
    					self.state = 43
    					if not self.precpred(self._ctx, 5):
    					    from antlr4.error.Errors import FailedPredicateException
    					    raise FailedPredicateException(self, "self.precpred(self._ctx, 5)")
    					self.state = 44
    					self.match(stlParser.ANDOP)
    					self.state = 45
    					self.phi(6)
    				elif la_ == 3:
    					localctx = stlParser.OpOrExprContext(self, stlParser.PhiContext(self, _parentctx, _parentState))
    					self.pushNewRecursionContext(localctx, _startState, self.RULE_phi)
    					self.state = 46
    					if not self.precpred(self._ctx, 4):
    					    from antlr4.error.Errors import FailedPredicateException
    					    raise FailedPredicateException(self, "self.precpred(self._ctx, 4)")
    					self.state = 47
    					self.match(stlParser.OROP)
    					self.state = 48
    					self.phi(5)
    				elif la_ == 4:
    					localctx = stlParser.OpPropExprContext(self, stlParser.PhiContext(self, _parentctx, _parentState))
    					self.pushNewRecursionContext(localctx, _startState, self.RULE_phi)
    					self.state = 49
    					if not self.precpred(self._ctx, 3):
    					    from antlr4.error.Errors import FailedPredicateException
    					    raise FailedPredicateException(self, "self.precpred(self._ctx, 3)")
    					self.state = 50
    					_la = self._input.LA(1)
    					if _la not in [stlParser.IMPLIESOP, stlParser.EQUIVOP]:
    						self._errHandler.recoverInline(self)
    					else:
    						self._errHandler.reportMatch(self)
    						self.consume()
    					self.state = 51
    					self.phi(4)
    			self.state = 56
    			self._errHandler.sync(self)
    			_alt = self._interp.adaptivePredict(self._input,5,self._ctx)

    	except RecognitionException as re:
    	    localctx.exception = re
    	    self._errHandler.reportError(self, re)
    	    self._errHandler.recover(self, re)
    	finally:
    		self.unrollRecursionContexts(_parentctx)
    	return localctx


    class SignalContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser


        def getRuleIndex(self):
            return stlParser.RULE_signal

     
        def copyFrom(self, ctx:ParserRuleContext):
            super().copyFrom(ctx)


    class SignalParenthesisExprContext(SignalContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a stlParser.SignalContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def LPAREN(self):
            return self.getToken(stlParser.LPAREN, 0)
        def signal(self):
            return self.getTypedRuleContext(stlParser.SignalContext,0)

        def RPAREN(self):
            return self.getToken(stlParser.RPAREN, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSignalParenthesisExpr" ):
                return visitor.visitSignalParenthesisExpr(self)
            else:
                return visitor.visitChildren(self)


    class SignalNameContext(SignalContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a stlParser.SignalContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def NAME(self):
            return self.getToken(stlParser.NAME, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSignalName" ):
                return visitor.visitSignalName(self)
            else:
                return visitor.visitChildren(self)


    class SignalAbsExprContext(SignalContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a stlParser.SignalContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def VBAR(self, i:int=None):
            if i is None:
                return self.getTokens(stlParser.VBAR)
            else:
                return self.getToken(stlParser.VBAR, i)
        def signal(self):
            return self.getTypedRuleContext(stlParser.SignalContext,0)


        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSignalAbsExpr" ):
                return visitor.visitSignalAbsExpr(self)
            else:
                return visitor.visitChildren(self)


    class SignalSumExprContext(SignalContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a stlParser.SignalContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def signal(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(stlParser.SignalContext)
            else:
                return self.getTypedRuleContext(stlParser.SignalContext,i)

        def PLUS(self):
            return self.getToken(stlParser.PLUS, 0)
        def MINUS(self):
            return self.getToken(stlParser.MINUS, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSignalSumExpr" ):
                return visitor.visitSignalSumExpr(self)
            else:
                return visitor.visitChildren(self)


    class SignalNumberContext(SignalContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a stlParser.SignalContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def NUMBER(self):
            return self.getToken(stlParser.NUMBER, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSignalNumber" ):
                return visitor.visitSignalNumber(self)
            else:
                return visitor.visitChildren(self)


    class SignalMultExprContext(SignalContext):

        def __init__(self, parser, ctx:ParserRuleContext): # actually a stlParser.SignalContext
            super().__init__(parser)
            self.copyFrom(ctx)

        def signal(self, i:int=None):
            if i is None:
                return self.getTypedRuleContexts(stlParser.SignalContext)
            else:
                return self.getTypedRuleContext(stlParser.SignalContext,i)

        def MULT(self):
            return self.getToken(stlParser.MULT, 0)
        def DIV(self):
            return self.getToken(stlParser.DIV, 0)

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitSignalMultExpr" ):
                return visitor.visitSignalMultExpr(self)
            else:
                return visitor.visitChildren(self)



    def signal(self, _p:int=0):
    	_parentctx = self._ctx
    	_parentState = self.state
    	localctx = stlParser.SignalContext(self, self._ctx, _parentState)
    	_prevctx = localctx
    	_startState = 4
    	self.enterRecursionRule(localctx, 4, self.RULE_signal, _p)
    	self._la = 0 # Token type
    	try:
    		self.enterOuterAlt(localctx, 1)
    		self.state = 68
    		self._errHandler.sync(self)
    		token = self._input.LA(1)
    		if token in [stlParser.NUMBER]:
    			localctx = stlParser.SignalNumberContext(self, localctx)
    			self._ctx = localctx
    			_prevctx = localctx

    			self.state = 58
    			self.match(stlParser.NUMBER)
    		elif token in [stlParser.NAME]:
    			localctx = stlParser.SignalNameContext(self, localctx)
    			self._ctx = localctx
    			_prevctx = localctx
    			self.state = 59
    			self.match(stlParser.NAME)
    		elif token in [stlParser.LPAREN]:
    			localctx = stlParser.SignalParenthesisExprContext(self, localctx)
    			self._ctx = localctx
    			_prevctx = localctx
    			self.state = 60
    			self.match(stlParser.LPAREN)
    			self.state = 61
    			self.signal(0)
    			self.state = 62
    			self.match(stlParser.RPAREN)
    		elif token in [stlParser.VBAR]:
    			localctx = stlParser.SignalAbsExprContext(self, localctx)
    			self._ctx = localctx
    			_prevctx = localctx
    			self.state = 64
    			self.match(stlParser.VBAR)
    			self.state = 65
    			self.signal(0)
    			self.state = 66
    			self.match(stlParser.VBAR)
    		else:
    			raise NoViableAltException(self)

    		self._ctx.stop = self._input.LT(-1)
    		self.state = 78
    		self._errHandler.sync(self)
    		_alt = self._interp.adaptivePredict(self._input,8,self._ctx)
    		while _alt not in [2, ATN.INVALID_ALT_NUMBER]:
    			if _alt==1:
    				if self._parseListeners is not None:
    				    self.triggerExitRuleEvent()
    				_prevctx = localctx
    				self.state = 76
    				self._errHandler.sync(self)
    				la_ = self._interp.adaptivePredict(self._input,7,self._ctx)
    				if la_ == 1:
    					localctx = stlParser.SignalMultExprContext(self, stlParser.SignalContext(self, _parentctx, _parentState))
    					self.pushNewRecursionContext(localctx, _startState, self.RULE_signal)
    					self.state = 70
    					if not self.precpred(self._ctx, 3):
    					    from antlr4.error.Errors import FailedPredicateException
    					    raise FailedPredicateException(self, "self.precpred(self._ctx, 3)")
    					self.state = 71
    					_la = self._input.LA(1)
    					if _la not in [stlParser.MULT, stlParser.DIV]:
    						self._errHandler.recoverInline(self)
    					else:
    						self._errHandler.reportMatch(self)
    						self.consume()
    					self.state = 72
    					self.signal(4)
    				elif la_ == 2:
    					localctx = stlParser.SignalSumExprContext(self, stlParser.SignalContext(self, _parentctx, _parentState))
    					self.pushNewRecursionContext(localctx, _startState, self.RULE_signal)
    					self.state = 73
    					if not self.precpred(self._ctx, 2):
    					    from antlr4.error.Errors import FailedPredicateException
    					    raise FailedPredicateException(self, "self.precpred(self._ctx, 2)")
    					self.state = 74
    					_la = self._input.LA(1)
    					if _la not in [stlParser.PLUS, stlParser.MINUS]:
    						self._errHandler.recoverInline(self)
    					else:
    						self._errHandler.reportMatch(self)
    						self.consume()
    					self.state = 75
    					self.signal(3)
    			self.state = 80
    			self._errHandler.sync(self)
    			_alt = self._interp.adaptivePredict(self._input,8,self._ctx)

    	except RecognitionException as re:
    	    localctx.exception = re
    	    self._errHandler.reportError(self, re)
    	    self._errHandler.recover(self, re)
    	finally:
    		self.unrollRecursionContexts(_parentctx)
    	return localctx


    class IntervalContext(ParserRuleContext):
        __slots__ = 'parser'

        def __init__(self, parser, parent:ParserRuleContext=None, invokingState:int=-1):
            super().__init__(parent, invokingState)
            self.parser = parser

        def COMMA(self):
            return self.getToken(stlParser.COMMA, 0)

        def LPAREN(self):
            return self.getToken(stlParser.LPAREN, 0)

        def LBRACK(self):
            return self.getToken(stlParser.LBRACK, 0)

        def NUMBER(self, i:int=None):
            if i is None:
                return self.getTokens(stlParser.NUMBER)
            else:
                return self.getToken(stlParser.NUMBER, i)

        def INF(self, i:int=None):
            if i is None:
                return self.getTokens(stlParser.INF)
            else:
                return self.getToken(stlParser.INF, i)

        def RPAREN(self):
            return self.getToken(stlParser.RPAREN, 0)

        def RBRACK(self):
            return self.getToken(stlParser.RBRACK, 0)

        def getRuleIndex(self):
            return stlParser.RULE_interval

        def accept(self, visitor:ParseTreeVisitor):
            if hasattr( visitor, "visitInterval" ):
                return visitor.visitInterval(self)
            else:
                return visitor.visitChildren(self)




    def interval(self):

    	localctx = stlParser.IntervalContext(self, self._ctx, self.state)
    	self.enterRule(localctx, 6, self.RULE_interval)
    	self._la = 0 # Token type
    	try:
    		self.enterOuterAlt(localctx, 1)
    		self.state = 81
    		_la = self._input.LA(1)
    		if _la not in [stlParser.LPAREN, stlParser.LBRACK]:
    			self._errHandler.recoverInline(self)
    		else:
    			self._errHandler.reportMatch(self)
    			self.consume()
    		self.state = 82
    		_la = self._input.LA(1)
    		if _la not in [stlParser.INF, stlParser.NUMBER]:
    			self._errHandler.recoverInline(self)
    		else:
    			self._errHandler.reportMatch(self)
    			self.consume()
    		self.state = 83
    		self.match(stlParser.COMMA)
    		self.state = 84
    		_la = self._input.LA(1)
    		if _la not in [stlParser.INF, stlParser.NUMBER]:
    			self._errHandler.recoverInline(self)
    		else:
    			self._errHandler.reportMatch(self)
    			self.consume()
    		self.state = 85
    		_la = self._input.LA(1)
    		if _la not in [stlParser.RPAREN, stlParser.RBRACK]:
    			self._errHandler.recoverInline(self)
    		else:
    			self._errHandler.reportMatch(self)
    			self.consume()
    	except RecognitionException as re:
    	    localctx.exception = re
    	    self._errHandler.reportError(self, re)
    	    self._errHandler.recover(self, re)
    	finally:
    		self.exitRule()
    	return localctx



    def sempred(self, localctx:RuleContext, ruleIndex:int, predIndex:int):
    	if self._predicates is None:
    		self._predicates = {}
    	self._predicates[1] = self.phi_sempred
    	self._predicates[2] = self.signal_sempred
    	pred = self._predicates.get(ruleIndex, None)
    	if pred is None:
    		raise Exception(f"No predicate with index:{ruleIndex}")
    	else:
    		return pred(localctx, predIndex)

    def phi_sempred(self, localctx:PhiContext, predIndex:int):
            if predIndex == 0:
                return self.precpred(self._ctx, 6)
         

            if predIndex == 1:
                return self.precpred(self._ctx, 5)
         

            if predIndex == 2:
                return self.precpred(self._ctx, 4)
         

            if predIndex == 3:
                return self.precpred(self._ctx, 3)
         

    def signal_sempred(self, localctx:SignalContext, predIndex:int):
            if predIndex == 4:
                return self.precpred(self._ctx, 3)
         

            if predIndex == 5:
                return self.precpred(self._ctx, 2)
         




