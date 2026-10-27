"""
Static analysis: does this submission file contain an explicit `for` or
`while` statement anywhere (including inside helper functions the student
added)? This is a pure AST walk over the parsed source — the file is never
executed for this check, so a syntax error is the only way it can fail.

List/dict/set/generator comprehensions are NOT flagged: they compile to
different AST nodes (ast.comprehension inside ast.ListComp etc.), not
ast.For, and the assignment's "no explicit loops" wording targets the
statement form. If a comprehension is used to sneak in row-by-row work on
the big test case anyway, the timing check in sandbox.py catches that
separately — comprehensions over large arrays are still Python-level
iteration and will blow past TIME_LIMIT_BIG.
"""

import ast


class LoopFinder(ast.NodeVisitor):
    def __init__(self):
        self.violations = []  # list of (lineno, node_type)

    def visit_For(self, node):
        self.violations.append((node.lineno, "for"))
        self.generic_visit(node)

    def visit_While(self, node):
        self.violations.append((node.lineno, "while"))
        self.generic_visit(node)

    # ast.AsyncFor is extremely unlikely here but costs nothing to catch
    def visit_AsyncFor(self, node):
        self.violations.append((node.lineno, "async for"))
        self.generic_visit(node)


def check_no_loops(source_code):
    """
    Returns (ok, violations, parse_error).
      ok           -- True if no for/while found and the file parsed cleanly
      violations   -- list of (lineno, "for"|"while"|"async for")
      parse_error  -- str or None; if set, ok is always False and
                       violations is always empty (couldn't even parse it)
    """
    try:
        tree = ast.parse(source_code)
    except SyntaxError as e:
        return False, [], f"SyntaxError: {e}"

    finder = LoopFinder()
    finder.visit(tree)
    return (len(finder.violations) == 0), finder.violations, None
