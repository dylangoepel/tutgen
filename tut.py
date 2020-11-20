import sympy
from sympy import sympify as simp
from random import choice, random, shuffle
import toml
import sys
import concurrent.futures

class Problem():
    def __init__(self, concept, given, wanted, significant=2):
        self.concept, self.given, self.wanted, self.significant = concept, given, wanted, significant

    def locals(self):
        l = {}
        for v in self.given:
            l[str(self.concept.to_expr(v))] = self.given[v]
        return l

    def solve(self):
        solution = {}
        l = self.locals()
        for v in self.wanted:
            for law in self.concept.laws:
                sol = sympy.solve(law, self.concept.to_expr(v))
                if len(sol) == 0:
                    continue
                sol = sol[-1]
                if not(all([str(a) in l or a.is_number for a in sol.atoms()])):
                    continue
                ssol = str(self.concept.from_expr(sol))
                for x in self.given:
                    ssol = ssol.replace(x, "(" + str(self.given[x]) + ")")
                solution[v] = round(float(self.concept.to_expr(ssol)), self.significant)
        return solution

    def __str__(self):
        return "{}\n".format(self.concept.formatTask(self))
    
    def __eq__(self, other):
        if type(other) != type(self) or type(other.concept) != type(self.concept) or len(self.given) != len(other.given):
            return False

        return all([k in other.given and other.given[k] == self.given[k] for k in self.given])

class ProblemFormat():
    def __init__(self, concept, given, wanted):
        self.concept, self.given, self.wanted = concept, given, wanted

    def randomProblem(self, significant=2):
        given = {}
        for key in self.given:
            while True:
                given[key] = simp(int(random() * (10 ** significant))) /  (10 ** (significant - 1))
                if given[key] > 0:
                    break
        return Problem(self.concept, given, self.wanted, significant=significant)

    def __str__(self):
        return "{}: {} -> {}".format(self.concept, self.given, self.wanted)

class Concept():
    def __init__(self, name, **params):
        self.name = name
        self.variables = {}
        self.units = {}
        self.givenSentences = {}
        self.wantedSentences = {}
        self.initSentence = params["init"]
        for i, p in enumerate(params):
            if p in ["init", "laws"]:
                continue
            self.variables[p] = simp("x_" + str(i))
            self.units[p] = params[p][2]
            self.givenSentences[p] = params[p][0]
            self.wantedSentences[p] = params[p][1]
        self.laws = []
        for law in params["laws"]:
            self.add_law(law)

    def to_expr(self, formula):
        return simp(formula, locals=self.variables)

    def from_expr(self, expr):
        formula = str(expr)
        for key in self.variables:
            formula = formula.replace(str(self.variables[key]), key)
        return formula

    def add_law(self, equality):
        left, right = equality.split("=")
        func = self.to_expr(left) - self.to_expr(right)
        new = []
        new.append(func)
        for a in func.atoms():
            if a.is_number:
                continue
            for law in self.laws:
                if a not in law.atoms():
                    continue
                alternateForm = sympy.solve(law, a)
                new.append(func.subs(a, alternateForm))
        self.laws = [*self.laws, *new]

    def terms(self, var):
        results = []
        for law in self.laws:
            try:
                terms = sympy.solve(law, self.variables[var])
            except:
                continue
            results = [*results, *terms]
        return results

    def problem_setups(self, var):
        setups = []
        for term in self.terms(var):
            given = list(map(self.from_expr, filter(lambda x: not x.is_number and not x in constants, term.atoms())))
            setups.append(ProblemFormat(self, given, [var]))
        return setups

    def problem_formats(self):
        formats = []
        for var in self.variables:
            formats = [*formats, *self.problem_setups(var)]
        return formats

    def formatTask(self, problem):
        return "{} {} {}".format(
                self.initSentence,
                " ".join([self.givenSentences[v].format("$"+str(round(float(problem.given[v]), problem.significant)) + self.units[v] + "$") for v in problem.given]),
                " ".join([self.wantedSentences[v] for v in problem.wanted]),
                )

    def formatSolution(self, problem):
        solution = problem.solve()
        return "\n".join(["\[" + v + " = " + str(solution[v]) + self.units[v] +  "\]" for v in solution])

with open("phys.tut") as f:
    config = toml.loads(f.read())

print("[*] read config", file=sys.stderr)
concepts = []
for conc in config:
    concept = Concept(conc, **config[conc])
    concepts.append(concept)

print("[*] generate exercises", file=sys.stderr)
problems = []
for c in concepts:
    for f in c.problem_formats():
        formatProblems = []
        for i in range(2):
            while True:
                prob = f.randomProblem()
                if prob not in formatProblems:
                    break
            formatProblems.append(prob)
        problems = [*problems, *formatProblems]

shuffle(problems)

print("[*] generate solutions", file=sys.stderr)
futureSolutions = []
executor = concurrent.futures.ThreadPoolExecutor()
for prob in problems:
    futureSolutions.append(executor.submit(prob.concept.formatSolution, prob))

solutions = []
for i, f in enumerate(futureSolutions):
    solutions.append(f.result())
    print("[+] got {} solutions".format(i + 1), file=sys.stderr)
del executor, futureSolutions

print("[*] output exercises", file=sys.stderr)

print("\section{Aufgaben}")
for n, prob in enumerate(problems):
    print("[*] generating task {}".format(n + 1), file=sys.stderr)
    print("\subsubsection*{{Aufgabe {}}}".format(n + 1))
    print(prob)

print("[*] output solutions", file=sys.stderr)

print("\section{Lösungen}")
for n, s in enumerate(solutions):
    print("\subsubsection*{{Lösung zu Aufgabe {}}}".format(n + 1))
    print(s)
