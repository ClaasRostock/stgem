# Generated from stlParser.g4 by ANTLR 4.10.1
from antlr4 import *
if __name__ is not None and "." in __name__:
    from .stlParser import stlParser
else:
    from stlParser import stlParser

from stl.robustness import *

# This class defines a complete generic visitor for a parse tree produced by stlParser.

class stlParserVisitor(ParseTreeVisitor):

    # Visit a parse tree produced by stlParser#stlSpecification.
    def visitStlSpecification(self, ctx:stlParser.StlSpecificationContext):
        return self.visit(ctx.getRuleContext().getChild(0))


    # Visit a parse tree produced by stlParser#predicateExpr.
    def visitPredicateExpr(self, ctx:stlParser.PredicateExprContext):
        phi1 = self.visit(ctx.getRuleContext().getChild(0))
        operator = ctx.getRuleContext().getChild(1).getText()
        phi2 = self.visit(ctx.getRuleContext().getChild(2))
        if operator == "<=":
            return LessThan(phi1, phi2)
        elif operator == ">=":
            return GreaterThan(phi1, phi2)
        elif operator == "<":
            return StrictlyLessThan(phi1, phi2)
        elif operator == ">":
            return StrictlyGreaterThan(phi1, phi2)
        elif operator == "==":
            return Equals(phi1, phi2)
        else: # !=
            return Not(Equals(phi1, phi2))


    # Visit a parse tree produced by stlParser#signalExpr.
    def visitSignalExpr(self, ctx:stlParser.SignalExprContext):
        return self.visit(ctx.getRuleContext().getChild(0))


    # Visit a parse tree produced by stlParser#opFutureExpr.
    def visitOpFutureExpr(self, ctx:stlParser.OpFutureExprContext):
        if ctx.getRuleContext().getChildCount() == 2:
            raise NotImplementedError("Eventually not supported without specifying an interval.")
        elif ctx.getRuleContext().getChildCount() == 3:
            phi = self.visit(ctx.getRuleContext().getChild(2))
            interval = self.visit(ctx.getRuleContext().getChild(1))
        return Finally(interval[0], interval[1], phi)


    # Visit a parse tree produced by stlParser#parenPhiExpr.
    def visitParenPhiExpr(self, ctx:stlParser.ParenPhiExprContext):
        child = self.visit(ctx.getRuleContext().getChild(1))
        # We keep track of parenthesized expressions in order to work with
        # potential And nonassociativity.
        child.parenthesized = True
        return child


    # Visit a parse tree produced by stlParser#opUntilExpr.
    def visitOpUntilExpr(self, ctx:stlParser.OpUntilExprContext):
        phi1 = self.visit(ctx.getRuleContext().getChild(0))
        if ctx.getRuleContext().getChildCount() == 3:
            raise NotImplementedError("Until not supported without specifying an interval.")
        elif ctx.getRuleContext().getChildCount() == 4: # Optional interval
            phi2 = self.visit(ctx.getRuleContext().getChild(3))
            interval = self.visit(ctx.getRuleContext().getChild(2))
            return Until(interval[0], interval[1], phi1, phi2)


    # Visit a parse tree produced by stlParser#opGloballyExpr.
    def visitOpGloballyExpr(self, ctx:stlParser.OpGloballyExprContext):
        if ctx.getRuleContext().getChildCount() == 2:
            raise NotImplementedError("Global not supported without specifying an interval.")
        elif ctx.getRuleContext().getChildCount() == 3:
            phi = self.visit(ctx.getRuleContext().getChild(2))
            interval = self.visit(ctx.getRuleContext().getChild(1))
        return Global(interval[0], interval[1], phi)


    # Visit a parse tree produced by stlParser#opAndExpr.
    def visitOpAndExpr(self, ctx:stlParser.OpAndExprContext):
        """
        We need to be a bit clever here as antlr does not seem to support what
        we want (maybe it does, but I could not figure it out). Consider two
        formulas X = 'A and B and C' and Y = 'A and (B and C)'. Since And is
        possibly nonassociative (for the alternative robustness functions),
        these are not the same formula to us. We want to return And(A, B, C)
        for X and And(A, And(B, C)) for Y. In order to accomplish this, we keep
        track which parts of the formula are in parentheses (see
        visitParenPhiExpr).

        And yes, you could think that 'A and B and C' would visit this method
        with getChildCount() = 5, but it does not. Hence the workarounds.
        """

        phi1 = self.visit(ctx.getRuleContext().getChild(0))
        phi2 = self.visit(ctx.getRuleContext().getChild(2))
        formulas = []
        if isinstance(phi1, And) and not hasattr(phi1, "parenthesized"):
            formulas += phi1.formulas
        else:
            formulas.append(phi1)
        if isinstance(phi2, And) and not hasattr(phi2, "parenthesized"):
            formulas += phi2.formulas
        else:
            formulas.append(phi2)

        nu = self.nu if hasattr(self, "nu") else None
        return And(*formulas, nu=nu)


    # Visit a parse tree produced by stlParser#opNextExpr.
    def visitOpNextExpr(self, ctx:stlParser.OpNextExprContext):
        return Next(self.visit(ctx.getRuleContext().getChild(1)))


    # Visit a parse tree produced by stlParser#opPropExpr.
    def visitOpPropExpr(self, ctx:stlParser.OpPropExprContext):
        phi1 = self.visit(ctx.getRuleContext().getChild(0))
        operator = ctx.getRuleContext().getChild(1).getText()
        phi2 = self.visit(ctx.getRuleContext().getChild(2))
        if operator in ["implies", "->"]:
            return Implication(phi1, phi2)
        elif operator in ["iff", "<->"]:
            raise NotImplementedError("Equivalence not implemented.")

    # Visit a parse tree produced by stlParser#opOrExpr.
    def visitOpOrExpr(self, ctx:stlParser.OpOrExprContext):
        # See visitOpAndExpr for explanation.
        phi1 = self.visit(ctx.getRuleContext().getChild(0))
        phi2 = self.visit(ctx.getRuleContext().getChild(2))
        formulas = []
        if isinstance(phi1, Or) and not hasattr(phi1, "parenthesized"):
            formulas += phi1.formulas
        else:
            formulas.append(phi1)
        if isinstance(phi2, Or) and not hasattr(phi2, "parenthesized"):
            formulas += phi2.formulas
        else:
            formulas.append(phi2)

        nu = self.nu if hasattr(self, "nu") else None
        return Or(*formulas, nu=nu)


    # Visit a parse tree produced by stlParser#opNegExpr.
    def visitOpNegExpr(self, ctx:stlParser.OpNegExprContext):
        phi = self.visit(ctx.getRuleContext().getChild(1))
        return Not(phi)


    # Visit a parse tree produced by stlParser#signalParenthesisExpr.
    def visitSignalParenthesisExpr(self, ctx:stlParser.SignalParenthesisExprContext):
        return self.visit(ctx.getRuleContext().getChild(1))


    # Visit a parse tree produced by stlParser#signalName.
    def visitSignalName(self, ctx:stlParser.SignalNameContext):
        name = ctx.getText()
        if hasattr(self, "ranges") and self.ranges is not None:
            try:
                range = self.ranges[name]
            except KeyError:
                range = None
        else:
            range = None
        return Signal(name, range=range)


    # Visit a parse tree produced by stlParser#signalAbsExpr.
    def visitSignalAbsExpr(self, ctx:stlParser.SignalAbsExprContext):
        return Abs(self.visit(ctx.getRuleContext().getChild(1)))


    # Visit a parse tree produced by stlParser#signalSumExpr.
    def visitSignalSumExpr(self, ctx:stlParser.SignalSumExprContext):
        signal1 = self.visit(ctx.getRuleContext().getChild(0))
        operator = ctx.getRuleContext().getChild(1).getText()
        signal2 = self.visit(ctx.getRuleContext().getChild(2))
        if operator == "+":
            return Sum(signal1, signal2)
        elif operator == "-":
            return Subtract(signal1, signal2)


    # Visit a parse tree produced by stlParser#signalNumber.
    def visitSignalNumber(self, ctx:stlParser.SignalNumberContext):
        value = float(ctx.getText())
        return Constant(value)


    # Visit a parse tree produced by stlParser#signalMultExpr.
    def visitSignalMultExpr(self, ctx:stlParser.SignalMultExprContext):
        signal1 = self.visit(ctx.getRuleContext().getChild(0))
        operator = ctx.getRuleContext().getChild(1).getText()
        signal2 = self.visit(ctx.getRuleContext().getChild(2))
        if operator == "*":
            return Multiply(signal1, signal2)
        elif operator == "/":
            return Divide(signal1, signal2)


    # Visit a parse tree produced by stlParser#interval.
    def visitInterval(self, ctx:stlParser.IntervalContext):
        A = float(ctx.getRuleContext().getChild(1).getText())
        B = float(ctx.getRuleContext().getChild(3).getText())
        return [A, B]



del stlParser
