from dataclasses import dataclass

from .core import Recipe

import re

class NixExporter:
    def recipe_id(self, r) -> str:
        ver_str = str(r.version).replace(".","_")
        return f"{r.name}_{ver_str}"

    def build_expression(self, recipe, recipes):
        return f"""buildPythonPackage {{
            pname="{recipe.name}";
            version="{recipe.version}";
        }}"""

    def format_expr(self, expr):
        # replace all multiple spaces
        # outside of strings by a single space
        # expr = re.sub(r"[\s]+", " ", expr)
        expr = re.sub(r'[\s]+(?=(?:[^"]*"[^"]*")*[^"]*$)', " ", expr)
        expr = expr.replace("{", "{\n").replace("}", "\n}").replace(";", ";\n")
        lines = []
        ident = 0
        pat = re.compile(r"[\s]+")
        for l in expr.split("\n"):
            lines.append(" "*ident + l)
            if l.endswith("{"):
                ident = ident + 1
            elif l.startswith("}"):
                ident = ident - 1
        expr = "\n".join(lines)
        return expr

    def expression(self, 
                env_recipes : dict[str, Recipe], 
                build_recipes : dict[str, Recipe]
            ) -> str:
        recipes = {}
        recipes.update(build_recipes)
        recipes.update(env_recipes)

        pkgsExpr = "\n".join([f"{r.name} = {self.build_expression(r, recipes)};" for r in env_recipes.values()])
        pkgsExpr = f"{{{pkgsExpr}}}"
        buildPkgsExpr = "\n".join([f"{r.name} = {self.build_expression(r, recipes)};" for r in build_recipes.values()])
        buildPkgsExpr = f"{{{buildPkgsExpr}}}"
        inputs = "{buildPythonPackage}"
        expr = f"""{{
            packages = {pkgsExpr};
            buildPackages = {buildPkgsExpr};
        }}"""
        expr = self.format_expr(expr)
        return f"{inputs}: {expr}"